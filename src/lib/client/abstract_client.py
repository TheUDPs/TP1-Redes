from abc import abstractmethod
from socket import socket as Socket
from socket import AF_INET, SOCK_DGRAM, SHUT_RDWR
import sys
from io import StringIO
from multiprocessing import Value
from ctypes import c_bool
from threading import Event, Thread

from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.client.protocol import ClientProtocol
from lib.common.address import Address
from lib.common.constants import (
    USE_ANY_AVAILABLE_PORT,
    USE_CURRENT_HOST,
    SOCKET_CONNECTION_LOST_TIMEOUT,
    GO_BACK_N_PROTOCOL_TYPE,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_ack_number import InvalidAckNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin_nor_ack import MessageNotFinNorAck
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.logger import Logger
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_saw import SocketSaw
from lib.common.wait_for_quit import wait_for_quit


class Client:
    def __init__(self, logger: Logger, host: str, port: int, protocol: str):
        self.logger: Logger = logger
        self.server_host: str = host
        self.server_port: int = port

        self.server_address: Address = Address(self.server_host, self.server_port)

        raw_socket: Socket = Socket(AF_INET, SOCK_DGRAM)
        raw_socket.bind((USE_CURRENT_HOST, USE_ANY_AVAILABLE_PORT))
        sockname: tuple[str, int] = raw_socket.getsockname()
        raw_socket.settimeout(SOCKET_CONNECTION_LOST_TIMEOUT)
        self.my_address: Address = Address(sockname[0], sockname[1])

        self.socket: SocketSaw = SocketSaw(raw_socket, self.logger)

        self.protocol = ClientProtocol(
            self.logger, self.socket, self.server_address, self.my_address, protocol
        )

        self.stopped = False
        self.sequence_number: SequenceNumber = SequenceNumber(
            0, self.protocol.protocol_version
        )

        self.ack_number = None
        if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            self.ack_number = SequenceNumber(0, self.protocol.protocol_version)

        self.logger.debug(f"Running on {self.my_address}")

    def handshake(self) -> Address:
        self.logger.debug("Starting handshake")
        self.logger.debug(f"Requesting connection to {self.server_address}")

        self.protocol.request_connection(self.sequence_number, self.ack_number)

        try:
            server_address = self.protocol.wait_for_connection_request_answer(
                self.sequence_number,
                self.ack_number,
                exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
            )
        except (UnexpectedFinMessage, MessageIsNotAck):
            self.logger.error("Protocol mismatch")
            raise ConnectionRefused()

        self.logger.debug("Connection request accepted")
        self.logger.debug(f"Completing handshake with {self.server_address}")

        return server_address

    def client_start(self, should_stop_event: Event) -> None:
        self.logger.debug("UDP socket ready")

        try:
            if not should_stop_event.is_set():
                server_address = self.handshake()
                self.perform_operation(server_address)
        except ConnectionRefused as e:
            self.logger.error(f"{e.message}")
        except (ConnectionLost, SocketShutdown):
            self.logger.error("Connection closed")
        finally:
            should_stop_event.set()

    def stop(
        self,
        client_start_thread: Thread,
        wait_for_quit_thread: Thread,
        quited: Value,  # type: ignore
    ) -> None:
        if self.stopped:
            return

        self.logger.info("Stopping")

        try:
            self.socket.shutdown(SHUT_RDWR)
        except OSError:
            try:
                self.socket.close()
            except OSError:
                pass
        finally:
            client_start_thread.join()
            if not quited.value:
                sys.stdin = StringIO("q\n")
                sys.stdin.flush()
                self.logger.force_info("Press Enter to finish")

            wait_for_quit_thread.join()
            self.logger.info("Client shutdown")
            self.stopped = True

    @abstractmethod
    def perform_operation(self, server_address: Address):
        pass

    def send_operation_intention(self, op_code: int, server_address: Address) -> None:
        try:
            self.logger.debug("Sending operation intention")

            self.sequence_number.step()

            if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
                self.ack_number.step()

            self.protocol.send_operation_intention(
                self.sequence_number, self.ack_number, op_code
            )

            self.logger.debug("Waiting for operation confirmation")
            self.protocol.wait_for_operation_confirmation(
                self.sequence_number,
                self.ack_number,
                exceptions_to_let_through=[UnexpectedFinMessage],
            )
            self.logger.debug("Operation accepted")

            # Update server address to update the server connection's port
            self.server_address: Address = server_address
            self.protocol.update_server_address(server_address)

            self.logger.debug("Connection established")
        except UnexpectedFinMessage:
            self.handle_connection_finalization()

    def handle_connection_finalization(self):
        try:
            self.logger.debug("Connection finalization received. Confirming it")
            self.protocol.send_ack(self.sequence_number, self.ack_number)
            self.logger.debug("Sending own connection finalization")
            self.protocol.send_fin(self.sequence_number, self.ack_number)

            self.sequence_number.step()
            try:
                self.protocol.wait_for_fin_or_ack(
                    self.sequence_number,
                    self.ack_number,
                    exceptions_to_let_through=[ConnectionLost],
                )
            except (ConnectionLost, MessageIsNotAck):
                pass

            self.logger.info("Connection closed")
        except SocketShutdown:
            self.logger.info("Connection closed")

    def initiate_close_connection(self):
        try:
            self.logger.debug("Waiting for confirmation of last packet")
            self.protocol.wait_for_fin_or_ack(self.sequence_number, self.ack_number)

            self.logger.force_info("Upload completed")
            self.logger.debug("Received connection finalization from server")
            self.sequence_number.step()
            self.protocol.send_ack(self.sequence_number, self.ack_number)
        except (MessageIsNotAck, MessageNotFinNorAck, InvalidAckNumber):
            self.logger.debug("Connection closed")

    def run(self) -> None:
        self.logger.info("Client started for upload")
        self.logger.debug(f"Protocol: {self.protocol.protocol_version}")

        should_stop_event: Event = Event()
        client_start_thread: Thread = Thread(
            target=self.client_start, args=(should_stop_event,)
        )
        client_start_thread.start()

        quited: Value = Value(c_bool, False)  # type: ignore

        wait_for_quit_thread = Thread(
            target=wait_for_quit, args=(should_stop_event, quited)
        )
        wait_for_quit_thread.start()

        should_stop_event.wait()

        self.stop(client_start_thread, wait_for_quit_thread, quited)

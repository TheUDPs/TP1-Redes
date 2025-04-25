from socket import socket as Socket
from socket import AF_INET, SOCK_DGRAM, SHUT_RDWR
import sys
from io import StringIO
from multiprocessing import Value
from ctypes import c_bool
from threading import Event, Thread

from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.client.protocol_interface import ClientProtocol
from lib.common.address import Address
from lib.common.constants import USE_ANY_AVAILABLE_PORT
from lib.common.logger import Logger
from lib.common.wait_for_quit import wait_for_quit

SOCKET_TIMEOUT = 30

USE_CURRENT_HOST = ""


class ClientUpload:
    def __init__(
        self, logger: Logger, host: str, port: int, src: str, name: str, protocol: str
    ):
        self.logger: Logger = logger
        self.server_host: str = host
        self.server_port: int = port
        self.src_filepath: str = src
        self.final_filename: str = name

        self.server_address: Address = Address(self.server_host, self.server_port)

        self.socket: Socket = Socket(AF_INET, SOCK_DGRAM)
        self.socket.bind((USE_CURRENT_HOST, USE_ANY_AVAILABLE_PORT))
        sockname: tuple[str, int] = self.socket.getsockname()
        self.my_address: Address = Address(sockname[0], sockname[1])
        self.socket.settimeout(SOCKET_TIMEOUT)

        self.protocol = ClientProtocol(
            self.logger, self.socket, self.server_address, self.my_address, protocol
        )

        self.stopped = False

        self.logger.debug(f"Running on {self.my_address}")

    def handshake(self) -> None:
        self.logger.debug("Starting handshake")
        self.logger.debug("Requesting connection")
        sequence_number = 0
        self.protocol.request_connection(sequence_number)
        server_address = self.protocol.wait_for_connection_request_answer(
            sequence_number
        )
        self.logger.debug("Connection request accepted")
        # Update server address to update the server connection's port
        self.server_address: Address = server_address
        self.protocol.update_server_address(server_address)

        sequence_number = 1
        self.protocol.send_hanshake_completion(sequence_number)
        self.logger.debug("Connection established")

    def client_start(self, should_stop_event: Event) -> None:
        self.logger.debug("UDP socket ready")

        try:
            if not should_stop_event.is_set():
                self.handshake()
        except ConnectionRefused as e:
            self.logger.error(e.message)
        finally:
            should_stop_event.set()

    def stop(
        self, client_start_thread: Thread, wait_for_quit_thread: Thread, quited: Value
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
                self.logger.info("Press Enter to finish")

            wait_for_quit_thread.join()
            self.logger.info("Client shutdown")
            self.stopped = True

    def run(self) -> None:
        self.logger.info("Client started for upload")
        self.logger.debug(f"Protocol: {self.protocol.protocol_version}")

        should_stop_event: Event = Event()
        client_start_thread: Thread = Thread(
            target=self.client_start, args=(should_stop_event,)
        )
        client_start_thread.start()

        quited: Value = Value(c_bool, False)

        wait_for_quit_thread = Thread(
            target=wait_for_quit, args=(should_stop_event, quited)
        )
        wait_for_quit_thread.start()

        should_stop_event.wait()

        self.stop(client_start_thread, wait_for_quit_thread, quited)

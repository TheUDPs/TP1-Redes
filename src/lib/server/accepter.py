from threading import Thread
from socket import socket as Socket
from socket import AF_INET, SOCK_DGRAM, SHUT_RDWR
from socket import timeout as SocketTimeout

from lib.common.address import Address
from lib.common.constants import USE_ANY_AVAILABLE_PORT, GO_BACK_N_PROTOCOL_TYPE
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_syn import MessageIsNotSyn
from lib.common.logger import CoolLogger
from lib.common.packet.packet import Packet
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_saw import SocketSaw
from lib.server.accepter_protocol import AccepterProtocol
from lib.server.client_manager import ClientManager
from lib.server.client_pool import ClientPool
from lib.server.exceptions.cannot_bind_socket import CannotBindSocket
from lib.server.exceptions.client_already_connected import ClientAlreadyConnected
from lib.server.exceptions.protocol_mismatch import ProtocolMismatch
from lib.common.file_handler import FileHandler
from lib.server.protocol import (
    MissingClientAddress,
    SocketShutdown,
)


class Accepter:
    def __init__(
            self,
            adress: Address,
            protocol: str,
            logger,
            file_handler: FileHandler):
        self.host: str = adress.host
        self.port: int = adress.port
        self.adress: Address = adress
        self.logger: CoolLogger = logger
        self.logger.set_prefix("[ACCEP]")

        self.file_handler: FileHandler = file_handler

        self.is_alive: bool = True
        self.thread_context: Thread = Thread(target=self.run)

        self.clients: ClientPool = ClientPool()
        self.client_manager: ClientManager = ClientManager(
            self.logger, protocol, self.clients
        )

        welcoming_socket: Socket = Socket(AF_INET, SOCK_DGRAM)

        try:
            welcoming_socket.bind(self.adress.to_tuple())
        except OSError as e:
            self.logger.error(
                f"Cannot bind socket to port {
                    self.port}. {e}")
            raise CannotBindSocket()

        self.welcoming_socket: SocketSaw = SocketSaw(
            welcoming_socket, self.logger)

        self.protocol: AccepterProtocol = AccepterProtocol(
            self.logger, self.welcoming_socket, self.adress, protocol, self.clients)

    def run(self) -> None:
        while self.is_alive:
            try:
                self.accept()

            except (ConnectionLost, SocketTimeout):
                self.logger.warn("Connection lost")
                continue

    def accept(self) -> None:
        client_address = None

        try:
            self.logger.debug(f"Waiting for connection on {self.adress}")
            self.welcoming_socket.reset_state()
            packet, packet_type, client_address = self.protocol.accept_connection()

            packet, connection_socket, connection_address = self.handshake(
                packet, client_address
            )
            self.client_manager.add_client(
                connection_socket,
                connection_address,
                client_address,
                self.file_handler,
                packet,
            )
            self.logger.set_prefix("[ACCEP]")

        except MissingClientAddress:
            self.logger.debug(
                "Client address not found, discarding message")

        except ClientAlreadyConnected:
            self.logger.debug(
                "Client is already connect, should not be talking to the welcomming socket"
            )

        except ProtocolMismatch:
            self.logger.info(
                f"Rejecting client {client_address} due to protocol mismatch, expected {
                    self.protocol.protocol_version}")

        except (MessageIsNotSyn, MessageIsNotSyn, MessageIsNotAck) as e:
            self.logger.debug(f"{e.message}")

        except SocketShutdown:
            self.logger.warn("Socket shutdown")
            self.stop()

    def handshake(
        self, packet: Packet, client_address: Address
    ) -> tuple[Packet, SocketSaw, Address]:
        if self.clients.is_client_connected(client_address):
            raise ClientAlreadyConnected()

        if packet.protocol != self.protocol.protocol_version:
            self.protocol.reject_connection(packet, client_address)
            raise ProtocolMismatch()

        connection_socket_raw: Socket = Socket(AF_INET, SOCK_DGRAM)
        connection_socket_raw.bind((self.host, USE_ANY_AVAILABLE_PORT))
        connection_sockname: tuple[str,
                                   int] = connection_socket_raw.getsockname()
        connection_address: Address = Address(
            connection_sockname[0], connection_sockname[1]
        )
        connection_socket: SocketSaw = SocketSaw(
            connection_socket_raw, self.logger)

        self.logger.debug(f"Accepting connection for {client_address}")

        sequence_number = SequenceNumber(
            packet.sequence_number, packet.protocol)
        ack_number = (
            SequenceNumber(packet.ack_number, self.protocol.protocol_version)
            if packet.protocol == GO_BACK_N_PROTOCOL_TYPE
            else None
        )

        self.protocol.send_connection_accepted(
            sequence_number, ack_number, client_address, connection_address
        )

        if ack_number is not None:
            ack_number.step()

        packet, packet_type, _ = self.protocol.expect_handshake_completion(
            ack_number)
        self.logger.debug(f"Transferred to {connection_address}")
        self.logger.debug("Handhsake completed")

        return (
            packet,
            connection_socket,
            connection_address,
        )

    def stop(self) -> None:
        self.is_alive = False

    def start(self) -> None:
        self.thread_context.start()

    def join(self) -> None:
        try:
            self.stop()
            self.client_manager.kill_all()
            self.welcoming_socket.shutdown(SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.thread_context.join()

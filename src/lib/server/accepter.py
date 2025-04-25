from threading import Thread
import socket

from lib.common.address import Address
from lib.common.logger import Logger
from lib.common.packet import Packet
from lib.server.client_manager import ClientManager
from lib.server.exceptions.client_already_connected import ClientAlreadyConnected
from lib.server.exceptions.protocol_mismatch import ProtocolMismatch
from lib.server.protocol_interface import ServerProtocol, MissingClientAddress

BUFFER_SIZE = 4028
USE_ANY_AVAILABLE_PORT = 0


class Accepter:
    def __init__(self, adress: Address, protocol: str, logger):
        self.host: str = adress.host
        self.port: int = adress.port
        self.adress: Address = adress
        self.logger: Logger = logger

        self.is_alive: bool = True
        self.thread_context: Thread = Thread(target=self.run)

        self.welcoming_socket: socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.welcoming_socket.bind(self.adress.to_tuple())
        self.protocol: ServerProtocol = ServerProtocol(
            self.logger, self.welcoming_socket, self.adress, protocol
        )

        self.client_manager: ClientManager = ClientManager(self.logger, protocol)

    def run(self) -> None:
        while self.is_alive:
            try:
                self.accept()
            except socket.timeout:
                self.logger.warning("Socket timed out")
                continue

    def accept(self) -> None:
        client_address = None

        try:
            self.logger.debug("Waiting for connection")
            packet, client_address = self.protocol.accept_connection()
            connection_socket, connection_address = self.handshake(
                packet, client_address
            )
            self.client_manager.add_client(connection_socket, connection_address)

        except MissingClientAddress:
            self.logger.debug("Client address not found, discarding message")

        except ClientAlreadyConnected:
            self.logger.debug(
                "Client is already connect, should not be talking to the welcomming socket"
            )

        except ProtocolMismatch:
            self.logger.info(
                f"Rejecting client {client_address} due to protocol mismatch, expected {self.protocol}"
            )

    def handshake(
        self, packet: Packet, client_address: Address
    ) -> tuple[socket, Address]:
        if self.client_manager.is_client_connected(client_address):
            raise ClientAlreadyConnected()

        if packet.protocol != self.protocol.protocol_version:
            self.protocol.reject_connection(packet, client_address)
            raise ProtocolMismatch()

        connection_socket: socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        connection_socket.bind((self.host, USE_ANY_AVAILABLE_PORT))
        connection_sockname: tuple[str, int] = connection_socket.getsockname()
        connection_address: Address = Address(
            connection_sockname[0], connection_sockname[1]
        )

        self.protocol.send_connection_accepted(
            packet, client_address, connection_address
        )
        return connection_socket, connection_address

    def stop(self) -> None:
        self.is_alive = False

    def start(self) -> None:
        self.thread_context.start()

    def join(self) -> None:
        try:
            self.stop()
            self.welcoming_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.thread_context.join()

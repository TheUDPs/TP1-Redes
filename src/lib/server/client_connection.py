from socket import socket, SHUT_RDWR
from threading import Thread

from lib.common.address import Address
from lib.common.logger import Logger
from lib.server.client_pool import ClientPool

from lib.server.protocol_interface import (
    ServerProtocol,
    MissingClientAddress,
    BadFlagsForHandshake,
    SocketShutdown,
)
from enum import Enum


class ConnectionState(Enum):
    HANDHSAKE = 1
    HANDHSAKE_FINISHED = 2
    READY_TO_TRANSMIT = 3
    READY_TO_RECEIVE = 4
    BAD_STATE = 99


class ClientConnection:
    def __init__(
        self,
        connection_socket: socket,
        connection_address: Address,
        protocol: str,
        logger: Logger,
    ):
        self.socket: socket = connection_socket
        self.address: Address = connection_address
        self.logger: Logger = logger
        self.protocol: ServerProtocol = ServerProtocol(
            self.logger, self.socket, self.address, protocol, ClientPool()
        )
        self.state: ConnectionState = ConnectionState.HANDHSAKE
        self.run_thread = Thread(target=self.run)

    def expect_handshake_completion(self) -> None:
        self.logger.debug("Waiting for handshake completion")
        try:
            self.protocol.expect_handshake_completion()
            self.state = ConnectionState.HANDHSAKE_FINISHED
            self.logger.debug("Handhsake completed")
        except SocketShutdown:
            self.logger.debug("Client connection socket shutdowned")
        except (MissingClientAddress, BadFlagsForHandshake) as e:
            self.state = ConnectionState.BAD_STATE
            raise e

    def run(self):
        self.expect_handshake_completion()

    def start(self):
        self.run_thread.start()

    def kill(self):
        try:
            self.socket.shutdown(SHUT_RDWR)
        except OSError:
            try:
                self.socket.close()
            except OSError:
                pass
        finally:
            self.run_thread.join()

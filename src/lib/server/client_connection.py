from socket import socket
from lib.common.address import Address
from lib.common.logger import Logger

from lib.server.protocol_interface import (
    ServerProtocol,
    MissingClientAddress,
    BadFlagsForHandshake,
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
            self.logger, self.socket, self.address, protocol
        )
        self.state: ConnectionState = ConnectionState.HANDHSAKE

    def expect_handshake_completion(self) -> None:
        self.logger.debug("Waiting for handshake completion")
        try:
            self.protocol.expect_handshake_completion()
            self.state = ConnectionState.HANDHSAKE_FINISHED

        except (MissingClientAddress, BadFlagsForHandshake) as e:
            self.state = ConnectionState.BAD_STATE
            raise e

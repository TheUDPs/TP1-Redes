from socket import socket

from lib.common.address import Address
from lib.common.logger import Logger
from lib.server.client_connection import ClientConnection


class ClientManager:
    def __init__(self, logger: Logger, protocol: str):
        self.clients = {}
        self.logger: Logger = logger
        self.protocol: str = protocol

    def add_client(
        self, connection_socket: socket, connection_address: Address
    ) -> None:
        new_connection: ClientConnection = ClientConnection(
            connection_socket, connection_address, self.protocol, self.logger
        )
        self.clients[connection_address.to_combined()] = new_connection
        new_connection.start()

    def is_client_connected(self, client_address: Address) -> bool:
        return client_address.to_combined() in self.clients

    def kill_all(self):
        for connection in self.clients.values():
            connection.kill()

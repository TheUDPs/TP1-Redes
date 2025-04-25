from socket import socket

from lib.common.address import Address
from lib.common.logger import Logger
from lib.server.client_connection import ClientConnection
from lib.server.client_pool import ClientPool


class ClientManager:
    def __init__(self, logger: Logger, protocol: str, client_pool: ClientPool):
        self.clients: ClientPool = client_pool
        self.logger: Logger = logger
        self.protocol: str = protocol

    def add_client(
        self, connection_socket: socket, connection_address: Address
    ) -> None:
        new_connection: ClientConnection = ClientConnection(
            connection_socket, connection_address, self.protocol, self.logger
        )
        self.clients.add(key=connection_address.to_combined(), value=new_connection)
        new_connection.start()

    def kill_all(self):
        for connection in self.clients.values():
            connection.kill()

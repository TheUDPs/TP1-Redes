from lib.common.address import Address
from lib.common.logger import Logger
from lib.common.socket_saw import SocketSaw
from lib.server.client_connection import ClientConnection
from lib.server.client_pool import ClientPool
from lib.server.file_handler import FileHandler


class ClientManager:
    def __init__(self, logger: Logger, protocol: str, client_pool: ClientPool):
        self.clients: ClientPool = client_pool
        self.logger: Logger = logger
        self.protocol: str = protocol

    def add_client(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        file_handler: FileHandler,
    ) -> None:
        self.rip_finished_clients()

        new_connection: ClientConnection = ClientConnection(
            connection_socket,
            connection_address,
            client_address,
            self.protocol,
            self.logger,
            file_handler,
        )
        self.clients.add(key=connection_address.to_combined(), value=new_connection)
        new_connection.start()

    def rip_finished_clients(self):
        killed_clients = []

        for connection in self.clients.values():
            if connection.is_done_and_ready_to_die():
                connection.kill()
                killed_clients.append(connection.address)

        for killed_client in killed_clients:
            self.clients.remove(killed_client)

    def kill_all(self):
        for connection in self.clients.values():
            connection.kill()

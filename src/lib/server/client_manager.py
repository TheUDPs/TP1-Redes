from lib.common.address import Address
from lib.common.constants import STOP_AND_WAIT_PROTOCOL_TYPE
from lib.common.logger import CoolLogger
from lib.common.packet.packet import Packet
from lib.common.socket_saw import SocketSaw
from lib.server.client_connection.abstract_client_connection import ClientConnection
from lib.server.client_connection.client_connection_gbn import ClientConnectionGbn
from lib.server.client_connection.client_connection_saw import ClientConnectionSaw
from lib.server.client_pool import ClientPool
from lib.common.file_handler import FileHandler


class ClientManager:
    def __init__(
            self,
            logger: CoolLogger,
            protocol: str,
            client_pool: ClientPool):
        self.clients: ClientPool = client_pool
        self.logger: CoolLogger = logger
        self.protocol: str = protocol

    def add_client(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        file_handler: FileHandler,
        packet: Packet,
    ) -> None:
        self.rip_finished_clients()

        client_connection: ClientConnection = self.create_connection(
            connection_socket,
            connection_address,
            client_address,
            file_handler,
            packet,
        )
        self.clients.add(key=connection_address.to_combined(),
                         value=client_connection)
        client_connection.start()

    def rip_finished_clients(self):
        killed_clients = []

        for connection in self.clients.values():
            if connection.is_ready_to_die():
                connection.kill()
                killed_clients.append(connection.address)

        for killed_client in killed_clients:
            self.logger.debug(
                f"Collected finished connection: {
                    killed_client.to_combined()}")
            self.clients.remove(killed_client)

    def kill_all(self):
        for connection in self.clients.values():
            connection.kill()

    def create_connection(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        file_handler: FileHandler,
        packet: Packet,
    ) -> ClientConnection:
        new_logger = CoolLogger(self.logger.current_level)
        new_logger.set_prefix("")
        if self.protocol == STOP_AND_WAIT_PROTOCOL_TYPE:
            new_connection: ClientConnectionSaw = ClientConnectionSaw(
                connection_socket,
                connection_address,
                client_address,
                self.protocol,
                new_logger,
                file_handler,
                packet,
            )
        else:  # if self.protocol == GO_BACK_N_PROTOCOL_TYPE:
            new_connection: ClientConnectionGbn = ClientConnectionGbn(
                connection_socket,
                connection_address,
                client_address,
                self.protocol,
                new_logger,
                file_handler,
                packet,
            )

        return new_connection

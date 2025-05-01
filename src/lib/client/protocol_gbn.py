from lib.common.address import Address
from lib.common.logger import Logger
from lib.common.socket_gbn import SocketGbn


class ClientProtocolGbn:
    def __init__(
        self,
        logger: Logger,
        client_socket: SocketGbn,
        server_address: Address,
        my_address: Address,
        protocol_version: str,
    ):
        self.logger: Logger = logger
        self.socket: SocketGbn = client_socket
        self.server_host: str = server_address.host
        self.server_port: int = server_address.port
        self.server_address: Address = server_address
        self.my_address: Address = my_address
        self.protocol_version: str = protocol_version

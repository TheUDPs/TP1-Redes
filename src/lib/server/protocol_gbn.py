from lib.common.address import Address
from lib.common.logger import Logger
from lib.common.socket_gbn import SocketGbn
from lib.common.socket_saw import SocketSaw
from lib.server.client_pool import ClientPool


class ServerProtocolGbn:
    def __init__(
        self,
        logger: Logger,
        socket: SocketGbn,
        address: Address,
        protocol_version: str,
        clients: ClientPool,
    ):
        self.logger: Logger = logger
        self.socket: SocketSaw = socket
        self.host: str = address.host
        self.port: int = address.port
        self.address: Address = address
        self.protocol_version: str = protocol_version
        self.clients: ClientPool = clients

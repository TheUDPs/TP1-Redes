from socket import socket as Socket
from socket import timeout as SocketTimeout

from lib.common.address import Address
from lib.common.constants import (
    SOCKET_RETRANSMIT_WINDOW_TIMEOUT,
)
from lib.common.exceptions.retransmission_needed import RetransmissionNeeded
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.logger import CoolLogger


class SocketGbn:
    def __init__(self, _socket: Socket, logger: CoolLogger):
        self.socket = _socket
        self.logger = logger
        self.timeout = SOCKET_RETRANSMIT_WINDOW_TIMEOUT

    def sendto(self, data: bytes, to_address: Address):
        try:
            self.socket.sendto(data, to_address.to_tuple())
        except OSError:
            raise SocketShutdown()

    def recvfrom(self, buffer_size: int):
        try:
            self.socket.settimeout(self.timeout)
            raw_packet, server_address_tuple = self.socket.recvfrom(
                buffer_size)
            return raw_packet, server_address_tuple

        except SocketTimeout:
            raise RetransmissionNeeded()

        except OSError:
            raise SocketShutdown()

    def set_timeout(self, timeout):
        self.timeout = timeout
        self.socket.settimeout(timeout)

    def shutdown(self, shutdown_type):
        self.socket.shutdown(shutdown_type)

    def close(self):
        self.socket.close()

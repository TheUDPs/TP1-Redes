from socket import socket as Socket
from lib.common.address import Address


class SocketSaw:
    def __init__(self, _socket: Socket):
        self.socket = _socket
        self.last_raw_packet = None
        self.last_address = None

    def save_state(self, data: bytes, to_address: Address):
        self.last_raw_packet = data
        self.last_address = to_address

    def sendto(self, data: bytes, to_address: Address):
        self.save_state(data, to_address)
        self.socket.sendto(data, to_address.to_tuple())

    def recvfrom(self, buffersize: int):
        raw_packet, server_address_tuple = self.socket.recvfrom(buffersize)
        return raw_packet, server_address_tuple

    def shutdown(self, shutdown_type):
        self.socket.shutdown(shutdown_type)

    def close(self):
        self.socket.close()

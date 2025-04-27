from socket import socket as Socket
from lib.common.address import Address


class SocketSaW:
    def __init__(self, _socket: Socket):
        self.socket = _socket
        self.last_raw_packet = None
        self.last_address = None

    def save_state(self, data: bytes, to_address: Address):
        self.last_raw_packet = data
        self.last_address = to_address

    def send(self, data: bytes, to_address: Address):
        self.save_state(data, to_address)
        self.socket.sendto(data, to_address.to_tuple())

    def receive(self, buffersize: int):
        _data = self.socket.recv(buffersize)

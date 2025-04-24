# import socket
# import struct
#
# from constants import (
#     IPV4_LOCALHOST,
#     DEFAULT_PORT,
# )
#
# BUFFER_SIZE = 1024
#
# protocol = 0x0001
#
# header = struct.pack("!H", protocol)
#
# server_address = (IPV4_LOCALHOST, DEFAULT_PORT)
#
# with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
#     data = header
#     client_sock.sendto(data, server_address)
#     print(client_sock)
#
#     while True:
#         data_rcv, addr = client_sock.recvfrom(BUFFER_SIZE)
#         if server_address[0] != addr[0]:
#             print(f"Unexpected addr: {addr[0]}, expected: {server_address[0]}")
#             continue
#
#         print("addr: ", addr)
#         print("Expected:", data)
#         print("Got:", data_rcv)

import socket


class Client:
    def __init__(self):
        self.some = None

    def run(self):
        skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        host = ("127.0.0.1", 8080)
        mensaje: bytes = "1".encode("utf-8")
        skt.sendto(mensaje, host)
        skt.sendto(mensaje, host)
        skt.sendto(mensaje, host)


if __name__ == "__main__":
    client: Client = Client()
    client.run()
    print("Client finished")

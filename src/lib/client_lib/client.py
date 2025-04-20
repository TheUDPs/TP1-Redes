import socket
import struct

from constants import (
    IPV4_LOCALHOST,
    DEFAULT_PORT,
)

BUFFER_SIZE = 1024

protocol = 0x0001

header = struct.pack("!H", protocol)

server_address = (IPV4_LOCALHOST, DEFAULT_PORT)

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
    data = header
    client_sock.sendto(data, server_address)
    print(client_sock)

    while True:
        data_rcv, addr = client_sock.recvfrom(BUFFER_SIZE)
        if server_address[0] != addr[0]:
            print(f"Unexpected addr: {addr[0]}, expected: {server_address[0]}")
            continue

        print("addr: ", addr)
        print("Expected:", data)
        print("Got:", data_rcv)

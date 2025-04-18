import socket
import struct

IPV4_LOCALHOST = "10.0.0.2"

BUFFER_SIZE = 1024

protocol = 0x0001

header = struct.pack("!H", protocol)

server_address = (IPV4_LOCALHOST, 40267)

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
    data = header
    client_sock.sendto(data, server_address)
    # data_rcv, addr = client_sock.recvfrom(BUFFER_SIZE)

    # print("addr: ", addr)
    # print("Expected:", data)
    # print("Got:", data_rcv)

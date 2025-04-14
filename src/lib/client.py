import socket
import struct

HOST = '127.0.0.1'
PORT = 12345

protocol = 0x0001

header = struct.pack('!H', protocol)

server_address = ('127.0.0.1', 65432)

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
    client_sock.sendto(header, server_address)
    print("Packet sent:", header)

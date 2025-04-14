import socket
import struct

from lib.constants import (
    DEFAULT_PORT,
    IPV4_LOCALHOST,
)

protocol = 0x0001

header = struct.pack('!H', protocol)

server_address = (IPV4_LOCALHOST, DEFAULT_PORT)

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
    client_sock.sendto(header, server_address)
    print("Packet sent:", header)

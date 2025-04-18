import socket
import struct
from constants import (
    IPV4_LOCALHOST,
)

DEFAULT_PORT = 45536

BUFFER_SIZE = 1024


def handle_message(data, address, server_sock):
    protocol = struct.unpack("!H", data)
    print(f"[{address}] Received: {protocol =}")
    server_sock.sendto(data, address)  # Echo back


def start_udp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_sock:
        server_sock.bind((IPV4_LOCALHOST, DEFAULT_PORT))
        print(f"[*] UDP server listening on {IPV4_LOCALHOST}:{DEFAULT_PORT}")
        while True:
            data, addr = server_sock.recvfrom(BUFFER_SIZE)
            print("addr: ", addr)
            server_sock.sendto(data, "10.0.0.3")

            # thread = threading.Thread(target=handle_message, args=(data, addr, server_sock), daemon=True)
            # thread.start()


if __name__ == "__main__":
    start_udp_server()

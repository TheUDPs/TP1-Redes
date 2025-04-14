import socket
import threading
import struct

HOST = '127.0.0.1'
PORT = 65432

def handle_message(data, address, server_sock):
    protocol = struct.unpack('!H', data)
    print(f"[{address}] Received: {protocol =}")
    server_sock.sendto(data, address) # Echo back

def start_udp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_sock:
        server_sock.bind((HOST, PORT))
        print(f"[*] UDP server listening on {HOST}:{PORT}")
        while True:
            data, addr = server_sock.recvfrom(1024)
            thread = threading.Thread(target=handle_message, args=(data, addr, server_sock), daemon=True)
            thread.start()

if __name__ == "__main__":
    start_udp_server()

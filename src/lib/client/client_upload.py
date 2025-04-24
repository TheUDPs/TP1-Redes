import random
import socket
import sys
import time
import tty
import termios
import threading
import struct

from lib.common.constants import (
    GO_BACK_N_PROTOCOL_TYPE,
)

QUIT_CHARACTER = "q"
SOCKET_CONTROLLED_TIMEOUT = 1.0
ZERO_BYTES = bytes([])
BUFFER_SIZE = 4028


def read_key():
    stdin_fd = sys.stdin.fileno()
    old_tty_settings = termios.tcgetattr(stdin_fd)
    try:
        tty.setraw(stdin_fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_tty_settings)


def wait_for_quit(should_stop):
    while not should_stop.is_set():
        if read_key() == QUIT_CHARACTER:
            should_stop.set()
            break


class ClientProtocol:
    def __init__(
        self, logger, client_socket, server_host, server_port, protocol_version
    ):
        self.logger = logger
        self.socket = client_socket
        self.server_host = server_host
        self.server_port = server_port
        self.protocol_version = protocol_version
        self.server_host_with_port = (self.server_host, self.server_port)

    def build_packet(
        self,
        is_ack: bool,
        is_syn: bool,
        is_fin: bool,
        sequence_number: int,
        data: bytes,
    ):
        flags = 0b0000_0000_0000_0000

        protocol_flag = 0b00
        if self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            protocol_flag = 0b01

        sequence_number = 0b1 if sequence_number == 1 else 0b0
        is_ack = 0b1 if is_ack else 0b0
        is_syn = 0b1 if is_syn else 0b0
        is_fin = 0b1 if is_fin else 0b0

        pos = 16
        pos -= 2
        flags |= protocol_flag << pos

        pos -= 1
        flags |= sequence_number << pos

        pos -= 1
        flags |= is_ack << pos

        pos -= 1
        flags |= is_syn << pos

        pos -= 1
        flags |= is_fin << pos

        print(f"{flags:016b}\n")

        port = random.randint(1, 10)
        payload_length = len(data)

        header = struct.pack("!HHH", flags, port, payload_length)

        return header + data

    def check_packet_origin(self, packet, server_address):
        if server_address != self.server_host_with_port:
            print(server_address)
            print("No es de quien esperaba el mensaje")
        else:
            print(packet.decode())

    def request_connection(self, sequence_number):
        self.logger.debug("Requesting connection")

        packet = self.build_packet(
            is_ack=False,
            is_syn=False,
            is_fin=False,
            sequence_number=sequence_number,
            data=ZERO_BYTES,
        )
        self.socket.sendto(packet, self.server_host_with_port)

        packet, server_address = self.socket.recvfrom(BUFFER_SIZE)
        packet = self.check_packet_origin(packet, server_address)


class ClientUpload:
    def __init__(self, logger, host, port, src, name, protocol):
        self.logger = logger
        self.server_host = host
        self.server_port = port
        self.src_filepath = src
        self.final_filename = name

        self.server_host_with_port = (self.server_host, self.server_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.protocol = ClientProtocol(
            self.logger, self.socket, self.server_host, self.server_port, protocol
        )

    def handshake(self):
        self.logger.debug("Starting handshake")
        sequence_number = 0
        self.protocol.request_connection(sequence_number)

        # mensaje: bytes = "1".encode("utf-8")
        # self.socket.sendto(mensaje, self.server_host_with_port)
        # msj, server_address = self.socket.recvfrom(1048)
        # if server_address != self.server_host_with_port:
        #     print(server_address)
        #     print("No es de quien esperaba el mensaje")
        # else:
        #     print(msj.decode())

    def worker(self, should_stop_event):
        self.socket.settimeout(SOCKET_CONTROLLED_TIMEOUT)

        self.logger.debug("UDP socket ready")

        try:
            while not should_stop_event.is_set():
                try:
                    self.handshake()
                    time.sleep(SOCKET_CONTROLLED_TIMEOUT)
                except socket.timeout:
                    continue
                except OSError as e:
                    if should_stop_event.is_set():
                        continue
                    else:
                        raise e
        finally:
            self.logger.debug("Closing UDP socket")
            self.socket.close()

    def stop(self, worker):
        worker.join()

        self.logger.info("Client shutdown")

    def run(self):
        self.logger.info("Client started for upload")
        self.logger.debug(f"Protocol: {self.protocol.protocol_version}")

        should_stop_event = threading.Event()
        worker = threading.Thread(target=self.worker, args=(should_stop_event,))
        worker.start()

        wait_for_quit(should_stop_event)
        self.stop(worker)

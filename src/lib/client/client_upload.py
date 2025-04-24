import random
import socket
import sys
import threading
import struct
from io import StringIO
from multiprocessing import Value
from ctypes import c_bool

from lib.common.constants import (
    GO_BACK_N_PROTOCOL_TYPE,
)

QUIT_CHARACTER = "q"
SOCKET_TIMEOUT = 3
ZERO_BYTES = bytes([])
BUFFER_SIZE = 4028


class ConnectionRefused(Exception):
    def __init__(self, message="Connection refused from server"):
        self.message = message


class UnexpectedMessage(Exception):
    def __init__(self, message="Received a message from an unexpected server"):
        self.message = message


def wait_for_quit(should_stop, quited):
    while not should_stop.is_set():
        key = sys.stdin.read(1)
        if key == QUIT_CHARACTER:
            quited.value = True
            should_stop.set()


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

        # print(f"{flags:016b}\n")

        port = random.randint(1, 10)
        payload_length = len(data)

        header = struct.pack("!HHH", flags, port, payload_length)

        return header + data

    def parse_packet(self, packet):
        pos = 16
        pos -= 2
        protocol = packet >> pos & 0b11

        pos -= 1
        sequence_number = packet >> pos & 0b1

        pos -= 1
        is_ack = packet >> pos & 0b1

        pos -= 1
        is_syn = packet >> pos & 0b1

        pos -= 1
        is_fin = packet >> pos & 0b1

        # print(protocol, sequence_number, is_ack, is_syn, is_fin)

    def validate_incomming_packet(self, packet, server_address):
        if server_address != self.server_host_with_port:
            raise UnexpectedMessage()
        else:
            return self.parse_packet(packet)

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

        try:
            raw_packet, server_address = self.socket.recvfrom(BUFFER_SIZE)
        except OSError:
            raise ConnectionRefused()

        packet = self.validate_incomming_packet(raw_packet, server_address)


class ClientUpload:
    def __init__(self, logger, host, port, src, name, protocol):
        self.logger = logger
        self.server_host = host
        self.server_port = port
        self.src_filepath = src
        self.final_filename = name

        self.server_host_with_port = (self.server_host, self.server_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(SOCKET_TIMEOUT)

        self.protocol = ClientProtocol(
            self.logger, self.socket, self.server_host, self.server_port, protocol
        )

        self.stopped = False

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
        self.logger.debug("UDP socket ready")

        try:
            if not should_stop_event.is_set():
                self.handshake()
        except ConnectionRefused as e:
            self.logger.error(e.message)
        finally:
            should_stop_event.set()

    def stop(self, worker, wait_for_quit_thread, quited):
        if self.stopped:
            return

        self.logger.info("Stopping")

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            try:
                self.socket.close()
            except OSError:
                pass
        finally:
            worker.join()
            if not quited.value:
                sys.stdin = StringIO("q\n")
                sys.stdin.flush()
                self.logger.info("Press Enter to finish")

            wait_for_quit_thread.join()
            self.logger.info("Client shutdown")
            self.stopped = True

    def run(self):
        self.logger.info("Client started for upload")
        self.logger.debug(f"Protocol: {self.protocol.protocol_version}")

        should_stop_event = threading.Event()
        worker = threading.Thread(target=self.worker, args=(should_stop_event,))
        worker.start()

        quited = Value(c_bool, False)

        wait_for_quit_thread = threading.Thread(
            target=wait_for_quit, args=(should_stop_event, quited)
        )
        wait_for_quit_thread.start()

        should_stop_event.wait()

        self.stop(worker, wait_for_quit_thread, quited)

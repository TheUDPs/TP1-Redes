import socket
import sys
import threading
from io import StringIO
from multiprocessing import Value
from ctypes import c_bool

from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.client.protocol_interface import ClientProtocol

QUIT_CHARACTER = "q"
SOCKET_TIMEOUT = 3


def wait_for_quit(should_stop, quited):
    while not should_stop.is_set():
        key = sys.stdin.read(1)
        if key == QUIT_CHARACTER:
            quited.value = True
            should_stop.set()


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

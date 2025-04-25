import socket
import sys
from io import StringIO
from multiprocessing import Value
from ctypes import c_bool
from threading import Event, Thread

from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.client.protocol_interface import ClientProtocol
from lib.common.address import Address
from lib.common.logger import Logger
from lib.common.wait_for_quit import wait_for_quit

SOCKET_TIMEOUT = 30


class ClientUpload:
    def __init__(
        self, logger: Logger, host: str, port: int, src: str, name: str, protocol: str
    ):
        self.logger: Logger = logger
        self.server_host: str = host
        self.server_port: int = port
        self.src_filepath: str = src
        self.final_filename: str = name

        self.server_address: Address = Address(self.server_host, self.server_port)
        self.socket: socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(SOCKET_TIMEOUT)

        self.protocol = ClientProtocol(
            self.logger, self.socket, self.server_address, protocol
        )

        self.stopped = False

    def handshake(self) -> None:
        self.logger.debug("Starting handshake")
        self.logger.debug("Requesting connection")
        sequence_number = 0
        self.protocol.request_connection(sequence_number)

    def client_start(self, should_stop_event: Event) -> None:
        self.logger.debug("UDP socket ready")

        try:
            if not should_stop_event.is_set():
                self.handshake()
        except ConnectionRefused as e:
            self.logger.error(e.message)
        finally:
            should_stop_event.set()

    def stop(
        self, client_start_thread: Thread, wait_for_quit_thread: Thread, quited: Value
    ) -> None:
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
            client_start_thread.join()
            if not quited.value:
                sys.stdin = StringIO("q\n")
                sys.stdin.flush()
                self.logger.info("Press Enter to finish")

            wait_for_quit_thread.join()
            self.logger.info("Client shutdown")
            self.stopped = True

    def run(self) -> None:
        self.logger.info("Client started for upload")
        self.logger.debug(f"Protocol: {self.protocol.protocol_version}")

        should_stop_event: Event = Event()
        client_start_thread: Thread = Thread(
            target=self.client_start, args=(should_stop_event,)
        )
        client_start_thread.start()

        quited: Value = Value(c_bool, False)

        wait_for_quit_thread = Thread(
            target=wait_for_quit, args=(should_stop_event, quited)
        )
        wait_for_quit_thread.start()

        should_stop_event.wait()

        self.stop(client_start_thread, wait_for_quit_thread, quited)

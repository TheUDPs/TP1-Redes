import sys
import threading
from os import getcwd
from ctypes import c_bool
from io import StringIO
from multiprocessing import Value
from threading import Thread

from lib.common.address import Address
from lib.common.constants import ERROR_EXIT_CODE
from lib.common.logger import Logger
from lib.common.wait_for_quit import wait_for_quit
from lib.server.accepter import Accepter
from lib.server.exceptions.cannot_bind_socket import CannotBindSocket
from lib.server.file_handler import FileHandler


class Server:
    def __init__(
        self, logger: Logger, host: str, port: int, storage: str, protocol: str
    ):
        self.logger: Logger = logger
        self.host: str = host
        self.port: int = port
        self.storage: str = storage
        self.protocol: str = protocol
        self.address: Address = Address(self.host, self.port)

        if self.storage is None or self.storage == "":
            self.storage = getcwd()

        try:
            self.file_handler: FileHandler = FileHandler(self.storage, self.logger)
        except Exception as e:
            self.logger.error(f"Error opening storage directory: {e}")
            sys.exit(ERROR_EXIT_CODE)

        try:
            self.accepter: Accepter = Accepter(
                self.address, self.protocol, self.logger, self.file_handler
            )
        except CannotBindSocket:
            self.logger.error("Shutdown server")
            sys.exit(ERROR_EXIT_CODE)

        self.stopped = False

    def stop(self, wait_for_quit_thread: Thread, quited: Value) -> None:
        if self.stopped:
            return

        self.logger.info("Stopping")
        self.accepter.join()

        if not quited.value:
            sys.stdin = StringIO("q\n")
            sys.stdin.flush()
            self.logger.info("Press Enter to finish")

        wait_for_quit_thread.join()
        self.logger.info("Server shutdown")
        self.stopped = True

    def run(self) -> None:
        self.logger.info("Server started")
        self.logger.debug(f"Protocol: {self.protocol}")

        should_stop_event = threading.Event()
        quited = Value(c_bool, False)

        wait_for_quit_thread = Thread(
            target=wait_for_quit, args=(should_stop_event, quited)
        )
        wait_for_quit_thread.start()

        self.accepter.start()

        should_stop_event.wait()

        self.stop(wait_for_quit_thread, quited)

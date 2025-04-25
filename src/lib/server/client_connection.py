from shutil import disk_usage
from socket import socket, SHUT_RDWR
from threading import Thread

from lib.common.address import Address
from lib.common.constants import UPLOAD_OPERATION, DOWNLOAD_OPERATION
from lib.common.logger import Logger
from lib.common.sequence_number import SequenceNumber
from lib.server.client_pool import ClientPool

from lib.server.protocol_interface import (
    ServerProtocol,
    MissingClientAddress,
    BadFlagsForHandshake,
    SocketShutdown,
)
from enum import Enum


class ConnectionState(Enum):
    HANDHSAKE = 1
    HANDHSAKE_FINISHED = 2
    READY_TO_TRANSMIT = 3
    READY_TO_RECEIVE = 4
    BAD_STATE = 99


class ClientConnection:
    def __init__(
        self,
        connection_socket: socket,
        connection_address: Address,
        client_address: Address,
        protocol: str,
        logger: Logger,
    ):
        self.socket: socket = connection_socket
        self.address: Address = connection_address
        self.client_address: Address = client_address
        self.logger: Logger = logger
        self.protocol: ServerProtocol = ServerProtocol(
            self.logger, self.socket, self.address, protocol, ClientPool()
        )
        self.state: ConnectionState = ConnectionState.HANDHSAKE
        self.run_thread = Thread(target=self.run)

    def expect_handshake_completion(self) -> None:
        self.logger.debug("Waiting for handshake completion")
        try:
            self.protocol.expect_handshake_completion()
            self.state = ConnectionState.HANDHSAKE_FINISHED
            self.logger.debug("Handhsake completed")
        except SocketShutdown:
            self.logger.debug("Client connection socket shutdowned")
        except (MissingClientAddress, BadFlagsForHandshake) as e:
            self.state = ConnectionState.BAD_STATE
            raise e

    def receive_operation_intention(self) -> tuple[int, SequenceNumber]:
        self.logger.debug("[CONN] Waiting for operation intention")
        try:
            op_code, sequence_number = self.protocol.receive_operation_intention()

            if op_code == UPLOAD_OPERATION:
                self.state = ConnectionState.READY_TO_RECEIVE
            elif op_code == DOWNLOAD_OPERATION:
                self.state = ConnectionState.READY_TO_TRANSMIT
            else:
                self.state = ConnectionState.BAD_STATE
                self.logger.debug("[CONN] Bad state")

            return op_code, sequence_number

        except SocketShutdown:
            self.logger.debug("Client connection socket shutdowned")
            raise SocketShutdown

        except (MissingClientAddress, BadFlagsForHandshake) as e:
            self.state = ConnectionState.BAD_STATE
            raise e

    def is_filename_valid(self, filename) -> bool:
        pass

    def is_filesize_valid(self, filesize) -> bool:
        total, used, free = disk_usage("/home/gabriel/Uni/2025/Redes/TPs/TP1-Redes")
        print(total, used, free)

    def receive_file(self, sequence_number):
        self.logger.debug(f"[CONN] Ready to receive from {self.client_address}")
        self.protocol.send_ack(sequence_number, self.client_address, self.address)

        sequence_number.flip()
        sequence_number, filename = self.protocol.receive_filename(sequence_number)
        if self.is_filename_valid(filename):
            self.protocol.send_ack(sequence_number, self.client_address, self.address)
        else:
            self.protocol.send_fin(sequence_number, self.client_address, self.address)
            raise SocketShutdown()

        sequence_number.flip()
        sequence_number, filesize = self.protocol.receive_filesize(sequence_number)
        if self.is_filesize_valid(filesize):
            self.protocol.send_ack(sequence_number, self.client_address, self.address)
        else:
            self.protocol.send_fin(sequence_number, self.client_address, self.address)
            raise SocketShutdown()

    def transmit_file(self, _sequence_number):
        self.logger.debug("[CONN] Ready to transmit")

    def run(self):
        try:
            self.expect_handshake_completion()
            op_code, sequence_number = self.receive_operation_intention()

            if op_code == UPLOAD_OPERATION:
                self.receive_file(sequence_number)
            elif op_code == DOWNLOAD_OPERATION:
                self.transmit_file(sequence_number)

        except SocketShutdown:
            pass
        except Exception as e:
            self.logger.error(f"[CONN] Fatal error: {e}")
            self.kill()

    def start(self):
        self.run_thread.start()

    def kill(self):
        try:
            self.socket.shutdown(SHUT_RDWR)
        except OSError:
            try:
                self.socket.close()
            except OSError:
                pass
        finally:
            self.run_thread.join()

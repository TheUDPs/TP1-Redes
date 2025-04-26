from math import ceil
from socket import socket, SHUT_RDWR
from threading import Thread

from lib.common.address import Address
from lib.common.constants import FILE_CHUNK_SIZE, UPLOAD_OPERATION, DOWNLOAD_OPERATION
from lib.common.logger import Logger
from lib.common.sequence_number import SequenceNumber
from lib.server.client_pool import ClientPool
from lib.server.exceptions.invalid_filename import InvalidFilename
from lib.server.file_handler import FileHandler

from lib.server.protocol import (
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
    DONE_READY_TO_DIE = 5
    UNRECOVERABLE_BAD_STATE = 99


class ClientConnection:
    def __init__(
        self,
        connection_socket: socket,
        connection_address: Address,
        client_address: Address,
        protocol: str,
        logger: Logger,
        file_handler: FileHandler,
    ):
        self.socket: socket = connection_socket
        self.address: Address = connection_address
        self.client_address: Address = client_address
        self.logger: Logger = logger
        self.file_handler: FileHandler = file_handler

        self.protocol: ServerProtocol = ServerProtocol(
            self.logger, self.socket, self.address, protocol, ClientPool()
        )
        self.state: ConnectionState = ConnectionState.HANDHSAKE
        self.run_thread = Thread(target=self.run)
        self.file = None
        self.killed = False

    def expect_handshake_completion(self) -> None:
        self.logger.debug("Waiting for handshake completion")
        try:
            self.protocol.expect_handshake_completion()
            self.state = ConnectionState.HANDHSAKE_FINISHED
            self.logger.debug("Handhsake completed")
        except SocketShutdown:
            self.logger.debug("Client connection socket shutdowned")
        except (MissingClientAddress, BadFlagsForHandshake) as e:
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
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
                self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
                self.logger.debug("[CONN] Bad state")

            return op_code, sequence_number

        except SocketShutdown:
            self.logger.debug("Client connection socket shutdowned")
            raise SocketShutdown

        except (MissingClientAddress, BadFlagsForHandshake) as e:
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise e

    def is_filename_valid(self, filename: str) -> bool:
        try:
            self.file = self.file_handler.open_file(filename)
            return True
        except InvalidFilename:
            return False

    def is_filesize_valid(self, filesize: int) -> bool:
        return self.file_handler.can_file_fit(filesize)

    def receive_file_info(
        self, sequence_number: SequenceNumber
    ) -> tuple[str, int, SequenceNumber]:
        sequence_number.flip()
        sequence_number, filename = self.protocol.receive_filename(sequence_number)
        if self.is_filename_valid(filename):
            self.protocol.send_ack(sequence_number, self.client_address, self.address)
            self.logger.debug("[CONN] Filename received valid")
        else:
            self.protocol.send_fin(sequence_number, self.client_address, self.address)
            self.logger.error("[CONN] Filename received invalid")
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise SocketShutdown()

        sequence_number.flip()
        sequence_number, filesize = self.protocol.receive_filesize(sequence_number)
        if self.is_filesize_valid(filesize):
            self.protocol.send_ack(sequence_number, self.client_address, self.address)
            self.logger.debug("[CONN] Filesize received valid")
        else:
            self.protocol.send_fin(sequence_number, self.client_address, self.address)
            self.logger.error("[CONN] Filesize received invalid")
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise SocketShutdown()

        return filename, filesize, sequence_number

    def receive_file(self, sequence_number: SequenceNumber):
        self.logger.debug("[CONN] Validating filename and filesize")
        self.protocol.send_ack(sequence_number, self.client_address, self.address)

        filename, _filesize, sequence_number = self.receive_file_info(sequence_number)
        self.logger.debug(f"[CONN] Ready to receive from {self.client_address}")

        chunk_number: int = 1

        sequence_number.flip()
        sequence_number_return, packet = self.protocol.receive_file_chunk(
            sequence_number
        )
        if packet.is_fin:
            self.protocol.send_fin_ack(
                sequence_number_return, self.client_address, self.address
            )
        else:
            self.protocol.send_ack(
                sequence_number_return, self.client_address, self.address
            )

        self.logger.debug(f"[CONN] Received chunk {chunk_number}")
        self.file_handler.append_to_file(self.file, packet)

        while not packet.is_fin:
            chunk_number += 1
            sequence_number_return.flip()
            sequence_number_return, packet = self.protocol.receive_file_chunk(
                sequence_number_return
            )

            if packet.is_fin:
                self.protocol.send_fin_ack(
                    sequence_number_return, self.client_address, self.address
                )
            else:
                self.protocol.send_ack(
                    sequence_number_return, self.client_address, self.address
                )

            self.file_handler.append_to_file(self.file, packet)
            self.logger.debug(f"[CONN] Received chunk {chunk_number}")

        self.logger.debug("[CONN] Finished receiving file")
        self.file.close()

        return sequence_number_return

    def transmit_file(self, sequence_number: SequenceNumber):
        self.logger.debug("[CONN] transmitting file")
        try:
            sequence_number.flip()
            self.protocol.send_ack(sequence_number, self.client_address, self.address)
            sequence_number = self.receive_file_name_transmit(sequence_number)

            self.logger.debug(
                f"[CONN] Configuration is done, sending file chunks {self.client_address}"
            )

            self.logger.debug(f"[CONN] sequence_number {sequence_number.value}")
            chunk_number: int = 1
            is_last_chunk: bool = False
            while chunk := self.file.read(FILE_CHUNK_SIZE):
                chunk_len = len(chunk)
                self.logger.debug(
                    f"[CONN] Sending chunk {chunk_number} of size {self.bytes_to_kilobytes(chunk_len)} KB"
                )

                self.logger.debug(f"[CONN] sequence_number {sequence_number.value}")
                if chunk_len < FILE_CHUNK_SIZE:
                    is_last_chunk = True

                sequence_number.flip()

                self.logger.debug("Sending file chunk")
                self.protocol.send_file_chunk(
                    sequence_number,
                    chunk,
                    chunk_len,
                    is_last_chunk,
                    self.client_address,
                )

                self.logger.debug(
                    f"[CONN] Waiting confirmation for chunk {chunk_number}"
                )

                self.logger.debug("Is last chunk: " + str(is_last_chunk))

                if is_last_chunk:
                    self.protocol.wait_for_fin_ack(sequence_number)
                else:
                    self.protocol.wait_for_ack(sequence_number)

                chunk_number += 1

            self.protocol.send_ack(sequence_number, self.client_address, self.address)
            self.logger.info("[CONN] File transfer complete")

        # to do: Agregar manejo de excepciones
        except Exception as e:
            print(e)
            self.logger.error(f"[CONN] Error transmitting file: {e.message}")

    def receive_file_name_transmit(self, sequence_number: SequenceNumber):
        try:
            self.logger.debug("[CONN] Waiting for filename")
            sequence_number.flip()
            sequence_number, filename = self.protocol.receive_filename(sequence_number)
            self.file = self.file_handler.open_file_read(filename)
            self.logger.debug(f"[CONN] Filename received: {filename}, sending ACK")
            self.protocol.send_ack(sequence_number, self.client_address, self.address)
            return sequence_number
        except InvalidFilename:
            self.logger.error("[CONN] Filename received invalid")
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            self.protocol.send_fin(sequence_number, self.client_address, self.address)

    def closing_handshake(self, sequence_number: SequenceNumber):
        sequence_number.flip()
        self.protocol.wait_for_ack(sequence_number)
        self.logger.debug("[CONN] Connection closed")
        self.state = ConnectionState.DONE_READY_TO_DIE

    def run(self):
        try:
            self.expect_handshake_completion()
            op_code, sequence_number = self.receive_operation_intention()

            if op_code == UPLOAD_OPERATION:
                sequence_number = self.receive_file(sequence_number)
                self.closing_handshake(sequence_number)
            elif op_code == DOWNLOAD_OPERATION:
                self.transmit_file(sequence_number)

        except SocketShutdown:
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            pass
        except Exception as e:
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            self.logger.error(f"[CONN] Fatal error: {e}")
            self.kill()

    def start(self):
        self.run_thread.start()

    def kill(self):
        if not self.killed:
            return

        try:
            self.socket.shutdown(SHUT_RDWR)
        except OSError:
            try:
                self.socket.close()
            except OSError:
                pass
        finally:
            self.run_thread.join()
            self.killed = True

    def is_done_and_ready_to_die(self):
        return (
            self.state == ConnectionState.DONE_READY_TO_DIE
            or self.state == ConnectionState.UNRECOVERABLE_BAD_STATE
        )

    def bytes_to_megabytes(self, bytes: int) -> str:
        megabytes = bytes / (1024 * 1024)
        return "{0:.2f}".format(megabytes)

    def bytes_to_kilobytes(self, bytes: int) -> str:
        megabytes = bytes / (1024)
        return "{0:.2f}".format(megabytes)

    def get_number_of_chunks(self, file_size: int) -> int:
        return ceil(file_size / FILE_CHUNK_SIZE)

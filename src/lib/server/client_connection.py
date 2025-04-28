from socket import SHUT_RDWR
from threading import Thread

from lib.common.address import Address
from lib.common.constants import (
    FILE_CHUNK_SIZE,
    UPLOAD_OPERATION,
    DOWNLOAD_OPERATION,
    OPERATION_STRING_FROM_CODE,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin_ack import MessageIsNotFinAck
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.logger import Logger
from lib.common.mutable_variable import MutableVariable
from lib.common.packet import Packet
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_saw import SocketSaw
from lib.server.client_pool import ClientPool
from lib.server.connection_state import ConnectionState
from lib.server.exceptions.unexpected_operation import UnexpectedOperation
from lib.server.exceptions.client_already_connected import ClientAlreadyConnected
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.server.exceptions.missing_client_address import MissingClientAddress
from lib.common.file_handler import FileHandler

from lib.server.protocol import ServerProtocol


class ClientConnection:
    def __init__(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        protocol: str,
        logger: Logger,
        file_handler: FileHandler,
        initial_sequence_number: SequenceNumber,
    ):
        self.socket: SocketSaw = connection_socket
        self.address: Address = connection_address
        self.client_address: Address = client_address
        self.logger: Logger = logger
        self.logger.set_prefix(f"[CONN:{connection_address.port}]")
        self.initial_sequence_number: SequenceNumber = initial_sequence_number

        self.file_handler: FileHandler = file_handler

        self.protocol: ServerProtocol = ServerProtocol(
            self.logger, self.socket, self.address, protocol, ClientPool()
        )
        self.state: ConnectionState = ConnectionState.HANDHSAKE_FINISHED
        self.run_thread = Thread(target=self.run)
        self.file = None
        self.killed = False

    def receive_operation_intention(self, sequence_number: MutableVariable) -> int:
        self.logger.debug("Waiting for operation intention")
        try:
            op_code, _seq = self.protocol.receive_operation_intention()
            sequence_number.value = _seq

            if op_code == UPLOAD_OPERATION:
                self.state = ConnectionState.READY_TO_RECEIVE
            elif op_code == DOWNLOAD_OPERATION:
                self.state = ConnectionState.READY_TO_TRANSMIT
            else:
                self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
                self.logger.debug("Bad state. Unexpected operation")

            self.logger.debug(f"Operation is: {OPERATION_STRING_FROM_CODE[op_code]}")
            self.logger.debug("Confirming operation")

            self.protocol.send_ack(
                sequence_number.value, self.client_address, self.address
            )

            return op_code

        except MissingClientAddress as e:
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise e

    def is_filename_valid_for_upload(self, filename: str) -> bool:
        try:
            self.file = self.file_handler.open_file_write_mode(
                filename, is_path_complete=False
            )
            return True
        except InvalidFilename:
            return False

    def is_filesize_valid_for_upload(self, filesize: int) -> bool:
        return self.file_handler.can_file_fit(filesize)

    def receive_file_info_for_upload(
        self, sequence_number: MutableVariable
    ) -> tuple[str, int]:
        self.logger.debug("Validating filename")
        sequence_number.value.flip()
        _seq, filename = self.protocol.receive_filename(sequence_number.value)
        sequence_number.value = _seq

        if self.is_filename_valid_for_upload(filename):
            self.protocol.send_ack(
                sequence_number.value, self.client_address, self.address
            )
            self.logger.debug(f"Filename received valid: {filename}")
        else:
            self.protocol.send_fin(
                sequence_number.value, self.client_address, self.address
            )
            self.logger.warn("Filename received invalid")
            self.logger.error(
                f"Client {self.client_address.to_combined()} shutdowned due to file '{filename}' already existing in the server"
            )
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise SocketShutdown()

        self.logger.debug("Validating filesize")
        sequence_number.value.flip()
        _seq, filesize = self.protocol.receive_filesize(sequence_number.value)
        sequence_number.value = _seq

        if self.is_filesize_valid_for_upload(filesize):
            self.protocol.send_ack(
                sequence_number.value, self.client_address, self.address
            )
            self.logger.debug(f"Filesize received valid: {filesize} bytes")
        else:
            self.protocol.send_fin(
                sequence_number.value, self.client_address, self.address
            )
            self.logger.warn("Filesize received invalid")
            self.logger.error(
                f"Client {self.client_address.to_combined()} shutdowned due to file being too big"
            )
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise SocketShutdown()

        return filename, filesize

    def receive_single_chunk(
        self, sequence_number: MutableVariable, chunk_number: int
    ) -> Packet:
        _seq, packet = self.protocol.receive_file_chunk(sequence_number.value)
        sequence_number.value = _seq

        if packet.is_fin:
            self.protocol.send_fin_ack(
                sequence_number.value, self.client_address, self.address
            )
        else:
            self.protocol.send_ack(
                sequence_number.value, self.client_address, self.address
            )

        self.logger.debug(f"Received chunk {chunk_number}")
        self.file_handler.append_to_file(self.file, packet)

        return packet

    def receive_file(
        self,
        sequence_number: MutableVariable,
        filename: MutableVariable,
        filesize: MutableVariable,
    ):
        _filename, _filesize = self.receive_file_info_for_upload(sequence_number)
        filename.value = _filename
        filesize.value = _filesize

        self.logger.debug(f"Ready to receive from {self.client_address}")

        chunk_number: int = 1

        sequence_number.value.flip()
        packet = self.receive_single_chunk(sequence_number, chunk_number)

        while not packet.is_fin:
            chunk_number += 1
            sequence_number.value.flip()
            packet = self.receive_single_chunk(sequence_number, chunk_number)

        self.logger.debug("Finished receiving file")
        self.file_handler.close(self.file)

    def transmit_file(
        self, sequence_number: MutableVariable, filename: MutableVariable
    ):
        _filename, filesize = self.receive_file_info_for_download(sequence_number)
        filename.value = _filename

        self.logger.debug(f"Ready to transmit to {self.client_address}")

        chunk_number: int = 1
        total_chunks: int = self.file_handler.get_number_of_chunks(
            filesize, FILE_CHUNK_SIZE
        )
        is_last_chunk: bool = False

        self.logger.info(
            f"Sending file {filename.value} of {self.file_handler.bytes_to_megabytes(filesize)} MB"
        )

        while chunk := self.file_handler.read(self.file, FILE_CHUNK_SIZE):
            chunk_len = len(chunk)
            self.logger.debug(
                f"Sending chunk {chunk_number}/{total_chunks} of size {self.file_handler.bytes_to_kilobytes(chunk_len)} KB"
            )

            if chunk_number == total_chunks:
                is_last_chunk = True

            sequence_number.value.flip()
            self.protocol.send_file_chunk(
                sequence_number.value,
                chunk,
                chunk_len,
                is_last_chunk,
                self.client_address,
            )

            self.logger.debug(f"Waiting confirmation for chunk {chunk_number}")

            if is_last_chunk:
                self.protocol.wait_for_fin_ack(sequence_number.value)
            else:
                self.protocol.wait_for_ack(sequence_number.value)

            chunk_number += 1

        self.logger.info("File transfer complete")

    def is_filename_valid_for_download(self, filename: str):
        try:
            self.file = self.file_handler.open_file_read_mode(
                filename, is_path_complete=False
            )
            return True
        except InvalidFilename:
            return False

    def receive_file_info_for_download(
        self, sequence_number: MutableVariable
    ) -> tuple[str, int]:
        self.logger.debug("Validating filename")
        sequence_number.value.flip()
        _seq, filename = self.protocol.receive_filename(sequence_number.value)
        sequence_number.value = _seq

        if self.is_filename_valid_for_download(filename):
            self.protocol.send_ack(
                sequence_number.value, self.client_address, self.address
            )
            self.logger.debug("Filename received valid")
        else:
            self.protocol.send_fin(
                sequence_number.value, self.client_address, self.address
            )
            self.logger.warn("Filename received invalid")
            self.logger.error(
                f"Client {self.client_address.to_combined()} shutdowned due to file '{filename}' not existing in server for download"
            )
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise SocketShutdown()

        filesize = self.file_handler.get_filesize(filename, is_path_complete=False)

        return filename, filesize

    def closing_handshake_for_upload(self, sequence_number: MutableVariable):
        sequence_number.value.flip()
        self.protocol.wait_for_ack(sequence_number.value)
        self.logger.debug("Connection closed")
        self.state = ConnectionState.DONE_READY_TO_DIE

    def closing_handshake_for_download(self, sequence_number: MutableVariable):
        sequence_number.value.flip()
        self.protocol.send_ack(sequence_number.value, self.client_address, self.address)
        self.logger.debug("Connection closed")
        self.state = ConnectionState.DONE_READY_TO_DIE

    def file_cleanup_after_error(
        self, filename_for_upload: MutableVariable, filesize_for_upload: MutableVariable
    ):
        if self.file is not None and self.file_handler.is_closed(self.file):
            self.file_handler.close(self.file)

        if filename_for_upload.value is not None:
            self.file_handler.remove_file_if_corrupted_or_incomplete(
                filename_for_upload, filesize_for_upload, is_path_complete=False
            )

    def run(self):
        filename_for_upload = MutableVariable(None)
        filesize_for_upload = MutableVariable(None)
        filename_for_download = MutableVariable(None)
        sequence_number = MutableVariable(
            SequenceNumber(self.initial_sequence_number.value)
        )
        sequence_number.value.flip()

        try:
            op_code = self.receive_operation_intention(sequence_number)

            if op_code == UPLOAD_OPERATION:
                self.receive_file(
                    sequence_number, filename_for_upload, filesize_for_upload
                )
                self.closing_handshake_for_upload(sequence_number)
                self.logger.force_info(
                    f"Upload completed from client {self.client_address.to_combined()}"
                )
            elif op_code == DOWNLOAD_OPERATION:
                self.transmit_file(sequence_number, filename_for_download)
                self.closing_handshake_for_download(sequence_number)
                self.logger.force_info(
                    f"Download completed to client {self.client_address.to_combined()}"
                )

        except (SocketShutdown, ConnectionLost):
            self.logger.debug("State is unrecoverable")
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            self.logger.debug("Connection shutdown")
            self.file_cleanup_after_error(filename_for_upload, filesize_for_upload)
            self.kill()
        except (
            MissingClientAddress,
            UnexpectedOperation,
            InvalidSequenceNumber,
            UnexpectedFinMessage,
            ClientAlreadyConnected,
            MessageIsNotAck,
            MessageIsNotFinAck,
        ) as e:
            self.logger.warn(f"Error: {e.message}")
            self.logger.debug("State can be recovered")

        except Exception as e:
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            self.logger.error(f"Fatal error: {e}")
            self.file_cleanup_after_error(filename_for_upload, filesize_for_upload)
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

    def is_ready_to_die(self):
        return (
            self.state == ConnectionState.DONE_READY_TO_DIE
            or self.state == ConnectionState.UNRECOVERABLE_BAD_STATE
        )

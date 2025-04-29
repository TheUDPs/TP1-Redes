from os import path, getcwd
from sys import exit

from lib.client.abstract_client import Client
from lib.client.exceptions.file_already_exists import FileAlreadyExists
from lib.client.exceptions.file_too_big import FileTooBig
from lib.common.constants import (
    UPLOAD_OPERATION,
    ERROR_EXIT_CODE,
    FILE_CHUNK_SIZE,
    GO_BACK_N_PROTOCOL_TYPE,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.file_handler import FileHandler
from lib.common.logger import Logger
from lib.server.exceptions.protocol_mismatch import ProtocolMismatch


class UploadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, src: str, name: str, protocol: str
    ):
        if protocol == GO_BACK_N_PROTOCOL_TYPE:
            raise ProtocolMismatch()

        self.src_filepath: str = src
        self.filename_in_server: str = name

        try:
            self.file_handler: FileHandler = FileHandler(getcwd(), logger)
            self.file = self.file_handler.open_file_read_mode(
                self.src_filepath, is_path_complete=True
            )
            self.filesize = self.file_handler.get_filesize(
                self.src_filepath, is_path_complete=True
            )
            print(self.file, self.filesize)
        except InvalidFilename:
            logger.error(f"Could not find or open file {src}")
            exit(ERROR_EXIT_CODE)

        if name is None or name == "":
            self.filename_in_server = path.basename(self.src_filepath)

        super().__init__(logger, host, port, protocol)

    def perform_operation(self) -> None:
        self.perform_upload()

    def perform_upload(self) -> None:
        try:
            self.send_operation_intention(UPLOAD_OPERATION)
            self.inform_size_and_name()
            self.send_file()
            self.closing_handshake()

        except (FileAlreadyExists, FileTooBig, ConnectionLost) as e:
            self.logger.error(f"{e.message}")
            self.file_cleanup_after_error()

        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")
            self.file_cleanup_after_error()

    def inform_filename(self):
        self.sequence_number.step()
        self.logger.debug(f"Informing filename: {self.filename_in_server}")
        self.protocol.inform_filename(self.sequence_number, self.filename_in_server)

        self.logger.debug("Waiting for filename confirmation")
        try:
            self.protocol.wait_for_ack(
                self.sequence_number,
                exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
            )
        except (UnexpectedFinMessage, MessageIsNotAck):
            self.logger.debug("Filename confirmation failed")
            raise FileAlreadyExists()

    def inform_filesize(self):
        self.sequence_number.step()
        self.logger.debug(f"Informing filesize: {self.filesize} bytes")
        self.protocol.inform_filesize(self.sequence_number, self.filesize)

        self.logger.debug("Waiting for filesize confirmation")

        try:
            self.protocol.wait_for_ack(
                self.sequence_number,
                exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
            )
        except (UnexpectedFinMessage, MessageIsNotAck):
            self.logger.debug("Filesize confirmation failed")
            raise FileTooBig()

    def inform_size_and_name(self) -> None:
        self.inform_filename()
        self.inform_filesize()

    def send_file(self) -> None:
        chunk_number: int = 1
        total_chunks: int = self.file_handler.get_number_of_chunks(
            self.filesize, FILE_CHUNK_SIZE
        )
        is_last_chunk: bool = False

        self.logger.info(
            f"Sending file {self.filename_in_server} of {self.file_handler.bytes_to_megabytes(self.filesize)} MB"
        )

        while chunk := self.file_handler.read(self.file, FILE_CHUNK_SIZE):
            chunk_len = len(chunk)
            self.logger.debug(
                f"Sending chunk {chunk_number}/{total_chunks} of size {self.file_handler.bytes_to_kilobytes(chunk_len)} KB"
            )

            if chunk_number == total_chunks:
                is_last_chunk = True

            self.sequence_number.step()
            self.protocol.send_file_chunk(
                self.sequence_number, chunk, chunk_len, is_last_chunk
            )

            self.logger.debug(
                f"Waiting confirmation for chunk {chunk_number}/{total_chunks}"
            )

            if is_last_chunk:
                self.protocol.wait_for_fin_ack(self.sequence_number)
            else:
                self.protocol.wait_for_ack(self.sequence_number)

            chunk_number += 1

        self.logger.force_info("File transfer complete")
        self.file_handler.close(self.file)

    def closing_handshake(self) -> None:
        self.sequence_number.step()
        self.protocol.send_ack(self.sequence_number)
        self.logger.debug("Connection closed")

    def file_cleanup_after_error(self):
        if not self.file_handler.is_closed(self.file):
            self.file_handler.close(self.file)

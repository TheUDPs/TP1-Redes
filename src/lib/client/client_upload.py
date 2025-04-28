from os import stat, path
from math import ceil
from sys import exit

from lib.client.abstract_client import Client
from lib.client.exceptions.file_already_exists import FileAlreadyExists
from lib.client.exceptions.file_too_big import FileTooBig
from lib.common.constants import (
    UPLOAD_OPERATION,
    FOPEN_READ_MODE,
    FOPEN_BINARY_MODE,
    ERROR_EXIT_CODE,
    FILE_CHUNK_SIZE,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.logger import Logger


class UploadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, src: str, name: str, protocol: str
    ):
        self.src_filepath: str = src
        self.final_filename: str = name

        try:
            self.file = open(self.src_filepath, FOPEN_READ_MODE + FOPEN_BINARY_MODE)
            self.file_stats = stat(self.src_filepath)
        except FileNotFoundError:
            logger.error(f"Could not find or open file {src}")
            exit(ERROR_EXIT_CODE)
        except IOError as e:
            logger.error(f"I/O error occurred: {e}")
            exit(ERROR_EXIT_CODE)

        if name is None or name == "":
            self.final_filename = path.basename(self.src_filepath)

        super().__init__(logger, host, port, protocol)

    def perform_operation(self) -> None:
        self.perform_upload()

    def bytes_to_megabytes(self, bytes: int) -> str:
        megabytes = bytes / (1024 * 1024)
        return "{0:.2f}".format(megabytes)

    def bytes_to_kilobytes(self, bytes: int) -> str:
        megabytes = bytes / (1024)
        return "{0:.2f}".format(megabytes)

    def get_number_of_chunks(self, file_size: int) -> int:
        return ceil(file_size / FILE_CHUNK_SIZE)

    def perform_upload(self) -> None:
        try:
            self.send_operation_intention()
            self.inform_size_and_name()

            self.logger.info(
                f"Sending file {self.final_filename} of {self.bytes_to_megabytes(self.file_stats.st_size)} MB"
            )
            self.send_file()
            self.closing_handshake()

        except (FileAlreadyExists, FileTooBig, ConnectionLost) as e:
            self.logger.error(f"{e.message}")

        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")

    def send_operation_intention(self) -> None:
        self.logger.debug("Sending operation intention")

        self.sequence_number.flip()
        self.protocol.send_operation_intention(self.sequence_number, UPLOAD_OPERATION)

        self.logger.debug("Waiting for operation confirmation")
        self.protocol.wait_for_operation_confirmation(self.sequence_number)
        self.logger.debug("Operation accepted")

    def inform_size_and_name(self) -> None:
        self.sequence_number.flip()
        self.logger.debug(f"Informing filename: {self.final_filename}")
        self.protocol.inform_filename(self.sequence_number, self.final_filename)

        self.logger.debug("Waiting for filename confirmation")
        try:
            self.protocol.wait_for_ack(
                self.sequence_number,
                exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
            )
        except (UnexpectedFinMessage, MessageIsNotAck):
            self.logger.debug("Filename confirmation failed")
            raise FileAlreadyExists()

        self.sequence_number.flip()
        self.logger.debug(f"Informing filesize: {self.file_stats.st_size} bytes")
        self.protocol.inform_filesize(self.sequence_number, self.file_stats.st_size)

        self.logger.debug("Waiting for filesize confirmation")

        try:
            self.protocol.wait_for_ack(
                self.sequence_number,
                exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
            )
        except (UnexpectedFinMessage, MessageIsNotAck):
            self.logger.debug("Filesize confirmation failed")
            raise FileTooBig()

    def send_file(self) -> None:
        chunk_number: int = 1
        total_chunks: int = self.get_number_of_chunks(self.file_stats.st_size)
        is_last_chunk: bool = False

        while chunk := self.file.read(FILE_CHUNK_SIZE):
            chunk_len = len(chunk)
            self.logger.debug(
                f"Sending chunk {chunk_number}/{total_chunks} of size {self.bytes_to_kilobytes(chunk_len)} KB"
            )

            if chunk_number == total_chunks:
                is_last_chunk = True

            self.sequence_number.flip()
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
        self.file.close()

    def closing_handshake(self) -> None:
        self.sequence_number.flip()
        self.protocol.send_ack(self.sequence_number)
        self.logger.debug("Connection closed")

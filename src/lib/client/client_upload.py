from os import stat, path
from math import ceil
from sys import exit

from lib.client.abstract_client import Client
from lib.common.constants import UPLOAD_OPERATION, FOPEN_READ_MODE, FOPEN_BINARY_MODE
from lib.common.logger import Logger

ERROR_EXIT_CODE = 1
CHUNK_SIZE = 61440


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
        return ceil(file_size / CHUNK_SIZE)

    def perform_upload(self) -> None:
        try:
            self.sequence_number.flip()
            self.protocol.send_operation_intention(
                self.sequence_number, UPLOAD_OPERATION
            )
            self.protocol.wait_for_operation_confirmation(self.sequence_number)
            self.logger.debug("Operation accepted")

            self.inform_size_and_name()

            self.logger.info(
                f"Sending file {self.final_filename} of {self.bytes_to_megabytes(self.file_stats.st_size)} MB"
            )
            self.send_file()
        except Exception as e:
            self.logger.error(e)

    def inform_size_and_name(self) -> None:
        self.sequence_number.flip()
        self.protocol.inform_filename(self.sequence_number, self.final_filename)
        self.protocol.wait_for_ack(self.sequence_number)

        self.sequence_number.flip()
        self.protocol.inform_filesize(self.sequence_number, self.file_stats.st_size)
        self.protocol.wait_for_ack(self.sequence_number)

    def send_file(self) -> None:
        chunk_number: int = 1
        total_chunks: int = self.get_number_of_chunks(self.file_stats.st_size)
        is_last_chunk: bool = False

        while chunk := self.file.read(CHUNK_SIZE):
            self.sequence_number.flip()
            chunk_len = len(chunk)
            self.logger.debug(
                f"Sending chunk {chunk_number}/{total_chunks} of size {self.bytes_to_kilobytes(chunk_len)} KB"
            )

            if chunk_number == total_chunks:
                is_last_chunk = True

            self.protocol.send_file_chunk(
                self.sequence_number, chunk, chunk_len, is_last_chunk
            )

            self.logger.debug(
                f"Waiting confirmation for chunk {chunk_number}/{total_chunks}"
            )
            self.protocol.wait_for_ack(self.sequence_number)

        self.file.close()

from os import getcwd, path

from lib.client.abstract_client import Client
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.common.file_handler import FileHandler
from lib.common.mutable_variable import MutableVariable
from lib.common.logger import Logger
from lib.common.constants import (
    ERROR_EXIT_CODE,
    DOWNLOAD_OPERATION,
)

from lib.client.exceptions.file_does_not_exist import FileDoesNotExist
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.packet.packet import PacketGbn
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage


class DownloadClientGbn(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, src: str, name: str, protocol: str
    ):
        self.src_filepath: str = src
        self.filename_in_server: str = name
        self.sequence_number: int = 0
        self.expected_sqn_number: int = 1
        self.file_destination: str = ""
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
        self.perform_download_gbn()

    def perform_download_gbn(self) -> None:
        try:
            self.send_operation_intention(DOWNLOAD_OPERATION)
            self.inform_name_to_download()
            self.receive_file_gbn()
            self.closing_handshake_gbn()

        except (FileDoesNotExist, ConnectionLost) as e:
            self.logger.error(f"{e.message}")
            self.file_cleanup_after_error()

        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")
            self.file_cleanup_after_error()

    def receive_file_gbn(self):
        chunk_number: int = 1
        packet = self.receive_single_chunk_gbn(chunk_number)

        if packet.sequence_number == 1:
            self.expected_sqn_number += 1
            self.sequence_number += 1

        while not packet.is_fin:
            chunk_number += 1
            packet = self.receive_single_chunk_gbn(chunk_number)

        self.logger.force_info("Download completed")
        self.download_completed = True
        self.file_handler.close(self.file)

    def receive_single_chunk_gbn(self, chunk_number: int) -> PacketGbn:
        sequence_number, packet = self.protocol.receive_file_chunk(self.sequence_number)

        if not self.expected_sqn_number == sequence_number:
            self.protocol.send_ack(self.sequence_number)
            return packet

        self.expected_sqn_number += 1
        self.sequence_number += 1

        if packet.is_fin:
            self.protocol.send_fin_ack(self.sequence_number)
        else:
            self.protocol.send_ack(self.sequence_number)

        self.logger.debug(f"Received chunk {chunk_number}")
        self.file_handler.append_to_file(self.file, packet)

        return packet

    def closing_handshake_gbn(self) -> None:
        self.protocol.wait_for_ack(self.sequence_number)
        self.logger.debug("Connection closed")

    def file_cleanup_after_error(self):
        if not self.file_handler.is_closed(self.file):
            self.file_handler.close(self.file)

        if self.download_completed:
            self.logger.debug(f"File {self.file_destination} is OK")
            return

        self.file_handler.remove_file_if_corrupted_or_incomplete(
            MutableVariable(self.file_destination),
            MutableVariable(None),
            is_path_complete=True,
        )

    def inform_name_to_download(self):
        self.sequence_number.step()
        self.logger.debug(
            f"Informing filename to download: {self.filename_for_download}"
        )
        self.protocol.inform_filename(self.sequence_number, self.filename_for_download)

        self.logger.debug("Waiting for filename confirmation")
        try:
            self.protocol.wait_for_ack(
                self.sequence_number,
                exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
            )
        except (UnexpectedFinMessage, MessageIsNotAck):
            self.logger.debug("Filename confirmation failed")
            raise FileDoesNotExist()

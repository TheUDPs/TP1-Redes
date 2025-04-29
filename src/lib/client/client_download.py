from os import getcwd
from sys import exit

from lib.client.abstract_client import Client
from lib.client.exceptions.file_does_not_exist import FileDoesNotExist
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.logger import Logger
from lib.common.constants import (
    DOWNLOAD_OPERATION,
    ERROR_EXIT_CODE,
    GO_BACK_N_PROTOCOL_TYPE,
)
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.common.file_handler import FileHandler
from lib.common.mutable_variable import MutableVariable
from lib.common.packet.packet import Packet


class DownloadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, dst: str, name: str, protocol: str
    ):
        self.file_destination: str = dst
        self.filename_for_download: str = name
        self.protocol_version: str = protocol

        try:
            self.file_handler: FileHandler = FileHandler(getcwd(), logger)
            self.file = self.file_handler.open_file_write_mode(
                dst, is_path_complete=True
            )
        except InvalidFilename:
            logger.error(f"File {self.file_destination} already exists")
            exit(ERROR_EXIT_CODE)

        super().__init__(logger, host, port, self.protocol_version)
        self.logger.debug(f"Location to save downloaded file: {self.file_destination}")
        self.download_completed = False

        if self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            self.expected_sqn_number: int = 1

    def perform_operation(self) -> None:
        self.perform_download()

    def perform_download(self) -> None:
        try:
            self.send_operation_intention(DOWNLOAD_OPERATION)
            self.inform_name_to_download()
            self.receive_file()
            self.closing_handshake()

        except (FileDoesNotExist, ConnectionLost) as e:
            self.logger.error(f"{e.message}")
            self.file_cleanup_after_error()

        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")
            self.file_cleanup_after_error()

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

    def receive_single_chunk(self, chunk_number: int) -> Packet:
        if self.protocol_version != GO_BACK_N_PROTOCOL_TYPE:
            self.sequence_number.step()

        self.sequence_number, packet = self.protocol.receive_file_chunk(
            self.sequence_number
        )

        if self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            if not self.expected_sqn_number == self.sequence_number:
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

    def receive_file(self) -> None:
        chunk_number: int = 1
        packet = self.receive_single_chunk(chunk_number)

        if self.protocol_version == GO_BACK_N_PROTOCOL_TYPE and packet.sequence_number == self.expected_sqn_number:
            self.expected_sqn_number += 1
            self.sequence_number += 1

        while not packet.is_fin:
            chunk_number += 1
            packet = self.receive_single_chunk(chunk_number)

        self.logger.force_info("Download completed")
        self.download_completed = True
        self.file_handler.close(self.file)

    def closing_handshake(self) -> None:
        if self.protocol_version != GO_BACK_N_PROTOCOL_TYPE:
            self.sequence_number.step()
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

from os import path, getcwd
from sys import exit

from lib.client.abstract_client import Client
from lib.client.exceptions.file_already_exists import FileAlreadyExists
from lib.client.exceptions.file_too_big import FileTooBig
from lib.client.protocol_gbn import ClientProtocolGbn
from lib.common.address import Address
from lib.common.constants import (
    UPLOAD_OPERATION,
    ERROR_EXIT_CODE,
    FILE_CHUNK_SIZE_SAW,
    GO_BACK_N_PROTOCOL_TYPE,
    STOP_AND_WAIT_PROTOCOL_TYPE,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.file_handler import FileHandler
from lib.common.logger import CoolLogger
from lib.client.go_back_n_sender_client import GoBackNSender
from lib.common.socket_gbn import SocketGbn


class UploadClient(Client):
    def __init__(
        self,
        logger: CoolLogger,
        host: str,
        port: int,
        src: str,
        name: str,
        protocol: str,
    ):
        self.src_filepath: str = src
        self.filename_in_server: str = name
        self.protocol_version: str = protocol

        try:
            self.file_handler: FileHandler = FileHandler(getcwd(), logger)
            self.file = self.file_handler.open_file_read_mode(
                self.src_filepath, is_path_complete=True
            )
            self.filesize = self.file_handler.get_filesize(
                self.src_filepath, is_path_complete=True
            )
        except InvalidFilename:
            logger.error(f"Could not find or open file {src}")
            exit(ERROR_EXIT_CODE)

        if name is None or name == "":
            self.filename_in_server = path.basename(self.src_filepath)

        super().__init__(logger, host, port, protocol)

    def perform_operation(self, server_address: Address) -> None:
        self.perform_upload(server_address)

    def perform_upload(self, server_address: Address) -> None:
        try:
            self.send_operation_intention(UPLOAD_OPERATION, server_address)
            self.inform_size_and_name()
            already_received_fin_back = self.send_file()
            self.initiate_close_connection(already_received_fin_back)

        except (FileAlreadyExists, FileTooBig, ConnectionLost) as e:
            self.logger.error(f"{e.message}")

            self.sequence_number.step()
            if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
                self.ack_number.step()

            self.handle_connection_finalization()
            self.file_cleanup_after_error()

        except SocketShutdown as e:
            self.logger.debug(f"{e.message}")
            self.file_cleanup_after_error()

        except Exception as e:
            err = e.message if hasattr(e, "message") else e
            self.logger.error(f"Error message: {err}")
            self.file_cleanup_after_error()

    def inform_filename(self):
        self.sequence_number.step()
        self.logger.debug(f"Informing filename: {self.filename_in_server}")

        if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            self.ack_number.step()

        self.protocol.inform_filename(
            self.sequence_number, self.ack_number, self.filename_in_server
        )

        self.logger.debug("Waiting for filename confirmation")

        try:
            self.protocol.wait_for_ack(
                self.sequence_number,
                self.ack_number,
                exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
            )
        except (UnexpectedFinMessage, MessageIsNotAck):
            self.logger.debug("Filename confirmation failed")
            raise FileAlreadyExists()

    def inform_filesize(self):
        self.sequence_number.step()
        self.logger.debug(f"Informing filesize: {self.filesize} bytes")

        if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            self.ack_number.step()

        self.protocol.inform_filesize(
            self.sequence_number, self.ack_number, self.filesize
        )

        self.logger.debug("Waiting for filesize confirmation")

        try:
            self.protocol.wait_for_ack(
                self.sequence_number,
                self.ack_number,
                exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
            )
        except (UnexpectedFinMessage, MessageIsNotAck):
            self.logger.debug("Filesize confirmation failed")
            raise FileTooBig()

    def inform_size_and_name(self) -> None:
        self.inform_filename()
        self.inform_filesize()

    def send_file(self) -> bool:
        if self.protocol_version == STOP_AND_WAIT_PROTOCOL_TYPE:
            self.send_file_saw()
            return False
        elif self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            already_received_fin_back = self.send_file_gbn()
            return already_received_fin_back

    def send_file_gbn(self) -> None:
        self.socket.reset_state()
        socket_gbn = SocketGbn(self.socket.socket, self.logger)

        gbn_protocol = ClientProtocolGbn(
            self.logger,
            socket_gbn,
            self.server_address,
            self.my_address,
            self.protocol.protocol_version,
        )

        gbn_sender = GoBackNSender(
            self.logger,
            gbn_protocol,
            self.file_handler,
            self.sequence_number,
            self.ack_number,
        )
        _seq, _ack, last_raw_packet, already_received_fin_back = gbn_sender.send_file(
            self.file, self.filesize, self.filename_in_server
        )
        self.sequence_number = _seq
        self.ack_number = _ack

        self.file_handler.close(self.file)

        self.socket.save_state(last_raw_packet, self.server_address)
        return already_received_fin_back

    def send_file_saw(self) -> None:
        chunk_number: int = 1
        total_chunks: int = self.file_handler.get_number_of_chunks(
            self.filesize, FILE_CHUNK_SIZE_SAW
        )
        is_last_chunk: bool = False

        self.logger.info(
            f"Sending file {self.filename_in_server} of {self.file_handler.bytes_to_megabytes(self.filesize)} MB"
        )

        while chunk := self.file_handler.read(self.file, FILE_CHUNK_SIZE_SAW):
            chunk_len = len(chunk)
            self.logger.debug(
                f"Sending chunk {chunk_number}/{total_chunks} of size {self.file_handler.bytes_to_kilobytes(chunk_len)} KB"
            )

            if chunk_number == total_chunks:
                is_last_chunk = True

            self.sequence_number.step()
            self.protocol.send_file_chunk_saw(
                self.sequence_number, chunk, chunk_len, is_last_chunk
            )

            self.logger.debug(
                f"Waiting confirmation for chunk {chunk_number}/{total_chunks}"
            )

            if not is_last_chunk:
                self.protocol.wait_for_ack(
                    self.sequence_number,
                    self.ack_number,
                )

            chunk_number += 1

        self.file_handler.close(self.file)

    def file_cleanup_after_error(self):
        if not self.file_handler.is_closed(self.file):
            self.file_handler.close(self.file)

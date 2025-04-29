from os import getcwd, path
from typing import List
from lib.client.abstract_client import Client
from lib.client.exceptions.file_already_exists import FileAlreadyExists
from lib.client.exceptions.file_too_big import FileTooBig
from lib.common.constants import (
    ERROR_EXIT_CODE,
    FILE_CHUNK_SIZE,
    MAX_ACK_REPEATED,
    UPLOAD_OPERATION,
    WINDOWS_SIZE,
    MAXIMUM_RETRANSMISSION_ATTEMPTS,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.max_retransmission_attempts import MaxRetransmissionAttempts
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.file_handler import FileHandler
from lib.common.logger import Logger


# TODO: work in progess, luego lo integramos a client_upload para no repetir codigo, igual que con dowload.
class UploadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, src: str, name: str, protocol: str
    ):
        self.src_filepath: str = src
        self.filename_in_server: str = name
        self.windows_size: int = WINDOWS_SIZE
        self.curr_sqn_number: int = 0
        self.expected_sqn_number: int = 1
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

    def inform_size_and_name(self) -> None:
        self.inform_filename()
        self.inform_filesize()

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

    def send_file(self) -> None:
        self.logger.debug(f"Sending file {self.src_filepath}")

        chunks: List[bytes] = self.separete_file_to_chunks()

        base: int = 0
        next_seq_num: int = 0
        total_chunks: int = len(chunks)
        retransmission_attempts: int = 0

        while base < total_chunks:
            # MIEntras aun quede data que enviar, enviamos los paquetes dentro de la ventana
            while next_seq_num < base + self.windows_size and next_seq_num < total_chunks:
                is_last_chunk = next_seq_num == total_chunks - 1
                chunk = chunks[next_seq_num]
                self.protocol.send_file_chunk(
                    self.sequence_number, chunk, len(chunk), is_last_chunk
                )
                self.logger.debug(f"Sent chunk {next_seq_num}")
                self.sequence_number += 1
                next_seq_num += 1

            try:
                # TODO: ver bien tema de timeout, verificar que lo que recibo es ack, y revisar todo
                ack_seq_num, ack_packet = self.protocol.wait_for_ack(
                    self.sequence_number,
                    exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
                )

                if ack_seq_num >= base:
                    self.logger.debug(f"ACK received for chunk {ack_seq_num}")
                    base = ack_seq_num + 1
                    retransmission_attempts = 0
                else:
                    self.logger.debug(f"Duplicate ACK received for chunk {ack_seq_num}")
            except TimeoutError:
                self.logger.debug("Timeout occurred, retransmitting window")
                retransmission_attempts += 1
                if retransmission_attempts > MAXIMUM_RETRANSMISSION_ATTEMPTS:
                    raise MaxRetransmissionAttempts()
                next_seq_num = base

        self.logger.force_info("File transfer complete")
        self.file_handler.close(self.file)

    def separete_file_to_chunks(self) -> List[bytes]:
        total_chunks: int = self.file_handler.get_number_of_chunks(
            self.filesize, FILE_CHUNK_SIZE
        )
        # Todo: modificar para no levantar todo el file en memoria, mejor ir levantando de a ventanas en memoria
        chunk_list: list[bytes] = []

        for _ in range(total_chunks):
            chunk = self.file_handler.read(self.file, FILE_CHUNK_SIZE)
            chunk_list.append(chunk)

        return chunk_list

    def closing_handshake(self) -> None:
        self.sequence_number.step()
        self.protocol.send_ack(self.sequence_number)
        self.logger.debug("Connection closed")

    def file_cleanup_after_error(self) -> None:
        if not self.file_handler.is_closed(self.file):
            self.file_handler.close(self.file)

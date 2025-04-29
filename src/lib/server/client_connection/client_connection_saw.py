from lib.common.address import Address
from lib.common.constants import (
    FILE_CHUNK_SIZE,
)
from lib.common.logger import Logger
from lib.common.mutable_variable import MutableVariable
from lib.common.packet.packet import Packet
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_saw import SocketSaw
from lib.server.client_connection.abstract_client_connection import ClientConnection
from lib.server.connection_state import ConnectionState
from lib.common.file_handler import FileHandler


class ClientConnectionSaw(ClientConnection):
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
        super().__init__(
            connection_socket,
            connection_address,
            client_address,
            protocol,
            logger,
            file_handler,
            initial_sequence_number,
        )

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

        sequence_number.value.step()
        packet = self.receive_single_chunk(sequence_number, chunk_number)

        while not packet.is_fin:
            chunk_number += 1
            sequence_number.value.step()
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

            sequence_number.value.step()
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

    def closing_handshake_for_upload(self, sequence_number: MutableVariable):
        sequence_number.value.step()
        self.protocol.wait_for_ack(sequence_number.value)
        self.logger.debug("Connection closed")
        self.state = ConnectionState.DONE_READY_TO_DIE

    def closing_handshake_for_download(self, sequence_number: MutableVariable):
        sequence_number.value.step()
        self.protocol.send_ack(sequence_number.value, self.client_address, self.address)
        self.logger.debug("Connection closed")
        self.state = ConnectionState.DONE_READY_TO_DIE

    def perform_upload(
        self,
        sequence_number: MutableVariable,
        filename_for_upload: MutableVariable,
        filesize_for_upload: MutableVariable,
    ):
        self.receive_file(sequence_number, filename_for_upload, filesize_for_upload)
        self.closing_handshake_for_upload(sequence_number)

    def perform_download(
        self, sequence_number: MutableVariable, filename_for_download: MutableVariable
    ):
        self.transmit_file(sequence_number, filename_for_download)
        self.closing_handshake_for_download(sequence_number)

    def is_ready_to_die(self) -> bool:
        return (
            self.state == ConnectionState.DONE_READY_TO_DIE
            or self.state == ConnectionState.UNRECOVERABLE_BAD_STATE
        )

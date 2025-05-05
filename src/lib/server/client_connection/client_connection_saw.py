from _socket import SHUT_RDWR

from lib.common.address import Address
from lib.common.constants import (
    FILE_CHUNK_SIZE_SAW,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.logger import CoolLogger
from lib.common.mutable_variable import MutableVariable
from lib.common.packet.packet import Packet
from lib.common.socket_saw import SocketSaw
from lib.server.client_connection.abstract_client_connection import ClientConnection
from lib.server.connection_state import ConnectionState
from lib.common.file_handler import FileHandler

NO_ACK_NUMBER = MutableVariable(None)


class ClientConnectionSaw(ClientConnection):
    def __init__(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        protocol: str,
        logger: CoolLogger,
        file_handler: FileHandler,
        packet: Packet,
    ):
        super().__init__(
            connection_socket,
            connection_address,
            client_address,
            protocol,
            logger,
            file_handler,
            packet,
        )

        self.socket.reset_state()

    def receive_single_chunk(
        self, sequence_number: MutableVariable, chunk_number: int
    ) -> Packet:
        _seq, packet = self.protocol.receive_file_chunk(sequence_number.value)
        sequence_number.value = _seq

        if not packet.is_fin:
            self.protocol.send_ack(
                sequence_number.value,
                NO_ACK_NUMBER.value,
                self.client_address,
                self.address,
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
        _filename, _filesize = self.receive_file_info_for_upload(
            sequence_number, NO_ACK_NUMBER
        )
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
        _filename, filesize = self.receive_file_info_for_download(
            sequence_number, NO_ACK_NUMBER
        )
        filename.value = _filename

        self.logger.debug(f"Ready to transmit to {self.client_address}")

        chunk_number: int = 1
        total_chunks: int = self.file_handler.get_number_of_chunks(
            filesize, FILE_CHUNK_SIZE_SAW
        )
        is_last_chunk: bool = False
        is_first_chunk: bool = True

        self.logger.info(
            f"Sending file {filename.value} of {self.file_handler.bytes_to_megabytes(filesize)} MB"
        )

        while chunk := self.file_handler.read(self.file, FILE_CHUNK_SIZE_SAW):
            chunk_len = len(chunk)
            self.logger.debug(
                f"Sending chunk {chunk_number}/{total_chunks} of size {self.file_handler.bytes_to_kilobytes(chunk_len)} KB"
            )

            if chunk_number == total_chunks:
                is_last_chunk = True

            if not is_first_chunk:
                sequence_number.value.step()

            self.protocol.send_file_chunk(
                sequence_number.value,
                None,
                chunk,
                chunk_len,
                is_last_chunk,
                is_first_chunk,
                self.client_address,
            )

            if not is_last_chunk:
                self.logger.debug(f"Waiting confirmation for chunk {chunk_number}")
                self.protocol.wait_for_ack(sequence_number.value)

            chunk_number += 1
            is_first_chunk = False

    def closing_handshake_for_upload(self, sequence_number: MutableVariable):
        try:
            self.logger.debug("Connection finalization received. Confirming it")
            self.protocol.send_ack(
                sequence_number.value,
                NO_ACK_NUMBER.value,
                self.client_address,
                self.address,
            )

            self.logger.debug("Sending own connection finalization")
            self.protocol.send_fin(
                sequence_number.value,
                NO_ACK_NUMBER.value,
                self.client_address,
                self.address,
            )

            sequence_number.value.step()
            try:
                self.protocol.wait_for_ack(
                    sequence_number.value, exceptions_to_let_through=[ConnectionLost]
                )
            except ConnectionLost:
                pass

            self.logger.info("Connection closed")
        except SocketShutdown:
            self.logger.info("Connection closed")
        finally:
            self.state = ConnectionState.DONE_READY_TO_DIE

    def closing_handshake_for_download(self, sequence_number: MutableVariable):
        self.logger.debug("Waiting for confirmation of last packet")
        self.protocol.wait_for_fin_or_ack(sequence_number.value)

        self.logger.force_info("File transfer complete")
        self.logger.debug("Received connection finalization from server")
        sequence_number.value.step()
        self.protocol.send_ack(
            sequence_number.value,
            NO_ACK_NUMBER.value,
            self.client_address,
            self.address,
        )
        self.state = ConnectionState.DONE_READY_TO_DIE

    def perform_upload(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_upload: MutableVariable,
        filesize_for_upload: MutableVariable,
    ):
        self.receive_file(sequence_number, filename_for_upload, filesize_for_upload)
        self.closing_handshake_for_upload(sequence_number)

    def perform_download(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_download: MutableVariable,
    ):
        self.transmit_file(sequence_number, filename_for_download)
        self.closing_handshake_for_download(sequence_number)

    def is_ready_to_die(self) -> bool:
        return (
            self.state == ConnectionState.DONE_READY_TO_DIE
            or self.state == ConnectionState.UNRECOVERABLE_BAD_STATE
        )

    def kill(self):
        try:
            self.socket.shutdown(SHUT_RDWR)
        except (OSError, SocketShutdown):
            try:
                self.socket.close()
            except (OSError, SocketShutdown):
                pass

        try:
            self.run_thread.join()
            self.killed = True
        except RuntimeError:
            pass

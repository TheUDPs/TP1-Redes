from _socket import SHUT_RDWR

from lib.common.address import Address
from lib.common.constants import FILE_CHUNK_SIZE_GBN
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.logger import Logger
from lib.common.mutable_variable import MutableVariable
from lib.common.packet.packet import Packet
from lib.common.socket_gbn import SocketGbn, RetransmissionNeeded
from lib.common.socket_saw import SocketSaw
from lib.server.client_connection.abstract_client_connection import ClientConnection
from lib.common.file_handler import FileHandler
from lib.server.connection_state import ConnectionState
from lib.server.go_back_n_receiver import GoBackNReceiver
from lib.server.go_back_n_sender import GoBackNSender
from lib.server.protocol_gbn import ServerProtocolGbn


class ClientConnectionGbn(ClientConnection):
    def __init__(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        protocol: str,
        logger: Logger,
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
        self.socket_gbn = None

    def receive_file(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename: MutableVariable,
        filesize: MutableVariable,
    ):
        _filename, _filesize = self.receive_file_info_for_upload(
            sequence_number, ack_number
        )
        filename.value = _filename
        filesize.value = _filesize

        self.logger.debug(f"Ready to receive from {self.client_address}")

        last_transmitted_packet = self.socket.last_raw_packet

        self.socket.reset_state()
        self.socket_gbn = SocketGbn(self.socket.socket, self.logger)
        gbn_protocol = ServerProtocolGbn(
            self.logger,
            self.socket_gbn,
            self.client_address,
            self.address,
            self.protocol.protocol_version,
            self.protocol.clients,
        )

        gbn_sender = GoBackNReceiver(
            self.logger,
            gbn_protocol,
            self.file_handler,
            sequence_number.value,
            ack_number.value,
        )
        try:
            _seq, _ack = gbn_sender.receive_file(self.file, last_transmitted_packet)
            sequence_number.value = _seq
            ack_number.value = _ack
        except RetransmissionNeeded:
            raise ConnectionLost()
            # self.logger.error("Retransmission needed. State is unrecoverable")

        self.logger.debug("Finished receiving file")
        self.file_handler.close(self.file)

    def perform_upload(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_upload: MutableVariable,
        filesize_for_upload: MutableVariable,
    ):
        self.receive_file(
            sequence_number, ack_number, filename_for_upload, filesize_for_upload
        )
        self.closing_handshake_for_upload(sequence_number, ack_number)

    def send_first_packet(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename: str,
        filesize: int,
    ):
        chunk_number: int = 1
        total_chunks: int = self.file_handler.get_number_of_chunks(
            filesize, FILE_CHUNK_SIZE_GBN
        )
        is_last_chunk: bool = False
        is_first_chunk: bool = True

        self.logger.info(
            f"Sending file {filename} of {self.file_handler.bytes_to_megabytes(filesize)} MB"
        )

        chunk = self.file_handler.read(self.file, FILE_CHUNK_SIZE_GBN)
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
            ack_number.value,
            chunk,
            chunk_len,
            is_last_chunk,
            is_first_chunk,
            self.client_address,
        )

        self.logger.debug(f"Waiting confirmation for chunk {chunk_number}")

        if not is_last_chunk:
            self.protocol.wait_for_ack(sequence_number.value)

    def send_file(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_download: MutableVariable,
    ):
        _filename, filesize = self.receive_file_info_for_download(
            sequence_number, ack_number
        )
        filename_for_download.value = _filename

        self.send_first_packet(
            sequence_number, ack_number, filename_for_download.value, filesize
        )

        self.socket.reset_state()
        socket_gbn = SocketGbn(self.socket.socket, self.logger)

        gbn_protocol = ServerProtocolGbn(
            self.logger,
            socket_gbn,
            self.client_address,
            self.address,
            self.protocol.protocol_version,
            self.protocol.clients,
        )

        gbn_sender = GoBackNSender(
            self.logger,
            gbn_protocol,
            self.file_handler,
            sequence_number.value,
            ack_number.value,
        )

        _seq, _ack = gbn_sender.send_file(
            self.file, filesize, filename_for_download.value
        )
        sequence_number.value = _seq
        ack_number.value = _ack

        self.file_handler.close(self.file)

    def perform_download(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_download: MutableVariable,
    ):
        self.send_file(sequence_number, ack_number, filename_for_download)
        self.closing_handshake_for_download(sequence_number, ack_number)

    def closing_handshake_for_upload(
        self, sequence_number: MutableVariable, ack_number: MutableVariable
    ):
        try:
            self.logger.debug("Connection finalization received. Confirming it")
            self.protocol.send_ack(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )

            self.logger.debug("Sending own connection finalization")
            self.protocol.send_fin(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )

            sequence_number.value.step()
            try:
                self.protocol.wait_for_ack(
                    sequence_number.value, exceptions_to_let_through=[ConnectionLost]
                )
            except (ConnectionLost, MessageIsNotAck):
                pass

            self.logger.info("Connection closed")
        except SocketShutdown:
            self.logger.info("Connection closed")
        finally:
            self.state = ConnectionState.DONE_READY_TO_DIE

    def closing_handshake_for_download(
        self, sequence_number: MutableVariable, ack_number: MutableVariable
    ):
        self.logger.debug("Waiting for confirmation of last packet")
        self.protocol.wait_for_fin_or_ack(sequence_number.value)

        self.logger.force_info("File transfer complete")
        self.logger.debug("Received connection finalization from server")
        sequence_number.value.step()
        self.protocol.send_ack(
            sequence_number.value,
            ack_number.value,
            self.client_address,
            self.address,
        )
        self.state = ConnectionState.DONE_READY_TO_DIE

    def is_ready_to_die(self) -> bool:
        return (
            self.state == ConnectionState.DONE_READY_TO_DIE
            or self.state == ConnectionState.UNRECOVERABLE_BAD_STATE
        )

    def kill(self):
        try:
            if self.socket_gbn is not None:
                self.socket_gbn.shutdown(SHUT_RDWR)
        except (OSError, SocketShutdown):
            try:
                if self.socket_gbn is not None:
                    self.socket_gbn.close()
            except (OSError, SocketShutdown):
                pass

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

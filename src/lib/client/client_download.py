from os import getcwd
from sys import exit

from lib.client.abstract_client import Client
from lib.client.exceptions.file_does_not_exist import FileDoesNotExist
from lib.client.go_back_n_receiver_client import GoBackNReceiver
from lib.client.protocol_gbn import ClientProtocolGbn
from lib.common.address import Address
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.retransmission_needed import RetransmissionNeeded
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.hash_compute import compute_chunk_sha256
from lib.common.logger import CoolLogger
from lib.common.constants import (
    DOWNLOAD_OPERATION,
    ERROR_EXIT_CODE,
    GO_BACK_N_PROTOCOL_TYPE,
    STOP_AND_WAIT_PROTOCOL_TYPE,
    SHOULD_PRINT_CHUNK_HASH,
)
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.common.file_handler import FileHandler
from lib.common.mutable_variable import MutableVariable
from lib.common.packet.packet import Packet
from lib.common.socket_gbn import SocketGbn


class DownloadClient(Client):
    def __init__(
        self,
        logger: CoolLogger,
        host: str,
        port: int,
        dst: str,
        name: str,
        protocol: str,
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
        self.logger.debug(
            f"Location to save downloaded file: {self.file_destination}")
        self.download_completed = False

        if self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            self.expected_sqn_number: int = 1

    def perform_operation(self, server_address: Address) -> None:
        self.perform_download(server_address)

    def perform_download(self, server_address: Address) -> None:
        try:
            self.send_operation_intention(
                DOWNLOAD_OPERATION, server_address)
            packet = self.inform_name_to_download()
            self.receive_file(packet)
            self.handle_connection_finalization()

        except (FileDoesNotExist, ConnectionLost, SocketShutdown) as e:
            self.logger.error(f"{e.message}")

            self.sequence_number.step()
            if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
                self.ack_number.step()

            self.handle_connection_finalization()
            self.file_cleanup_after_error()

        except Exception as e:
            err = e.message if hasattr(e, "message") else e
            self.logger.error(f"Error message: {err}")
            self.file_cleanup_after_error()

    def inform_name_to_download(self) -> Packet:
        self.sequence_number.step()

        if self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            self.ack_number.step()

        self.logger.debug(
            f"Informing filename to download: {self.filename_for_download}"
        )
        self.protocol.inform_filename(
            self.sequence_number,
            self.ack_number,
            self.filename_for_download)

        self.logger.debug("Waiting for filename confirmation")
        try:
            packet = self.protocol.wait_for_ack(
                self.sequence_number,
                self.ack_number,
                exceptions_to_let_through=[
                    UnexpectedFinMessage, MessageIsNotAck],
            )
            return packet
        except UnexpectedFinMessage as e:
            if e.packet.payload_length > 0:
                return e.packet
            else:
                self.logger.debug("Filename confirmation failed")
                raise FileDoesNotExist()

        except MessageIsNotAck:
            self.logger.debug("Filename confirmation failed")
            raise FileDoesNotExist()

    def receive_single_chunk(self, chunk_number: int) -> Packet:
        if self.protocol_version != GO_BACK_N_PROTOCOL_TYPE:
            self.sequence_number.step()

        self.sequence_number, packet = self.protocol.receive_file_chunk_saw(
            self.sequence_number)

        if self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            if not self.expected_sqn_number == self.sequence_number:
                self.protocol.send_ack(
                    self.sequence_number, self.ack_number
                )  # We send the last in order ack
                return packet

            self._update_sqn_and_excpected()

        if not packet.is_fin:
            self.protocol.send_ack(self.sequence_number, self.ack_number)

        self.logger.debug(f"Received chunk {chunk_number}")
        self.file_handler.append_to_file(self.file, packet)

        return packet

    def receive_file_saw(self, first_chunk_packet: Packet) -> None:
        chunk_number: int = 1

        packet = first_chunk_packet
        if not packet.is_fin:
            self.protocol.send_ack(self.sequence_number, self.ack_number)

        self.logger.debug(f"Received chunk {chunk_number}")
        self.file_handler.append_to_file(self.file, packet)

        if (
            self.protocol_version == GO_BACK_N_PROTOCOL_TYPE
            and packet.sequence_number == self.expected_sqn_number
        ):
            self._update_sqn_and_excpected()

        while not packet.is_fin:
            chunk_number += 1
            packet = self.receive_single_chunk(chunk_number)

        self.logger.force_info("Download completed")
        self.download_completed = True
        self.file_handler.close(self.file)

    def receive_file_gbn(self, first_chunk_packet: Packet) -> None:
        self.logger.debug(f"Ready to receive from {self.server_address}")

        chunk_number: int = 1

        packet = first_chunk_packet
        if not packet.is_fin:
            self.protocol.send_ack(self.sequence_number, self.ack_number)

        msg = f"Received chunk {chunk_number}. "

        if SHOULD_PRINT_CHUNK_HASH:
            msg += f"Hash is: {compute_chunk_sha256(packet.data)}"

        self.logger.debug(msg)

        self.file_handler.append_to_file(self.file, packet)

        if not packet.is_fin:
            last_transmitted_packet = self.socket.last_raw_packet

            self.socket.reset_state()
            socket_gbn = SocketGbn(self.socket.socket, self.logger)
            gbn_protocol = ClientProtocolGbn(
                self.logger,
                socket_gbn,
                self.server_address,
                self.my_address,
                self.protocol.protocol_version,
            )

            gbn_receiver = GoBackNReceiver(
                self.logger,
                gbn_protocol,
                self.file_handler,
                self.sequence_number,
                self.ack_number,
            )

            try:
                _seq, _ack = gbn_receiver.receive_file(
                    self.file, last_transmitted_packet
                )
                self.sequence_number = _seq
                self.ack_number = _ack
            except RetransmissionNeeded:
                self.logger.error(
                    "Retransmission needed. Unhandled exception")

        self.logger.force_info("Download completed")
        self.download_completed = True
        self.file_handler.close(self.file)

    def receive_file(self, first_chunk_packet: Packet) -> None:
        if self.protocol_version == STOP_AND_WAIT_PROTOCOL_TYPE:
            self.receive_file_saw(first_chunk_packet)
        elif self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            self.receive_file_gbn(first_chunk_packet)

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

    def _update_sqn_and_excpected(self) -> None:
        self.expected_sqn_number += 1
        self.sequence_number.step()

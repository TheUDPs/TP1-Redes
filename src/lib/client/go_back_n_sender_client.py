from time import time

from lib.client.protocol_gbn import ClientProtocolGbn
from lib.common.constants import (
    WINDOW_SIZE,
    FILE_CHUNK_SIZE_GBN,
    SOCKET_RETRANSMIT_WINDOW_TIMEOUT,
)
from lib.common.exceptions.retransmission_needed import RetransmissionNeeded
from lib.common.file_handler import FileHandler
from lib.common.hash_compute import compute_chunk_sha256
from lib.common.logger import Logger
from typing import List

from lib.common.mutable_variable import MutableVariable
from lib.common.sequence_number import SequenceNumber


class GoBackNSender:
    def __init__(
        self,
        logger: Logger,
        protocol: ClientProtocolGbn,
        file_handler: FileHandler,
        sequence_number: SequenceNumber,
        ack_number: SequenceNumber,
    ) -> None:
        self.base: SequenceNumber = SequenceNumber(0, protocol.protocol_version)
        self.logger: Logger = logger
        self.protocol: ClientProtocolGbn = protocol
        self.sqn_number: SequenceNumber = sequence_number
        self.offset_initial_seq_number: SequenceNumber = sequence_number
        self.ack_number: SequenceNumber = ack_number
        self.next_seq_num: SequenceNumber = SequenceNumber(0, protocol.protocol_version)
        self.file_handler: FileHandler = file_handler

        self.last_ack = self.ack_number.clone()
        self.oldest_packet = None
        self.spent_in_reception: float = 0.0

        self.sqn_number.step()
        self.ack_number.step()

    def reset_window(self):
        self.logger.debug(
            f"Reseting next sequence number to base packet number {self.base.value + 1}"
        )
        self.next_seq_num.value = self.base.value
        self.spent_in_reception = 0.0

    def send_file(
        self, file, filesize: int, filename: str
    ) -> tuple[SequenceNumber, SequenceNumber, bytes]:
        self.logger.debug(
            f"Sending file '{filename}' with window size of {WINDOW_SIZE} packets"
        )

        chunks: List[bytes] = self.split_file_in_chunks(file, filesize)
        total_chunks: int = len(chunks)
        pending_last_ack = False
        last_raw_packet = MutableVariable(None)

        while self.base.value < total_chunks and not pending_last_ack:
            last_raw_packet.value = self.send_packets_in_window(total_chunks, chunks)

            try:
                pending_last_ack = self.await_ack_phase(total_chunks)
            except RetransmissionNeeded:
                self.logger.debug("Retransmission is needed")
                self.reset_window()

        return (
            SequenceNumber(
                self.next_seq_num.value + self.offset_initial_seq_number.value - 1,
                self.protocol.protocol_version,
            ),
            SequenceNumber(self.ack_number.value, self.protocol.protocol_version),
            last_raw_packet.value,
        )

    def send_packets_in_window(self, total_chunks: int, chunks: List[bytes]) -> bytes:
        packet = MutableVariable(None)

        while (
            self.next_seq_num.value < self.base.value + WINDOW_SIZE
            and self.next_seq_num.value < total_chunks
        ):
            is_last_chunk = self.next_seq_num.value == total_chunks - 1
            chunk_to_send = chunks[self.next_seq_num.value]
            chunk_len = len(chunk_to_send)

            msg = f"Sending chunk {self.next_seq_num.value + 1}/{total_chunks} of size {self.file_handler.bytes_to_kilobytes(chunk_len)} KB. "
            msg += f"Hash is: {compute_chunk_sha256(chunk_to_send)}"
            self.logger.debug(msg)

            seq_number_to_send = SequenceNumber(
                self.next_seq_num.value + self.offset_initial_seq_number.value,
                self.protocol.protocol_version,
            )

            packet.value = self.protocol.send_file_chunk(
                seq_number_to_send,
                self.ack_number,
                chunk_to_send,
                chunk_len,
                is_last_chunk,
            )
            self.next_seq_num.step()

        return packet.value

    def await_ack_phase(self, total_chunks: int) -> bool:
        is_last_chunk_acked = MutableVariable(self.base.value + 1 == total_chunks)
        if is_last_chunk_acked.value:
            return True

        start_time: float = time()
        packet = self.protocol.wait_for_ack(self.sqn_number, self.ack_number)
        if not packet.is_ack and packet.is_fin:
            is_last_chunk_acked.value = True

        reception_duration: float = time() - start_time

        if packet.ack_number >= self.ack_number.value:
            self.base.value += packet.ack_number - self.ack_number.value
            self.logger.debug(f"Received ack of packet {self.base.value + 1}")
            self.last_ack = self.ack_number.clone()
            self.ack_number = SequenceNumber(
                packet.ack_number, self.protocol.protocol_version
            )
            self.protocol.socket.set_timeout(SOCKET_RETRANSMIT_WINDOW_TIMEOUT)
            self.spent_in_reception = 0
        else:
            self.logger.warn(
                f"Detected ACK from packet {packet.ack_number - self.offset_initial_seq_number.value + 1}"
            )
            self.logger.debug(
                f"Acumulated {reception_duration} before retransmission needed. Totalling {self.spent_in_reception}"
            )
            self.spent_in_reception += reception_duration
            if self.spent_in_reception >= SOCKET_RETRANSMIT_WINDOW_TIMEOUT:
                raise RetransmissionNeeded()

        return is_last_chunk_acked.value

    def split_file_in_chunks(self, file, filesize) -> List[bytes]:
        total_chunks: int = self.file_handler.get_number_of_chunks(
            filesize, FILE_CHUNK_SIZE_GBN
        )

        chunk_list: list[bytes] = []

        for _ in range(total_chunks):
            chunk = self.file_handler.read(file, FILE_CHUNK_SIZE_GBN)
            if len(chunk) > 0:
                chunk_list.append(chunk)

        return chunk_list

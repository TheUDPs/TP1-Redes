from time import sleep

from lib.client.protocol_gbn import ClientProtocolGbn
from lib.common.constants import (
    MAX_ACK_REPEATED,
    MAXIMUM_RETRANSMISSION_ATTEMPTS,
    WINDOW_SIZE,
    FILE_CHUNK_SIZE_GBN,
)
from lib.common.file_handler import FileHandler
from lib.common.logger import Logger
from typing import List
from lib.common.exceptions.max_retransmission_attempts import MaxRetransmissionAttempts
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
        # self.windows_size: int = WINDOWS_SIZE
        self.base: SequenceNumber = SequenceNumber(0, protocol.protocol_version)
        self.logger: Logger = logger
        self.protocol: ClientProtocolGbn = protocol
        self.sqn_number: SequenceNumber = sequence_number
        self.offset_initial_seq_number: SequenceNumber = sequence_number
        self.ack_number: SequenceNumber = ack_number
        self.next_seq_num: SequenceNumber = SequenceNumber(0, protocol.protocol_version)
        self.file_handler: FileHandler = file_handler

        self.last_ack = self.ack_number.clone()

        self.sqn_number.step()
        self.ack_number.step()

    def send_file(
        self, file, filesize: int, filename: str
    ) -> tuple[SequenceNumber, SequenceNumber]:
        self.logger.debug(
            f"Sending file '{filename}' with window size of {WINDOW_SIZE} packets"
        )

        chunks: List[bytes] = self.split_file_in_chunks(file, filesize)

        total_chunks: int = len(chunks)
        pending_last_ack = False
        while self.base.value < total_chunks and not pending_last_ack:
            self.send_packets_in_window(total_chunks, chunks)

            try:
                pending_last_ack = self.await_ack_phase(total_chunks)
            except TimeoutError:
                raise MaxRetransmissionAttempts()

        return (
            SequenceNumber(
                self.next_seq_num.value + self.offset_initial_seq_number.value - 1,
                self.protocol.protocol_version,
            ),
            SequenceNumber(self.ack_number.value, self.protocol.protocol_version),
        )

    def send_packets_in_window(self, total_chunks: int, chunks: List[bytes]) -> None:
        while (
            self.next_seq_num.value < self.base.value + WINDOW_SIZE
            and self.next_seq_num.value < total_chunks
        ):
            is_last_chunk = self.next_seq_num.value == total_chunks - 1
            chunk_to_send = chunks[self.next_seq_num.value]
            chunk_len = len(chunk_to_send)

            self.logger.debug(
                f"Sending chunk {self.next_seq_num.value + 1}/{total_chunks} of size {self.file_handler.bytes_to_kilobytes(chunk_len)} KB"
            )

            if is_last_chunk:
                self.logger.debug("Sending the last chunk")

            seq_number_to_send = SequenceNumber(
                self.next_seq_num.value + self.offset_initial_seq_number.value,
                self.protocol.protocol_version,
            )

            self.protocol.send_file_chunk(
                seq_number_to_send,
                self.ack_number,
                chunk_to_send,
                chunk_len,
                is_last_chunk,
            )
            self.next_seq_num.step()
            sleep(0.01)

    def await_ack_phase(self, total_chunks: int) -> bool:
        # espero el ack
        # si no llega
        # hago time out y reenvio todo desde la base de la windows
        # si llega el ack
        # si es nuevo ack registro y continuo
        # si no es nuevo ack (es ack repetido) amplio la cuenta hasta llegar a 4. Si llega a 4 retransmitir toda la ventada

        repeated_ack_counter = ()
        repeated_ack_global_counter: int = 0
        ## Esto no va a andar, necesito algo que simplemente reciba un ack
        # Acá habría que esperar el timeout del expected_sqn_number
        is_last_chunk_acked = (
            self.ack_number.value - self.offset_initial_seq_number.value
            == total_chunks - 1
        )
        if is_last_chunk_acked:
            return True

        packet = self.protocol.wait_for_ack(self.sqn_number, self.ack_number)

        if (
            packet.ack_number == self.ack_number.value
            and packet.ack_number == self.last_ack.value
        ):
            self.logger.debug(f"Received repeated ack {repeated_ack_counter} ")

            if repeated_ack_counter == MAX_ACK_REPEATED:
                if MAXIMUM_RETRANSMISSION_ATTEMPTS == repeated_ack_global_counter:
                    raise MaxRetransmissionAttempts()

                self.logger.debug(f"Received repeated ack {self.base} ")
                self.base.value = (
                    self.ack_number.value + 1 - self.offset_initial_seq_number.value
                )

        elif packet.ack_number >= self.ack_number.value:
            self.logger.debug(f"Received ack of packet {self.base.value + 1}")
            self.base.value += packet.ack_number - self.ack_number.value
            self.last_ack = self.ack_number.clone()
            self.ack_number = SequenceNumber(
                packet.ack_number, self.protocol.protocol_version
            )

            # self.ack_number.step()
            if self.base.value == self.next_seq_num:
                # self.protocol.stop_timer()
                pass
            else:
                # start_timer
                pass

        return False

    # Could read window instead of full file
    def split_file_in_chunks(self, file, filesize) -> List[bytes]:
        total_chunks: int = self.file_handler.get_number_of_chunks(
            filesize, FILE_CHUNK_SIZE_GBN
        )

        chunk_list: list[bytes] = []

        for _ in range(total_chunks):
            chunk = self.file_handler.read(file, FILE_CHUNK_SIZE_GBN)
            chunk_list.append(chunk)

        return chunk_list

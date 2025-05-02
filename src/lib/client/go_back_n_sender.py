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
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.max_retransmission_attempts import MaxRetransmissionAttempts
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
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
        self.base: int = 0
        self.logger: Logger = logger
        self.protocol: ClientProtocolGbn = protocol
        self.sqn_number: SequenceNumber = sequence_number
        self.ack_number: SequenceNumber = ack_number
        self.next_seq_num: int = 0
        self.file_handler: FileHandler = file_handler

    def send_file(self, file, filesize: int) -> None:
        self.logger.debug(f"Sending file {file}")

        chunks: List[bytes] = self.separete_file_to_chunks(file, filesize)

        total_chunks: int = len(chunks)

        # Propuesta:
        # self.protocol.start_timer()
        # o sino manejar el timer acá
        while self.base < total_chunks:
            # MIEntras aun quede data que enviar, enviamos los paquetes dentro de la ventana
            self.send_packets_in_window(total_chunks, chunks, filesize)

            try:
                self.await_ack_phase(total_chunks, chunks, filesize)
            except TimeoutError:
                raise MaxRetransmissionAttempts()

    def await_ack_phase(
        self, total_chunks: int, chunks: List[bytes], filesize: int
    ) -> None:
        # espero el ack
        # si no llegaa
        # hago time out y reenvio todo desde la base de la windows
        # si llega el ack
        # si es nuevo ack registro y continuo
        # si no es nuevo ack (es ack repetido) amplio la cuenta hasta llegar a 4. Si llega a 4 retransmitir toda la ventada

        ack_counter: int = 0
        global_counter: int = 0
        ## Esto no va a andar, necesito algo que simplemente reciba un ack
        # Acá habría que esperar el timeout del expected_sqn_number
        ack_seq_num, packet = self.protocol.wait_for_ack(
            self.sqn_number,
            exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
        )

        if ack_seq_num != self.base:
            self.logger.debug(f"Received repeated ack {ack_counter} ")

            if ack_counter == MAX_ACK_REPEATED:
                if MAXIMUM_RETRANSMISSION_ATTEMPTS == global_counter:
                    raise MaxRetransmissionAttempts()

                self.logger.debug(f"Received repeated ack {self.base} ")
                self.base = ack_seq_num + 1
                self.send_packets_in_window(total_chunks, chunks, filesize)
        else:  # CASO FELIZ
            self.logger.debug(f"Received ack {self.base} ")
            # self.expected_sqn_number += 1
            self.base = ack_seq_num + 1
            if self.base == self.next_seq_num:
                # self.protocol.stop_timer()
                pass
            else:
                # start_timer
                pass

        return

    def send_packets_in_window(
        self, total_chunks: int, chunks: List[bytes], filesize
    ) -> None:
        while (
            self.next_seq_num < self.base + WINDOW_SIZE
            and self.next_seq_num < total_chunks
        ):
            is_last_chunk = self.next_seq_num == total_chunks - 1
            chunk = chunks[self.next_seq_num]
            self.protocol.send_file_chunk(
                self.next_seq_num, chunk, len(chunk), is_last_chunk
            )
            if self.base == self.next_seq_num:
                pass
                # INICIAR TIMER
                # self.protocol.start_timer(self.sqn_number)
            # self.sqn_number += 1
            self.next_seq_num += 1

            self.logger.debug(f"Sent chunk {self.next_seq_num}")
        # REFUSE DATA
        pass

    # Could read window instead of full file
    def separete_file_to_chunks(self, file, filesize) -> List[bytes]:
        total_chunks: int = self.file_handler.get_number_of_chunks(
            filesize, FILE_CHUNK_SIZE_GBN
        )

        chunk_list: list[bytes] = []

        for _ in range(total_chunks):
            chunk = self.file_handler.read(file, FILE_CHUNK_SIZE_GBN)
            chunk_list.append(chunk)

        return chunk_list

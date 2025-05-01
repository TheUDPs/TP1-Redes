from lib.common.constants import (
    FILE_CHUNK_SIZE,
    MAX_ACK_REPEATED,
    WINDOWS_SIZE,
    MAXIMUM_RETRANSMISSION_ATTEMPTS,
)
from lib.common.file_handler import FileHandler
from lib.common.logger import Logger
from lib.client.protocol import ClientProtocol
from typing import List
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.max_retransmission_attempts import MaxRetransmissionAttempts
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.sequence_number import SequenceNumber

class GoBackN:
    def __init__(self, logger: Logger, protocol: ClientProtocol, sequence_number: SequenceNumber) -> None:
        self.windows_size: int = WINDOWS_SIZE
        self.base: int = 0
        self.expected_sqn_number: int = 1
        self.logger: Logger = logger
        self.protocol: ClientProtocol = protocol
        self.sequence_number: SequenceNumber = sequence_number

    def send_file(self, src_filepath: str) -> None:
        self.logger.debug(f"Sending file {src_filepath}")

        chunks: List[bytes] = self.separete_file_to_chunks()

        next_seq_num: int = 1   # Número de sqn que le vamos a asignar al próximo paquete a enviar
        total_chunks: int = len(chunks)

        # Propuesta:
        # self.protocol.start_timer()
        # o sino manejar el timer acá
        while self.base < total_chunks:
            # MIEntras aun quede data que enviar, enviamos los paquetes dentro de la ventana
            while next_seq_num < self.base + self.windows_size and next_seq_num < total_chunks:
                is_last_chunk = (next_seq_num == total_chunks - 1)
                chunk = chunks[next_seq_num]
                self.protocol.send_file_chunk(
                    self.sequence_number, chunk, len(chunk), is_last_chunk
                )
                self.logger.debug(f"Sent chunk {next_seq_num}")
                self.sequence_number += 1
                next_seq_num += 1

            try:
                self.await_ack_phase()
            except TimeoutError:
                raise MaxRetransmissionAttempts()

        self.logger.force_info("File transfer complete")
        self.file_handler.close(self.file)

    def await_ack_phase(self):
        # espero el ack
        # si no llegaa
        # hago time out y reenvio todo desde la base de la windows
        # si llega el ack
        # si es nuevo ack registro y continuo
        # si no es nuevo ack (es ack repetido) amplio la cuenta hasta llegar a 4. Si llega a 4 retransmitir toda la ventada

        counter: int = 0
        global_counter: int = 0
        ## Esto no va a andar, necesito algo que simplemente reciba un ack
        ack_seq_num, packet = self.protocol.wait_for_ack(
            self.sequence_number,
            exceptions_to_let_through=[UnexpectedFinMessage, MessageIsNotAck],
        )

        if ack_seq_num != self.expected_sqn_number:
            self.logger.debug(f"Received repeated ack {counter} ")

            if counter == MAX_ACK_REPEATED:
                if MAXIMUM_RETRANSMISSION_ATTEMPTS == global_counter:
                    raise MaxRetransmissionAttempts()

                self.logger.debug(f"Received repeated ack {self.expected_sqn_number} ")
                self.retransmit_phase()
        else:
            self.logger.debug(f"Received ack {self.expected_sqn_number} ")
            self.expected_sqn_number += 1
            self.base += 1

        return

    def separete_file_to_chunks(self) -> List[bytes]:
        total_chunks: int = self.file_handler.get_number_of_chunks(
            self.filesize, FILE_CHUNK_SIZE
        )
        # TODO: modificar para no levantar todo el file en memoria, mejor ir levantando de a ventanas en memoria
        chunk_list: list[bytes] = []

        for _ in range(total_chunks):
            chunk = self.file_handler.read(self.file, FILE_CHUNK_SIZE)
            chunk_list.append(chunk)

        return chunk_list
    
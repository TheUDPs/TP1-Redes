from time import sleep

from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.file_handler import FileHandler
from lib.common.logger import Logger
from lib.common.mutable_variable import MutableVariable
from lib.common.sequence_number import SequenceNumber
from lib.server.protocol_gbn import ServerProtocolGbn


class GoBackNReceiver:
    def __init__(
        self,
        logger: Logger,
        protocol: ServerProtocolGbn,
        file_handler: FileHandler,
        sequence_number: SequenceNumber,
        ack_number: SequenceNumber,
    ) -> None:
        # self.windows_size: int = WINDOWS_SIZE
        self.base: int = 0
        self.logger: Logger = logger
        self.protocol: ServerProtocolGbn = protocol
        self.sqn_number: SequenceNumber = sequence_number
        self.sqn_number_last_received: SequenceNumber = sequence_number
        self.ack_number: SequenceNumber = ack_number
        self.next_seq_num: int = 0
        self.file_handler: FileHandler = file_handler

    def receive_single_chunk(self, file, chunk_number: int):
        packet = self.protocol.receive_file_chunk(self.sqn_number)

        if not packet.is_fin:
            self.protocol.send_ack(self.sqn_number, self.ack_number)

        self.logger.debug(f"Received chunk {chunk_number}")
        self.file_handler.append_to_file(file, packet)

        return packet

    def receive_file(self, file) -> None:
        self.logger.debug("Beginning file reception in GBN manner")
        chunk_number: int = 1
        should_continue_reception = MutableVariable(True)

        self.sqn_number.step()
        self.ack_number.step()

        try:
            packet = self.receive_single_chunk(file, chunk_number)
            should_continue_reception.value = not packet.is_fin
            self.sqn_number.step()
            self.ack_number.step()
        except InvalidSequenceNumber:
            self.logger.warn("Found invalid sequence number")
            self.protocol.send_ack(self.sqn_number, self.ack_number)
            should_continue_reception.value = False

        while should_continue_reception.value:
            sleep(1)
            chunk_number += 1

            try:
                packet = self.receive_single_chunk(file, chunk_number)
                should_continue_reception.value = not packet.is_fin
                self.sqn_number.step()
                self.ack_number.step()
            except InvalidSequenceNumber:
                self.logger.warn("Found invalid sequence number")
                self.protocol.send_ack(self.sqn_number, self.ack_number)
                should_continue_reception.value = False

        self.logger.force_info("Upload completed")
        self.file_handler.close(file)

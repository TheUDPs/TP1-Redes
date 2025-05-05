from lib.common.constants import SOCKET_CONNECTION_LOST_TIMEOUT
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.file_handler import FileHandler
from lib.common.hash_compute import compute_chunk_sha256
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
        self.base: int = 0
        self.logger: Logger = logger
        self.protocol: ServerProtocolGbn = protocol
        self.sqn_number: SequenceNumber = sequence_number
        self.sqn_number_last_received: SequenceNumber = sequence_number
        self.ack_number: SequenceNumber = ack_number
        self.next_seq_num: int = 0
        self.file_handler: FileHandler = file_handler
        self.protocol.socket.set_timeout(SOCKET_CONNECTION_LOST_TIMEOUT)

    def receive_single_chunk(self, chunk_number: int):
        packet = self.protocol.receive_file_chunk(self.sqn_number)

        if not packet.is_fin:
            self.protocol.send_ack(self.sqn_number, self.ack_number)

        if chunk_number > 0:
            msg = f"Received chunk {chunk_number}. Hash is: {compute_chunk_sha256(packet.data)}"
            self.logger.debug(msg)

        return packet

    def validate_first_packet_and_resend(
        self,
        packet,
        first_chunk_received,
        should_continue_reception,
        last_transmitted_packet,
        packet_storage: MutableVariable,
    ):
        if packet.sequence_number == self.ack_number.value + 1:
            should_continue_reception.value = not packet.is_fin
            first_chunk_received.value = True
            packet_storage.value = packet
        else:
            self.logger.warn(
                f"Found invalid sequence number, expected seq {self.sqn_number.value}"
            )
            self.logger.debug("Resending filesize status")
            self.protocol.socket.sendto(
                last_transmitted_packet, self.protocol.client_address
            )

    def receive_first_chunk(
        self, last_transmitted_packet, chunk_number, should_continue_reception
    ):
        first_chunk_received = MutableVariable(False)
        packet = MutableVariable(None)

        while not first_chunk_received.value:
            try:
                packet.value = self.receive_single_chunk(chunk_number)
                self.validate_first_packet_and_resend(
                    packet.value,
                    first_chunk_received,
                    should_continue_reception,
                    last_transmitted_packet,
                    packet,
                )
            except InvalidSequenceNumber as e:
                self.validate_first_packet_and_resend(
                    e.packet,
                    first_chunk_received,
                    should_continue_reception,
                    last_transmitted_packet,
                    packet,
                )

        return packet.value

    def receive_file(
        self, file, last_transmitted_packet
    ) -> tuple[SequenceNumber, SequenceNumber]:
        self.logger.debug("Beginning file reception in GBN manner")
        should_continue_reception = MutableVariable(True)

        packet = self.receive_first_chunk(
            last_transmitted_packet, 0, should_continue_reception
        )

        self.sqn_number.step()
        self.ack_number.step()
        chunk_number: int = 0

        if not should_continue_reception.value and packet.payload_length > 0:
            msg = f"Received chunk {chunk_number + 1}. Hash is: {compute_chunk_sha256(packet.data)}"
            self.logger.debug(msg)
            self.file_handler.append_to_file(file, packet)

        while should_continue_reception.value:
            chunk_number += 1

            try:
                packet = self.receive_single_chunk(chunk_number)
                self.file_handler.append_to_file(file, packet)

                should_continue_reception.value = not packet.is_fin
                if should_continue_reception.value:
                    self.sqn_number.step()
                    self.ack_number.step()
            except InvalidSequenceNumber:
                chunk_number -= 1
                self.logger.warn(
                    f"Found invalid sequence number, expected seq {self.sqn_number.value}"
                )
                self.protocol.send_ack(self.sqn_number, self.ack_number)

        return self.sqn_number, self.ack_number

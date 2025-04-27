from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.client.exceptions.missing_server_address import MissingServerAddress
from lib.client.exceptions.unexpected_message import UnexpectedMessage
from lib.common.address import Address
from lib.common.constants import (
    FULL_BUFFER_SIZE,
    STRING_ENCODING_FORMAT,
    COMMS_BUFFER_SIZE,
    ZERO_BYTES,
    INT_DESERIALIZATION_BYTEORDER,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin import MessageIsNotFin
from lib.common.exceptions.message_not_fin_ack import MessageIsNotFinAck
from lib.common.exceptions.message_not_syn import MessageIsNotSyn
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.logger import Logger
from lib.common.packet import Packet, PacketParser
from lib.common.sequence_number import SequenceNumber
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.socket_saw import SocketSaw


class ClientProtocol:
    def __init__(
        self,
        logger: Logger,
        client_socket: SocketSaw,
        server_address: Address,
        my_address: Address,
        protocol_version: str,
    ):
        self.logger: Logger = logger
        self.socket: SocketSaw = client_socket
        self.server_host: str = server_address.host
        self.server_port: int = server_address.port
        self.server_address: Address = server_address
        self.my_address: Address = my_address
        self.protocol_version: str = protocol_version

    def socket_receive_from(self, buffer_size: int, should_retransmit: bool):
        raw_packet, server_address_tuple = self.socket.recvfrom(
            buffer_size, should_retransmit
        )
        return raw_packet, server_address_tuple

    def socket_send_to(self, packet_to_send: Packet, server_address_tuple: Address):
        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, server_address_tuple)

    def update_server_address(self, server_address: Address):
        self.server_address = server_address

    def validate_inbound_packet(
        self, raw_packet, server_address_tuple
    ) -> tuple[Packet, Address]:
        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not server_address_tuple:
            raise MissingServerAddress()

        server_address: Address = Address(
            server_address_tuple[0], server_address_tuple[1]
        )
        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        return packet, server_address

    def validate_inbound_ack(
        self, raw_packet, server_address_tuple
    ) -> tuple[Packet, Address]:
        packet, server_address = self.validate_inbound_packet(
            raw_packet, server_address_tuple
        )

        if not packet.is_ack:
            raise MessageIsNotAck()

        return packet, server_address

    def validate_fin(self, packet: Packet):
        if not packet.is_fin:
            raise MessageIsNotFin()

    def validate_not_fin(self, packet: Packet):
        if packet.is_fin:
            raise UnexpectedFinMessage()

    def validate_sequence_number(
        self, packet: Packet, sequence_number: SequenceNumber
    ) -> None:
        if sequence_number.value != packet.sequence_number:
            raise InvalidSequenceNumber()

    def request_connection(self, sequence_number: SequenceNumber) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=True,
            is_fin=False,
            port=self.my_address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            data=ZERO_BYTES,
        )
        self.socket_send_to(packet_to_send, self.server_address)

    def wait_for_connection_request_answer(
        self, sequence_number: SequenceNumber
    ) -> Address:
        try:
            raw_packet, server_address_tuple = self.socket_receive_from(
                COMMS_BUFFER_SIZE, should_retransmit=True
            )
        except ConnectionLost:
            raise ConnectionRefused()

        packet, server_address = self.validate_inbound_ack(
            raw_packet, server_address_tuple
        )
        self.validate_not_fin(packet)
        self.validate_sequence_number(packet, sequence_number)

        if not packet.is_syn:
            raise MessageIsNotSyn()

        return Address(server_address.host, packet.port)

    def send_hanshake_completion(self, sequence_number: SequenceNumber) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=True,
            is_syn=False,
            is_fin=False,
            port=self.my_address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            data=ZERO_BYTES,
        )

        self.socket_send_to(packet_to_send, self.server_address)

    def send_operation_intention(
        self, sequence_number: SequenceNumber, op_code: int
    ) -> None:
        data = op_code.to_bytes(1, byteorder=INT_DESERIALIZATION_BYTEORDER)

        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=False,
            port=self.my_address.port,
            payload_length=len(data),
            sequence_number=sequence_number.value,
            data=data,
        )
        self.socket_send_to(packet_to_send, self.server_address)

    def wait_for_operation_confirmation(self, sequence_number: SequenceNumber) -> None:
        try:
            raw_packet, server_address_tuple = self.socket_receive_from(
                COMMS_BUFFER_SIZE,
                should_retransmit=True,
            )
        except ConnectionLost:
            raise ConnectionRefused()

        packet, server_address = self.validate_inbound_ack(
            raw_packet, server_address_tuple
        )
        self.validate_not_fin(packet)
        self.validate_sequence_number(packet, sequence_number)

    def send_file_chunk(
        self,
        sequence_number: SequenceNumber,
        chunk: bytes,
        chunk_len: int,
        is_last_chunk: bool,
    ) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=is_last_chunk,
            port=self.my_address.port,
            payload_length=chunk_len,
            sequence_number=sequence_number.value,
            data=chunk,
        )

        self.socket_send_to(packet_to_send, self.server_address)

    def wait_for_ack(self, sequence_number: SequenceNumber) -> None:
        try:
            raw_packet, server_address_tuple = self.socket_receive_from(
                COMMS_BUFFER_SIZE, should_retransmit=True
            )
        except ConnectionLost:
            raise ConnectionRefused()

        packet, server_address = self.validate_inbound_ack(
            raw_packet, server_address_tuple
        )
        self.validate_not_fin(packet)
        self.validate_sequence_number(packet, sequence_number)

    def wait_for_fin_ack(self, sequence_number: SequenceNumber) -> None:
        try:
            raw_packet, server_address_tuple = self.socket_receive_from(
                COMMS_BUFFER_SIZE, should_retransmit=True
            )
        except ConnectionLost:
            raise ConnectionRefused()

        packet, server_address = self.validate_inbound_packet(
            raw_packet, server_address_tuple
        )
        self.validate_sequence_number(packet, sequence_number)

        if not (packet.is_ack and packet.is_fin):
            raise MessageIsNotFinAck()

    def inform_filename(self, sequence_number: SequenceNumber, filename: str) -> None:
        data = filename.encode(STRING_ENCODING_FORMAT)

        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=False,
            port=self.my_address.port,
            payload_length=len(data),
            sequence_number=sequence_number.value,
            data=data,
        )
        self.socket_send_to(packet_to_send, self.server_address)

    def inform_filesize(self, sequence_number: SequenceNumber, file_size: int) -> None:
        data = file_size.to_bytes(4, byteorder=INT_DESERIALIZATION_BYTEORDER)

        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=False,
            port=self.my_address.port,
            payload_length=len(data),
            sequence_number=sequence_number.value,
            data=data,
        )
        self.socket_send_to(packet_to_send, self.server_address)

    def send_ack(
        self,
        sequence_number: SequenceNumber,
    ) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=True,
            is_syn=False,
            is_fin=False,
            port=self.my_address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            data=ZERO_BYTES,
        )
        self.socket_send_to(packet_to_send, self.server_address)

    def send_fin_ack(
        self,
        sequence_number: SequenceNumber,
    ) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=True,
            is_syn=False,
            is_fin=True,
            port=self.server_address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            data=ZERO_BYTES,
        )
        self.socket_send_to(packet_to_send, self.server_address)

    def receive_file_chunk(
        self, sequence_number: SequenceNumber
    ) -> tuple[SequenceNumber, Packet]:
        raw_packet, server_address = self.socket_receive_from(
            FULL_BUFFER_SIZE, should_retransmit=False
        )

        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not server_address:
            raise UnexpectedMessage()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        if sequence_number.value != packet.sequence_number:
            raise InvalidSequenceNumber()

        return SequenceNumber(packet.sequence_number), packet

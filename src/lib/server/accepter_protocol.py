from lib.common.address import Address
from lib.common.constants import (
    UPLOAD_OPERATION,
    DOWNLOAD_OPERATION,
    STRING_ENCODING_FORMAT,
    COMMS_BUFFER_SIZE,
    FULL_BUFFER_SIZE,
    ZERO_BYTES,
    INT_DESERIALIZATION_BYTEORDER,
    STOP_AND_WAIT_PROTOCOL_TYPE,
)
from lib.common.exceptions.message_not_syn import MessageIsNotSyn
from lib.common.logger import Logger
from lib.common.packet.packet import Packet, PacketParser
from lib.common.re_listen_decorator import re_listen_if_failed
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_saw import SocketSaw
from lib.server.client_pool import ClientPool

from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin_ack import MessageIsNotFinAck
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.server.exceptions.unexpected_operation import UnexpectedOperation
from lib.server.exceptions.client_already_connected import ClientAlreadyConnected
from lib.server.exceptions.missing_client_address import MissingClientAddress


class AccepterProtocol:
    def __init__(
        self,
        logger: Logger,
        socket: SocketSaw,
        address: Address,
        protocol_version: str,
        clients: ClientPool,
    ):
        self.logger: Logger = logger
        self.socket: SocketSaw = socket
        self.host: str = address.host
        self.port: int = address.port
        self.address: Address = address
        self.protocol_version: str = protocol_version
        self.clients: ClientPool = clients

    def socket_receive_from(
        self, buffer_size: int, should_retransmit: bool, do_not_timeout: bool = False
    ):
        raw_packet, client_address_tuple = self.socket.recvfrom(
            buffer_size, should_retransmit, do_not_timeout
        )
        return raw_packet, client_address_tuple

    def socket_send_to(self, packet_to_send: Packet, client_address: Address):
        if self.protocol_version == STOP_AND_WAIT_PROTOCOL_TYPE:
            packet_bin: bytes = PacketParser.compose_packet_saw_for_net(packet_to_send)
        else:
            packet_bin: bytes = PacketParser.compose_packet_gbn_for_net(packet_to_send)

        self.socket.sendto(packet_bin, client_address)

    def validate_inbound_packet(
        self, raw_packet, client_address_tuple
    ) -> tuple[Packet, str, Address]:
        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not client_address_tuple:
            raise MissingClientAddress()

        client_address: Address = Address(
            client_address_tuple[0], client_address_tuple[1]
        )
        packet, packet_type = PacketParser.get_packet_from_bytes(raw_packet)

        return packet, packet_type, client_address

    def validate_inbound_ack(
        self, raw_packet, client_address_tuple
    ) -> tuple[Packet, str, Address]:
        packet, packet_type, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
        )

        if not packet.is_ack:
            raise MessageIsNotAck()

        if packet.is_fin:
            raise UnexpectedFinMessage()

        return packet, packet_type, client_address

    def validate_sequence_number(
        self, packet: Packet, sequence_number: SequenceNumber
    ) -> None:
        if sequence_number.value != packet.sequence_number:
            raise InvalidSequenceNumber()

    def accept_connection(self) -> tuple[Packet, str, Address]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            COMMS_BUFFER_SIZE, should_retransmit=False, do_not_timeout=True
        )

        packet, packet_type, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
        )

        if not packet.is_syn:
            raise MessageIsNotSyn()

        if self.clients.is_client_connected(client_address):
            raise ClientAlreadyConnected()

        return packet, packet_type, client_address

    def reject_connection(self, packet: Packet, client_address: Address) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=True,
            port=client_address.port,
            payload_length=0,
            sequence_number=packet.sequence_number,
            data=ZERO_BYTES,
        )

        self.socket_send_to(packet_to_send, client_address)

    def send_connection_accepted(
        self, packet: Packet, client_address: Address, connection_address: Address
    ) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=True,
            is_syn=True,
            is_fin=False,
            port=connection_address.port,
            payload_length=0,
            sequence_number=packet.sequence_number,
            data=ZERO_BYTES,
        )

        self.socket_send_to(packet_to_send, client_address)

    @re_listen_if_failed()
    def expect_handshake_completion(self) -> tuple[Packet, str, Address]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            COMMS_BUFFER_SIZE, should_retransmit=True
        )

        packet, packet_type, client_address = self.validate_inbound_ack(
            raw_packet, client_address_tuple
        )

        return packet, packet_type, client_address

    @re_listen_if_failed()
    def receive_operation_intention(self) -> tuple[int, SequenceNumber]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            COMMS_BUFFER_SIZE, should_retransmit=True
        )
        packet, packet_type, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
        )

        op_code: int = int.from_bytes(packet.data, INT_DESERIALIZATION_BYTEORDER)

        if op_code != UPLOAD_OPERATION and op_code != DOWNLOAD_OPERATION:
            raise UnexpectedOperation()

        return op_code, SequenceNumber(packet.sequence_number)

    def send_ack(
        self,
        sequence_number: SequenceNumber,
        client_address: Address,
        connection_address: Address,
    ) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=True,
            is_syn=False,
            is_fin=False,
            port=connection_address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            data=ZERO_BYTES,
        )

        self.socket_send_to(packet_to_send, client_address)

    def send_fin(
        self,
        sequence_number: SequenceNumber,
        client_address: Address,
        connection_address: Address,
    ) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=True,
            port=connection_address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            data=ZERO_BYTES,
        )

        self.socket_send_to(packet_to_send, client_address)

    def send_fin_ack(
        self,
        sequence_number: SequenceNumber,
        client_address: Address,
        connection_address: Address,
    ) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=True,
            is_syn=False,
            is_fin=True,
            port=connection_address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            data=ZERO_BYTES,
        )

        self.socket_send_to(packet_to_send, client_address)

    @re_listen_if_failed()
    def receive_filename(
        self, sequence_number: SequenceNumber
    ) -> tuple[SequenceNumber, str]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            FULL_BUFFER_SIZE, should_retransmit=True
        )
        packet, packet_type, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
        )
        filename: str = packet.data.decode(STRING_ENCODING_FORMAT)

        self.validate_sequence_number(packet, sequence_number)
        return SequenceNumber(packet.sequence_number), filename

    @re_listen_if_failed()
    def receive_filesize(
        self, sequence_number: SequenceNumber
    ) -> tuple[SequenceNumber, int]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            COMMS_BUFFER_SIZE, should_retransmit=True
        )
        packet, packet_type, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
        )
        filesize: int = int.from_bytes(packet.data, INT_DESERIALIZATION_BYTEORDER)

        self.validate_sequence_number(packet, sequence_number)
        return SequenceNumber(packet.sequence_number), filesize

    @re_listen_if_failed()
    def receive_file_chunk(
        self, sequence_number: SequenceNumber
    ) -> tuple[SequenceNumber, Packet]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            FULL_BUFFER_SIZE, should_retransmit=True
        )

        packet, packet_type, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
        )
        self.validate_sequence_number(packet, sequence_number)
        return SequenceNumber(packet.sequence_number), packet

    @re_listen_if_failed()
    def wait_for_ack(self, sequence_number: SequenceNumber) -> None:
        try:
            raw_packet, client_address_tuple = self.socket_receive_from(
                COMMS_BUFFER_SIZE, should_retransmit=True
            )
        except OSError:
            raise ConnectionLost()

        packet, packet_type, client_address = self.validate_inbound_ack(
            raw_packet, client_address_tuple
        )
        self.validate_sequence_number(packet, sequence_number)

    def send_file_chunk(
        self,
        sequence_number: SequenceNumber,
        chunk: bytes,
        chunk_len: int,
        is_last_chunk: bool,
        client_address: Address,
    ) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=is_last_chunk,
            port=self.address.port,
            payload_length=chunk_len,
            sequence_number=sequence_number.value,
            data=chunk,
        )

        self.socket_send_to(packet_to_send, client_address)

    @re_listen_if_failed()
    def wait_for_fin_ack(self, sequence_number: SequenceNumber) -> None:
        try:
            raw_packet, client_address_tuple = self.socket_receive_from(
                COMMS_BUFFER_SIZE, should_retransmit=True
            )
        except ConnectionLost:
            raise ConnectionLost()

        packet, packet_type, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
        )
        self.validate_sequence_number(packet, sequence_number)

        if not (packet.is_ack and packet.is_fin):
            raise MessageIsNotFinAck()

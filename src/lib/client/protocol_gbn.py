from lib.client.exceptions.missing_server_address import MissingServerAddress
from lib.common.address import Address
from lib.common.constants import COMMS_BUFFER_SIZE, FULL_BUFFER_SIZE, ZERO_BYTES
from lib.common.exceptions.invalid_ack_number import InvalidAckNumber
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin import MessageIsNotFin
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.logger import Logger
from lib.common.packet.packet import Packet, PacketGbn, PacketParser
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_gbn import SocketGbn


class ClientProtocolGbn:
    def __init__(
        self,
        logger: Logger,
        client_socket: SocketGbn,
        server_address: Address,
        my_address: Address,
        protocol_version: str,
    ):
        self.logger: Logger = logger
        self.socket: SocketGbn = client_socket
        self.server_host: str = server_address.host
        self.server_port: int = server_address.port
        self.server_address: Address = server_address
        self.my_address: Address = my_address
        self.protocol_version: str = protocol_version

    def socket_receive_from(self, buffer_size: int):
        raw_packet, client_address_tuple = self.socket.recvfrom(buffer_size)
        return raw_packet, client_address_tuple

    def socket_send_to(self, packet_to_send: Packet, client_address: Address):
        packet_bin: bytes = PacketParser.compose_packet_gbn_for_net(packet_to_send)
        self.socket.sendto(packet_bin, client_address)

    def update_server_address(self, server_address: Address):
        self.server_address = server_address

    def validate_inbound_packet(
        self, raw_packet, server_address_tuple
    ) -> tuple[PacketGbn, Address]:
        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not server_address_tuple:
            raise MissingServerAddress()

        server_address: Address = Address(
            server_address_tuple[0], server_address_tuple[1]
        )
        packet, _ = PacketParser.get_packet_from_bytes(raw_packet)
        _packet: PacketGbn = packet

        return _packet, server_address

    def validate_ack_number(
        self, packet: PacketGbn, ack_number: SequenceNumber
    ) -> None:
        is_valid = ack_number.value <= packet.ack_number
        if not is_valid:
            raise InvalidAckNumber()

    def validate_inbound_ack(
        self, raw_packet, server_address_tuple, ack_number: SequenceNumber
    ) -> tuple[PacketGbn, Address]:
        packet, server_address = self.validate_inbound_packet(
            raw_packet, server_address_tuple
        )

        # self.logger.debug(f"ACK expected {ack_number.value}, got {_packet.ack_number}")
        if not packet.is_ack:
            raise MessageIsNotAck()

        # self.validate_ack_number(_packet, ack_number)

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

    def send_file_chunk(
        self,
        sequence_number: SequenceNumber,
        ack_number: SequenceNumber,
        chunk: bytes,
        chunk_len: int,
        is_last_chunk: bool,
    ) -> None:
        packet_to_send: Packet = PacketGbn(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=is_last_chunk,
            port=self.my_address.port,
            payload_length=chunk_len,
            sequence_number=sequence_number.value,
            ack_number=ack_number.value,
            data=chunk,
        )

        self.socket_send_to(packet_to_send, self.server_address)

    def wait_for_ack(
        self, sequence_number: SequenceNumber, ack_number: SequenceNumber
    ) -> PacketGbn:
        raw_packet, server_address_tuple = self.socket_receive_from(COMMS_BUFFER_SIZE)

        packet, server_address = self.validate_inbound_ack(
            raw_packet, server_address_tuple, ack_number
        )
        self.validate_not_fin(packet)
        # self.validate_sequence_number(packet, sequence_number)
        return packet

    def receive_file_chunk(self, sequence_number: SequenceNumber) -> PacketGbn:
        raw_packet, server_address_tuple = self.socket_receive_from(FULL_BUFFER_SIZE)

        packet, server_address = self.validate_inbound_packet(
            raw_packet, server_address_tuple
        )

        self.validate_sequence_number(packet, sequence_number)
        return packet

    def send_ack(
        self,
        sequence_number: SequenceNumber,
        ack_number: SequenceNumber,
    ) -> None:
        packet_to_send: PacketGbn = PacketGbn(
            protocol=self.protocol_version,
            is_ack=True,
            is_syn=False,
            is_fin=False,
            port=self.my_address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            ack_number=ack_number.value,
            data=ZERO_BYTES,
        )
        self.socket_send_to(packet_to_send, self.server_address)

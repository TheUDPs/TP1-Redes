from lib.common.address import Address
from lib.common.constants import FULL_BUFFER_SIZE, ZERO_BYTES
from lib.common.exceptions.invalid_ack_number import InvalidAckNumber
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin import MessageIsNotFin
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.logger import Logger
from lib.common.packet.packet import PacketGbn, Packet, PacketParser
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_gbn import SocketGbn
from lib.server.client_pool import ClientPool
from lib.server.exceptions.missing_client_address import MissingClientAddress


class ServerProtocolGbn:
    def __init__(
        self,
        logger: Logger,
        socket: SocketGbn,
        client_address: Address,
        address: Address,
        protocol_version: str,
        clients: ClientPool,
    ):
        self.logger: Logger = logger
        self.socket: SocketGbn = socket
        self.host: str = address.host
        self.port: int = address.port
        self.client_address: Address = client_address
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

    def socket_send_to(self, packet_to_send: PacketGbn, client_address: Address):
        packet_bin: bytes = PacketParser.compose_packet_gbn_for_net(packet_to_send)
        self.socket.sendto(packet_bin, client_address)

    def validate_inbound_packet(
        self, raw_packet, client_address_tuple
    ) -> tuple[PacketGbn, Address]:
        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not client_address_tuple:
            raise MissingClientAddress()

        client_address: Address = Address(
            client_address_tuple[0], client_address_tuple[1]
        )
        packet, packet_type = PacketParser.get_packet_from_bytes(raw_packet)
        _packet: PacketGbn = packet

        return _packet, client_address

    def validate_ack_number(
        self, packet: PacketGbn, ack_number: SequenceNumber
    ) -> None:
        if ack_number.value != packet.ack_number:
            raise InvalidAckNumber()

    def validate_inbound_ack(
        self, raw_packet, client_address_tuple, ack_number: SequenceNumber
    ) -> tuple[Packet, str, Address]:
        packet, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
        )

        if not packet.is_ack:
            raise MessageIsNotAck()

        self.validate_ack_number(packet, ack_number)

        return packet, client_address

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

    def receive_file_chunk(self, sequence_number: SequenceNumber) -> PacketGbn:
        raw_packet, client_address_tuple = self.socket_receive_from(
            FULL_BUFFER_SIZE, should_retransmit=False
        )

        packet, client_address = self.validate_inbound_packet(
            raw_packet, client_address_tuple
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
            port=self.address.port,
            payload_length=0,
            sequence_number=sequence_number.value,
            ack_number=ack_number.value,
            data=ZERO_BYTES,
        )
        self.socket_send_to(packet_to_send, self.client_address)

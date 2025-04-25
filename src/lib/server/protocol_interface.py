from socket import socket as Socket
from lib.common.address import Address
from lib.common.constants import (
    UPLOAD_OPERATION,
    DOWNLOAD_OPERATION,
    STRING_ENCODING_FORMAT,
)
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.logger import Logger
from lib.common.packet import Packet, PacketParser

from lib.common.exceptions.bag_flags_for_handshake import BadFlagsForHandshake
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.sequence_number import SequenceNumber
from lib.server.client_pool import ClientPool
from lib.server.exceptions.bad_operation import BadOperation
from lib.server.exceptions.missing_client_address import MissingClientAddress

ZERO_BYTES = bytes([])
BUFFER_SIZE = 4028


class ServerProtocol:
    def __init__(
        self,
        logger: Logger,
        socket: Socket,
        address: Address,
        protocol_version: str,
        clients: ClientPool,
    ):
        self.logger: Logger = logger
        self.socket: Socket = socket
        self.host: str = address.host
        self.port: int = address.port
        self.address: Address = address
        self.protocol_version: str = protocol_version
        self.clients: ClientPool = clients

    def accept_connection(self) -> tuple[Packet, Address]:
        raw_packet, client_address_tuple = self.socket.recvfrom(BUFFER_SIZE)

        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not client_address_tuple:
            raise MissingClientAddress()

        client_address: Address = Address(
            client_address_tuple[0], client_address_tuple[1]
        )
        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        if not packet.is_syn and not self.clients.is_client_connected(client_address):
            raise BadFlagsForHandshake()

        return packet, client_address

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

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, client_address.to_tuple())

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

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, client_address.to_tuple())

    def expect_handshake_completion(self) -> tuple[Packet, Address]:
        raw_packet, client_address_tuple = self.socket.recvfrom(BUFFER_SIZE)

        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not client_address_tuple:
            raise MissingClientAddress()

        client_address: Address = Address(
            client_address_tuple[0], client_address_tuple[1]
        )
        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        if not packet.is_ack:
            self.logger.error("Expected ACK packet")
            raise BadFlagsForHandshake()

        return packet, client_address

    def receive_operation_intention(self) -> tuple[int, SequenceNumber]:
        raw_packet, client_address_tuple = self.socket.recvfrom(BUFFER_SIZE)

        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not client_address_tuple:
            raise MissingClientAddress()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)
        op_code: int = int.from_bytes(packet.data, "big")
        if op_code != UPLOAD_OPERATION and op_code != DOWNLOAD_OPERATION:
            raise BadOperation()

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

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, client_address.to_tuple())

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

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, client_address.to_tuple())

    def receive_filename(
        self, sequence_number: SequenceNumber
    ) -> tuple[SequenceNumber, str]:
        raw_packet, client_address_tuple = self.socket.recvfrom(BUFFER_SIZE)

        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not client_address_tuple:
            raise MissingClientAddress()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)
        filename: str = packet.data.decode(STRING_ENCODING_FORMAT)

        if sequence_number.value != packet.sequence_number:
            raise InvalidSequenceNumber()

        return SequenceNumber(packet.sequence_number), filename

    def receive_filesize(
        self, sequence_number: SequenceNumber
    ) -> tuple[SequenceNumber, int]:
        raw_packet, client_address_tuple = self.socket.recvfrom(BUFFER_SIZE)

        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not client_address_tuple:
            raise MissingClientAddress()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)
        filesize: int = int.from_bytes(packet.data, "big")

        if sequence_number.value != packet.sequence_number:
            raise InvalidSequenceNumber()

        return SequenceNumber(packet.sequence_number), filesize

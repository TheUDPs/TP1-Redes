from socket import socket
from lib.common.address import Address
from lib.common.logger import Logger
from lib.common.packet import Packet, PacketParser

ZERO_BYTES = bytes([])
BUFFER_SIZE = 4028


class MissingClientAddress(Exception):
    def __init__(self, message="Client address not found"):
        self.message = message


class BadFlagsForHandshake(Exception):
    def __init__(
        self, message="Flags in the packet for the handshake are in an unexpected state"
    ):
        self.message = message


class SocketShutdown(Exception):
    def __init__(self, message="Socket was shutdowned"):
        self.message = message


class ServerProtocol:
    def __init__(
        self, logger: Logger, socket_: socket, address: Address, protocol_version: str
    ):
        self.logger: Logger = logger
        self.socket: socket = socket_
        self.host: str = address.host
        self.port: int = address.port
        self.address: Address = address
        self.protocol_version: str = protocol_version

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

        if not packet.is_syn:
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

    def expect_handshake_completion(self):
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
            raise BadFlagsForHandshake()

        return packet, client_address

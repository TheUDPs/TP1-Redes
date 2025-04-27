from lib.client.exceptions.invalid_message import InvalidMessage
from lib.client.exceptions.unexpected_message import UnexpectedMessage
from lib.common.address import Address
from lib.common.constants import (
    UPLOAD_OPERATION,
    DOWNLOAD_OPERATION,
    STRING_ENCODING_FORMAT,
    COMMS_BUFFER_SIZE,
    FULL_BUFFER_SIZE,
    ZERO_BYTES,
)
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.logger import Logger
from lib.common.packet import Packet, PacketParser

from lib.common.exceptions.bag_flags_for_handshake import BadFlagsForHandshake
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_saw import SocketSaw
from lib.server.client_pool import ClientPool
from lib.server.exceptions.bad_operation import BadOperation
from lib.server.exceptions.missing_client_address import MissingClientAddress
from lib.client.exceptions.connection_refused import ConnectionRefused


class ServerProtocol:
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
        self, buffer_size: int, should_retransmit: bool, should_re_listen: bool
    ):
        raw_packet, server_address_tuple = self.socket.recvfrom(
            buffer_size, should_retransmit, should_re_listen
        )
        return raw_packet, server_address_tuple

    def socket_send_to(self, packet_bin: bytes, server_address_tuple: Address):
        self.socket.sendto(packet_bin, server_address_tuple)

    def accept_connection(self) -> tuple[Packet, Address]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            COMMS_BUFFER_SIZE, should_retransmit=False, should_re_listen=False
        )

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
        self.socket_send_to(packet_bin, client_address)

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
        self.socket_send_to(packet_bin, client_address)

    def expect_handshake_completion(self) -> tuple[Packet, Address]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            COMMS_BUFFER_SIZE, should_retransmit=False, should_re_listen=True
        )

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
        raw_packet, client_address_tuple = self.socket_receive_from(
            COMMS_BUFFER_SIZE, should_retransmit=False, should_re_listen=True
        )

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
        self.socket_send_to(packet_bin, client_address)

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
        self.socket_send_to(packet_bin, client_address)

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

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket_send_to(packet_bin, client_address)

    def receive_filename(
        self, sequence_number: SequenceNumber
    ) -> tuple[SequenceNumber, str]:
        raw_packet, client_address_tuple = self.socket_receive_from(
            FULL_BUFFER_SIZE, should_retransmit=False, should_re_listen=True
        )

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
        raw_packet, client_address_tuple = self.socket_receive_from(
            COMMS_BUFFER_SIZE, should_retransmit=False, should_re_listen=True
        )

        if len(raw_packet) == 0:
            raise SocketShutdown()

        if not client_address_tuple:
            raise MissingClientAddress()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)
        filesize: int = int.from_bytes(packet.data, "big")

        if sequence_number.value != packet.sequence_number:
            raise InvalidSequenceNumber()

        return SequenceNumber(packet.sequence_number), filesize

    def receive_file_chunk(
        self, sequence_number: SequenceNumber
    ) -> tuple[SequenceNumber, Packet]:
        while True:
            try:
                raw_packet, client_address_tuple = self.socket_receive_from(
                    FULL_BUFFER_SIZE, should_retransmit=False, should_re_listen=True
                )

                if len(raw_packet) == 0:
                    raise SocketShutdown()

                if not client_address_tuple:
                    raise MissingClientAddress()

                packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

                if sequence_number.value != packet.sequence_number:
                    raise InvalidSequenceNumber()

                return SequenceNumber(packet.sequence_number), packet
            except InvalidSequenceNumber:
                self.logger.warn(
                    "Received invalid sequence number. Discarding and waiting again"
                )
                pass

    def wait_for_ack(self, sequence_number: SequenceNumber) -> None:
        try:
            raw_packet, client_address_tuple = self.socket_receive_from(
                COMMS_BUFFER_SIZE, should_retransmit=True, should_re_listen=True
            )
        except OSError:
            raise InvalidMessage()

        if not client_address_tuple:
            raise UnexpectedMessage()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        if packet.sequence_number != sequence_number.value:
            raise InvalidSequenceNumber()

        if not packet.is_ack or packet.is_fin:
            raise InvalidMessage()

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

        self.logger.debug(f"Sending chunk of size {chunk_len}, to: {client_address}")
        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket_send_to(packet_bin, client_address)

    def wait_for_fin_ack(self, sequence_number: SequenceNumber) -> None:
        try:
            raw_packet, server_address_tuple = self.socket_receive_from(
                COMMS_BUFFER_SIZE, should_retransmit=True, should_re_listen=True
            )
        except OSError:
            raise ConnectionRefused()

        if not server_address_tuple:
            raise UnexpectedMessage()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        if packet.sequence_number != sequence_number.value:
            raise InvalidSequenceNumber()

        if not packet.is_ack or not packet.is_fin:
            raise InvalidMessage()

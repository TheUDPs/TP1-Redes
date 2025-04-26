from socket import socket as Socket

from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.client.exceptions.operation_refused import OperationRefused
from lib.client.exceptions.unexpected_message import UnexpectedMessage
from lib.common.address import Address
from lib.common.constants import STRING_ENCODING_FORMAT, COMMS_BUFFER_SIZE, ZERO_BYTES
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.logger import Logger
from lib.common.packet import Packet, PacketParser
from lib.common.exceptions.bag_flags_for_handshake import BadFlagsForHandshake
from lib.common.sequence_number import SequenceNumber


class ClientProtocol:
    def __init__(
        self,
        logger: Logger,
        client_socket: Socket,
        server_address: Address,
        my_address: Address,
        protocol_version: str,
    ):
        self.logger: Logger = logger
        self.socket: Socket = client_socket
        self.server_host: str = server_address.host
        self.server_port: int = server_address.port
        self.server_address: Address = server_address
        self.my_address: Address = my_address
        self.protocol_version: str = protocol_version

    # def validate_incomming_packet(self, packet: bytes, server_address: tuple[str, int]) -> Packet:
    #     if server_address != self.server_address.to_tuple():
    #         raise UnexpectedMessage()
    #     else:
    #         return PacketParser.get_packet_from_bytes(packet)

    def update_server_address(self, server_address: Address):
        self.server_address = server_address

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
        self.logger.debug(f"Requesting connection to {self.server_address}")
        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, self.server_address.to_tuple())

    def wait_for_connection_request_answer(
        self, sequence_number: SequenceNumber
    ) -> Address:
        try:
            raw_packet, server_address_tuple = self.socket.recvfrom(COMMS_BUFFER_SIZE)
        except OSError:
            raise ConnectionRefused()

        if not server_address_tuple:
            raise UnexpectedMessage()

        server_address: Address = Address(
            server_address_tuple[0], server_address_tuple[1]
        )

        self.logger.debug(f"Got connection accepted from {self.server_address}")
        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        if packet.sequence_number != sequence_number.value:
            raise InvalidSequenceNumber()

        if not packet.is_syn:
            raise BadFlagsForHandshake()
        if not packet.is_ack or packet.is_fin:
            raise ConnectionRefused()

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
        self.logger.debug(f"Completing handshake with {self.server_address}")

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, self.server_address.to_tuple())

    def send_operation_intention(
        self, sequence_number: SequenceNumber, op_code: int
    ) -> None:
        data = op_code.to_bytes(1, byteorder="big")

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
        self.logger.debug("Sending operation intention")

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, self.server_address.to_tuple())

    def wait_for_operation_confirmation(self, sequence_number: SequenceNumber) -> None:
        try:
            self.logger.debug("Waiting for operation confirmation")
            raw_packet, server_address_tuple = self.socket.recvfrom(COMMS_BUFFER_SIZE)
        except OSError:
            raise ConnectionRefused()

        if not server_address_tuple:
            raise UnexpectedMessage()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        if packet.sequence_number != sequence_number.value:
            raise InvalidSequenceNumber()

        if not packet.is_ack or packet.is_fin:
            raise OperationRefused()

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

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, self.server_address.to_tuple())

    def wait_for_ack(self, sequence_number: SequenceNumber) -> None:
        try:
            raw_packet, server_address_tuple = self.socket.recvfrom(COMMS_BUFFER_SIZE)
        except OSError:
            raise ConnectionRefused()

        if not server_address_tuple:
            raise UnexpectedMessage()

        packet: Packet = PacketParser.get_packet_from_bytes(raw_packet)

        if packet.sequence_number != sequence_number.value:
            raise InvalidSequenceNumber()

        if not packet.is_ack or packet.is_fin:
            raise OperationRefused()

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

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, self.server_address.to_tuple())

    def inform_filesize(self, sequence_number: SequenceNumber, file_size: int) -> None:
        data = file_size.to_bytes(4, byteorder="big")

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

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, self.server_address.to_tuple())

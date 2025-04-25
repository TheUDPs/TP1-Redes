from socket import socket
from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.client.exceptions.unexpected_message import UnexpectedMessage
from lib.common.address import Address
from lib.common.logger import Logger
from lib.common.packet import Packet, PacketParser, get_random_port

ZERO_BYTES = bytes([])
BUFFER_SIZE = 4028


class ClientProtocol:
    def __init__(
        self,
        logger: Logger,
        client_socket: socket,
        server_address: Address,
        protocol_version: str,
    ):
        self.logger: Logger = logger
        self.socket: socket = client_socket
        self.server_host: str = server_address.host
        self.server_port: int = server_address.port
        self.server_address: Address = server_address
        self.protocol_version: str = protocol_version

    def validate_incomming_packet(self, packet: bytes, server_address) -> Packet:
        if server_address != self.server_address.to_tuple():
            raise UnexpectedMessage()
        else:
            return PacketParser.get_packet_from_bytes(packet)

    def request_connection(self, sequence_number: int) -> None:
        packet_to_send: Packet = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=True,
            is_fin=False,
            port=get_random_port(),
            payload_length=0,
            sequence_number=sequence_number,
            data=ZERO_BYTES,
        )

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, self.server_address.to_tuple())

        try:
            raw_packet, server_address = self.socket.recvfrom(BUFFER_SIZE)
        except OSError:
            raise ConnectionRefused()

        _packet: Packet = self.validate_incomming_packet(raw_packet, server_address)

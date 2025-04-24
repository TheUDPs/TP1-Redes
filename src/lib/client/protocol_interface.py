from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.client.exceptions.unexpected_message import UnexpectedMessage
from lib.common.packet import Packet, PacketParser, get_random_port

ZERO_BYTES = bytes([])
BUFFER_SIZE = 4028


class ClientProtocol:
    def __init__(
        self, logger, client_socket, server_host, server_port, protocol_version
    ):
        self.logger = logger
        self.socket = client_socket
        self.server_host = server_host
        self.server_port = server_port
        self.protocol_version = protocol_version
        self.server_host_with_port = (self.server_host, self.server_port)

    def validate_incomming_packet(self, packet, server_address) -> Packet:
        if server_address != self.server_host_with_port:
            raise UnexpectedMessage()
        else:
            return PacketParser.get_packet_from_bytes(packet)

    def request_connection(self, sequence_number):
        self.logger.debug("Requesting connection")

        packet_to_send = Packet(
            protocol=self.protocol_version,
            is_ack=False,
            is_syn=False,
            is_fin=False,
            port=get_random_port(),
            payload_length=0,
            sequence_number=sequence_number,
            data=ZERO_BYTES,
        )

        packet_bin: bytes = PacketParser.compose_packet_for_net(packet_to_send)
        self.socket.sendto(packet_bin, self.server_host_with_port)

        try:
            raw_packet, server_address = self.socket.recvfrom(BUFFER_SIZE)
        except OSError:
            raise ConnectionRefused()

        _packet: Packet = self.validate_incomming_packet(raw_packet, server_address)

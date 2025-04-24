import random
import struct

from lib.client.exceptions.connection_refused import ConnectionRefused
from lib.common.constants import (
    GO_BACK_N_PROTOCOL_TYPE,
    STOP_AND_WAIT_PROTOCOL_TYPE,
)

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

    def build_packet(
        self,
        is_ack: bool,
        is_syn: bool,
        is_fin: bool,
        sequence_number: int,
        data: bytes,
    ):
        flags = 0b0000_0000_0000_0000

        protocol_flag = 0b00
        if self.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            protocol_flag = 0b01

        sequence_number = 0b1 if sequence_number == 1 else 0b0
        is_ack = 0b1 if is_ack else 0b0
        is_syn = 0b1 if is_syn else 0b0
        is_fin = 0b1 if is_fin else 0b0

        pos = 16
        pos -= 2
        flags |= protocol_flag << pos

        pos -= 1
        flags |= sequence_number << pos

        pos -= 1
        flags |= is_ack << pos

        pos -= 1
        flags |= is_syn << pos

        pos -= 1
        flags |= is_fin << pos

        # print(f"{flags:016b}\n")

        port = random.randint(1, 10)
        payload_length = len(data)

        header = struct.pack("!HHH", flags, port, payload_length)

        return header + data

    def parse_packet(self, packet):
        header = int.from_bytes(packet[0:2], byteorder="big")

        pos = 16
        pos -= 2
        protocol = header >> pos & 0b11

        pos -= 1
        sequence_number = header >> pos & 0b1

        pos -= 1
        is_ack = header >> pos & 0b1
        is_ack = True if is_ack == 0b1 else False

        pos -= 1
        is_syn = header >> pos & 0b1
        is_syn = True if is_syn == 0b1 else False

        pos -= 1
        is_fin = header >> pos & 0b1
        is_fin = True if is_fin == 0b1 else False

        if protocol == 0b01:
            protocol = GO_BACK_N_PROTOCOL_TYPE
        else:
            protocol = STOP_AND_WAIT_PROTOCOL_TYPE

        port = int.from_bytes(packet[2:4], byteorder="big")
        payload_length = int.from_bytes(packet[4:6], byteorder="big")
        data = bytes(packet[6 : 6 + payload_length])

        print(f"packet: {protocol}, {sequence_number}, {is_ack}, {is_syn}, {is_fin}")
        print(f"port: {port}")
        print(f"payload_length: {payload_length}")
        print(f"data: {data}")

        return (
            protocol,
            sequence_number,
            is_ack,
            is_syn,
            is_fin,
            port,
            payload_length,
            data,
        )

    def validate_incomming_packet(self, packet, server_address):
        # if server_address != self.server_host_with_port:
        #     raise UnexpectedMessage()
        # else:
        return self.parse_packet(packet)

    def request_connection(self, sequence_number):
        self.logger.debug("Requesting connection")

        packet = self.build_packet(
            is_ack=False,
            is_syn=False,
            is_fin=False,
            sequence_number=sequence_number,
            data=ZERO_BYTES,
        )
        self.socket.sendto(packet, self.server_host_with_port)

        try:
            raw_packet, server_address = self.socket.recvfrom(BUFFER_SIZE)
        except OSError:
            raise ConnectionRefused()

        (
            _protocol,
            _sequence_number,
            _is_ack,
            _is_syn,
            _is_fin,
            _port,
            _payload_length,
            _data,
        ) = self.validate_incomming_packet(raw_packet, server_address)

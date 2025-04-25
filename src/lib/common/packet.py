import random
import struct

from lib.common.constants import (
    GO_BACK_N_PROTOCOL_TYPE,
    STOP_AND_WAIT_PROTOCOL_TYPE,
)


def get_random_port() -> int:
    return random.randint(1, 10)


class Packet:
    def __init__(
        self,
        protocol: str,
        sequence_number: int,
        is_ack: bool,
        is_syn: bool,
        is_fin: bool,
        port: int,
        payload_length: int,
        data: bytes,
    ):
        self.protocol: str = protocol
        self.sequence_number: int = sequence_number
        self.is_ack: bool = is_ack
        self.is_syn: bool = is_syn
        self.is_fin: bool = is_fin
        self.port: int = port
        self.payload_length: int = payload_length
        self.data: bytes = data


class PacketParser:
    @staticmethod
    def compose_packet_for_net(packet: Packet) -> bytes:
        flags = 0b0000_0000_0000_0000

        protocol_flag = 0b00
        if packet.protocol == GO_BACK_N_PROTOCOL_TYPE:
            protocol_flag = 0b01

        sequence_number = 0b1 if packet.sequence_number == 1 else 0b0
        is_ack = 0b1 if packet.is_ack else 0b0
        is_syn = 0b1 if packet.is_syn else 0b0
        is_fin = 0b1 if packet.is_fin else 0b0

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

        header = struct.pack(
            "!HHH", flags, int(packet.port), int(packet.payload_length)
        )

        return header + packet.data

    @staticmethod
    def get_packet_from_bytes(packet: bytes) -> Packet:
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

        # print(f"packet: {protocol}, {sequence_number}, {is_ack}, {is_syn}, {is_fin}")
        # print(f"port: {port}")
        # print(f"payload_length: {payload_length}")
        # print(f"data: {data}")

        return Packet(
            protocol,
            sequence_number,
            is_ack,
            is_syn,
            is_fin,
            port,
            payload_length,
            data,
        )

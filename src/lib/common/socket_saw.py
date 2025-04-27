from time import time
from socket import socket as Socket
from socket import timeout as SocketTimeout

from lib.common.address import Address
from lib.common.constants import (
    MAX_RETRANSMISSION_ATTEMPTS,
    SOCKET_RETRANSMISSION_TIMEOUT,
    SOCKET_CONNECTION_LOST_TIMEOUT,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.logger import Logger


class RetransmissionNeeded(Exception):
    pass


class InvalidTimeProvided(Exception):
    pass


class SocketSaw:
    def __init__(self, _socket: Socket, logger: Logger):
        self.socket = _socket
        self.logger = logger
        self.last_raw_packet = None
        self.last_address = None

    def save_state(self, data: bytes, to_address: Address):
        self.last_raw_packet = data
        self.last_address = to_address

    def sendto(self, data: bytes, to_address: Address):
        self.save_state(data, to_address)
        self.socket.sendto(data, to_address.to_tuple())

    def retransmit_last_packet(self, attempt_number: int):
        if self.last_raw_packet is None:
            return

        self.logger.warn(f"Retransmission attempt number {attempt_number - 1}")
        self.sendto(self.last_raw_packet, self.last_address)

    def recvfrom_with_retransmission(self, buffer_size: int):
        transmission_attempt = 1
        raw_packet, server_address_tuple = None, None
        connection_lost_deadline = time() + SOCKET_CONNECTION_LOST_TIMEOUT

        did_not_exceed_max_retransmissions = (
            transmission_attempt <= MAX_RETRANSMISSION_ATTEMPTS
        )
        connection_not_lost_yet = time() <= connection_lost_deadline
        can_still_retransmit = (
            did_not_exceed_max_retransmissions and connection_not_lost_yet
        )
        while can_still_retransmit:
            retransmission_necessary_deadline = time() + SOCKET_RETRANSMISSION_TIMEOUT

            while True:
                remaining_until_retransmission = (
                    retransmission_necessary_deadline - time()
                )

                if remaining_until_retransmission <= 0:
                    transmission_attempt += 1

                    did_not_exceed_max_retransmissions = (
                        transmission_attempt <= MAX_RETRANSMISSION_ATTEMPTS
                    )
                    connection_not_lost_yet = time() <= connection_lost_deadline
                    can_still_retransmit = (
                        did_not_exceed_max_retransmissions and connection_not_lost_yet
                    )

                    if can_still_retransmit:
                        self.retransmit_last_packet(transmission_attempt)
                    else:
                        self.logger.debug("Connection lost")
                        raise ConnectionLost()
                    break
                else:
                    try:
                        self.socket.settimeout(remaining_until_retransmission)
                        raw_packet, server_address_tuple = self.socket.recvfrom(
                            buffer_size
                        )
                        return raw_packet, server_address_tuple

                    except SocketTimeout:
                        continue

                    except OSError:
                        raise ConnectionLost()
        return raw_packet, server_address_tuple

    def recvfrom(self, buffer_size: int, should_retransmit: bool):
        if not should_retransmit:
            try:
                raw_packet, server_address_tuple = self.socket.recvfrom(buffer_size)
                return raw_packet, server_address_tuple
            except OSError:
                raise ConnectionLost()

        raw_packet, server_address_tuple = self.recvfrom_with_retransmission(
            buffer_size
        )
        return raw_packet, server_address_tuple

    def shutdown(self, shutdown_type):
        self.socket.shutdown(shutdown_type)

    def close(self):
        self.socket.close()

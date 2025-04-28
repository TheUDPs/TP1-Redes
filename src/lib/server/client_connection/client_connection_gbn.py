from lib.common.address import Address
from lib.common.logger import Logger
from lib.common.mutable_variable import MutableVariable
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_saw import SocketSaw
from lib.server.client_connection.abstract_client_connection import ClientConnection
from lib.common.file_handler import FileHandler


class ClientConnectionGbn(ClientConnection):
    def __init__(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        protocol: str,
        logger: Logger,
        file_handler: FileHandler,
        initial_sequence_number: SequenceNumber,
    ):
        super().__init__(
            connection_socket,
            connection_address,
            client_address,
            protocol,
            logger,
            file_handler,
            initial_sequence_number,
        )

    def perform_upload(
        self,
        sequence_number: MutableVariable,
        filename_for_upload: MutableVariable,
        filesize_for_upload: MutableVariable,
    ):
        pass

    def perform_download(
        self, sequence_number: MutableVariable, filename_for_download: MutableVariable
    ):
        pass

    def is_ready_to_die(self) -> bool:
        pass

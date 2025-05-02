from lib.common.address import Address
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.logger import Logger
from lib.common.mutable_variable import MutableVariable
from lib.common.packet.packet import Packet
from lib.common.socket_gbn import SocketGbn
from lib.common.socket_saw import SocketSaw
from lib.server.client_connection.abstract_client_connection import ClientConnection
from lib.common.file_handler import FileHandler
from lib.server.connection_state import ConnectionState
from lib.server.go_back_n_receiver import GoBackNReceiver
from lib.server.protocol_gbn import ServerProtocolGbn


class ClientConnectionGbn(ClientConnection):
    def __init__(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        protocol: str,
        logger: Logger,
        file_handler: FileHandler,
        packet: Packet,
    ):
        super().__init__(
            connection_socket,
            connection_address,
            client_address,
            protocol,
            logger,
            file_handler,
            packet,
        )

    def receive_file(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename: MutableVariable,
        filesize: MutableVariable,
    ):
        _filename, _filesize = self.receive_file_info_for_upload(
            sequence_number, ack_number
        )
        filename.value = _filename
        filesize.value = _filesize

        self.logger.debug(f"Ready to receive from {self.client_address}")

        self.socket.reset_state()
        socket_gbn = SocketGbn(self.socket.socket, self.logger)
        gbn_protocol = ServerProtocolGbn(
            self.logger,
            socket_gbn,
            self.client_address,
            self.address,
            self.protocol.protocol_version,
            self.protocol.clients,
        )

        gbn_sender = GoBackNReceiver(
            self.logger,
            gbn_protocol,
            self.file_handler,
            sequence_number.value,
            ack_number.value,
        )
        gbn_sender.receive_file(self.file)

        self.logger.force_info("File transfer complete")
        self.file_handler.close(self.file)

    def perform_upload(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_upload: MutableVariable,
        filesize_for_upload: MutableVariable,
    ):
        self.receive_file(
            sequence_number, ack_number, filename_for_upload, filesize_for_upload
        )
        self.closing_handshake_for_upload(sequence_number, ack_number)

    def perform_download(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_download: MutableVariable,
    ):
        pass

    def closing_handshake_for_upload(
        self, sequence_number: MutableVariable, ack_number: MutableVariable
    ):
        try:
            self.logger.debug("Connection finalization received. Confirming it")
            self.protocol.send_ack(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )

            self.logger.debug("Sending own connection finalization")
            self.protocol.send_fin(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )

            sequence_number.value.step()
            try:
                self.protocol.wait_for_ack(
                    sequence_number.value, exceptions_to_let_through=[ConnectionLost]
                )
            except ConnectionLost:
                pass

            self.logger.info("Connection closed")
        except SocketShutdown:
            self.logger.info("Connection closed")
        finally:
            self.state = ConnectionState.DONE_READY_TO_DIE

    def is_ready_to_die(self) -> bool:
        pass

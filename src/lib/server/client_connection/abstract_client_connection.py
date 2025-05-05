from abc import abstractmethod
from threading import Thread

from lib.common.address import Address
from lib.common.constants import (
    UPLOAD_OPERATION,
    DOWNLOAD_OPERATION,
    OPERATION_STRING_FROM_CODE,
    GO_BACK_N_PROTOCOL_TYPE,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin_ack import MessageIsNotFinAck
from lib.common.exceptions.socket_shutdown import SocketShutdown
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage
from lib.common.logger import CoolLogger
from lib.common.mutable_variable import MutableVariable
from lib.common.packet.packet import Packet, PacketGbn
from lib.common.sequence_number import SequenceNumber
from lib.common.socket_saw import SocketSaw
from lib.server.client_pool import ClientPool
from lib.server.connection_state import ConnectionState
from lib.server.exceptions.unexpected_operation import UnexpectedOperation
from lib.server.exceptions.client_already_connected import ClientAlreadyConnected
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.server.exceptions.missing_client_address import MissingClientAddress
from lib.common.file_handler import FileHandler

from lib.server.protocol import ServerProtocol


class ConnectionClosingNeeded(Exception):
    def __init__(
        self, message="Client is already connect", sequence_number=None, ack_number=None
    ):
        self.message = message
        self.sequence_number = sequence_number
        self.ack_number = ack_number

    def __repr__(self):
        return f"ClientAlreadyConnected: {self.message})"


class ClientConnection:
    def __init__(
        self,
        connection_socket: SocketSaw,
        connection_address: Address,
        client_address: Address,
        protocol: str,
        logger: CoolLogger,
        file_handler: FileHandler,
        packet: Packet,
    ):
        self.socket: SocketSaw = connection_socket
        self.address: Address = connection_address
        self.client_address: Address = client_address
        self.logger: CoolLogger = logger
        self.logger.set_prefix(f"[CONN:{connection_address.port}]")
        self.socket.logger.set_prefix(f"[CONN:{connection_address.port}]")
        self.initial_sequence_number: SequenceNumber = SequenceNumber(
            packet.sequence_number, protocol
        )
        self.initial_packet = packet

        self.file_handler: FileHandler = file_handler

        self.protocol: ServerProtocol = ServerProtocol(
            self.logger, self.socket, self.address, protocol, ClientPool()
        )
        self.state: ConnectionState = ConnectionState.HANDHSAKE_FINISHED
        self.run_thread = Thread(target=self.run)
        self.file = None
        self.killed = False

    def process_operation_intention(
        self, sequence_number: MutableVariable, ack_number: MutableVariable
    ) -> int:
        self.logger.debug("Processing operation intention")
        try:
            op_code, _seq, _ack = self.protocol.process_operation_intention(
                self.initial_packet
            )
            sequence_number.value = _seq

            if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
                ack_number.value = _ack

            if op_code == UPLOAD_OPERATION:
                self.state = ConnectionState.READY_TO_RECEIVE
            elif op_code == DOWNLOAD_OPERATION:
                self.state = ConnectionState.READY_TO_TRANSMIT
            else:
                self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
                self.logger.debug("Bad state. Unexpected operation")

            self.logger.debug(f"Operation is: {OPERATION_STRING_FROM_CODE[op_code]}")
            self.logger.debug("Confirming operation")
            self.protocol.send_ack(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )

            return op_code

        except MissingClientAddress as e:
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise e

    def is_filename_valid_for_upload(self, filename: str) -> bool:
        try:
            self.file = self.file_handler.open_file_write_mode(
                filename, is_path_complete=False
            )
            return True
        except InvalidFilename:
            return False

    def is_filesize_valid_for_upload(self, filesize: int) -> bool:
        return self.file_handler.can_file_fit(filesize)

    def receive_file_info_for_upload(
        self, sequence_number: MutableVariable, ack_number: MutableVariable
    ) -> tuple[str, int]:
        self.logger.debug("Validating filename")
        sequence_number.value.step()

        if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            ack_number.value.step()

        _seq, filename = self.protocol.receive_filename(sequence_number.value)
        sequence_number.value = _seq

        if self.is_filename_valid_for_upload(filename):
            self.protocol.send_ack(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )
            self.logger.debug(f"Filename received valid: {filename}")
        else:
            self.logger.warn("Filename received invalid")
            self.logger.error(
                f"Client {self.client_address.to_combined()} shutting down due to file '{filename}' already existing in the server"
            )
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise ConnectionClosingNeeded(
                sequence_number=sequence_number, ack_number=ack_number
            )

        self.logger.debug("Validating filesize")
        sequence_number.value.step()
        _seq, filesize = self.protocol.receive_filesize(sequence_number.value)
        sequence_number.value = _seq

        if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            ack_number.value.step()

        if self.is_filesize_valid_for_upload(filesize):
            self.protocol.send_ack(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )
            self.logger.debug(f"Filesize received valid: {filesize} bytes")
        else:
            self.logger.warn("Filesize received invalid")
            self.logger.error(
                f"Client {self.client_address.to_combined()} shutdowned due to file being too big"
            )
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise ConnectionClosingNeeded(
                sequence_number=sequence_number, ack_number=ack_number
            )

        return filename, filesize

    def is_filename_valid_for_download(self, filename: str):
        try:
            self.file = self.file_handler.open_file_read_mode(
                filename, is_path_complete=False
            )
            return True
        except InvalidFilename:
            return False

    def receive_file_info_for_download(
        self, sequence_number: MutableVariable, ack_number: MutableVariable
    ) -> tuple[str, int]:
        self.logger.debug("Validating filename")
        sequence_number.value.step()
        _seq, filename = self.protocol.receive_filename(sequence_number.value)
        sequence_number.value = _seq

        if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            ack_number.value.step()

        if self.is_filename_valid_for_download(filename):
            self.logger.debug("Filename received valid")
        else:
            self.protocol.send_fin(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )
            self.logger.warn("Filename received invalid")
            self.logger.error(
                f"Client {self.client_address.to_combined()} shutdowned due to file '{filename}' not existing in server for download"
            )
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            raise ConnectionClosingNeeded(
                sequence_number=sequence_number, ack_number=ack_number
            )

        filesize = self.file_handler.get_filesize(filename, is_path_complete=False)

        return filename, filesize

    def file_cleanup_after_error(
        self, filename_for_upload: MutableVariable, filesize_for_upload: MutableVariable
    ):
        if self.file is not None and self.file_handler.is_closed(self.file):
            self.file_handler.close(self.file)

        if filename_for_upload.value is not None:
            self.file_handler.remove_file_if_corrupted_or_incomplete(
                filename_for_upload, filesize_for_upload, is_path_complete=False
            )

    def initiate_close_connection(
        self, sequence_number: MutableVariable, ack_number: MutableVariable
    ):
        try:
            self.logger.debug("Initiating connection close")
            sequence_number.value.step()

            if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
                ack_number.value.step()

            self.protocol.send_fin(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )

            # sequence_number.value.step()
            #
            # if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            #     ack_number.value.step()

            self.protocol.wait_for_fin_or_ack(sequence_number.value)
            self.logger.debug("Received connection finalization from client")

            sequence_number.value.step()

            if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
                ack_number.value.step()

            self.protocol.send_ack(
                sequence_number.value,
                ack_number.value,
                self.client_address,
                self.address,
            )
            self.logger.info("Connection closed")
        except Exception as e:
            err = e.message if hasattr(e, "message") else e
            self.logger.debug(err)

    @abstractmethod
    def perform_upload(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_upload: MutableVariable,
        filesize_for_upload: MutableVariable,
    ):
        pass

    @abstractmethod
    def perform_download(
        self,
        sequence_number: MutableVariable,
        ack_number: MutableVariable,
        filename_for_download: MutableVariable,
    ):
        pass

    def run(self):
        filename_for_upload = MutableVariable(None)
        filesize_for_upload = MutableVariable(None)
        filename_for_download = MutableVariable(None)
        sequence_number = MutableVariable(
            SequenceNumber(
                self.initial_sequence_number.value, self.protocol.protocol_version
            )
        )

        ack_number = MutableVariable(None)
        if self.protocol.protocol_version == GO_BACK_N_PROTOCOL_TYPE:
            packet: PacketGbn = self.initial_packet
            ack_number = MutableVariable(
                SequenceNumber(packet.ack_number, self.protocol.protocol_version)
            )

        try:
            op_code = self.process_operation_intention(sequence_number, ack_number)

            if op_code == UPLOAD_OPERATION:
                self.perform_upload(
                    sequence_number,
                    ack_number,
                    filename_for_upload,
                    filesize_for_upload,
                )
                self.logger.force_info(
                    f"Upload completed from client {self.client_address.to_combined()}"
                )
            elif op_code == DOWNLOAD_OPERATION:
                self.perform_download(
                    sequence_number, ack_number, filename_for_download
                )
                self.logger.force_info(
                    f"Download completed to client {self.client_address.to_combined()}"
                )

        except (SocketShutdown, ConnectionLost):
            self.logger.debug("State is unrecoverable")
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            self.logger.debug("Connection shutdown")
            self.file_cleanup_after_error(filename_for_upload, filesize_for_upload)
            self.kill()
        except ConnectionClosingNeeded as e:
            self.initiate_close_connection(e.sequence_number, e.ack_number)
        except (
            MissingClientAddress,
            UnexpectedOperation,
            InvalidSequenceNumber,
            UnexpectedFinMessage,
            ClientAlreadyConnected,
            MessageIsNotAck,
            MessageIsNotFinAck,
        ) as e:
            self.logger.warn(f"{e.message}")
            self.logger.debug("State can be recovered")

        except Exception as e:
            self.state = ConnectionState.UNRECOVERABLE_BAD_STATE
            err = e.message if hasattr(e, "message") else e
            err_class = e.__class__.__name__
            self.logger.error(f"Fatal error: [{err_class}] {err}")
            self.file_cleanup_after_error(filename_for_upload, filesize_for_upload)
            self.kill()

    def start(self):
        self.run_thread.start()

    @abstractmethod
    def kill(self):
        pass

    @abstractmethod
    def is_ready_to_die(self) -> bool:
        pass

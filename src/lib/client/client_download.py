from os import getcwd
import sys
from lib.client.abstract_client import Client
from lib.common.logger import Logger
from lib.common.constants import DOWNLOAD_OPERATION, ERROR_EXIT_CODE
from lib.common.exceptions.invalid_filename import InvalidFilename
from lib.common.file_handler import FileHandler


class DownloadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, dst: str, name: str, protocol: str
    ):
        try:
            self.file_handler: FileHandler = FileHandler(getcwd(), logger)
            self.file = self.file_handler.open_file_absolute(dst)
        except InvalidFilename:
            sys.exit(ERROR_EXIT_CODE)

        super().__init__(logger, host, port, protocol)
        self.file_destination: str = dst
        self.file_name: str = name

        self.logger.debug(f"Location to save downloaded file: {self.file_destination}")

    def perform_operation(self) -> None:
        self.perform_download()

    def perform_download(self) -> None:
        try:
            self.send_operation_intention()
            self.send_file_name_to_download()
            self.receive_file()
            self.closing_handshake()
        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")

    def send_operation_intention(self) -> None:
        try:
            self.logger.debug("Sending operation intention")

            self.sequence_number.flip()
            self.protocol.send_operation_intention(
                self.sequence_number, DOWNLOAD_OPERATION
            )

            self.logger.debug("Waiting for operation confirmation")
            self.protocol.wait_for_operation_confirmation(self.sequence_number)
            self.logger.debug("Operation accepted")
        except Exception:
            # To do: Agregar manejo de excepciones
            pass

    def send_file_name_to_download(self):
        try:
            self.logger.debug(f"Sending file name to download: {self.file_name}")
            self.protocol.inform_filename(self.sequence_number, self.file_name)

            self.logger.debug("Waiting for file name confirmation")
            self.protocol.wait_for_ack(self.sequence_number)

            self.logger.debug("Filename to download confirmed")
        except Exception as e:
            # To do: Agregar manejo de excepciones
            self.logger.error(f"Error sending file name, {e}")

    def receive_file(self) -> None:
        self.logger.debug("Receiving file info")
        try:
            chunk_number: int = 1

            self.sequence_number.flip()
            self.sequence_number, packet = self.protocol.receive_file_chunk(
                self.sequence_number
            )

            if packet.is_fin:
                self.protocol.send_fin_ack(self.sequence_number)
            else:
                self.protocol.send_ack(self.sequence_number)

            self.file_handler.append_to_file(self.file, packet)

            self.logger.debug(f"Received chunk {chunk_number} info: {len(packet.data)}")

            while not packet.is_fin:
                chunk_number += 1
                self.sequence_number.flip()
                self.sequence_number, packet = self.protocol.receive_file_chunk(
                    self.sequence_number
                )

                if packet.is_fin:
                    self.protocol.send_fin_ack(self.sequence_number)
                else:
                    self.protocol.send_ack(self.sequence_number)

                self.logger.debug(f"Received chunk {chunk_number}")
                self.file_handler.append_to_file(self.file, packet)

            self.logger.debug("Finished receiving file")
            self.file.close()

        except Exception as e:
            # To do: Agregar manejo de excepciones
            self.logger.error(f"Error receiving file, {e}")
            pass

    def closing_handshake(self) -> None:
        self.logger.debug("Starting closing handshake")
        try:
            self.sequence_number.flip()
            self.protocol.wait_for_ack(self.sequence_number)
            self.logger.debug("Connection closed, file transfer complete")
        except Exception:
            # To do: Agregar manejo de excepciones
            pass

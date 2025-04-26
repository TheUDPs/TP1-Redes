from lib.client.abstract_client import Client
from lib.common.logger import Logger
from src.lib.common.constants import DOWNLOAD_OPERATION
from src.lib.server.file_handler import FileHandler


class DownloadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, dst: str, name: str, protocol: str
    ):
        try:
            self.file_handler: FileHandler = FileHandler(self.logger, dst)
        except Exception as e:
            self.logger.error(f"Error opening storage directory: {e}")
            pass
        super().__init__(logger, host, port, protocol)
        self.file_destination: str = dst
        self.file_name: str = name

    def perform_operation(self) -> None:
        self.perform_download()

    def perform_download(self) -> None:
        try:
            self.send_operation_intention()
            self.send_file_name()
            self.receive_file()
        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")

    def send_operation_intention(self) -> None:
        self.logger.debug("Sending operation intention")
        try:
            self.protocol.send_operation_intention(
                self.sequence_number, DOWNLOAD_OPERATION
            )
            self.protocol.wait_for_operation_confirmation(self.sequence_number)
            self.logger.debug("Operation accepted")
        except Exception:
            pass
        except Exception:
            pass

    def send_file_name(self):
        try:
            self.logger.debug("Sending file name")
            self.protocol.inform_filename(self.sequence_number, self.file_name)
            self.logger.debug("Awaiting for file name confirmation")
            self.protocol.wait_for_file_info_confirmation(self.sequence_number)
            self.logger.debug("File name confirmed")
            # To do: Agregar manejo de excepciones
        except Exception:
            self.logger.error("Error sending file name")

    def receive_file(self) -> None:
        self.logger.debug("Receiving file info")
        try:
            self.protocol.send_ack(
                self.sequence_number, self.client_address, self.address
            )

            chunk_number: int = 1

            self.sequence_number.flip()
            self.sequence_number, packet = self.protocol.receive_file_chunk(
                self.sequence_number
            )

            if packet.is_fin:
                self.protocol.send_fin_ack(
                    self.sequence_number, self.client_address, self.address
                )

            self.protocol.send_ack(
                self.sequence_number, self.client_address, self.address
            )

            self.logger.debug(f"Received chunk {chunk_number}")

            while not packet.is_fin:
                chunk_number += 1
                self.sequence_number.flip()
                self.sequence_number, packet = self.protocol.receive_file_chunk(
                    self.sequence_number
                )

                if packet.is_fin:
                    self.protocol.send_fin_ack(
                        self.sequence_number, self.client_address, self.address
                    )
                else:
                    self.protocol.send_ack(
                        self.sequence_number, self.client_address, self.address
                    )

                self.logger.debug(f"Received chunk {chunk_number}")
                self.file_handler.append_to_file(self.file, packet)

        except Exception:
            pass

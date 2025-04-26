from lib.client.abstract_client import Client
from lib.common.logger import Logger
from src.lib.common.constants import DOWNLOAD_OPERATION


class DownloadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, dst: str, name: str, protocol: str
    ):
        super().__init__(logger, host, port, protocol)

    def perform_operation(self) -> None:
        self.perform_download()

    def perform_download(self) -> None:
        try:
            self.operation_intention()
            self.receive_file_info()
            self.receive_file()
        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")

    def receive_file_info(self) -> None:
        try:
            self.logger.debug("Receiving file info")
            self.send_file_name()

        except Exception:
            pass

    def send_file_name(self):
        pass

    def receive_file(self) -> None:
        self.logger.debug("Receiving file info")
        try:
            pass
        except Exception:
            pass

    def send_operation_intention(self) -> None:
        self.logger.debug("[CONN] Sending operation intention")
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

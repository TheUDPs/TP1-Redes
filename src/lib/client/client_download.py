from lib.client.abstract_client import Client
from lib.common.logger import Logger


class DownloadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, dst: str, name: str, protocol: str
    ):
        super().__init__(logger, host, port, protocol)

    def perform_operation(self) -> None:
        self.perform_download()

    def perform_download(self) -> None:
        try:
            pass
        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")

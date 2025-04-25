from lib.client.abstract_client import Client
from lib.common.constants import UPLOAD_OPERATION
from lib.common.logger import Logger


class UploadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, src: str, name: str, protocol: str
    ):
        super().__init__(logger, host, port, src, name, protocol)

    def perform_operation(self) -> None:
        self.perform_upload()

    def perform_upload(self) -> None:
        self.protocol.send_operation_intention(self.sequence_number, UPLOAD_OPERATION)
        self.protocol.wait_for_operation_confirmation(self.sequence_number)
        self.logger.debug("Operation accepted")
        _file = self.get_file()

    def get_file(self) -> []:
        self.logger.info("Reading file")
        return []

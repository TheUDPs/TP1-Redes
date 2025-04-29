from os import getcwd, path

from src.lib.client.abstract_client import Client
from src.lib.client.exceptions.file_already_exists import FileAlreadyExists
from src.lib.client.exceptions.file_too_big import FileTooBig
from src.lib.common.constants import ERROR_EXIT_CODE, UPLOAD_OPERATION
from src.lib.common.exceptions.connection_lost import ConnectionLost
from src.lib.common.exceptions.invalid_filename import InvalidFilename
from src.lib.common.file_handler import FileHandler
from src.lib.common.logger import Logger


# TODO
class UploadClient(Client):
    def __init__(
        self, logger: Logger, host: str, port: int, src: str, name: str, protocol: str
    ):
        self.src_filepath: str = src
        self.filename_in_server: str = name

        try:
            self.file_handler: FileHandler = FileHandler(getcwd(), logger)
            self.file = self.file_handler.open_file_read_mode(
                self.src_filepath, is_path_complete=True
            )
            self.filesize = self.file_handler.get_filesize(
                self.src_filepath, is_path_complete=True
            )
            print(self.file, self.filesize)
        except InvalidFilename:
            logger.error(f"Could not find or open file {src}")
            exit(ERROR_EXIT_CODE)

        if name is None or name == "":
            self.filename_in_server = path.basename(self.src_filepath)

        super().__init__(logger, host, port, protocol)

    def perform_operation(self) -> None:
        self.perform_upload()

    def perform_upload(self) -> None:
        try:
            self.send_operation_intention(UPLOAD_OPERATION)
            self.inform_size_and_name()
            self.send_file()
            self.closing_handshake()

        except (FileAlreadyExists, FileTooBig, ConnectionLost) as e:
            self.logger.error(f"{e.message}")
            self.file_cleanup_after_error()

        except Exception as e:
            err = e.message if e.message else e
            self.logger.error(f"Error message: {err}")
            self.file_cleanup_after_error()

    def inform_size_and_name(self) -> None:
        pass

    def send_file(self) -> None:
        pass

    def closing_handshake(self) -> None:
        pass

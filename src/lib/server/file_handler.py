from os import path
from shutil import disk_usage

from lib.common.constants import (
    FOPEN_BINARY_MODE,
    FOPEN_READ_MODE,
    FOPEN_WRITE_TRUNCATE_MODE,
)
from lib.common.logger import Logger
from lib.common.packet import Packet
from lib.server.exceptions.invalid_directory import InvalidDirectory
from lib.server.exceptions.invalid_filename import InvalidFilename

MINIMUM_FREE_GAP = 100_000_000


class FileHandler:
    def __init__(self, dirpath: str, logger: Logger):
        self.dirpath: str = dirpath
        self.logger: Logger = logger

        if not path.isdir(self.dirpath):
            raise InvalidDirectory()

    def open_file(self, filename: str):
        file_path = path.join(self.dirpath, filename)
        try:
            if path.isfile(file_path):
                self.logger.error("Invalid filename, already exists")
                raise InvalidFilename()

            file = open(file_path, FOPEN_WRITE_TRUNCATE_MODE + FOPEN_BINARY_MODE)
            return file
        except IOError as e:
            self.logger.error(f"I/O error occurred: {e}")
            raise InvalidFilename()

    def open_file_read(self, filename: str):
        file_path = path.join(self.dirpath, filename)
        try:
            if not path.isfile(file_path):
                self.logger.error("Invalid filename, does not exist")
                raise InvalidFilename()

            file = open(file_path, FOPEN_READ_MODE + FOPEN_BINARY_MODE)
            return file
        except IOError as e:
            self.logger.error(f"I/O error occurred: {e}")
            raise InvalidFilename()

    def open_file_absolute(self, abs_route: str):
        try:
            self.logger.debug(f"Absolute path: {abs_route}")
            if path.isfile(abs_route):
                self.logger.error("Invalid filename, already exists")
                raise InvalidFilename()
            file = open(abs_route, FOPEN_WRITE_TRUNCATE_MODE + FOPEN_BINARY_MODE)
            return file
        except IOError as e:
            self.logger.error(f"I/O error occurred: {e}")
            raise InvalidFilename()

    def can_file_fit(self, filesize: int) -> bool:
        _total_space, _used_space, free_space = disk_usage(self.dirpath)
        return (free_space - MINIMUM_FREE_GAP) > filesize

    def append_to_file(self, file, packet: Packet) -> None:
        file.write(packet.data)

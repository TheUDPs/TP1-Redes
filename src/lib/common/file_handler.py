from math import ceil
from os import path, stat, remove
from shutil import disk_usage

from lib.common.constants import (
    FOPEN_BINARY_MODE,
    FOPEN_READ_MODE,
    FOPEN_WRITE_TRUNCATE_MODE,
)
from lib.common.logger import Logger
from lib.common.mutable_variable import MutableVariable
from lib.common.packet import Packet
from lib.server.exceptions.invalid_directory import InvalidDirectory
from lib.common.exceptions.invalid_filename import InvalidFilename

MINIMUM_FREE_GAP = 104_857_600  # 100 MB


class FileHandler:
    def __init__(self, dirpath: str, logger: Logger):
        self.dirpath: str = dirpath
        self.logger: Logger = logger

        if not path.isdir(self.dirpath):
            raise InvalidDirectory()

    def open_file(self, filepath: str, is_write: bool, is_binary: bool):
        flags = ""

        if is_write:
            flags += FOPEN_WRITE_TRUNCATE_MODE
        else:
            flags += FOPEN_READ_MODE

        if is_binary:
            flags += FOPEN_BINARY_MODE

        try:
            if is_write and path.isfile(filepath):
                raise InvalidFilename()

            file = open(filepath, flags)
            return file

        except IOError as e:
            self.logger.debug(f"I/O error occurred: {e}")
            raise InvalidFilename()

    def get_filepath(self, base_filepath: str, is_path_complete: bool):
        if is_path_complete:
            final_filepath = base_filepath
        else:
            final_filepath = path.join(self.dirpath, base_filepath)

        return final_filepath

    def open_file_write_mode(self, filepath: str, is_path_complete: bool):
        final_filepath = self.get_filepath(filepath, is_path_complete)
        return self.open_file(final_filepath, is_write=True, is_binary=True)

    def open_file_read_mode(self, filepath: str, is_path_complete: bool):
        final_filepath = self.get_filepath(filepath, is_path_complete)
        return self.open_file(final_filepath, is_write=False, is_binary=True)

    def get_filesize(self, filepath: str, is_path_complete: bool):
        final_filepath = self.get_filepath(filepath, is_path_complete)
        stats = stat(final_filepath)
        return stats.st_size

    def is_closed(self, file) -> bool:
        return file.closed

    def close(self, file):
        file.close()

    def read(self, file, n_bytes: int):
        return file.read(n_bytes)

    def can_file_fit(self, filesize: int) -> bool:
        _total_space, _used_space, free_space = disk_usage(self.dirpath)
        return (free_space - MINIMUM_FREE_GAP) > filesize

    def append_to_file(self, file, packet: Packet) -> None:
        file.write(packet.data)

    def bytes_to_megabytes(self, bytes: int) -> str:
        megabytes = bytes / (1024 * 1024)
        return "{0:.2f}".format(megabytes)

    def bytes_to_kilobytes(self, bytes: int) -> str:
        megabytes = bytes / (1024)
        return "{0:.2f}".format(megabytes)

    def get_number_of_chunks(self, file_size: int, chunk_size: int) -> int:
        return ceil(file_size / chunk_size)

    def remove_file_if_corrupted_or_incomplete(
        self,
        filename: MutableVariable,
        filesize: MutableVariable,
        is_path_complete: bool,
    ):
        try:
            final_filepath = self.get_filepath(filename.value, is_path_complete)

            if not path.isfile(final_filepath):
                return

            real_size = path.getsize(final_filepath)

            if filesize.value is None:
                self.logger.warn(
                    f"File {final_filepath} is corrupted or incomplete. Removing file"
                )
                remove(final_filepath)
            elif real_size != filesize.value:
                self.logger.warn(f"File {final_filepath} is corrupted or incomplete.")
                self.logger.warn(
                    f"Expected {self.bytes_to_kilobytes(filesize.value)} kB, got {self.bytes_to_kilobytes(real_size)} kB. Removing file"
                )
                remove(final_filepath)
            else:
                self.logger.debug(f"File {final_filepath} is OK")

        except Exception as e:
            self.logger.warn(f"Error checking or removing file {filename.value}: {e}")

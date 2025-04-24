import argparse

from lib.common.constants import (
    DEFAULT_PORT,
    GO_BACK_N_PROTOCOL_TYPE,
    STOP_AND_WAIT_PROTOCOL_TYPE,
)


class ClientUploadArgParser:
    def __init__(self):
        self.internal_parser = argparse.ArgumentParser(
            description="Client side application to upload files to the server side"
        )

    def parse(self):
        verbosity_group = self.internal_parser.add_mutually_exclusive_group(
            required=False
        )

        verbosity_group.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="increase output verbosity",
        )

        verbosity_group.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="decrease output verbosity",
        )

        self.internal_parser.add_argument(
            "-H",
            "--host",
            required=True,
            type=str,
            metavar="ADDR",
            help="server IP address",
        )

        self.internal_parser.add_argument(
            "-p",
            "--port",
            required=False,
            default=DEFAULT_PORT,
            type=int,
            metavar="PORT",
            help="server port",
        )

        self.internal_parser.add_argument(
            "-s",
            "--src",
            required=True,
            type=str,
            metavar="FILEPATH",
            help="source file path",
        )

        self.internal_parser.add_argument(
            "-n",
            "--name",
            required=False,
            type=str,
            metavar="FILENAME",
            help="file name on the server",
        )

        self.internal_parser.add_argument(
            "-r",
            "--protocol",
            required=False,
            choices=[STOP_AND_WAIT_PROTOCOL_TYPE, GO_BACK_N_PROTOCOL_TYPE],
            default=GO_BACK_N_PROTOCOL_TYPE,
            metavar="PROTOCOL",
            help="error recovery protocol",
        )

        return self.internal_parser.parse_args()

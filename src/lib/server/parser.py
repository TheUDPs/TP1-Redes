import argparse

from lib.common.constants import (
    DEFAULT_PORT,
    GO_BACK_N_PROTOCOL_TYPE,
    STOP_AND_WAIT_PROTOCOL_TYPE,
    IPV4_LOCALHOST,
)


class ServerArgParser:
    def __init__(self):
        self.internal_parser = argparse.ArgumentParser(
            description="Serve side application to upload and download files from"
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
            required=False,
            type=str,
            default=IPV4_LOCALHOST,
            metavar="ADDR",
            help="service IP address",
        )

        self.internal_parser.add_argument(
            "-p",
            "--port",
            required=False,
            default=DEFAULT_PORT,
            type=int,
            metavar="PORT",
            help="service port",
        )

        self.internal_parser.add_argument(
            "-s",
            "--storage",
            required=False,
            type=str,
            metavar="DIRPATH",
            help="storage dir path",
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

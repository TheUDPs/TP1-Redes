#!/usr/bin/env python3

import argparse
from lib.constants import (
    DEFAULT_PORT,
    GO_BACK_N_PROTOCOL_TYPE,
    STOP_AND_WAIT_PROTOCOL_TYPE,
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Client side application to upload files to the server side"
    )

    verbosity_group = parser.add_mutually_exclusive_group(required=False)

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

    parser.add_argument(
        "-H",
        "--host",
        required=True,
        type=str,
        metavar="ADDR",
        help="server IP address",
    )

    parser.add_argument(
        "-p",
        "--port",
        required=False,
        default=DEFAULT_PORT,
        type=int,
        metavar="PORT",
        help="server port",
    )

    parser.add_argument(
        "-s",
        "--src",
        required=True,
        type=str,
        metavar="FILEPATH",
        help="source file path",
    )

    parser.add_argument(
        "-n",
        "--name",
        required=False,
        type=str,
        metavar="FILENAME",
        help="file name",
    )

    parser.add_argument(
        "-r",
        "--protocol",
        required=False,
        choices=[STOP_AND_WAIT_PROTOCOL_TYPE, GO_BACK_N_PROTOCOL_TYPE],
        default=GO_BACK_N_PROTOCOL_TYPE,
        metavar="PROTOCOL",
        help="error recovery protocol",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()
    print("Args received:")
    print(args)


if __name__ == "__main__":
    main()

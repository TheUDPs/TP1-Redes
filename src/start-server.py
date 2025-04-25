#!/usr/bin/env python3
from lib.common.logger import get_logger
from lib.server.parser import ServerArgParser
from lib.server.server import Server


def start_server():
    arg_parser = ServerArgParser()
    args = arg_parser.parse()

    logger = get_logger(args.verbose, args.quiet)

    args_dict = vars(args)
    args_dict.pop("verbose")
    args_dict.pop("quiet")

    server: Server = Server(logger, **args_dict)
    server.run()


if __name__ == "__main__":
    start_server()

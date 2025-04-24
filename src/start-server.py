#!/usr/bin/env python3
from lib.common.logger import Logger
from lib.server.parser import ServerArgParser
from lib.server.server import Server


def start_server():
    arg_parser = ServerArgParser()
    args = arg_parser.parse()
    logger = Logger(Logger.INFO_LOG_LEVEL)

    logger.info(f"Starting server at {args.host}:{args.port}")

    server: Server = Server(args, logger)
    server.run()

    logger.info("Server shutdown")


if __name__ == "__main__":
    start_server()

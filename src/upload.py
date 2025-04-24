#!/usr/bin/env python3
from lib.client.client import Client
from lib.client.parser_upload import ClientUploadArgParser
from lib.common.logger import Logger


def upload():
    arg_parser = ClientUploadArgParser()
    args = arg_parser.parse()
    logger = Logger(Logger.INFO_LOG_LEVEL)

    logger.info("Client started for upload")

    client: Client = Client(args, logger)
    client.run()

    logger.info("Shutdown")


if __name__ == "__main__":
    upload()

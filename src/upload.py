#!/usr/bin/env python3
from lib.client.client_upload import UploadClient
from lib.client.parser_upload import ClientUploadArgParser
from lib.common.logger import get_logger


def upload():
    arg_parser = ClientUploadArgParser()
    args = arg_parser.parse()

    logger = get_logger(args.verbose, args.quiet)

    args_dict = vars(args)
    args_dict.pop("verbose")
    args_dict.pop("quiet")

    client: UploadClient = UploadClient(logger, **args_dict)
    client.run()


if __name__ == "__main__":
    upload()

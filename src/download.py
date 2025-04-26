#!/usr/bin/env python3
from lib.client.client_download import DownloadClient
from lib.client.parser_download import ClientDownloadArgParser
from lib.common.logger import get_logger


def download():
    arg_parser = ClientDownloadArgParser()
    args = arg_parser.parse()

    logger = get_logger(args.verbose, args.quiet)

    args_dict = vars(args)
    args_dict.pop("verbose")
    args_dict.pop("quiet")

    client: DownloadClient = DownloadClient(logger, **args_dict)
    client.run()


if __name__ == "__main__":
    download()

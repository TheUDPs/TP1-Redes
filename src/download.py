#!/usr/bin/env python3
from lib.client.parser_download import ClientDownloadArgParser


def download():
    arg_parser = ClientDownloadArgParser()
    _args = arg_parser.parse()  # noqa: F841

    print("Client started for download")
    print("Shutdown")


if __name__ == "__main__":
    download()

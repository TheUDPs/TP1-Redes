#!/usr/bin/env python3

from lib.client.parser_upload import ClientUploadArgParser


def upload():
    arg_parser = ClientUploadArgParser()
    _args = arg_parser.parse()  # noqa: F841

    print("Client started for upload")
    print("Shutdown")


if __name__ == "__main__":
    upload()

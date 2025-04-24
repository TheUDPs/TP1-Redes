#!/usr/bin/env python3
from lib.server.parser import ServerArgParser


def start_server():
    arg_parser = ServerArgParser()
    args = arg_parser.parse()

    print(f"Server running on {args.host}:{args.port}")
    print("Shutdown")


if __name__ == "__main__":
    start_server()

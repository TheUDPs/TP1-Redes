#!/usr/bin/env python3
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Script to start a file upload server with configurable storage and protocol."
    )

    parser.add_argument(
        "-H",
        "--host",
        default="0.0.0.0",
        metavar="ADDR",
        help="The address the server will bind to (default: 0.0.0.0).",
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=7001,
        metavar="PORT",
        help="The port the server will listen on (default: 7001).",
    )

    parser.add_argument(
        "-s",
        "--storage",
        required=True,
        metavar="DIRPATH",
        help="Path to the directory where uploaded files will be stored.",
    )

    parser.add_argument(
        "-t",
        "--protocol",
        choices=["stop-and-wait", "gbn"],
        metavar="PROTOCOL",
        help="Protocol to use for receiving files. Allowed values: 'stop-and-wait' or 'gbn'.",
    )

    args = parser.parse_args()

    print("Starting server with the following configuration:")
    print(f"  Host:     {args.host}")
    print(f"  Port:     {args.port}")
    print(f"  Storage:  {args.storage}")
    print(f"  Protocol: {args.protocol}")

    print("Server is now running...")


if __name__ == "__main__":
    main()

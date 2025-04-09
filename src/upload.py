#!/usr/bin/env python3
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Script to upload files to a server with optional verbosity/quiet modes, "
        "and a choice of protocol."
    )

    parser.add_argument(
        "-v",
        action="store_true",
        help="Enable verbose mode (print extra information during upload).",
    )
    parser.add_argument(
        "-q",
        action="store_true",
        help="Enable quiet mode (print as little output as possible).",
    )

    parser.add_argument(
        "-H",
        "--host",
        default="127.0.0.1",
        metavar="ADDR",
        help="The server's IP address or hostname to which files are uploaded (default: 127.0.0.1).",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=7001,
        metavar="PORT",
        help="The port on the server to connect to (default: 7001).",
    )

    parser.add_argument(
        "-s",
        "--filepath",
        required=True,
        metavar="FILEPATH",
        help="The local path of the file to be uploaded.",
    )

    parser.add_argument(
        "-n",
        "--filename",
        required=False,
        metavar="FILENAME",
        help="The name under which the file will be saved on the server.",
    )

    parser.add_argument(
        "-t",
        "--protocol",
        choices=["stop-and-wait", "gbn"],
        metavar="PROTOCOL",
        help="Protocol to use for file transfer. Allowed values: 'stop-and-wait' or 'gbn'.",
    )

    args = parser.parse_args()

    if args.v and args.q:
        print(
            "Error: You cannot use both -v (verbose) and -q (quiet) at the same time.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.v:
        print("Arguments received:")
        print(f"  Verbose Mode: {args.v}")
        print(f"  Quiet Mode:   {args.q}")
        print(f"  Host:         {args.host}")
        print(f"  Port:         {args.port}")
        print(f"  File Path:    {args.filepath}")
        print(f"  File Name:    {args.filename}")
        print(f"  Protocol:     {args.protocol}")

    if not args.q:
        print(
            "File upload script is ready to upload the file with the specified arguments."
        )
        if args.filepath:
            print(
                f"Preparing to upload {args.filepath} to {args.host}:{args.port} as {args.filename} using {args.protocol}."
            )


if __name__ == "__main__":
    main()

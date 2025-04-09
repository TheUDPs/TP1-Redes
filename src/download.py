#!/usr/bin/env python3
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Script to download a file from a server using a specified transfer protocol."
    )

    # Verbose and quiet flags
    parser.add_argument(
        "-v",
        action="store_true",
        help="Enable verbose mode (print extra information during download).",
    )
    parser.add_argument(
        "-q", action="store_true", help="Enable quiet mode (print minimal output)."
    )

    parser.add_argument(
        "-H",
        "--host",
        default="127.0.0.1",
        metavar="ADDR",
        help="Server's IP address or hostname to download the file from (default: 127.0.0.1).",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=7001,
        metavar="PORT",
        help="Port on the server to connect to (default: 7001).",
    )

    parser.add_argument(
        "-n",
        "--filename",
        required=True,
        metavar="FILENAME",
        help="Name of the remote file to be downloaded.",
    )

    parser.add_argument(
        "-d",
        "--destination",
        metavar="DEST",
        help="Local path (directory or full file path) to save the downloaded file. Defaults to the current directory.",
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
        print(f"  Remote File:  {args.filename}")
        print(f"  Destination:  {args.destination}")
        print(f"  Protocol:     {args.protocol}")

    if not args.q:
        print("Download script is ready to retrieve the file from the server.")

        dest_str = args.destination if args.destination else "current directory"
        print(
            f"Preparing to download {args.filename} from {args.host}:{args.port} "
            f"and save it to {dest_str} using {args.protocol} protocol."
        )


if __name__ == "__main__":
    main()

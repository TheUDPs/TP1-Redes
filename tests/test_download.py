#!/usr/bin/env python3

import os
from tests.utils import (
    PROJECT_ROOT,
    generate_random_text_file,
    hosts_setup,
    net_setup,
    operation_to_test,
    shutdown,
)


def start_download_client(host, tmp_path, server_filename, client_dest_path):
    log_file = f"{tmp_path}/client_output.log"
    pid = host.cmd(
        f"{PROJECT_ROOT}/src/download.py -H 10.0.0.1 -n {server_filename} -d {client_dest_path} -r saw -q > {log_file} 2>&1 & echo $!"
    )
    return pid.strip(), log_file


def test_download_of_random_text_is_correct_without_packet_loss():
    net, h1, h2 = net_setup()
    tmp_path, filepath, server_pid, server_log = hosts_setup(h1, h2)

    # Create the file directly in server path
    original_filename = "test_file.txt"
    server_path = os.path.join(tmp_path, "server", original_filename)
    generate_random_text_file(server_path)

    # Choose dir where client will download the file
    client_download_path = os.path.join(tmp_path, "client", "downloaded_file.txt")

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_download_client(
        h2,
        tmp_path,
        server_filename=original_filename,
        client_dest_path=client_download_path,
    )

    was_client_successful, was_server_successful, start_time = operation_to_test(
        server_log, client_log, "Download completed", "Download completed to client"
    )
    shutdown(
        start_time,
        h1,
        h2,
        server_pid,
        client_pid,
        net,
        server_log,
        client_log,
        tmp_path,
    )

    assert was_client_successful.value, "Client did not report successful file transfer"
    assert was_server_successful.value, "Server did not report successful file upload"

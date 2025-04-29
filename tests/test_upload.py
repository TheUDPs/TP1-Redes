#!/usr/bin/env python3

from tests.utils import (
    PROJECT_ROOT,
    hosts_setup,
    net_setup,
    operation_to_test,
    shutdown,
)


def start_upload_client(host, tmp_path, file_to_upload):
    log_file = f"{tmp_path}/client_output.log"
    pid = host.cmd(
        f"{PROJECT_ROOT}/src/upload.py -H 10.0.0.1 -s {file_to_upload} -r saw -q > {log_file} 2>&1 & echo $!"
    )
    return pid.strip(), log_file


def test_upload_of_random_text_is_correct_without_packet_loss():
    net, h1, h2 = net_setup()
    tmp_path, filepath, server_pid, server_log = hosts_setup(h1, h2)

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(h2, tmp_path, file_to_upload=filepath)

    was_client_successful, was_server_successful, start_time = operation_to_test(
        server_log, client_log, "File transfer complete", "Upload completed"
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

#!/usr/bin/env python3

import os
import shutil
import subprocess
import pytest
from time import sleep

from src.lib.common.mutable_variable import MutableVariable
from mininet_topo.linear_ends_topo import LinearEndsTopo
from mininet.link import TCLink
from mininet.net import Mininet

from tests.common import (
    emergency_directory_teardown,
    setup_directories,
    TESTS_DIR,
    generate_random_text_file,
    get_random_port,
    start_server,
    start_upload_client,
    check_results,
    kill_process,
    print_outputs,
    teardown_directories,
    compute_sha256,
    create_empty_file_with_name,
    start_download_client,
)

PACKET_LOSS_PERCENTAGE = 10

P_LOSS = MutableVariable(0)


@pytest.fixture(scope="session", params=[0, 10, 40])
def mininet_net_setup(request):
    packet_loss_percentage = request.param
    P_LOSS.value = packet_loss_percentage

    topo = LinearEndsTopo(
        client_number=1, packet_loss_percentage=packet_loss_percentage
    )
    net = Mininet(topo=topo, link=TCLink)
    print(
        f"[Fixture] Starting Mininet network with p_loss={packet_loss_percentage}%..."
    )

    net.start()

    yield net
    print("[Fixture] Stopping Mininet network...")
    net.stop()
    subprocess.run(["sudo", "mn", "-c"], check=False)
    emergency_directory_teardown()


def test_01_upload_is_correct(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")

    p_loss = P_LOSS.value

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_path}/test_file.txt"
    generate_random_text_file(filepath)

    port = get_random_port()

    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_path, port)

    sleep(1)  # wait for server start

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(
        h2, tmp_path, port, file_to_upload=filepath
    )

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = ["Upload completed"]
    server_message_expected = ["Upload completed from client"]
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=server_log,
        server_message_expected=server_message_expected,
        client_message_expected=client_message_expected,
        p_loss=p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)
    kill_process(h2, client_pid)

    print_outputs(server_log, client_log)

    teardown_directories(tmp_path)

    assert was_client_successful.value
    assert was_server_successful.value

    if os.path.exists(client_log) and os.path.exists(server_log):
        hash_client = compute_sha256(client_log)
        hash_server = compute_sha256(server_log)

        print(f"Client file hash: {hash_client}")
        print(f"Server file hash: {hash_server}")

        assert hash_client == hash_server, (
            "SHA256 mismatch: uploaded file is not identical to the original"
        )


def test_02_upload_fails_when_is_already_present_in_server(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")
    p_loss = P_LOSS.value

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_path}/test_file.txt"
    generate_random_text_file(filepath)

    port = get_random_port()
    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_path, port)

    sleep(1)  # wait for server start

    create_empty_file_with_name(f"{tmp_path}/server/test_file.txt")

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(
        h2, tmp_path, port, file_to_upload=filepath
    )

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = [
        "File in server already exists",
        "connection lost",
        "Connection was lost",
    ]
    server_message_expected = ["already existing in the server"]
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=server_log,
        server_message_expected=server_message_expected,
        client_message_expected=client_message_expected,
        p_loss=p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)
    kill_process(h2, client_pid)

    print_outputs(server_log, client_log)

    teardown_directories(tmp_path)

    assert was_client_successful.value
    assert was_server_successful.value


def test_03_upload_fails_when_file_to_upload_does_not_exist(mininet_net_setup):
    h2 = mininet_net_setup.get("h2")
    print(mininet_net_setup.topo)
    p_loss = P_LOSS.value

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_path}/test_file.txt"

    port = get_random_port()
    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(
        h2, tmp_path, port, file_to_upload=filepath
    )

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = ["Could not find or open file"]
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=None,
        server_message_expected="",
        client_message_expected=client_message_expected,
        p_loss=p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h2, client_pid)

    teardown_directories(tmp_path)

    assert was_client_successful.value


def test_04_download_is_correct(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")
    p_loss = P_LOSS.value

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_path}/server/test_file.txt"
    generate_random_text_file(filepath)

    port = get_random_port()
    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_path, port)

    sleep(1)  # wait for server start

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_download_client(
        h2, tmp_path, port, file_to_download="test_file.txt"
    )

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = ["Download completed"]
    server_message_expected = ["Download completed to client"]
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=server_log,
        server_message_expected=server_message_expected,
        client_message_expected=client_message_expected,
        p_loss=p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)
    kill_process(h2, client_pid)

    print_outputs(server_log, client_log)

    teardown_directories(tmp_path)

    assert was_client_successful.value
    assert was_server_successful.value

    if os.path.exists(client_log) and os.path.exists(server_log):
        hash_client = compute_sha256(f"{tmp_path}/client/test_file.txt")
        hash_server = compute_sha256(filepath)

        print(f"Client file hash: {hash_client}")
        print(f"Server file hash: {hash_server}")

        assert hash_client == hash_server, (
            "SHA256 mismatch: downloaded file is not identical to the original"
        )


def test_05_download_fails_when_is_not_present_in_server(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")
    p_loss = P_LOSS.value

    tmp_path, timestamp = setup_directories(TESTS_DIR)

    port = get_random_port()
    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_path, port)

    sleep(1)  # wait for server start

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_download_client(
        h2, tmp_path, port, file_to_download="test_file.txt"
    )
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = [
        "File in server does not exist",
        "connection lost",
        "Connection was lost",
    ]
    server_message_expected = ["not existing in server for download"]

    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=server_log,
        server_message_expected=server_message_expected,
        client_message_expected=client_message_expected,
        p_loss=p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)
    kill_process(h2, client_pid)

    print_outputs(server_log, client_log)

    teardown_directories(tmp_path)

    assert was_client_successful.value
    assert was_server_successful.value


def test_06_download_fails_when_file_already_exists_in_client(mininet_net_setup):
    h2 = mininet_net_setup.get("h2")
    p_loss = P_LOSS.value

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    create_empty_file_with_name(f"{tmp_path}/client/test_file.txt")

    port = get_random_port()
    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_download_client(
        h2, tmp_path, port, file_to_download=f"{tmp_path}/client/test_file.txt"
    )

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = ["already exists"]
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=None,
        server_message_expected="",
        client_message_expected=client_message_expected,
        p_loss=p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h2, client_pid)

    teardown_directories(tmp_path)

    assert was_client_successful.value


def test_07_cannot_boot_server_with_invalid_storage(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    p_loss = P_LOSS.value

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    shutil.rmtree(f"{tmp_path}/server")

    port = get_random_port()
    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_path, port)

    sleep(1)  # wait for server start

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = None
    server_message_expected = ["Error opening storage directory"]
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=None,
        server_log=server_log,
        server_message_expected=server_message_expected,
        client_message_expected=client_message_expected,
        p_loss=p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)

    print_outputs(server_log, None)

    teardown_directories(tmp_path)

    assert was_server_successful.value

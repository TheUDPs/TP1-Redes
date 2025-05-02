import subprocess
from time import sleep

import pytest
from mininet.link import TCLink
from mininet.net import Mininet

from src.lib.common.mutable_variable import MutableVariable
from mininet_topo.linear_ends_topo import LinearEndsTopo
from tests.common import (
    TESTS_DIR,
    emergency_directory_teardown,
    setup_directories,
    get_random_port,
    start_server,
    start_download_client,
    check_results,
    kill_process,
    print_outputs,
    teardown_directories,
    start_upload_client,
    create_empty_file_with_name,
)

P_LOSS = MutableVariable(0)


@pytest.fixture(scope="module", params=[0, 10, 40])
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


def test_01_server_saw_rejects_download_gbn(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")
    p_loss = P_LOSS.value

    tmp_dirpath, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_dirpath}/server/test_file.txt"
    create_empty_file_with_name(filepath)

    port = get_random_port()
    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_dirpath, port, "saw")

    sleep(1)  # wait for server start

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_download_client(
        h2, tmp_dirpath, port, "gbn", file_to_download="test_file.txt"
    )
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = ["Protocol mismatch"]
    server_message_expected = ["due to protocol mismatch"]

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

    teardown_directories(tmp_dirpath)

    assert was_client_successful.value
    assert was_server_successful.value


def test_02_server_saw_rejects_upload_gbn(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")
    p_loss = P_LOSS.value

    tmp_dirpath, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_dirpath}/test_file.txt"
    create_empty_file_with_name(filepath)

    port = get_random_port()
    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_dirpath, port, "saw")

    sleep(1)  # wait for server start

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(
        h2, tmp_dirpath, port, "gbn", file_to_upload=filepath
    )
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = ["Protocol mismatch"]
    server_message_expected = ["due to protocol mismatch"]

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

    teardown_directories(tmp_dirpath)

    assert was_client_successful.value
    assert was_server_successful.value


def test_03_server_gbn_rejects_download_saw(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")
    p_loss = P_LOSS.value

    tmp_dirpath, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_dirpath}/server/test_file.txt"
    create_empty_file_with_name(filepath)

    port = get_random_port()
    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_dirpath, port, "gbn")

    sleep(1)  # wait for server start

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_download_client(
        h2, tmp_dirpath, port, "saw", file_to_download="test_file.txt"
    )
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = ["Protocol mismatch"]
    server_message_expected = ["due to protocol mismatch"]

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

    teardown_directories(tmp_dirpath)

    assert was_client_successful.value
    assert was_server_successful.value


def test_04_server_gbn_rejects_upload_saw(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")
    p_loss = P_LOSS.value

    tmp_dirpath, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_dirpath}/test_file.txt"
    create_empty_file_with_name(filepath)

    port = get_random_port()
    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_dirpath, port, "gbn")

    sleep(1)  # wait for server start

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(
        h2, tmp_dirpath, port, "saw", file_to_upload=filepath
    )
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = ["Protocol mismatch"]
    server_message_expected = ["due to protocol mismatch"]

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

    teardown_directories(tmp_dirpath)

    assert was_client_successful.value
    assert was_server_successful.value

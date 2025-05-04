import os
import subprocess
from time import sleep

import pytest
from mininet.link import TCLink
from mininet.net import Mininet

from src.lib.common.mutable_variable import MutableVariable
from mininet_topo.linear_ends_topo import LinearEndsTopo
from tests.common import (
    TESTS_DIR,
    check_results,
    compute_sha256,
    emergency_directory_teardown,
    setup_directories,
    get_random_port,
    start_server,
    start_download_client,
    kill_process,
    teardown_directories,
    start_upload_client,
    generate_random_text_file,
)

P_LOSS = MutableVariable(0)
PROTOCOL = MutableVariable("saw")


@pytest.fixture(
    scope="module", params=["saw;0", "saw;10", "saw;40", "gbn;0", "gbn;10", "gbn;40"]
)  # Pending to add: "gbn;0", "gbn;10", "gbn;40"
def mininet_net_setup(request):
    protocol = request.param.split(";")[0]
    packet_loss_percentage = int(request.param.split(";")[1])

    P_LOSS.value = packet_loss_percentage
    PROTOCOL.value = protocol

    topo = LinearEndsTopo(
        client_number=7, packet_loss_percentage=packet_loss_percentage
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


def start_all_upload_clients(upload_hosts, tmp_dirpath, port, protocol, file_to_upload):
    pids_and_logs = {}

    for host in upload_hosts:
        print(f"Starting client on {host.name}...")
        client_pid, client_log = start_upload_client(
            host, tmp_dirpath, port, protocol, file_to_upload=file_to_upload
        )

        pids_and_logs[host.name] = {"pid": client_log, "log": client_log}

    return pids_and_logs


def start_all_download_clients(
    download_hosts, tmp_dirpath, port, protocol, file_to_download
):
    pids_and_logs = {}

    for host in download_hosts:
        print(f"Starting client on {host.name}...")
        client_pid, client_log = start_download_client(
            host, tmp_dirpath, port, protocol, file_to_download=file_to_download
        )

        pids_and_logs[host.name] = {"pid": client_log, "log": client_log}

    return pids_and_logs


# @pytest.mark.skip()
def test_01_server_can_handle_correctly_3_downloads_and_3_uploads_simultaneously(
    mininet_net_setup,
):
    h1 = mininet_net_setup.get("h1")

    # Uploaders
    h2 = mininet_net_setup.get("h2")
    # h3 = mininet_net_setup.get("h3")
    # h4 = mininet_net_setup.get("h4")

    # Downloaders
    h5 = mininet_net_setup.get("h5")
    h6 = mininet_net_setup.get("h6")
    h7 = mininet_net_setup.get("h7")

    _p_loss = P_LOSS.value

    tmp_dirpath1, timestamp = setup_directories(TESTS_DIR)
    tmp_dirpath2, timestamp = setup_directories(TESTS_DIR)
    tmp_dirpath3, timestamp = setup_directories(TESTS_DIR)
    filepath_for_upload = f"{tmp_dirpath1}/test_file_upload1.txt"
    filepath_for_download = f"{tmp_dirpath1}/server/test_file_download.txt"
    generate_random_text_file(filepath_for_upload, 5)
    generate_random_text_file(filepath_for_download, 5)

    port = get_random_port()

    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_dirpath1, port, PROTOCOL.value)

    sleep(1)  # wait for server start

    dw_cltn_1_pid, dw_cltn_1_log = start_download_client(
        h5,
        tmp_dirpath1,
        port,
        PROTOCOL.value,
        file_to_download="test_file_download.txt",
    )

    dw_cltn_2_pid, dw_cltn_2_log = start_download_client(
        h6,
        tmp_dirpath2,
        port,
        PROTOCOL.value,
        file_to_download="test_file_download.txt",
    )

    dw_cltn_3_pid, dw_cltn_3_log = start_download_client(
        h7,
        tmp_dirpath3,
        port,
        PROTOCOL.value,
        file_to_download="test_file_download.txt",
    )

    up_cltn_1_pid, up_cltn_1_log = start_upload_client(
        h5, tmp_dirpath1, port, PROTOCOL.value, file_to_upload=filepath_for_upload
    )

    # pids_and_logs_uploaders = start_all_upload_clients(
    #     [h2],
    #     tmp_dirpath,
    #     port,
    #     PROTOCOL.value,
    #     file_to_upload=filepath_for_upload,
    # )
    # pids_and_logs_downloaders = start_all_download_clients(
    #     [h5],
    #     tmp_dirpath,
    #     port,
    #     PROTOCOL.value,
    #     file_to_download=filepath_for_download,
    # )

    were_client_uploaders_successful = [
        MutableVariable(False),
        #     # MutableVariable(False),
        #     # MutableVariable(False),
    ]
    were_client_downloaders_successful = [
        MutableVariable(False),
        MutableVariable(False),
        MutableVariable(False),
    ]
    was_server_successful = MutableVariable(False)

    _client_uploader_message_expected = ["Upload completed"]
    _client_downloader_message_expected = ["Download completed"]

    _server_message_expected = [
        "Upload completed from client",
        "Download completed to client",
    ]

    check_results(
        was_client_successful=were_client_uploaders_successful[0],
        was_server_successful=was_server_successful,
        client_log=up_cltn_1_log,
        server_log=server_log,
        server_message_expected=_server_message_expected,
        client_message_expected=_client_uploader_message_expected,
        p_loss=_p_loss,
    )

    check_results(
        was_client_successful=were_client_downloaders_successful[0],
        was_server_successful=was_server_successful,
        client_log=dw_cltn_1_log,
        server_log=server_log,
        server_message_expected=_server_message_expected,
        client_message_expected=_client_downloader_message_expected,
        p_loss=_p_loss,
    )

    check_results(
        was_client_successful=were_client_downloaders_successful[1],
        was_server_successful=was_server_successful,
        client_log=dw_cltn_2_log,
        server_log=server_log,
        server_message_expected=_server_message_expected,
        client_message_expected=_client_downloader_message_expected,
        p_loss=_p_loss,
    )

    check_results(
        was_client_successful=were_client_downloaders_successful[2],
        was_server_successful=was_server_successful,
        client_log=dw_cltn_2_log,
        server_log=server_log,
        server_message_expected=_server_message_expected,
        client_message_expected=_client_downloader_message_expected,
        p_loss=_p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)

    kill_process(h2, up_cltn_1_pid)
    # kill_process(h3, pids_and_logs_uploaders["h3"]["pid"])
    # kill_process(h4, pids_and_logs_uploaders["h4"]["pid"])

    kill_process(h5, dw_cltn_1_pid)
    kill_process(h6, dw_cltn_2_pid)
    kill_process(h7, dw_cltn_3_pid)
    # kill_process(h6, pids_and_logs_downloaders["h6"]["pid"])
    # kill_process(h7, pids_and_logs_downloaders["h7"]["pid"])

    # print_outputs(server_log, pids_and_logs_uploaders["h2"]["log"])
    # print_outputs(server_log, pids_and_logs_uploaders["h3"]["log"])
    # print_outputs(server_log, pids_and_logs_uploaders["h4"]["log"])

    # print_outputs(server_log, pids_and_logs_downloaders["h5"]["log"])
    # print_outputs(server_log, pids_and_logs_downloaders["h6"]["log"])
    # print_outputs(server_log, pids_and_logs_downloaders["h7"]["log"])

    assert os.path.exists(
        f"{tmp_dirpath1}/client/test_file_download.txt"
    ) and os.path.exists(filepath_for_download)

    assert os.path.exists(filepath_for_upload) and os.path.exists(
        f"{tmp_dirpath1}/server/test_file_upload1.txt"
    )

    hash_client_1 = compute_sha256(f"{tmp_dirpath1}/client/test_file_download.txt")
    hash_client_1_up = compute_sha256(f"{tmp_dirpath1}/test_file_upload1.txt")
    hash_client_2 = compute_sha256(f"{tmp_dirpath2}/client/test_file_download.txt")
    hash_client_3 = compute_sha256(f"{tmp_dirpath3}/client/test_file_download.txt")
    hash_server = compute_sha256(filepath_for_download)
    hash_server_up = compute_sha256(f"{tmp_dirpath1}/server/test_file_upload1.txt")

    assert hash_client_1 == hash_server, (
        "SHA256 mismatch: downloaded file is not identical to the original"
    )
    assert hash_client_2 == hash_server, (
        "SHA256 mismatch: downloaded file is not identical to the original"
    )

    assert hash_client_3 == hash_server, (
        "SHA256 mismatch: downloaded file is not identical to the original"
    )

    assert hash_client_1_up == hash_server_up, (
        "SHA256 mismatch: uploaded file is not identical to the original"
    )

    teardown_directories(tmp_dirpath1)
    teardown_directories(tmp_dirpath2)
    teardown_directories(tmp_dirpath3)

    assert was_server_successful.value

    assert were_client_uploaders_successful[0].value
    # assert were_client_uploaders_successful[1].value
    # assert were_client_uploaders_successful[2].value

    assert were_client_downloaders_successful[0].value
    assert were_client_downloaders_successful[1].value
    assert were_client_downloaders_successful[2].value

    # if os.path.exists(client_log) and os.path.exists(server_log):
    #     hash_client = compute_sha256(client_log)
    #     hash_server = compute_sha256(server_log)

    #     print(f"Client file hash: {hash_client}")
    #     print(f"Server file hash: {hash_server}")

    #     assert hash_client == hash_server, (
    #         "SHA256 mismatch: uploaded file is not identical to the original"
    #     )

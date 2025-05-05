import subprocess
from time import sleep, time

import pytest
from mininet.link import TCLink
from mininet.net import Mininet

from src.lib.common.mutable_variable import MutableVariable
from mininet_topo.linear_ends_topo import LinearEndsTopo
from tests.common import (
    TESTS_DIR,
    compute_sha256,
    emergency_directory_teardown,
    setup_directories,
    get_random_port,
    start_server,
    kill_process,
    teardown_directories,
    start_upload_client,
    generate_random_text_file,
    start_download_client2,
    poll_results,
    ErrorDetected,
    print_outputs2,
)

P_LOSS = MutableVariable(0)
PROTOCOL = MutableVariable("saw")


@pytest.fixture(
    scope="module", params=["saw;0", "saw;10", "saw;40", "gbn;0", "gbn;10", "gbn;40"]
)
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


def are_all_successful(was_client_successful_array, was_server_successful):
    are_all_clients_successful = True
    for was_client_successful in was_client_successful_array:
        if not was_client_successful.value:
            are_all_clients_successful = False
            break

    return are_all_clients_successful and was_server_successful.value


def check_results_multiple_clients(
    was_client_successful_array,
    was_server_successful,
    client_logs_array,
    server_log,
    server_message_expected,
    client_message_expected,
    p_loss,
):
    if not (len(was_client_successful_array) == len(client_logs_array)):
        raise RuntimeError("All array lengths for client are not equal")

    TEST_TIMEOUT = 90
    TEST_POLLING_TIME = 1
    start_time = time()

    timeout_coefficient = p_loss / 13
    total_timeout = TEST_TIMEOUT + (TEST_TIMEOUT * timeout_coefficient)

    end_time = start_time + total_timeout
    print(f"Waiting up to {total_timeout} seconds for file transfer to complete...")

    while time() < end_time:
        sleep(TEST_POLLING_TIME)
        should_break = MutableVariable(False)

        for i in range(len(was_client_successful_array)):
            client_log = client_logs_array[i]
            was_client_successful = was_client_successful_array[i]

            print(f"Polling results at {time() - start_time:.1f}s...")
            try:
                (
                    _was_client_successful,
                    _was_server_successful,
                ) = poll_results(
                    server_log=server_log,
                    client_log=client_log,
                    server_message_expected=server_message_expected,
                    client_message_expected=client_message_expected,
                )
            except ErrorDetected:
                print("Failure: error detected.")
                should_break.value = True

            was_client_successful.value = _was_client_successful.value
            was_server_successful.value = _was_server_successful.value

            if are_all_successful(was_client_successful_array, was_server_successful):
                print("Success! All clients and the server reported completion.")
                should_break.value = True

        if should_break.value:
            break

    elapsed = time() - start_time
    print(f"Test finished after {elapsed:.1f}s")


# @pytest.mark.skip()
def test_01_server_can_handle_correctly_3_downloads_and_1_upload_simultaneously(
    mininet_net_setup,
):
    h1 = mininet_net_setup.get("h1")

    # Uploaders
    h2 = mininet_net_setup.get("h2")

    # Downloaders
    h5 = mininet_net_setup.get("h5")
    h6 = mininet_net_setup.get("h6")
    h7 = mininet_net_setup.get("h7")

    p_loss = P_LOSS.value

    FILE_SIZE_IN_MB = 5

    tmp_dirpath, timestamp = setup_directories(TESTS_DIR)
    filepath_to_download1 = "test_file_download1.txt"
    filepath_to_download2 = "test_file_download2.txt"
    filepath_to_download3 = "test_file_download3.txt"

    filepath_for_upload = f"{tmp_dirpath}/client/test_file_upload.txt"

    file_in_server = f"{tmp_dirpath}/server/test_file.txt"

    generate_random_text_file(filepath_for_upload, size_mb=FILE_SIZE_IN_MB)
    generate_random_text_file(file_in_server, size_mb=FILE_SIZE_IN_MB)

    port = get_random_port()

    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_dirpath, port, PROTOCOL.value)

    sleep(1)  # wait for server start

    download_client_1_pid, download_client_1_log = start_download_client2(
        h5,
        tmp_dirpath,
        port,
        PROTOCOL.value,
        file_to_download="test_file.txt",
        saved_as=filepath_to_download1,
    )

    sleep(0.5)  # wait for client start

    download_client_2_pid, download_client_2_log = start_download_client2(
        h6,
        tmp_dirpath,
        port,
        PROTOCOL.value,
        file_to_download="test_file.txt",
        saved_as=filepath_to_download2,
    )

    sleep(0.5)  # wait for client start

    download_client_3_pid, download_client_3_log = start_download_client2(
        h7,
        tmp_dirpath,
        port,
        PROTOCOL.value,
        file_to_download="test_file.txt",
        saved_as=filepath_to_download3,
    )

    sleep(0.5)  # wait for client start

    upload_client_1_pid, upload_client_1_log = start_upload_client(
        h2, tmp_dirpath, port, PROTOCOL.value, file_to_upload=filepath_for_upload
    )

    sleep(0.5)  # wait for client start

    were_client_uploaders_successful_array = [MutableVariable(False)]
    were_client_downloaders_successful_array = [
        MutableVariable(False),
        MutableVariable(False),
        MutableVariable(False),
    ]
    was_server_successful = MutableVariable(False)

    client_uploader_message_expected_array = ["Upload completed"]
    client_downloader_message_expected_array = ["Download completed"]

    server_message_expected_array = [
        "Upload completed from client",
        "Download completed to client",
    ]

    check_results_multiple_clients(
        was_client_successful_array=were_client_uploaders_successful_array
        + were_client_downloaders_successful_array,
        was_server_successful=was_server_successful,
        client_logs_array=[
            download_client_1_log,
            download_client_2_log,
            download_client_3_log,
            upload_client_1_log,
        ],
        server_log=server_log,
        server_message_expected=server_message_expected_array,
        client_message_expected=client_uploader_message_expected_array
        + client_downloader_message_expected_array,
        p_loss=p_loss,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)

    kill_process(h2, upload_client_1_pid)

    kill_process(h5, download_client_1_pid)
    kill_process(h6, download_client_2_pid)
    kill_process(h7, download_client_3_pid)

    print_outputs2(
        server_log,
        [
            download_client_1_log,
            download_client_2_log,
            download_client_3_log,
            upload_client_1_log,
        ],
    )

    hash_server_for_download = compute_sha256(file_in_server)
    hash_client_1_download = compute_sha256(
        f"{tmp_dirpath}/client/{filepath_to_download1}"
    )
    hash_client_2_download = compute_sha256(
        f"{tmp_dirpath}/client/{filepath_to_download2}"
    )
    hash_client_3_download = compute_sha256(
        f"{tmp_dirpath}/client/{filepath_to_download3}"
    )

    hash_client_1_upload = compute_sha256(filepath_for_upload)
    hash_server_upload = compute_sha256(f"{tmp_dirpath}/server/test_file_upload.txt")

    assert hash_client_1_download == hash_server_for_download, (
        "SHA256 mismatch: downloaded file (client 1) is not identical to the original"
    )

    assert hash_client_2_download == hash_server_for_download, (
        "SHA256 mismatch: downloaded file (client 2) is not identical to the original"
    )

    assert hash_client_3_download == hash_server_for_download, (
        "SHA256 mismatch: downloaded file (client 3) is not identical to the original"
    )

    assert hash_client_1_upload == hash_server_upload, (
        "SHA256 mismatch: uploaded file (client 1) is not identical to the original"
    )

    assert was_server_successful.value

    assert were_client_downloaders_successful_array[0].value

    assert were_client_downloaders_successful_array[0].value
    assert were_client_downloaders_successful_array[1].value
    assert were_client_downloaders_successful_array[2].value

    teardown_directories(tmp_dirpath)

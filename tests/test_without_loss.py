#!/usr/bin/env python3

import os
import random
import shutil
import string
import pytest
import hashlib
from time import time_ns, time, sleep

from src.lib.common.mutable_variable import MutableVariable
from mininet_topo.linear_ends_topo import LinearEndsTopo
from mininet.link import TCLink
from mininet.net import Mininet


PACKET_LOSS_PERCENTAGE = 10

RANDOM_SEED = 100

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)


def compute_sha256(path):
    hasher = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error computing hash for {path}: {e}")
        return None


def kill_process(node, pid):
    node.cmd(f"kill -9 {pid}")


def setup_directories(tests_dir):
    timestamp = time_ns()

    tmp_path = os.path.join(tests_dir, f"tmp_{timestamp}")

    shutil.rmtree(tmp_path, ignore_errors=True)
    os.makedirs(tmp_path, exist_ok=True)
    os.chmod(tmp_path, 0o777)

    # Create client and server subdirectories
    client_path = os.path.join(tmp_path, "client")
    server_path = os.path.join(tmp_path, "server")

    os.makedirs(client_path, exist_ok=True)
    os.makedirs(server_path, exist_ok=True)

    os.chmod(client_path, 0o777)
    os.chmod(server_path, 0o777)

    return tmp_path, timestamp


def start_server(host, tmp_path):
    log_file = f"{tmp_path}/server_output.log"
    pid = host.cmd(
        f"{PROJECT_ROOT}/src/start-server.py -s {tmp_path}/server/ -H 10.0.0.1 -r saw -q > {log_file} 2>&1 & echo $!"
    )
    return pid.strip(), log_file


def start_upload_client(host, tmp_path, file_to_upload):
    log_file = f"{tmp_path}/client_output.log"
    pid = host.cmd(
        f"{PROJECT_ROOT}/src/upload.py -H 10.0.0.1 -s {file_to_upload} -r saw -q > {log_file} 2>&1 & echo $!"
    )
    return pid.strip(), log_file


def teardown_directories(tmp_path):
    shutil.rmtree(tmp_path, ignore_errors=True)


def generate_random_text_file(filepath, size_mb=5):
    random.seed(RANDOM_SEED)
    size_bytes = size_mb * 1024 * 1024
    chars = string.ascii_letters + string.digits + "\n "

    with open(filepath, "w", encoding="utf-8") as f:
        written = 0
        chunk_size = 4096

        while written < size_bytes:
            to_write = "".join(random.choices(chars, k=chunk_size))
            f.write(to_write)
            written += chunk_size

    print(f"File created with size approximately {size_mb} MB")


# cmd = "start-server.py -s ./tmp/server/ -H 10.0.0.1 -r saw -v"
# cmd = "download.py -H 10.0.0.1 -d ./tmp/client/c.pdf -n c.pdf -r saw -v"
# cmd = "upload.py -H 10.0.0.1 -s ./tmp/client/c.pdf -r saw -v"


def print_outputs(server_log, client_log):
    print("\n=== SERVER OUTPUT ===")
    try:
        with open(server_log, "r") as f:
            print(f.read())
    except Exception as e:
        print(f"Error reading server log: {e}")

    print("\n=== CLIENT OUTPUT ===")
    try:
        with open(client_log, "r") as f:
            print(f.read())
    except Exception as e:
        print(f"Error reading client log: {e}")


def poll_results(
    server_log, client_log, server_message_expected, client_message_expected
):
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    try:
        # Check client log for client success message
        try:
            with open(client_log, "r", encoding="utf-8") as f:
                output = f.read()
                if client_message_expected in output:
                    was_client_successful.value = True
                    print(f"Found client success message: '{client_message_expected}'")
        except Exception as e:
            print(f"Error reading client log: {e}")

        # Check server log for server success message
        try:
            if server_log is None:
                return was_client_successful, was_server_successful

            with open(server_log, "r", encoding="utf-8") as f:
                output = f.read()
                if server_message_expected in output:
                    was_server_successful.value = True
                    print(f"Found server success message: '{server_message_expected}'")
        except Exception as e:
            print(f"Error reading server log: {e}")
    except Exception as e:
        print(f"Error in poll_results: {e}")

    return was_client_successful, was_server_successful


def emergency_directory_teardown():
    prefix = "tmp_"
    for name in os.listdir(TESTS_DIR):
        full_path = os.path.join(TESTS_DIR, name)
        if os.path.isdir(full_path) and name.startswith(prefix):
            shutil.rmtree(full_path)
            print(f"Deleted undeleted dir: {full_path}")


@pytest.fixture(scope="session")
def mininet_net_setup():
    topo = LinearEndsTopo(client_number=1)
    net = Mininet(topo=topo, link=TCLink)
    print("[Fixture] Starting Mininet network...")
    net.start()

    yield net
    print("[Fixture] Stopping Mininet network...")
    net.stop()
    emergency_directory_teardown()


def check_results(
    was_client_successful,
    was_server_successful,
    client_log,
    server_log,
    server_message_expected: str,
    client_message_expected: str,
):
    TEST_TIMEOUT = 30
    TEST_POLLING_TIME = 1

    print(f"Waiting up to {TEST_TIMEOUT} seconds for file transfer to complete...")

    start_time = time()
    end_time = start_time + TEST_TIMEOUT

    while time() < end_time:
        sleep(TEST_POLLING_TIME)
        print(f"Polling results at {time() - start_time:.1f}s...")

        _was_client_successful, _was_server_successful = poll_results(
            server_log=server_log,
            client_log=client_log,
            server_message_expected=server_message_expected,
            client_message_expected=client_message_expected,
        )
        was_client_successful.value = _was_client_successful.value
        was_server_successful.value = _was_server_successful.value

        if server_log is None:
            if was_client_successful.value:
                print("Success! Client reported completion.")
                break
        else:
            if was_client_successful.value and was_server_successful.value:
                print("Success! Both client and server reported completion.")
                break

    elapsed = time() - start_time
    print(f"Test finished after {elapsed:.1f}s")


def test_upload_is_correct_without_packet_loss(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_path}/test_file.txt"
    generate_random_text_file(filepath)

    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_path)

    sleep(2)  # wait for server start

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(h2, tmp_path, file_to_upload=filepath)

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = "File transfer complete"
    server_message_expected = "Upload completed"
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=server_log,
        server_message_expected=server_message_expected,
        client_message_expected=client_message_expected,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)
    kill_process(h2, client_pid)

    print_outputs(server_log, client_log)

    teardown_directories(tmp_path)

    assert was_client_successful.value, "Client did not report successful file transfer"
    assert was_server_successful.value, "Server did not report successful file upload"

    if os.path.exists(client_log) and os.path.exists(server_log):
        hash_client = compute_sha256(client_log)
        hash_server = compute_sha256(server_log)

        print(f"Client file hash: {hash_client}")
        print(f"Server file hash: {hash_server}")

        assert hash_client == hash_server, (
            "SHA256 mismatch: uploaded file is not identical to the original"
        )


def create_empty_file_with_name(filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("Just some empty text. It's important that is has the same name\n")


def test_upload_fails_when_its_not_present_in_server(mininet_net_setup):
    h1 = mininet_net_setup.get("h1")
    h2 = mininet_net_setup.get("h2")

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_path}/test_file.txt"
    generate_random_text_file(filepath)

    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_path)

    sleep(2)  # wait for server start

    create_empty_file_with_name(f"{tmp_path}/server/test_file.txt")

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(h2, tmp_path, file_to_upload=filepath)

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = "File in server already exists"
    server_message_expected = "already existing in the server"
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=server_log,
        server_message_expected=server_message_expected,
        client_message_expected=client_message_expected,
    )

    print("Cleaning up processes...")
    kill_process(h1, server_pid)
    kill_process(h2, client_pid)

    print_outputs(server_log, client_log)

    teardown_directories(tmp_path)

    assert was_client_successful.value, "Expected failure but client completed transfer"
    assert was_server_successful.value, "Expected failure but server completed transfer"


def test_upload_fails_when_file_to_upload_does_not_exist(mininet_net_setup):
    h2 = mininet_net_setup.get("h2")

    tmp_path, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_path}/test_file.txt"

    print(f"Starting client on {h2.name}...")
    client_pid, client_log = start_upload_client(h2, tmp_path, file_to_upload=filepath)

    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    client_message_expected = "Could not find or open file"
    check_results(
        was_client_successful=was_client_successful,
        was_server_successful=was_server_successful,
        client_log=client_log,
        server_log=None,
        server_message_expected="",
        client_message_expected=client_message_expected,
    )

    print("Cleaning up processes...")
    kill_process(h2, client_pid)

    teardown_directories(tmp_path)

    assert was_client_successful.value, "Expected failure but client completed transfer"

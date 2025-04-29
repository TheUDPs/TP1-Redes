#!/usr/bin/env python3

import os
import random
import shutil
import string
from time import time_ns, time, sleep

from src.lib.common.mutable_variable import MutableVariable
from mininet_topo.linear_ends_topo import LinearEndsTopo
from mininet.link import TCLink
from mininet.net import Mininet


PACKET_LOSS_PERCENTAGE = 10

RANDOM_SEED = 100

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)


def kill_process(node, pid):
    node.cmd(f"kill {pid}")


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
    with open(server_log, "r") as f:
        print(f.read())

    print("\n=== CLIENT OUTPUT ===")
    with open(client_log, "r") as f:
        print(f.read())


def poll_results(server_log, client_log, client_success_msg, server_success_msg):
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    try:
        # Check client log for client success message
        with open(client_log, "r", encoding="utf-8") as f:
            output = f.read()
            if client_success_msg in output:
                was_client_successful.value = True
                print(f"Found client success message: '{client_success_msg}'")

        # Check server log for server success message
        with open(server_log, "r", encoding="utf-8") as f:
            output = f.read()
            if server_success_msg in output:
                was_server_successful.value = True
                print(f"Found server success message: '{server_success_msg}'")
    except Exception as e:
        print(f"Error reading log files: {e}")

    return was_client_successful, was_server_successful


def net_setup():
    topo = LinearEndsTopo(client_number=1)
    net = Mininet(topo=topo, link=TCLink)

    net.start()

    h1 = net.get("h1")
    h2 = net.get("h2")

    return net, h1, h2


def hosts_setup(h1, h2):
    tmp_path, timestamp = setup_directories(TESTS_DIR)
    filepath = f"{tmp_path}/test_file.txt"
    generate_random_text_file(filepath)

    sleep(1)  # wait for server start

    print(f"Starting server on {h1.name}...")
    server_pid, server_log = start_server(h1, tmp_path)

    sleep(2)

    return tmp_path, filepath, server_pid, server_log


def operation_to_test(server_log, client_log, client_success_msg, server_success_msg):
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    TEST_TIMEOUT = 30
    TEST_POLLING_TIME = 2

    print(f"Waiting up to {TEST_TIMEOUT} seconds for file transfer to complete...")

    start_time = time()
    end_time = start_time + TEST_TIMEOUT

    while time() < end_time:
        sleep(TEST_POLLING_TIME)
        print(f"Polling results at {time() - start_time:.1f}s...")

        _was_client_successful, _was_server_successful = poll_results(
            server_log, client_log, "File transfer complete", "Upload completed"
        )
        was_client_successful.value = _was_client_successful.value
        was_server_successful.value = _was_server_successful.value

        if was_client_successful.value and was_server_successful.value:
            print("Success! Both client and server reported completion.")
            break

    return was_client_successful, was_server_successful, start_time


def shutdown(
    start_time, h1, h2, server_pid, client_pid, net, server_log, client_log, tmp_path
):
    elapsed = time() - start_time
    print(f"Test finished after {elapsed:.1f}s")

    print("Cleaning up processes...")
    kill_process(h1, server_pid)
    kill_process(h2, client_pid)
    net.stop()

    print_outputs(server_log, client_log)
    teardown_directories(tmp_path)

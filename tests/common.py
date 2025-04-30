import os
import random
import shutil
import string
import hashlib
from time import time_ns, time, sleep
from src.lib.common.mutable_variable import MutableVariable

RANDOM_SEED = 100

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

USED_PORTS = set()


class ErrorDetected(Exception):
    pass


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
    sleep(1)


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


def start_server(host, tmp_path, port):
    log_file = f"{tmp_path}/server_output.log"
    pid = host.cmd(
        f"{PROJECT_ROOT}/src/start-server.py -p {port} -s {tmp_path}/server/ -H 10.0.0.1 -r saw > {log_file} 2>&1 & echo $!"
    )
    return pid.strip(), log_file


def start_upload_client(host, tmp_path, port, file_to_upload):
    log_file = f"{tmp_path}/client_output.log"
    pid = host.cmd(
        f"{PROJECT_ROOT}/src/upload.py -H 10.0.0.1 -p {port} -s {file_to_upload} -r saw > {log_file} 2>&1 & echo $!"
    )
    return pid.strip(), log_file


def start_download_client(host, tmp_path, port, file_to_download):
    log_file = f"{tmp_path}/client_output.log"
    downloaded_filepath = f"{tmp_path}/client/{file_to_download}"
    pid = host.cmd(
        f"{PROJECT_ROOT}/src/download.py -H 10.0.0.1 -p {port} -d {downloaded_filepath} -n {file_to_download} -r saw -q > {log_file} 2>&1 & echo $!"
    )
    return pid.strip(), log_file


def teardown_directories(tmp_path):
    shutil.rmtree(tmp_path, ignore_errors=True)


def create_empty_file_with_name(filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("Just some empty text. It's important that is has the same name\n")


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


def print_outputs(server_log, client_log):
    print("\n=== SERVER OUTPUT ===")
    try:
        if server_log is not None:
            with open(server_log, "r") as f:
                print(f.read())
    except Exception as e:
        print(f"Error reading server log: {e}")

    print("\n=== CLIENT OUTPUT ===")
    try:
        if client_log is not None:
            with open(client_log, "r") as f:
                print(f.read())
    except Exception as e:
        print(f"Error reading client log: {e}")


def emergency_directory_teardown():
    prefix = "tmp_"
    for name in os.listdir(TESTS_DIR):
        full_path = os.path.join(TESTS_DIR, name)
        if os.path.isdir(full_path) and name.startswith(prefix):
            shutil.rmtree(full_path)
            print(f"Deleted undeleted dir: {full_path}")


def get_random_port():
    port = random.randint(1024, 65535)

    while port in USED_PORTS:
        port = random.randint(7000, 65000)

    USED_PORTS.add(port)
    return port


def poll_results(
    server_log, client_log, server_message_expected, client_message_expected
):
    was_client_successful = MutableVariable(False)
    was_server_successful = MutableVariable(False)

    error_prefix = "ERROR"

    try:
        try:
            if client_log is not None:
                with open(client_log, "r", encoding="utf-8") as f:
                    output = f.read()
                    for message in client_message_expected:
                        if message in output:
                            was_client_successful.value = True
                            print(f"Found client success message: '{message}'")
                            break

                    if error_prefix in output and not was_client_successful.value:
                        raise ErrorDetected()
        except Exception as e:
            print(f"Error reading client log: {e}")
            if e.__class__ == ErrorDetected:
                raise e

        try:
            if server_log is None:
                return was_client_successful, was_server_successful

            with open(server_log, "r", encoding="utf-8") as f:
                output = f.read()
                for message in server_message_expected:
                    if message in output:
                        was_server_successful.value = True
                        print(f"Found server success message: '{message}'")
                        break

                if error_prefix in output and not was_server_successful.value:
                    raise ErrorDetected()
        except Exception as e:
            print(f"Error reading server log: {e}")
            if e.__class__ == ErrorDetected:
                raise e
    except Exception as e:
        print(f"Error in poll_results: {e}")
        if e.__class__ == ErrorDetected:
            raise e

    return was_client_successful, was_server_successful


def check_results(
    was_client_successful,
    was_server_successful,
    client_log,
    server_log,
    server_message_expected,
    client_message_expected,
    p_loss,
):
    TEST_TIMEOUT = 30
    TEST_POLLING_TIME = 1
    start_time = time()

    # To increase the time allow to pass before timeout taking into account package loss
    timeout_coefficient = p_loss / 20
    # 0 -> 0
    # 10 -> 0.5
    # 40 -> 2
    total_timeout = TEST_TIMEOUT + (TEST_TIMEOUT * timeout_coefficient)

    end_time = start_time + total_timeout
    print(f"Waiting up to {total_timeout} seconds for file transfer to complete...")

    while time() < end_time:
        sleep(TEST_POLLING_TIME)
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
            break

        was_client_successful.value = _was_client_successful.value
        was_server_successful.value = _was_server_successful.value

        if server_log is None:
            if was_client_successful.value:
                print("Success! Client reported completion.")
                break
        elif client_log is None:
            if was_server_successful.value:
                print("Success! Client reported completion.")
                break
        else:
            if was_client_successful.value and was_server_successful.value:
                print("Success! Both client and server reported completion.")
                break

    elapsed = time() - start_time
    print(f"Test finished after {elapsed:.1f}s")

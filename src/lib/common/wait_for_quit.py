import multiprocessing
import sys
import threading

QUIT_CHARACTER = "q"


def wait_for_quit(should_stop: threading.Event, quited: multiprocessing.Value):
    while not should_stop.is_set():
        key = sys.stdin.read(1)
        if key == QUIT_CHARACTER:
            quited.value = True
            should_stop.set()

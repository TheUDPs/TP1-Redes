from enum import Enum


class ConnectionState(Enum):
    HANDHSAKE = 1
    HANDHSAKE_FINISHED = 2
    READY_TO_TRANSMIT = 3
    READY_TO_RECEIVE = 4
    DONE_READY_TO_DIE = 5
    UNRECOVERABLE_BAD_STATE = 99

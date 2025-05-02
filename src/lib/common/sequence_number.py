from lib.common.constants import STOP_AND_WAIT_PROTOCOL_TYPE

MAX_SEQUENCE_NUMBER = 1_000_000


class SequenceNumber:
    def __init__(self, first: int, protocol: str):
        self.value = first
        self.protocol = protocol

    def _step_saw(self):
        if self.value == 0:
            self.value = 1
        else:
            self.value = 0

    def _step_gbn(self):
        if self.value <= MAX_SEQUENCE_NUMBER:
            self.value = 1
        else:
            self.value += 1

    def step(self):
        if self.protocol == STOP_AND_WAIT_PROTOCOL_TYPE:
            self._step_saw()
        else:  # if self.protocol == GO_BACK_N_PROTOCOL_TYPE
            self._step_gbn()

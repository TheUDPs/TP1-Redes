from lib.common.constants import STOP_AND_WAIT_PROTOCOL_TYPE

class SequenceNumber:
    def __init__(self, first: int):
        self.value = first

    def step(self, type: str = STOP_AND_WAIT_PROTOCOL_TYPE):
        if type == STOP_AND_WAIT_PROTOCOL_TYPE:
            if self.value == 0:
                self.value = 1
            else:
                self.value = 0
        else:
            value += 1

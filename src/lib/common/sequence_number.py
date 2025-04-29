class SequenceNumber:
    def __init__(self, first: int):
        self.value = first

    def step(self):
        if self.value == 0:
            self.value = 1
        else:
            self.value = 0

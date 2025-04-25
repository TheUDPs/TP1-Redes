class MissingClientAddress(Exception):
    def __init__(self, message="Client address not found"):
        self.message = message

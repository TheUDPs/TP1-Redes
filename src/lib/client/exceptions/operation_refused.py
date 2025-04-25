class OperationRefused(Exception):
    def __init__(self, message="Operation refused from server"):
        self.message = message

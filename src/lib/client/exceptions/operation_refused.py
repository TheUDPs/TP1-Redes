class OperationRefused(Exception):
    def __init__(self, message="Operation refused from server"):
        self.message = message

    def __repr__(self):
        return f"OperationRefused: {self.message})"

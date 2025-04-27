class UnexpectedOperation(Exception):
    def __init__(self, message="Invalid operation"):
        self.message = message

    def __repr__(self):
        return f"UnpextecOperation: {self.message})"

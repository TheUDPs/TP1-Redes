class BadOperation(Exception):
    def __init__(self, message="Invalid operation"):
        self.message = message

    def __repr__(self):
        return f"BadOperation: {self.message})"

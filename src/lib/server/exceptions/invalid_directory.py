class InvalidDirectory(Exception):
    def __init__(self, message="Invalid directory"):
        self.message = message

    def __repr__(self):
        return f"InvalidDirectory: {self.message})"

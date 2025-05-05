class InvalidFilename(Exception):
    def __init__(self, message="Invalid filename"):
        self.message = message

    def __repr__(self):
        return f"InvalidFilename: {self.message})"

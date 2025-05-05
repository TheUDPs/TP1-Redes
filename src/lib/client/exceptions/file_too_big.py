class FileTooBig(Exception):
    def __init__(self, message="File in too big and cannot fit in the server"):
        self.message = message

    def __repr__(self):
        return f"FileTooBig: {self.message})"

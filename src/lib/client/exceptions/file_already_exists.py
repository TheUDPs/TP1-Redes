class FileAlreadyExists(Exception):
    def __init__(self, message="File in server already exists"):
        self.message = message

    def __repr__(self):
        return f"FileAlreadyExists: {self.message})"

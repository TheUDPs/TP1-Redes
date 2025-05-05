class FileDoesNotExist(Exception):
    def __init__(self, message="File in server does not exist"):
        self.message = message

    def __repr__(self):
        return f"FileDoesNotExist: {self.message})"

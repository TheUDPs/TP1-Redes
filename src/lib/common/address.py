class Address:
    def __init__(self, host: str, port: int):
        self.host: str = host
        self.port: int = port

    def to_tuple(self) -> tuple[str, int]:
        return self.host, self.port

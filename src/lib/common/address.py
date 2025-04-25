class Address:
    def __init__(self, host: str, port: int):
        self.host: str = host
        self.port: int = port

    def to_tuple(self) -> tuple[str, int]:
        return self.host, self.port

    # Concatenate host and port
    def to_combined(self) -> str:
        return f"{self.host}:{self.port}"

    def __repr__(self):
        return f"Address({self.host}:{self.port})"

from lib.common.address import Address


class ClientPool:
    def __init__(self):
        self.clients = {}

    # value: ClientConnection
    def add(self, key: tuple[str, int], value):
        self.clients[key] = value

    def remove(self, client_to_remove: Address):
        del self.clients[client_to_remove.to_combined()]

    def is_client_connected(self, client_address: Address) -> bool:
        return client_address.to_combined() in self.clients

    def values(self):
        return self.clients.values()

    def __repr__(self):
        string = "ClientPool("
        for key, value in self.clients.items():
            string += f"[{key},{value.state}]"
        string += ")"
        return string

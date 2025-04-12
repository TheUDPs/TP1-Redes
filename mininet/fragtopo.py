from mininet.topo import Topo


class FragTopo(Topo):
    def build(self, client_number=1):
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        s3 = self.addSwitch("s3")

        h1_server = self.addHost("h1")

        # links between switches
        self.addLink(s1, s2)
        self.addLink(s2, s3)

        # link server-s1
        self.addLink(
            h1_server,
            s1,
        )

        for i in range(client_number + 1):
            host_client_i = self.addHost(f"h{i + 1}")
            self.addLink(host_client_i, s3)


topos = {"fragtopo": (lambda client_number=1: FragTopo(client_number))}

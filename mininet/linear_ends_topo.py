#!/usr/bin/env python3
from mininet.topo import Topo
from mininet.net import Mininet

DEFAULT_PACKET_LOSS_PERCENTAGE = 0
DEFAULT_CLIENT_NUMBER = 1

# because it applies twice the loss percentage (once per side)
NORMALIZATION_FACTOR = 0.5


class LinearEndsTopo(Topo):
    def build(
        self,
        client_number=DEFAULT_CLIENT_NUMBER,
        packet_loss_percentage=DEFAULT_PACKET_LOSS_PERCENTAGE,
    ):
        # add switches
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        s3 = self.addSwitch("s3")

        h1_server = self.addHost("h1")

        # set links between switches
        self.addLink(s1, s2)
        self.addLink(s2, s3)

        normalized_loss = packet_loss_percentage * NORMALIZATION_FACTOR

        # set link server-s1
        self.addLink(h1_server, s1, loss=normalized_loss)

        # set links for each client and the s3
        # 1 is added because the server is taken into account
        for i in range(1, client_number + 1):
            host_client_i = self.addHost(f"h{i + 1}")
            self.addLink(host_client_i, s3)

    def export(self, filename="topology.dot"):
        net = Mininet(topo=self)
        with open(filename, "w") as f:
            f.write("graph mininet {\n")
            for host in net.hosts:
                f.write(f"    {host.name} [shape=box];\n")
            for switch in net.switches:
                f.write(f"    {switch.name} [shape=circle];\n")
            for link in net.links:
                intf1, intf2 = link.intf1, link.intf2
                node1, node2 = intf1.node, intf2.node
                f.write(f"    {node1.name} -- {node2.name};\n")
            f.write("}\n")


topos = {
    "linends": (
        lambda client_number=DEFAULT_CLIENT_NUMBER,
        packet_loss_percentage=DEFAULT_PACKET_LOSS_PERCENTAGE: LinearEndsTopo(
            client_number, packet_loss_percentage
        )
    )
}

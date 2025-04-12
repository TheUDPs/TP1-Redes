#!/usr/bin/env python3
from mininet.topo import Topo
from mininet.net import Mininet


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


topos = {"fragtopo": (lambda client_number=1: FragTopo(client_number))}

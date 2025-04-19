#!/usr/bin/env python3
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node

DEFAULT_PACKET_LOSS_PERCENTAGE = 0
DEFAULT_CLIENT_NUMBER = 1
DO_NOT_MODIFY_MTU = -1

# because it applies twice the loss percentage (once per side)
NORMALIZATION_FACTOR = 0.5


class Router(Node):
    def config(self, **params):
        super(Router, self).config(**params)

        self.cmd("sysctl -w net.ipv4.ip_forward=1")
        self.cmd(f"ifconfig {self.name}-eth0 10.0.0.254/24")

        for i in range(1, params.get("client_number", DEFAULT_CLIENT_NUMBER) + 1):
            self.cmd(f"ifconfig {self.name}-eth1 10.0.{i}.254/24")

        if params.get("mtu", DO_NOT_MODIFY_MTU) != DO_NOT_MODIFY_MTU:
            self.cmd(f"ifconfig {self.name}-eth0 mtu {params.get('mtu')}")

    def terminate(self):
        self.cmd("sysctl -w net.ipv4.ip_forward=0")
        super(Router, self).terminate()


class Host(Node):
    def config(self, **params):
        super(Host, self).config(**params)

        # Disable PMTU discovery on hosts to allow fragmentation
        self.cmd("sysctl -w net.ipv4.ip_no_pmtu_disc=1")
        self.cmd("ip route flush cache")

    def terminate(self):
        super(Host, self).terminate()


class LinearEndsTopo(Topo):
    def build(
        self,
        client_number=DEFAULT_CLIENT_NUMBER,
        packet_loss_percentage=DEFAULT_PACKET_LOSS_PERCENTAGE,
        mtu=DO_NOT_MODIFY_MTU,
    ):
        # add switches & router
        s1 = self.addSwitch("s1")
        r2 = self.addNode("r2", cls=Router, client_number=client_number, mtu=mtu)
        s3 = self.addSwitch("s3")

        # set links between switches & router
        self.addLink(s1, r2)
        self.addLink(r2, s3)

        h1_server = self.addHost(
            "h1", ip="10.0.0.1/24", defaultRoute="via 10.0.0.254", cls=Host
        )

        normalized_loss = packet_loss_percentage * NORMALIZATION_FACTOR

        # set link server-s1
        self.addLink(h1_server, s1, loss=normalized_loss)

        # set links for each client and the s3
        # 1 is added because the server is taken into account
        for i in range(1, client_number + 1):
            host_client_i = self.addHost(
                f"h{i + 1}",
                ip=f"10.0.{i}.1/24",
                defaultRoute=f"via 10.0.{i}.254",
                cls=Host,
            )
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
        packet_loss_percentage=DEFAULT_PACKET_LOSS_PERCENTAGE,
        mtu=DO_NOT_MODIFY_MTU: LinearEndsTopo(
            client_number, packet_loss_percentage, mtu
        )
    )
}

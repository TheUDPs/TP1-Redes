#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Node
from mininet.topo import Topo

DEFAULT_PACKET_LOSS_PERCENTAGE = 0
DEFAULT_CLIENT_NUMBER = 1
DO_NOT_MODIFY_MTU = -1

# because it applies twice the loss percentage (once per side)
NORMALIZATION_FACTOR = 0.5


class Router(Node):
    def config(self, **params):
        super(Router, self).config(**params)

        # to let the node act as router
        self.cmd("sysctl -w net.ipv4.ip_forward=1")

        # configure eth0 interface to handle server subnet (10.0.0.0/24)
        # will use 10.0.0.254 as its IP on this subnet
        self.cmd(f"ifconfig {self.name}-eth0 10.0.0.254/24")

        # configure eth1 interface to handle clients' subnet (10.0.1.0/24)
        # will use 10.0.1.254 as its IP on this subnet
        self.cmd(f"ifconfig {self.name}-eth1 10.0.1.254/24")

        # add explicit routes for the server subnet via eth0
        # so packets destined for 10.0.0.0/24 go through eth0
        self.cmd(f"ip route add 10.0.0.0/24 dev {self.name}-eth0")

        # add explicit routes for the clients' subnet via eth1
        # so packets destined for 10.0.1.0/24 go through eth1
        self.cmd(f"ip route add 10.0.1.0/24 dev {self.name}-eth1")

        # if MTU is set to change apply the change only to eth0 side
        mtu = params.get("mtu", DO_NOT_MODIFY_MTU)
        if mtu != DO_NOT_MODIFY_MTU and mtu > 0:
            # self.cmd(f"ifconfig {self.name}-eth0 mtu {mtu}")
            self.cmd(f"ip link set dev {self.name}-eth0 mtu {mtu}")

    def terminate(self):
        self.cmd("sysctl -w net.ipv4.ip_forward=0")
        super(Router, self).terminate()


class Host(Node):
    def config(self, **params):
        super(Host, self).config(**params)

        # disable PMTU (Path MTU) discovery on hosts to allow fragmentation
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
        # add link-layer switches & router
        s1 = self.addSwitch("s1")
        r1 = self.addNode("r1", cls=Router, client_number=client_number, mtu=mtu)
        s2 = self.addSwitch("s2")

        # set links between switches & router
        self.addLink(s1, r1)
        self.addLink(r1, s2)

        # availbale at IP 10.0.0.1/24
        # default route via 10.0.0.254 (router's eth0 interface)
        h1_server = self.addHost(
            "h1", ip="10.0.0.1/24", defaultRoute="via 10.0.0.254", cls=Host
        )

        normalized_loss = packet_loss_percentage * NORMALIZATION_FACTOR

        # set link server-s1
        self.addLink(h1_server, s1, loss=normalized_loss)

        # set links for each client and the s3
        # 1 is added because the server is taken into account
        # each client gets an IP in the 10.0.1.0/24 subnet being 10.0.1.X/24
        for i in range(1, client_number + 1):
            host_client_i = self.addHost(
                f"h{i + 1}",
                ip=f"10.0.1.{i}/24",
                defaultRoute="via 10.0.1.254",  # router's eth1 interface
                cls=Host,
            )
            self.addLink(host_client_i, s2)

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

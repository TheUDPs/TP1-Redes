#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Node
from mininet.topo import Topo

DEFAULT_PACKET_LOSS_PERCENTAGE = 0
DEFAULT_CLIENT_NUMBER = 1
DO_NOT_MODIFY_MTU = -1
ETH_NUMBER_NOT_SET = -1

# because it applies twice the loss percentage (once per side)
NORMALIZATION_FACTOR = 0.5


class Router(Node):
    def config(self, **params):
        super(Router, self).config(**params)

        # to let the node act as router
        self.cmd("sysctl -w net.ipv4.ip_forward=1")
        self.cmd("sysctl -w net.ipv4.ip_no_pmtu_disc=1")

        # configure eth0 interface for server subnet
        self.cmd(f"ip addr add 10.0.0.254/24 dev {self.name}-eth0")
        self.cmd(f"ip link set {self.name}-eth0 up")

        # configure eth1 interface for clients' subnet
        self.cmd(f"ip addr add 10.0.1.254/24 dev {self.name}-eth1")
        self.cmd(f"ip link set {self.name}-eth1 up")

        # add routes
        self.cmd(f"ip route add 10.0.0.0/24 dev {self.name}-eth0")
        self.cmd(f"ip route add 10.0.1.0/24 dev {self.name}-eth1")

        # if MTU is set to change apply the change only to eth0 side
        mtu = params.get("mtu", DO_NOT_MODIFY_MTU)
        eth_number = params.get("eth_number", ETH_NUMBER_NOT_SET)
        if mtu != DO_NOT_MODIFY_MTU and mtu > 0 and eth_number != ETH_NUMBER_NOT_SET:
            print(f"[MTU: {mtu}]")
            self.cmd(f"ip link set dev {self.name}-eth{eth_number} mtu {mtu}")

        # allow all ICMP messages
        self.cmd("iptables -A INPUT -p icmp -j ACCEPT")
        self.cmd("iptables -A OUTPUT -p icmp -j ACCEPT")
        self.cmd("iptables -A FORWARD -p icmp -j ACCEPT")
        self.cmd(
            "iptables -I OUTPUT -p icmp --icmp-type fragmentation-needed -j ACCEPT"
        )

    def terminate(self):
        self.cmd("sysctl -w net.ipv4.ip_forward=0")

        # bring interfaces down and remove IPs
        self.cmd(f"ip addr flush dev {self.name}-eth0")
        self.cmd(f"ip link set {self.name}-eth0 down")

        self.cmd(f"ip addr flush dev {self.name}-eth1")
        self.cmd(f"ip link set {self.name}-eth1 down")

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
        s2 = self.addNode(
            "s2",
            ip="10.0.0.254/24",
            cls=Router,
            client_number=client_number,
            mtu=mtu,
            eth_number=0,
        )
        s3 = self.addSwitch("s3")

        # set links between switches & router
        self.addLink(s1, s2)
        self.addLink(s2, s3)

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

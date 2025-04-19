#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from subprocess import call
import time
from linear_ends_topo import LinearEndsTopo

PACKET_LOSS_PERCENTAGE = 10
REDUCED_MTU = 800  # MTU to apply to a router interface
FRAG_MSS = REDUCED_MTU + 200  # MSS > Reduced MTU to cause fragmentation
CAPTURE_DIR = "/tmp/captures"
TEST_DURATION = 3
WAIT_TIME = 1


def run_tcpdump(node, interface, output_file):
    """Start tcpdump on a node and return process ID"""
    return node.cmd(f"tcpdump -i {interface} -nn -w {output_file} & echo $!")


def kill_process(node, pid):
    """Kill a process on a node using its PID"""
    node.cmd(f"kill {pid}")


def kill_processes(node, process_name):
    """Kill all processes with given name on a node"""
    node.cmd(f"killall {process_name}")


def run_automated_test(protocol, h1, h2, r2):
    """Run automated fragmentation test with specified protocol (TCP or UDP)"""
    protocol_lower = protocol.lower()
    info(f"\n*** Running automated {protocol} fragmentation test ***\n")

    info(f"Starting tcpdump captures for {protocol}...\n")
    pid1 = run_tcpdump(
        r2, "r2-eth0", f"{CAPTURE_DIR}/router_eth0_{protocol_lower}.pcap"
    )
    pid2 = run_tcpdump(
        r2, "r2-eth1", f"{CAPTURE_DIR}/router_eth1_{protocol_lower}.pcap"
    )
    time.sleep(WAIT_TIME)

    info(f"Starting iperf {protocol} server on h1...\n")
    server_args = "-s -u" if protocol == "UDP" else "-s"
    h1.cmd(f"iperf {server_args} > {CAPTURE_DIR}/iperf_{protocol_lower}_server.log &")
    time.sleep(WAIT_TIME)

    info(f"Running iperf {protocol} client on h2...\n")
    if protocol == "TCP":
        client_output = h2.cmd(
            f"iperf -c 10.0.0.1 -t {TEST_DURATION} -i 1 -M {FRAG_MSS}"
        )
    else:
        client_output = h2.cmd(
            f"iperf -c 10.0.0.1 -u -b 10m -l {FRAG_MSS} -t {TEST_DURATION} -i 1"
        )

    with open(f"{CAPTURE_DIR}/iperf_{protocol_lower}_client.log", "w") as f:
        f.write(client_output)

    info("Stopping tcpdump and iperf processes...\n")
    kill_process(r2, pid1)
    kill_process(r2, pid2)
    kill_processes(h1, "iperf")
    time.sleep(WAIT_TIME)

    info(f"{protocol} test completed. Captures saved in {CAPTURE_DIR}\n")


def fragmentation_test():
    """IPv4 fragmentation test using a central router"""

    topo = LinearEndsTopo(
        client_number=1, packet_loss_percentage=PACKET_LOSS_PERCENTAGE, mtu=REDUCED_MTU
    )
    net = Mininet(topo=topo)

    net.start()

    # References to hosts and router
    h1 = net.get("h1")  # Server
    h2 = net.get("h2")  # Client
    r2 = net.get("r2")  # Central router

    # Make sure the router is configured as such
    r2.config()

    # Prepare directory for captures
    call("rm -rf /tmp/captures", shell=True)
    call("mkdir -p /tmp/captures", shell=True)
    call("chmod 777 /tmp/captures", shell=True)

    # Run automated tests
    info("\n*** IPv4 FRAGMENTATION AUTOMATED TESTS ***\n")

    run_automated_test("TCP", h1, h2, r2)
    run_automated_test("UDP", h1, h2, r2)

    # Summary of results
    info("\n*** TEST SUMMARY ***\n")
    info(f"All captures and logs saved in {CAPTURE_DIR}\n")
    info("TCP test captures:\n")
    info(f"  - {CAPTURE_DIR}/router_eth0_tcp.pcap\n")
    info(f"  - {CAPTURE_DIR}/router_eth1_tcp.pcap\n")
    info(f"  - {CAPTURE_DIR}/iperf_tcp_server.log\n")
    info(f"  - {CAPTURE_DIR}/iperf_tcp_client.log\n\n")

    info("UDP test captures:\n")
    info(f"  - {CAPTURE_DIR}/router_eth0_udp.pcap\n")
    info(f"  - {CAPTURE_DIR}/router_eth1_udp.pcap\n")
    info(f"  - {CAPTURE_DIR}/iperf_udp_server.log\n")
    info(f"  - {CAPTURE_DIR}/iperf_udp_client.log\n\n")

    info("To analyze the captures, you can run on other terminal:\n")
    info("  wireshark /tmp/captures/router_eth0_tcp.pcap\n")
    info("  wireshark /tmp/captures/router_eth1_tcp.pcap\n")
    info("  wireshark /tmp/captures/router_eth0_udp.pcap\n")
    info("  wireshark /tmp/captures/router_eth1_udp.pcap\n")
    info("Apply filter: ip.flags.mf == 1 or ip.frag_offset > 0\n")
    info("This will show fragmented packets in the captures\n\n")

    info('Entering CLI mode. Type "exit", "quit", or "use Ctrl+D" to quit.\n')
    CLI(net)
    net.stop()


if __name__ == "__main__":
    # Clean previous Mininet state
    call("sudo mn -c", shell=True)
    setLogLevel("info")
    fragmentation_test()

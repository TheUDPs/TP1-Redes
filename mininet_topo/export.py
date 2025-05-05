#!/usr/bin/env python3

from linear_ends_topo import LinearEndsTopo

topo = LinearEndsTopo(client_number=3)
topo.export(filename="topology.dot")

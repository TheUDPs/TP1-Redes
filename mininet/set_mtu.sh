#!/bin/bash

MTU=$1
DEFAULT_MTU="500"

if [ -z "$1" ]; then
  MTU="$DEFAULT_MTU"
fi

echo "\n══ Target MTU: $MTU bytes ══"
echo "══ Current state of link ══\n"

#ifconfig r1-eth0 10.0.0.254/24
#ifconfig r1-eth1 10.0.1.254/24

ip link show r1-eth0
ip link set dev r1-eth0 mtu $MTU

echo "\n══ Updated state of link ══\n"

ip link show r1-eth0

echo "\n"

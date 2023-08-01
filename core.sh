#!/bin/bash
apt update
apt install docker-compose -y 
git clone --branch dev https://github.com/giovpantaleo/blueprint.git
sysctl net.ipv4.conf.all.forwarding=1                                                                                                                                         
iptables -P FORWARD ACCEPT
ip route add 192.168.70.164 via 192.168.3.2
ip route add 192.168.70.165 via 192.168.3.2
ip route add 192.168.70.166 via 192.168.3.2
ip route add 192.168.70.160 via 192.168.3.2
ip route add 192.168.72.160 via 192.168.3.2
ip route add 192.168.70.169 via 192.168.3.5
ip route add 192.168.70.2 via 192.168.3.5
ip route add 192.168.70.4 via 192.168.3.5

cd blueprint/mep
docker-compose -f docker-compose/docker-compose-core-network.yaml up -d
docker-compose -f docker-compose/docker-compose-cm.yaml up -d
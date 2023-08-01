#!/bin/bash
apt update
apt install docker-compose -y 
git clone --branch dev https://github.com/giovpantaleo/blueprint.git
sysctl net.ipv4.conf.all.forwarding=1                                                                                                                                         
iptables -P FORWARD ACCEPT
ip route add  192.168.70.168 via 192.168.3.1
ip route add  192.168.70.167 via 192.168.3.1
ip route add 192.168.70.133 via 192.168.3.1
ip route add 192.168.70.132 via 192.168.3.1
ip route add 192.168.70.138 via 192.168.3.1
ip route add 192.168.70.137 via 192.168.3.1
ip route add 192.168.70.136 via 192.168.3.1
ip route add 192.168.70.134 via 192.168.3.1
ip route add 192.168.72.134 via 192.168.3.1
ip route add 192.168.73.134 via 192.168.3.1
ip route add 192.168.70.130 via 192.168.3.1
ip route add 192.168.70.131 via 192.168.3.1
ip route add 192.168.73.135 via 192.168.3.1
ip route add 192.168.70.169 via 192.168.3.5
ip route add 192.168.70.2 via 192.168.3.5
ip route add 192.168.70.4 via 192.168.3.5

uhd_find_devices
cd blueprint/mep
docker-compose -f docker-compose/docker-compose-ran.yaml up -d oai-gnb oai-flexric rabbitmq
docker-compose -f docker-compose/docker-compose-ran.yaml up -d oai-rnis-xapp
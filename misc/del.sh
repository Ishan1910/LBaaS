#!/bin/bash

docker container rm -f P1 P1_backup c1
ip link delete br1
ip link delete P1br
ip link delete P1mgmtbr
rm -rf /etc/lbaas
rm /etc/avail_conf
ip link delete veth_lb0
ip link delete veth_lb12
ip link delete veth_lb11
ip link delete veth_lb9
ip link delete veth_lb6
ip link delete veth_lb5
ip link delete veth_lb3
ip link delete veth_lb14
ip link delete veth_lb13
ip link delete veth_vm1
unlink /var/run/netns/c1
unlink /var/run/netns/P1
unlink /var/run/netns/P1_backup


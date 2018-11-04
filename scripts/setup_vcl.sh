#!/bin/bash
iptables -t filter -I INPUT 1 -p udp --dport 4789 -j ACCEPT

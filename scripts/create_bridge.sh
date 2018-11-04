#!/bin/bash
if [[ $# -eq 0 ]] ; then
    echo "Usage: $0 bridge_name"
    exit 0
fi
brctl addbr $1
ip link set dev $1 up

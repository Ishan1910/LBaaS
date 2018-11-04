#!/bin/bash

#echo "Enter Local endpoint's IP address:"
#read local_ip
#echo "Enter Remote endpoint's IP address:"
#read remote_ip
#echo "Enter physical device for endpoint"
#read phys_dev
#echo "Enter port number to use for vxlan"
#read port_num
#echo "Enter vxlan id to use"
#read vnid
#echo "Enter bridge name to attach Vxlan device to"
#read bridge_name

while getopts "l:r:d:p:i:b:" OPT; do
    case "$OPT" in
        l)
            local_ip="$OPTARG"
            ;;
        r)
            remote_ip="$OPTARG"
            ;;
        d)
            phys_dev="$OPTARG"
            ;;
        p)
            port_num="$OPTARG"
            ;;
        i)
            vnid="$OPTARG"
            ;;
        b)
            bridge_name="$OPTARG"
            ;;
esac
done

usage() {
  echo "$0 -l <local_ip> -r <remote_ip> -d <phys_dev> -p <port_num> -i <vnid> -b <bridge_name>"
  exit 0
}

if [ -z "$local_ip" ];
then
  echo "Local IP not specified"
  usage
fi

if [ -z "$remote_ip" ];
then
  echo "Remote IP not specified"
  usage
fi

if [ -z "$phys_dev" ];
then
  echo "Physical Device not specified"
  usage
fi

if [ -z "$port_num" ];
then
  echo "Port number not specified"
  usage
fi

if [ -z "$vnid" ];
then
  echo "Vnid not specified"
  usage
fi

if [ -z "$bridge_name" ];
then
  echo "Bridge name not specified"
  usage
fi

vxlan_num=0
while :
do
  vxlan_name="vxlan${vxlan_num}"
  if ! `ip addr | grep -Eq "${vxlan_name}"`; then
    break
  fi
  vxlan_num=$(($vxlan_num + 1))
done



ip link add ${vxlan_name} type vxlan id ${vnid} dev ${phys_dev} remote ${remote_ip} local ${local_ip} dstport ${port_num}
ip link set dev ${vxlan_name} up
brctl addif ${bridge_name} ${vxlan_name}

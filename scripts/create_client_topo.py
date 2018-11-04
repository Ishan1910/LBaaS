#!/usr/bin/python

import subprocess 
import os
import json
import argparse

def make_pair(veth):
  p1 = "veth_vm" + str(veth)
  p2 = "veth_vm" + str(veth+1)
  cmd = "sudo ip link add " + p1 +" type veth peer name " + p2
  os.system(cmd)
  cmd = "sudo ip link set dev "+p1+" up"
  os.system(cmd)
  cmd="sudo ip link set dev "+p2+" up"
  os.system(cmd)
  return [p1,p2]


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("client_topo", help="File containing client container specs in json format")
  args=parser.parse_args()
  c_list ={}
  veth = 0
  with open(args.client_topo,"r") as fh:
    c_list=json.loads(fh.read())
  if not os.path.exists("/var/run/netns/"):
    cmd = "sudo mkdir -p /var/run/netns/"
    os.system(cmd)
  for key,value in c_list.iteritems():
    cname = value["cname"]
    br = value["bridge"]
    image = value["image"]
    ip = value["ip"]
    gip = value["gateway_ip"]
    cmd = "sudo docker container run -itd --privileged --name " + cname + " " + image
    os.system(cmd)
    pid = subprocess.check_output(["sudo docker inspect -f {{.State.Pid}} " + cname],shell=True)
    pid = pid.strip()
    cmd = "sudo ln -s /proc/"+pid+"/ns/net /var/run/netns/"+cname
    os.system(cmd)
    cmd = "sudo docker network disconnect bridge "+cname
    os.system(cmd)
    p1,p2 = make_pair(veth)
    veth+=2
    cmd = "sudo ip link set " + p1 + " netns " + cname
    os.system(cmd)
    cmd = "sudo ip netns exec "+cname+" ip addr add dev "+p1+" " +ip
    os.system(cmd)
    cmd = "sudo ip netns exec " + cname+" ip link set dev "+p1+ " up"
    os.system(cmd)
    cmd = "sudo ip netns exec "+cname+" ip route add default via "+gip
    os.system(cmd)
    cmd = "sudo brctl addif "+br+" " +p2
    os.system(cmd)
if __name__=="__main__":
  main()

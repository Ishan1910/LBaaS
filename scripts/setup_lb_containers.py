#!/usr/bin/python

import os
import json
import subprocess
import os.path
import argparse

# Make Veth pairs
def make_pair(veth):
  p1 = "veth_lb" + str(veth)
  p2 = "veth_lb" + str(veth+1)
  cmd =  "sudo ip link add " + p1 + " type veth peer name "+ p2
  os.system(cmd)
  cmd = "sudo ip link set dev "+ p1 + " up"
  os.system(cmd)
  cmd = "sudo ip link set dev "+ p2 + " up"
  os.system(cmd)
  return [p1,p2]

def create_net(name, sub, br):
  p = subprocess.Popen(["sudo docker network create -d macvlan --subnet="+sub+" -o parent="+br+" "+name], shell=True)
  p.wait()

def remove_default_network(cname):
  p = subprocess.Popen(["sudo docker network disconnect bridge "+cname], shell=True)
  p.wait()

def create_container(cname):
  cmd = "sudo docker run -itd --privileged --name "+cname+" lb_ubuntu" 
  os.system(cmd)

def add_address(cname, interface, address):
  p = subprocess.Popen(["sudo ip netns exec "+cname+" ip addr add "+address +" dev " + interface], shell=True)
  p.wait()

def hypervisor_add_address(interface, address):
  p = subprocess.Popen(["sudo ip addr add dev " + interface + " " + address], shell=True)
  p.wait()

def up_interface(cname, interface):
  p = subprocess.Popen(["sudo ip netns exec "+cname+" ip link set "+ interface +" up"], shell=True)
  p.wait()

def assign_interface(namespace, interface):
  cmd = "sudo ip link set " + interface + " netns " + namespace
  os.system(cmd)

def add_default_route(cname, default_gateway):
  p = subprocess.Popen(["sudo ip netns exec "+cname+" ip route add default via "+default_gateway], shell=True)
  p.wait()

def attach_bridge(bridge, interface):
  cmd = "sudo brctl addif " + bridge + " " + interface
  os.system(cmd)

def create_bridge(bridge):
  cmd = "sudo brctl addbr " + bridge
  os.system(cmd)
  cmd = "sudo ip link set " + bridge + " up"
  os.system(cmd)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("init_config", help="File containing initial lb config in json format")
  args= parser.parse_args()
  init_config = {}
  with open(args.init_config,"r") as fh:
    init_config = json.loads(fh.read())
 
  # initialize veth value. Change if  veth_lb0 exists
  veth = 0
 
  # initialize primary lb name
  primary_lb = init_config["lb_name"]
  print("Primary load balancer name given\n",primary_lb)
  secondary_lb = primary_lb + "_backup"
 
  # initialize listening address for load balancer
  avail_conf = {"listening_addr":"172.20.10.1/30","management_sub":"172.18.0.0/24"}
  if os.path.exists("/etc/avail_conf"):
    with open("/etc/avail_conf","r") as fh:
      avail_conf = json.loads(fh.read())
  listening_addr = avail_conf["listening_addr"].strip()
  management_sub = avail_conf["management_sub"]
  print("listening address given\n",listening_addr)
 
  # initialize server-side address for load balancer
  private_addr = init_config["gateway_ip"]
  print("Server-side address given\n",private_addr)
 
  addr = listening_addr.split("/")
  addr_arr = addr[0].split(".")
  router_ip = addr_arr[:3] + [str(int(addr_arr[-1]) + 1)]
  rip = ".".join(router_ip)
  man_sub = management_sub.split("/")
  man_sub_arr = man_sub[0].split(".")
  next_man_sub = man_sub_arr[0:2] + [str(int(man_sub_arr[2])+1),"0"] 
 
  # update /etc/avail_ip file for next available listening/management addr
  next_avail_listeningIP = ".".join(addr_arr[:3] + [str(int(addr_arr[-1])+4)])+"/30"
  next_avail_managementSub = ".".join(next_man_sub) + "/24"
  next_avail_conf = {"listening_addr":next_avail_listeningIP, "management_sub":next_avail_managementSub}
  with open("/etc/avail_conf","w+") as fh:
     fh.write(json.dumps(next_avail_conf))
 
  # initialize binding device
  bind_dev = init_config["bind_dev"]
  print("binding device given\n",bind_dev)
 
  # create mgmt bridge
  create_bridge(primary_lb+"mgmtbr")
  print("management bridge created\n")
 
  # create load balancers
  create_container(primary_lb)
  print("primary load balancer created\n")
  create_container(secondary_lb)
  print("secondary load balancer created\n")
  if not os.path.exists("/var/run/netns"):
    cmd = "sudo mkdir -p /var/run/netns/"
    os.system(cmd)

  # link both lb containers to use netns
  plb_pid = subprocess.check_output(["sudo docker inspect -f {{.State.Pid}} " + primary_lb],shell=True)
  plb_pid = plb_pid.strip()
  slb_pid = subprocess.check_output(["sudo docker inspect -f {{.State.Pid}} " + secondary_lb],shell=True)
  slb_pid = slb_pid.strip()
  print("PID for both load balancers extracted\n")
  cmd = "sudo ln -s /proc/"+plb_pid+"/ns/net /var/run/netns/"+primary_lb
  os.system(cmd)
  cmd = "sudo ln -s /proc/"+slb_pid+"/ns/net /var/run/netns/"+secondary_lb
  os.system(cmd)
  print("netns linked to container name\n")

  # Remove default network from containers
  remove_default_network(primary_lb)
  remove_default_network(secondary_lb)
  print("default network from both load balancers removed\n")

  # create balancer bridge
  create_bridge(primary_lb + "br")
  print("balancer bridge created\n")

  config ={}
  config["primary_lb"] = primary_lb
  config["secondary_lb"] = secondary_lb
  config["bridge"] = bind_dev
  config["private_ip"] = private_addr
  config["listening_ip"] = listening_addr
  config["gateway_ip"] = rip
  config["primary_lb_PID"]=plb_pid
  config["secondary_lb_PID"]=slb_pid

  # attach primary load balancer to bridge
  p1,p2 = make_pair(veth)
  assign_interface(primary_lb, p2)
  up_interface(primary_lb, p2)
  attach_bridge(bind_dev, p1)
  add_address(primary_lb, p2, private_addr)
  config["primary_out"] = p2
  config["bridge_iface"] = p1
  print("primary load balancer attached to bridge\n")

  # attach primary load balancer to balancer bridge
  veth+=2
  p1,p2 = make_pair(veth)
  assign_interface(primary_lb, p1)
  up_interface(primary_lb, p1)
  attach_bridge(primary_lb + "br", p2)
  add_address(primary_lb, p1, listening_addr)
  add_default_route(primary_lb, rip)
  config["primary_in"] = p1
  config["balancer_iface"] = p2
  print("primary load balancer attached to balancer bridge\n")

  # Management_interface
  veth+=2
  p1,p2 = make_pair(veth)
  assign_interface(primary_lb,p1)
  up_interface(primary_lb,p1)
  attach_bridge(primary_lb+"mgmtbr",p2)
  primary_mgmt_ip = ".".join(man_sub_arr[:3] + [str(int(man_sub_arr[3])+2)]) + "/24"
  add_address(primary_lb,p1, primary_mgmt_ip)
  config["primary_mgmt_ip"] = primary_mgmt_ip
  config["primary_mgmt_iface"]=p1
  print("primary lb management ip stored\n")

  # attach secondary load balancer to bridge
  veth+=2
  p1,p2 = make_pair(veth)
  assign_interface(secondary_lb, p2)
  attach_bridge(bind_dev, p1)
  config["secondary_out"] = p2
  config["secondary_bridge_iface"] = p1
  print("secondary load balancer attached to bridge\n")

  # attach secondary load balancer to balancer bridge
  veth+=2
  p1,p2 = make_pair(veth)
  assign_interface(secondary_lb, p1)
  attach_bridge(primary_lb + "br", p2)
  config["secondary_in"] = p1
  config["secondary_balancer_iface"] = p2
  print("secondary load balancer attached to balancer bridge\n")

  # Management_interface
  veth+=2
  p1,p2 = make_pair(veth)
  assign_interface(secondary_lb,p1)
  up_interface(secondary_lb,p1)
  attach_bridge(primary_lb+"mgmtbr",p2)
  secondary_mgmt_ip = ".".join(man_sub_arr[:3] + [str(int(man_sub_arr[3])+3)]) + "/24"
  add_address(secondary_lb,p1, secondary_mgmt_ip)
  config["secondary_mgmt_ip"] = secondary_mgmt_ip
  config["secondary_mgmt_iface"]=p1
  print("secondary lb management ip stored\n")
 
  # connect management bridge to controller 
  veth+=2
  p1,p2=make_pair(veth)
  assign_interface("controller",p1)
  up_interface("controller",p1)
  attach_bridge(primary_lb+"mgmtbr",p2)
  controller_ip=".".join(man_sub_arr[:3] + [str(int(man_sub_arr[3])+1)]) + "/24"
  add_address("controller",p1,controller_ip)
  config["controller_ip"] = controller_ip
  print("Management bridge attached to controller\n")
  
  # give hypervisor router interface IP to balancer bridge
  veth+=2
  p1,p2=make_pair(veth)
  attach_bridge(primary_lb+"br",p2)
  hypervisor_add_address(p1, rip + "/" + listening_addr.split("/")[1])
  print("hypervisor router interface IP connected to balancer bridge\n")

  conf_path = "/etc/lbaas"
  try:
    os.makedirs(conf_path)
  except OSError as exc:
    pass

  with open(conf_path + "/" + primary_lb + '.conf', 'w') as fp:
    json.dump(config, fp, indent=4)

if __name__== "__main__":
  main()

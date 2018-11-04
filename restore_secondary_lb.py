'''
usage: monitor_lb.py [-h] [-v] [--lb_config LB_CONFIG]
                     lb_name

positional arguments:
  lb_name               Name of load balancer to monitor

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbosity       increase output verbosity
  --lb_config LB_CONFIG
                        Configuration of load balancer. If not given looks up
                        in /etc/lbaas for the config file
'''

import subprocess
import argparse
import os
import time
import json


def add_address(namespace, interface, address):
  p = subprocess.Popen(["ip netns exec " + namespace + " ip addr add dev " + interface + " " + address], shell=True)
  p.wait()

def up_interface(namespace, interface):
  p = subprocess.Popen(["ip netns exec " + namespace + " ip link set dev " + interface + " up"], shell=True)
  p.wait()

def add_default_route(namespace, default_gateway):
  p = subprocess.Popen(["ip netns exec " +  namespace + " ip route add default via " + default_gateway], shell=True)
  p.wait()

def send_gratuitous_arp(namespace, ip, interface):
  p = subprocess.Popen(["ip netns exec " + namespace + " arping -U " + ip.split('/')[0] + " -c 2 -I " + interface], shell=True)
  p.wait()

def restore_secondary_lb(namespace, server_switch_if, server_switch_ip, balancer_switch_if, balancer_switch_ip,
    default_gateway, primary_lb, primary_ip, secondary_ip, secondary_lb, verbosity):
  if verbosity:
    print("Secondary LB: Setting up server switch interface iface:" + server_switch_if)
  up_interface(namespace, server_switch_if)

  if verbosity:
    print("Secondary LB: Setting up balancer switch interface iface:" + balancer_switch_if)
  up_interface(namespace, balancer_switch_if)

  if verbosity:
    print("Secondary LB: Adding address to the server switch interface iface: " + server_switch_ip)
  add_address(namespace, server_switch_if, server_switch_ip)

  if verbosity:
    print("Secondary LB: Adding address to the balancer switch interface iface: " + balancer_switch_ip)
  add_address(namespace, balancer_switch_if, balancer_switch_ip)

  if verbosity:
    print("Secondary LB: Adding default route via " + default_gateway)
  add_default_route(namespace, default_gateway)

  if verbosity:
    print("Secondary LB: Sending gratuitous ARP on " + server_switch_ip)
  send_gratuitous_arp(namespace, server_switch_ip, server_switch_if)

  if verbosity:
    print("Secondary LB: Sending gratuitous ARP on " + balancer_switch_ip)
  send_gratuitous_arp(namespace, balancer_switch_ip, balancer_switch_if)

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("-v", "--verbosity", action="store_true", help="increase output verbosity", default=False)
  parser.add_argument("lb_name", help="Name of load balancer to monitor")
  parser.add_argument("--lb_config", help="Configuration of load balancer. If not given looks up in /etc/lbaas for the config file")

  args = parser.parse_args()
  if not args.lb_config:
      args.lb_config= "/etc/lbaas/" + args.lb_name + ".conf"

  lb_conf = {}
  with open(args.lb_config,'r') as handle:
    lb_conf = json.loads(handle.read())

  server_switch_if = lb_conf["secondary_out"]
  server_switch_ip = lb_conf["private_ip"]
  balancer_switch_if = lb_conf["secondary_in"]
  balancer_switch_ip = lb_conf["listening_ip"]
  default_gateway = lb_conf["gateway_ip"]
  primary_lb = lb_conf["primary_lb"]
  primary_ip = lb_conf["primary_mgmt_ip"]
  secondary_ip = lb_conf["secondary_mgmt_ip"]
  secondary_lb = lb_conf["secondary_lb"]
  restore_secondary_lb(
      secondary_lb,
      server_switch_if,
      server_switch_ip,
      balancer_switch_if,
      balancer_switch_ip,
      default_gateway,
      primary_lb,
      primary_ip,
      secondary_ip,
      secondary_lb,
      args.verbosity)

if __name__ == "__main__":
    main()

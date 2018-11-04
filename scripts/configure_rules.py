#!/usr/bin/python

import socket
import argparse
import json
import os
import uuid
import copy

'''
{
 "rule_name": {"mode":"", "protocol":"tcp", "port":, "servers":[], "weights":[]},
 "rule_name2": {"mode":"", "protocol":"tcp", "port":"", "servers":[], "weights":[]},
}
'''

PROTOCOL = "protocol"
MODE = "mode"
SERVERS = "servers"
WEIGHTS = "weights"
PORT = "port"
MODE_RR = "rr"
MODE_WRR = "wrr"
PROTO_TCP = "tcp"
PROTO_UDP = "udp"
PROTO_ICMP = "icmp"

def install_iptables_rule(namespace, iface, protocol, servers=[], weights=[], mode="rr", port=None, verbosity=False):
  cmd = "sudo ip netns exec " + namespace + " iptables -t nat -A PREROUTING -p " + protocol
  if port is not None:
    cmd+= " --dport " + str(port)

  for i, server in enumerate(servers):
    if mode == MODE_RR:
      total_cmd = cmd + " -m statistic --mode nth --every " + str(len(servers)) + " --packet " + str(i)
    else:
      total_cmd = cmd + " -m statistic --mode random --probability " + str(weights[i])
    total_cmd += " -i " + iface + " -j DNAT --to-destination " + server
    if port is not None:
      total_cmd += ":" + str(port)
    if verbosity:
      print total_cmd
    os.system(total_cmd)


def delete_iptables_rule(namespace, iface, protocol, servers=[], weights=[], mode="rr", port=None, verbosity=False):
  cmd = "sudo ip netns exec " + namespace + " iptables -t nat -D PREROUTING -p " + protocol
  if port is not None:
    cmd+= " --dport " + str(port)

  for i, server in enumerate(servers):
    if mode == MODE_RR:
      total_cmd = cmd + " -m statistic --mode nth --every " + str(len(servers)) + " --packet " + str(i)
    else:
      total_cmd = cmd + " -m statistic --mode random --probability " + str(weights[i])
    total_cmd += " -i " + iface + " -j DNAT --to-destination " + server
    if port is not None:
      total_cmd += ":" + str(port)
    if verbosity:
      print total_cmd
    os.system(total_cmd)


def flush_iptables(namespace, verbosity):
  cmd = "sudo ip netns exec " + namespace + " iptables -t nat -F"
  os.system(cmd)
  if verbosity:
    print(cmd)

def validate_rule(rule):
  keys = [PROTOCOL, MODE, SERVERS]
  for key in keys:
    if key not in rule:
      print(key + " not present in rule")
      return False
  if rule[MODE] not in [MODE_RR, MODE_WRR]:
    print("Invalid mode")
    return False

  if rule[PROTOCOL] not in [PROTO_TCP, PROTO_UDP, PROTO_ICMP]:
    print("Invalid protocol")
    return False

  if rule[PROTOCOL] == PROTO_ICMP and PORT in rule:
    print("Port specified with icmp")
    return False

  if rule[MODE] == MODE_WRR:
    if WEIGHTS not in rule:
      print("weights not present in rule")
      return False
    if len(rule[SERVERS]) != len(rule[WEIGHTS]):
      print("Number of servers do not match the number of weights entered")
      return False
    if len(rule[SERVERS]) < 2:
      print("Only one server specified in rule")
      return False

  for server_addr in rule[SERVERS]:
    try:
      socket.inet_aton(server_addr)
    except socket.error:
      print("Invalid address specified in rule")
      return False

  if PORT in rule:
    if rule[PORT] > 65535 or rule[PORT] <= 0:
        print("Invalid port")
        return False

  return True


def match_rule(rule1, rule2):
  if rule1[PROTOCOL] != rule2[PROTOCOL]:
    return -1

  if rule1[MODE] != rule2[MODE]:
    return -1

  if (PORT in rule1) ^ (PORT in rule2):
    return -1

  if PORT in rule1:
    if rule1[PORT] != rule2[PORT]:
      return -1

  if set(rule1[SERVERS]) != set(rule2[SERVERS]):
    return 0

  if rule1[MODE] == MODE_WRR:
    for server in rule1[SERVERS]:
      if rule1[WEIGHTS][rule1[SERVERS].index(server)] != \
          rule2[WEIGHTS][rule2[SERVERS].index(server)]:
        return 0
  return 1



def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("-v", "--verbosity", action="store_true", help="increase output verbosity", default=False)
  parser.add_argument("lb_name", help="Name of load balancer on which rules need to be applied")
  parser.add_argument("rules_filename", help="File containing rules in json format")
  parser.add_argument("--lb_config", help="Configuration of load balancer. If not given looks up in /etc/lbaas for the config file")
  parser.add_argument("--rules_db", help="Database of applied rules on load balancer. If not given looks up in /etc/lbaas for the database file")
  args = parser.parse_args()
  if not args.lb_config:
      args.lb_config= "/etc/lbaas/" + args.lb_name + ".conf"

  if not args.rules_db:
      args.rules_db= "/etc/lbaas/" + args.lb_name + "_applied_rules.json"

  lb_conf = {}
  applied_rules = {}
  with open(args.lb_config,'r') as handle:
    lb_conf = json.loads(handle.read())

  with open(args.rules_filename,'r') as handle:
    rules_list = json.loads(handle.read())

  if os.path.isfile(args.rules_db):
    with open(args.rules_db,'r') as handle:
      applied_rules = json.loads(handle.read())

  primary_lb = args.lb_name
  secondary_lb = args.lb_name + "_backup"
  primary_in = lb_conf["primary_in"]
  secondary_in = lb_conf["secondary_in"]

  for key, value in rules_list.iteritems():
    if not validate_rule(value):
      print "Invalid rule:" + json.dumps(value)
      return

  delete_rules = copy.deepcopy(applied_rules)
  add_rules = {}
  for rulename1, rule1 in rules_list.iteritems():
    for rulename2, rule2 in applied_rules.iteritems():
      if match_rule(rule1, rule2) == 0:
        #delete_rules[rulename2] = rule2
        add_rules[rulename1] = rule1
        break
      elif match_rule(rule1, rule2) == 1:
        print rulename1, " matches ", rulename2
        del delete_rules[rulename2]
        break
    else:
      add_rules[rulename1] = rule1

  for key, value in delete_rules.iteritems():
    print "Deleting rule: " + key
    protocol = value[PROTOCOL]
    servers = value[SERVERS]
    mode = value[MODE]
    weights = []
    port = None
    if mode == MODE_WRR:
      weights = value[WEIGHTS]
    if PORT in value:
      port = value[PORT]
    delete_iptables_rule(primary_lb, primary_in, protocol, servers, weights, mode, port, args.verbosity)
    delete_iptables_rule(secondary_lb, secondary_in, protocol, servers, weights, mode, port, args.verbosity)
    del applied_rules[key]

  for key, value in add_rules.iteritems():
    print "Adding rule: " + key
    protocol = value[PROTOCOL]
    servers = value[SERVERS]
    mode = value[MODE]
    weights = []
    port = None
    if mode == MODE_WRR:
      weights = value[WEIGHTS]
    if PORT in value:
      port = value[PORT]
    install_iptables_rule(primary_lb, primary_in, protocol, servers, weights, mode, port, args.verbosity)
    install_iptables_rule(secondary_lb, secondary_in, protocol, servers, weights, mode, port, args.verbosity)
    applied_rules[key + "-" +  str(uuid.uuid4())] = value

  with open(args.rules_db, 'w') as fp:
    json.dump(applied_rules, fp, indent=4)

if __name__ == "__main__":
    main()

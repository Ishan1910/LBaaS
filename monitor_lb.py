'''
usage: monitor_lb.py [-h] [-v] [--lb_config LB_CONFIG]
                     [--ping_tries PING_TRIES] [--ping_timeout PING_TIMEOUT]
                     [--ping_interval PING_INTERVAL]
                     lb_name

positional arguments:
  lb_name               Name of load balancer to monitor

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbosity       increase output verbosity
  --lb_config LB_CONFIG
                        Configuration of load balancer. If not given looks up
                        in /etc/lbaas for the config file
  --ping_tries PING_TRIES
                        Number of pings that should fail before declaring the
                        bridge down
  --ping_timeout PING_TIMEOUT
                        Timeout for each ping in seconds
  --ping_interval PING_INTERVAL
                        Interval in seconds between successful pings

'''

import subprocess
import argparse
import os
import time
import json
import paramiko
import getpass

def monitor_active_lb(primary_ip, ping_tries, ping_timeout, ping_interval, verbose=False):
  DEVNULL = open(os.devnull, 'wb')
  ping_failed = 0
  while True:
    if verbose:
      print("Pinging " + primary_ip)
    p1 = subprocess.Popen(['ping', primary_ip, '-c 1', '-w '+ str(ping_timeout)], stdout=DEVNULL, stderr=subprocess.STDOUT)
    p1.wait()
    if p1.returncode != 0:
      if verbose:
        print("Ping failed")
      ping_failed += 1
    else:
      if verbose:
        print("Ping succeeded")
      time.sleep(ping_interval)
      ping_failed = 0

    if ping_failed >= ping_tries:
      return

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("-v", "--verbosity", action="store_true", help="increase output verbosity", default=False)
  parser.add_argument("lb_name", help="Name of load balancer to monitor")
  parser.add_argument("--lb_config", help="Configuration of load balancer. If not given looks up in /etc/lbaas for the config file")
  parser.add_argument("--ping_tries", help="Number of pings that should fail before declaring the bridge down", type=int, default=3)
  parser.add_argument("--ping_timeout", help="Timeout for each ping in seconds", type=int, default=2)
  parser.add_argument("--ping_interval", help="Interval in seconds between successful pings", type=int, default=1)
  args = parser.parse_args()
 
  if not args.lb_config:
      args.lb_config= "/lbaas/" + args.lb_name + ".conf"

  host_config = {}
  with open("host.json","r") as fh:
    host_config = json.loads(fh.read())
  uname = host_config["username"]
  hip = host_config["ip"]
  # print(args.init_config)
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  p = getpass.getpass("enter hypervisor password")
  client.connect(hip, username=uname, password=p)
  sftp = client.open_sftp()
  sftp.get('/etc/lbaas/' + args.lb_name + '.conf', args.lb_config)

  lb_conf = {}
  with open(args.lb_config,'r') as handle:
    lb_conf = json.loads(handle.read())

  primary_ip = lb_conf["primary_mgmt_ip"].split("/")[0]
  monitor_active_lb(primary_ip, args.ping_tries, args.ping_timeout, args.ping_interval, args.verbosity)

  sftp.put("/lbaas/restore_secondary_lb.py", "/home/"+uname+"/restore_secondary_lb.py")
  sftp.close()
  client.invoke_shell()
  i,o,e = client.exec_command("sudo python /home/"+uname+"/restore_secondary_lb.py " + args.lb_name)
  print(e.read())
  client.close()


if __name__ == "__main__":
    main()

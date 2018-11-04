#!bin/python

import os 
import json
import subprocess
import argparse
import paramiko
import getpass

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("init_config", help="File containing initial lb config in json format")
  args = parser.parse_args()
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
  sftp.put(args.init_config, '/home/'+uname+'/lbaas/init_config.json')
  sftp.close()
  client.invoke_shell()
  i,o,e = client.exec_command("sudo python /home/"+uname+"/lbaas/setup_lb_containers.py /home/"+uname+"/lbaas/init_config.json")
  print(e.read())
  client.close()
 
if __name__=="__main__":
  main()

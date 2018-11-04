1. Get access to two hypervisor machines
 Add input rule for iptables to enable ssh access:
 sudo iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT


On one of the machines/hypervisor:

Clone this repo.
Run setup_controller.sh
Attach to the controller container:
sudo docker attach controller

Clone this repo.
Update the inventory file with the credentials of hypervisor machine

Update the config files to create your own topology:
- topology.yml
- client_topo.json
- client_topo2.json
Run ansible playbook to setup the client topology:
ansible-playbook -i inventory create_topology.yml --ask-pass -v


Update the config files for initial configuration for load balancer:
 - init_config.json
Run ansible playbook to setup the load balancer topology:
ansible-playbook -i inventory setup_lb.py.yml --ask-pass -v

Update the config files to configure rules on the load balancer:
- rules.json
Run ansible playbook to setup the client topology:
ansible-playbook -i inventory configure_rules.yml --ask-pass -v


In case of adding a new pool or updating existing pool for the same load balancer with the same listening address, update the rules.json and run the ansible-playbook again 


Update host.json file with credentials
Start the load balancer monitoring for HA
Command: sudo python monitor_lb.py lb_name






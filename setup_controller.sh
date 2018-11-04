#!/bin/bash

apt-get install docker.io
docker build -t controller_ubuntu -f docker/cont_dockerfile .
docker container run -itd --privileged --name controller controller_ubuntu
mkdir -p /var/run/netns/
pid="$(sudo docker inspect -f '{{.State.Pid}}' controller)"
ln -s /proc/${pid}/ns/net /var/run/netns/controller
#cp host.json /home/${USER}/controller/
#cp init_config.json /home/${USER}/controller/
#cp rules.json /home/${USER}/controller/
#cp setup_lb.py /home/${USER}/controller/


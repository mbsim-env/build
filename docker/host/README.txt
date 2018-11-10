Install docker and docker-python
# yum install yum-utils device-mapper-persistent-data lvm2
# yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
# apt-get install docker-ce
# apt-get install epel-release
# apt-get install python2-pip
# pip install docker


Copy the service file mbsimenv.service to /lib/systemd/system/mbsimenv.service


Add dockeruser as new user and group
# groupadd -g 1065 dockeruser
# useradd --no-log-init -u 1065 -g dockeruser dockeruser


Append sudoers.append to /etc/sudoers to allow dockeruser to restart mbsimenv


Allow dockeruser to access docker
# chgrp dockeruser /run/docker.sock
# chmod ug+rw /run/docker.sock
# chmod u+s /run/docker.sock


Add public ssh-key to /home/dockeruser/.ssh/authorized_keys to allow key-based login
Change PasswordAuthentication to no in /etc/ssh/sshd_config to disallow password login


Adapt firewalld using firewall-cmd such that the interface has the
following zone (returned by firewall-cmd --info-zone=public):
public (active)
  target: default
  icmp-block-inversion: no
  interfaces: eth0
  sources: 
  services: ssh http https
  ports: 
  protocols: 
  masquerade: no
  forward-ports: 
  source-ports: 
  icmp-blocks: 
  rich rules: 

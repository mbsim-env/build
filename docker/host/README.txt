Install docker and docker-python and enable it
# yum install yum-utils device-mapper-persistent-data lvm2
# yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
# yum install docker-ce
# yum install epel-release
# yum install python36-docker
# systemctl start docker
# systemctl enable docker


Install git
# yum install git


Add dockeruser as new user and group
# groupadd -g 1065 dockeruser
# useradd --no-log-init -u 1065 -g dockeruser dockeruser


Allow dockeruser to access docker
# chgrp dockeruser /run/docker.sock


Add public ssh-key to
/home/dockeruser/.ssh/authorized_keys
/root/.ssh/authorized_keys
to allow key-based login


Change PasswordAuthentication to no in /etc/ssh/sshd_config to disallow password login and restart
# systemctl restart sshd


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
# systemctl start firewalld
# systemctl enable firewalld
# firewall-cmd --permanent --zone=public --add-service=http
# firewall-cmd --permanent --zone=public --add-service=https
# firewall-cmd --permanent --zone=public --remove-service=dhcpv6-client
# systemctl restart firewalld



Git clone build to /home/dockeruser
$ git clone https://github.com/mbsim-env/build.git


Append sudoers.append to /etc/sudoers to allow dockeruser to restart mbsimenv


Copy the service file mbsimenv.service to /lib/systemd/system/mbsimenv.service and start
$ systemctl start mbsimenv
$ systemctl enable mbsimenv

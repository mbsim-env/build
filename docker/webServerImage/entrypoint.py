#!/usr/bin/python

# imports
from __future__ import print_function # to enable the print function for backward compatiblity with python2
import subprocess
import sys
import os
import shutil
import fileinput
import time

# mfmf remove all checks in entrypoints if this is ensure by the corresponding docker-compose.yml

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")

# check volumes
if not os.path.isdir("/etc/letsencrypt"):
  raise RuntimeError("Need a volume /etc/letsencrypt mounted when running the container")
if not os.path.isdir("/var/www/html/mbsim/releases"):
  raise RuntimeError("Need a volume /var/www/html/mbsim/releases mounted when running the container")
if not os.path.isdir("/var/www/html/mbsim/linux64-ci"):
  raise RuntimeError("Need a volume /var/www/html/mbsim/linux64-ci mounted when running the container")
if not os.path.isdir("/var/www/html/mbsim/linux64-dailydebug"):
  raise RuntimeError("Need a volume /var/www/html/mbsim/linux64-dailydebug mounted when running the container")
if not os.path.isdir("/var/www/html/mbsim/linux64-dailyrelease"):
  raise RuntimeError("Need a volume /var/www/html/mbsim/linux64-dailyrelease mounted when running the container")
#if not os.path.isdir("/var/www/html/mbsim/win64-dailyrelease"):
#  raise RuntimeError("Need a volume /var/www/html/mbsim/win64-dailyrelease mounted when running the container")
if not os.path.isdir("/var/www/html/mbsim/buildsystemstate"):
  raise RuntimeError("Need a volume /var/www/html/mbsim/buildsystemstate mounted when running the container")

# run cron in background
subprocess.check_call(["crond"])

# run web server (uses the default certs)
# the configuration files uses the envvar MBSIMENVSERVERNAME
httpd=subprocess.Popen(["httpd", "-DFOREGROUND"])

# create cert if not existing or renew if already existing
#mfmfsubprocess.check_call(["/usr/bin/certbot-2",
#mfmf  "--agree-tos", "--email", "friedrich.at.gc@gmail.com", "certonly", "-n", "--webroot", "-w", "/var/www/html",
#mfmf  "--cert-name", "mbsim-env", "-d", os.environ["MBSIMENVSERVERNAME"]])
#mfmf
#mfmf# adapt web server config to use the letsencrypt certs
#mfmffor line in fileinput.FileInput("/etc/httpd/conf.d/ssl.conf", inplace=1):
#mfmf  if line.lstrip().startswith("SSLCertificateFile "):
#mfmf    line="SSLCertificateFile /etc/letsencrypt/live/mbsim-env/cert.pem"
#mfmf  if line.lstrip().startswith("SSLCertificateKeyFile "):
#mfmf    line="SSLCertificateKeyFile /etc/letsencrypt/live/mbsim-env/privkey.pem"
#mfmf  print(line, end="")
#mfmf# reload web server config
#mfmfsubprocess.check_call(["httpd", "-k", "graceful"])

# wait for the web server to finish (will never happen) and return its return code
print("Service up and running.")
sys.stdout.flush()
httpd.wait()
sys.exit(httpd.returncode)

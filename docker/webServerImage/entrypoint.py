#!/usr/bin/python

# imports
from __future__ import print_function # to enable the print function for backward compatiblity with python2
import subprocess
import sys
import os
import shutil
import fileinput
import time
import argparse

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/webserver.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

args=argparser.parse_args()

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")

# run cron in background
subprocess.check_call(["crond"])

# add daily build to crontab
#mfmfcrontab=subprocess.check_output(["crontab", "-l"])
#mfmfcrontab=crontab+"\n0 1 * * * /mbsim-build/build/docker/webServerImage/cron-daily.py -j %1\n"%(args.jobs)
#mfmfsubprocess.check_call(["crontab", "/dev/stdin"], )
#mfmfp=subprocess.Popen(['crontab', '/dev/stdin'], stdin=PIPE)    
#mfmfp.communicate(input=crontab)
#mfmfp.wait()

# run web server (uses the default certs)
# the configuration files uses the envvar MBSIMENVSERVERNAME
httpd=subprocess.Popen(["httpd", "-DFOREGROUND"])

# create cert if not existing or renew if already existing
subprocess.check_call(["/usr/bin/certbot-2",
  "--agree-tos", "--email", "friedrich.at.gc@gmail.com", "certonly", "-n", "--webroot", "-w", "/var/www/html",
  "--cert-name", "mbsim-env", "-d", os.environ["MBSIMENVSERVERNAME"]])

# adapt web server config to use the letsencrypt certs
for line in fileinput.FileInput("/etc/httpd/conf.d/ssl.conf", inplace=1):
  if line.lstrip().startswith("SSLCertificateFile "):
    line="SSLCertificateFile /etc/letsencrypt/live/mbsim-env/cert.pem\n"
  if line.lstrip().startswith("SSLCertificateKeyFile "):
    line="SSLCertificateKeyFile /etc/letsencrypt/live/mbsim-env/privkey.pem\n"
  print(line, end="")
# reload web server config
subprocess.check_call(["httpd", "-k", "graceful"])

# wait for the web server to finish (will never happen) and return its return code
print("Service up and running.")
sys.stdout.flush()
httpd.wait()
sys.exit(httpd.returncode)

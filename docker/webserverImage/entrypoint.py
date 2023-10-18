#!/usr/bin/env python3

# imports
import subprocess
import sys
import os
import fileinput
import time
import argparse
import psutil
import requests
sys.path.append("/context")
import setup

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/webserver.")
  
argparser.add_argument("--jobs", "-j", type=int, default=psutil.cpu_count(False), help="Number of jobs to run in parallel")
argparser.add_argument("--noSSL", action='store_true', help="Disable SSL support")
argparser.add_argument("--cronBuilds", action='store_true', help="Run daily and CI builds in docker containers by cron.")

args=argparser.parse_args()

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")
if "MBSIMENVTAGNAME" not in os.environ or os.environ["MBSIMENVTAGNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVTAGNAME is not defined.")

if args.cronBuilds:
  # add daily build to crontab (starting at 01:00)
  crontab=\
    "MBSIMENVSERVERNAME=%s\n"%(os.environ["MBSIMENVSERVERNAME"])+\
    "MBSIMENVTAGNAME=%s\n"%(os.environ["MBSIMENVTAGNAME"])+\
    subprocess.check_output(["crontab", "-l"]).decode("UTF-8")+\
    "0 %d * * * /context/cron-daily.py -j %d 2> >(sed -re 's/^/DAILY: /' > /proc/1/fd/2) > >(sed -re 's/^/DAILY: /' > /proc/1/fd/1)\n"%(23 if os.environ["MBSIMENVTAGNAME"]!="staging" else 11, args.jobs)+\
    "* * * * * /context/cron-ci.py -j %d 2> >(sed -re 's/^/CI: /' > /proc/1/fd/2) > >(sed -re 's/^/CI: /' > /proc/1/fd/1)\n"%(args.jobs)
  p=subprocess.Popen(['crontab', '/dev/stdin'], stdin=subprocess.PIPE)    
  p.communicate(input=crontab.encode("UTF-8"))
  p.wait()

# run cron in background
subprocess.check_call(["crond"])

# run web server (uses the default certs)
# the configuration files uses the envvar MBSIMENVSERVERNAME
def waitForWWW(timeout):
  for i in range(0,timeout*10):
    try:
      if requests.head("http://localhost").status_code==301:
        return
    except:
      pass
    time.sleep(0.1)
  raise RuntimeError("Server start has timed out.")
# start httpd
httpd=subprocess.Popen(["httpd", "-DFOREGROUND"])
waitForWWW(10)
print("Started webserver, not allowing connections.")
sys.stdout.flush()

if not args.noSSL:
  # create cert if not existing or renew if already existing
  subprocess.check_call(["sudo", "-u", "dockeruser", "/usr/bin/certbot-2", "--work-dir", "/tmp/certbotwork", "--logs-dir", "/tmp/certbotlog",
    "--agree-tos", "--email", "fm12@freenet.de", "certonly", "-n", "--webroot", "-w", "/var/www/html/certbot",
    "--cert-name", "mbsim-env", "-d", os.environ["MBSIMENVSERVERNAME"]])

  # adapt web server config to use the letsencrypt certs
  for line in fileinput.FileInput("/opt/rh/httpd24/root/etc/httpd/conf.d/ssl.conf", inplace=1):
    if line.lstrip().startswith("SSLCertificateFile "):
      line="SSLCertificateFile /etc/letsencrypt/live/mbsim-env/cert.pem\n"
    if line.lstrip().startswith("SSLCertificateKeyFile "):
      line="SSLCertificateKeyFile /etc/letsencrypt/live/mbsim-env/privkey.pem\n"+\
           "SSLCertificateChainFile /etc/letsencrypt/live/mbsim-env/chain.pem\n"
    print(line, end="")
else:
  # adapt web server config to disable https to http redirect
  for line in fileinput.FileInput("/opt/rh/httpd24/root/etc/httpd/conf.d/le-redirect-mbsim-env.conf", inplace=1):
    if line.lstrip().startswith("RewriteEngine "):
      line="RewriteEngine Off\n"
    print(line, end="")

# reload web server config
subprocess.check_call(["httpd", "-k", "graceful"])

# now allow all connections
replaceNext=False
for line in fileinput.FileInput("/opt/rh/httpd24/root/etc/httpd/conf/httpd.conf", inplace=1):
  if line.find("MBSIMENV_ALLOW")>=0:
    replaceNext=True
  elif replaceNext:
    print("  Require all granted")
    replaceNext=False
  else:
    print(line, end="")
# reload web server config
subprocess.check_call(["httpd", "-k", "graceful"])
print("Reloaded webserver, allowing now all connections.")
sys.stdout.flush()

# wait for the web server to finish (will never happen) and return its return code
print("Service up and running.")
sys.stdout.flush()
httpd.wait()
sys.exit(httpd.returncode)

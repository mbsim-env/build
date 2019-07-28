#!/usr/bin/python3

# imports
import subprocess
import sys
import os
import shutil
import fileinput
import time
import argparse
import json
import requests
import setup
import stat
import docker

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/webserver.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")
argparser.add_argument("--webhookSecret", type=str, default="", help="Define webhook secret (required if no mbsimBuildService.conf exists)")
argparser.add_argument("--clientID", type=str, default="", help="Define client ID (required if no mbsimBuildService.conf exists)")
argparser.add_argument("--clientSecret", type=str, default="", help="Define client secret (required if no mbsimBuildService.conf exists)")
argparser.add_argument("--statusAccessToken", type=str, default="", help="Define status access token (optional; no GitHub status update if not given)")

args=argparser.parse_args()

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")
if "MBSIMENVTAGNAME" not in os.environ or os.environ["MBSIMENVTAGNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVTAGNAME is not defined.")

# create build status page
with open('/proc/1/cpuset', "r") as fid:
  containerID=fid.read().rstrip().split("/")[-1]
dockerClient=docker.from_env()
container=dockerClient.containers.get(containerID)
image=container.image
imageID=image.id
gitCommitID=image.labels["gitCommitID"]
with open("/var/www/html/mbsim/buildsysteminfo.txt", "w") as f:
  print("This build system is running in:", file=f)
  print("containerID: "+containerID, file=f)
  print("imageID: "+imageID, file=f)
  print("gitCommitID: "+gitCommitID, file=f)

# check/create mbsim-config
def createConfig(webhookSecret, clientID, clientSecret, statusAccessToken):
  config={
    "checkedExamples": [], 
    "curcibranch": [
      {
        "fmatvec": "master", 
        "hdf5serie": "master", 
        "openmbv": "master", 
        "mbsim": "master"
      }
    ], 
    "tobuild": [], 
    "buildDocker": [], 
    "session": {}, 
    "webhook_secret": webhookSecret, 
    "client_id": clientID, 
    "client_secret": clientSecret, 
    "status_access_token": statusAccessToken
  }
  fd=open(configFilename, 'w')
  json.dump(config, fd, indent=2)
  fd.close()
  os.chown(configFilename, 1065, 48)
  os.chmod(configFilename, stat.S_IWUSR | stat.S_IWGRP | stat.S_IWGRP | stat.S_IRGRP)
  return config
configFilename="/mbsim-config/mbsimBuildService.conf"
if not os.path.isfile(configFilename):
  # no config file: either error or create it
  if args.webhookSecret=="" or args.clientID=="" or args.clientSecret=="":
    raise RuntimeError("No mbsimBuildService.conf file found! Need at least the arguments --webhookSecret, --clientID and --clientSecret.")
  config=createConfig(args.webhookSecret, args.clientID, args.clientSecret, args.statusAccessToken)
else:
  # config file available: read it
  fd=open(configFilename, 'r')
  config=json.load(fd)
  fd.close()
  # if secrets are provided but differ from config file update config file
  if (args.webhookSecret     !="" and config["webhook_secret"     ]!=args.webhookSecret    ) or \
     (args.clientID          !="" and config["client_id"          ]!=args.clientID         ) or \
     (args.clientSecret      !="" and config["client_secret"      ]!=args.clientSecret     ) or \
     (args.statusAccessToken !="" and config["status_access_token"]!=args.statusAccessToken):
    config=createConfig(args.webhookSecret     if args.webhookSecret    !="" else config["webhook_secret"     ],
                        args.clientID          if args.clientID         !="" else config["client_id"          ],
                        args.clientSecret      if args.clientSecret     !="" else config["client_secret"      ],
                        args.statusAccessToken if args.statusAccessToken!="" else config["status_access_token"])

# adapt static html content (MBSIMENVCLIENTID)
for filename in ["/var/www/html/mbsim/html/index.html", "/var/www/html/mbsim/html/mbsimBuildServiceClient.js"]:
  for line in fileinput.FileInput(filename, inplace=1):
    line=line.replace("@MBSIMENVCLIENTID@", config["client_id"])
    print(line, end="")

# add daily build to crontab (starting at 01:00)
crontab=\
  "MBSIMENVSERVERNAME=%s\n"%(os.environ["MBSIMENVSERVERNAME"])+\
  "MBSIMENVTAGNAME=%s\n"%(os.environ["MBSIMENVTAGNAME"])+\
  subprocess.check_output(["crontab", "-l"]).decode("UTF-8")+\
  "0 %d * * * /context/cron-daily.py -j %d 2> >(sed -re 's/^/DAILY: /' > /proc/1/fd/2) > >(sed -re 's/^/DAILY: /' > /proc/1/fd/1)\n"%(0 if os.environ["MBSIMENVTAGNAME"]!="staging" else 12, args.jobs)+\
  "* * * * * /context/cron-ci.py -j %d 2> >(sed -re 's/^/CI: /' > /proc/1/fd/2) > >(sed -re 's/^/CI: /' > /proc/1/fd/1)\n"%(args.jobs)
subprocess.check_call(["crontab", "/dev/stdin"], )
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

# create cert if not existing or renew if already existing
subprocess.check_call(["/usr/bin/certbot-2",
  "--agree-tos", "--email", "friedrich.at.gc@gmail.com", "certonly", "-n", "--webroot", "-w", "/var/www/html",
  "--cert-name", "mbsim-env", "-d", os.environ["MBSIMENVSERVERNAME"]])

# adapt web server config to use the letsencrypt certs
for line in fileinput.FileInput("/etc/httpd/conf.d/ssl.conf", inplace=1):
  if line.lstrip().startswith("SSLCertificateFile "):
    line="SSLCertificateFile /etc/letsencrypt/live/mbsim-env/cert.pem\n"
  if line.lstrip().startswith("SSLCertificateKeyFile "):
    line="SSLCertificateKeyFile /etc/letsencrypt/live/mbsim-env/privkey.pem\n"+\
         "SSLCertificateChainFile /etc/letsencrypt/live/mbsim-env/chain.pem\n"
  print(line, end="")
# reload web server config
subprocess.check_call(["httpd", "-k", "graceful"])

if os.environ["MBSIMENVTAGNAME"]=="staging":
  # for staging service run the CI at service startup
  print("Starting linux-ci build.")
  setup.run("build-linux64-ci", args.jobs, printLog=False, detach=True, addCommands=["--forceBuild"],
            fmatvecBranch="master", hdf5serieBranch="master",
            openmbvBranch="master", mbsimBranch="master",
            statusAccessToken=args.statusAccessToken)

# wait for the web server to finish (will never happen) and return its return code
print("Service up and running.")
sys.stdout.flush()
httpd.wait()
sys.exit(httpd.returncode)

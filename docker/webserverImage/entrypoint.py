#!/usr/bin/python3

# imports
import subprocess
import sys
import os
import fileinput
import time
import django
import django.core.management
import allauth
import argparse
import requests
import docker
sys.path.append("/context")
import setup
sys.path.append("/context/mbsimenv")
import mbsimenvSecrets
import service

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/webserver.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

args=argparser.parse_args()

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")
if "MBSIMENVTAGNAME" not in os.environ or os.environ["MBSIMENVTAGNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVTAGNAME is not defined.")

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings"
django.setup()

# wait for database server
while True:
  try:
    django.db.connections['default'].cursor()
    break
  except django.db.utils.OperationalError:
    print("Waiting for database to startup. Retry in 0.5s")
    time.sleep(0.5)

# database migrations
django.core.management.call_command("migrate", interactive=False, traceback=True, no_color=True)

# create superuser (may fail if already exists)
try:
  django.core.management.call_command("createsuperuser", interactive=False, username="admin", email="dummy@dummy.org")
except django.core.management.base.CommandError:
  pass
# set superuser password
user=django.contrib.auth.models.User.objects.get(username='admin')
user.set_password(mbsimenvSecrets.getSecrets()["djangoAdminPassword"])
user.save()

# set site-name
site=django.contrib.sites.models.Site.objects.get(id=1)
site.domain=os.environ["MBSIMENVSERVERNAME"]
site.name=os.environ["MBSIMENVSERVERNAME"]
site.save()

# create github app
sa, _=allauth.socialaccount.models.SocialApp.objects.get_or_create(provider="github")
sa.name="MBSim-Environment Build Service"
sa.client_id=mbsimenvSecrets.getSecrets()["githubAppClientID"]
sa.secret=mbsimenvSecrets.getSecrets()["githubAppSecret"]
sa.save()
sa.sites.add(django.contrib.sites.models.Site.objects.get(id=1))
sa.save()

# create master, master, master, master in cibranches
if service.models.CIBranches.objects.filter(fmatvecBranch="master", hdf5serieBranch="master",
                                            openmbvBranch="master", mbsimBranch="master").count()==0:
  ci=service.models.CIBranches()
  ci.fmatvecBranch="master"
  ci.hdf5serieBranch="master"
  ci.openmbvBranch="master"
  ci.mbsimBranch="master"
  ci.save()

# service Info
with open('/proc/1/cpuset', "r") as fid:
  containerID=fid.read().rstrip().split("/")[-1]
dockerClient=docker.from_env()
image=dockerClient.containers.get(containerID).image
gitCommitID=image.labels["gitCommitID"]
info, _=service.models.Info.objects.get_or_create(id=gitCommitID)
info.shortInfo="Container ID: %s\nImage ID: %s\ngit Commit ID: %s"%(containerID, image.id, gitCommitID)
info.save()
service.models.Info.objects.exclude(id=gitCommitID).delete() # remove everything except the current runnig Info object

# add daily build to crontab (starting at 01:00)
crontab=\
  "MBSIMENVSERVERNAME=%s\n"%(os.environ["MBSIMENVSERVERNAME"])+\
  "MBSIMENVTAGNAME=%s\n"%(os.environ["MBSIMENVTAGNAME"])+\
  subprocess.check_output(["crontab", "-l"]).decode("UTF-8")+\
  "0 %d * * * /context/cron-daily.py -j %d 2> >(sed -re 's/^/DAILY: /' > /proc/1/fd/2) > >(sed -re 's/^/DAILY: /' > /proc/1/fd/1)\n"%(23 if os.environ["MBSIMENVTAGNAME"]!="staging" else 11, args.jobs)+\
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
  "--agree-tos", "--email", "friedrich.at.gc@gmail.com", "certonly", "-n", "--webroot", "-w", "/var/www/html/certbot",
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
  # for staging service run the CI at service startup (just for testing a build)
  print("Starting linux-ci build.")
  setup.run("build-linux64-ci", args.jobs, printLog=False, detach=True, addCommands=["--forceBuild"],
            fmatvecBranch="master", hdf5serieBranch="master",
            openmbvBranch="master", mbsimBranch="master")

# wait for the web server to finish (will never happen) and return its return code
print("Service up and running.")
sys.stdout.flush()
httpd.wait()
sys.exit(httpd.returncode)

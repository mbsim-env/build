#!/usr/bin/env python3

import sys
import subprocess
import os
import time
import shutil
import django
import django.core.management
import allauth
sys.path.append("/context/mbsimenv")
import mbsimenvSecrets
import service

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")

# start db server
if os.path.exists("/database/postmaster.pid"): os.remove("/database/postmaster.pid")
shutil.copyfile("/database.org/postgresql.conf", "/database/postgresql.conf") # use postgresql.conf from Dockerfile
shutil.copyfile("/database.org/pg_hba.conf", "/database/pg_hba.conf") # use pg_hba.conf from Dockerfile
pg=subprocess.Popen(["/usr/pgsql-13/bin/postgres", "-D", "/database", "-h", "*"])
print("DB server started, allow only internal hostnames to connect.")
sys.stdout.flush()

# wait for server (try with dummy and real password)
env=os.environ.copy()
while True:
  if pg.poll() is not None:
    print("database failed to start.")
    sys.exit(pg.returncode)
  env["PGPASSWORD"]="dummy"
  if subprocess.call(["/usr/pgsql-13/bin/psql", "-l", "-h", "localhost", "--username=mbsimenvuser"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)==0:
    break
  env["PGPASSWORD"]=mbsimenvSecrets.getSecrets("postgresPassword")
  if subprocess.call(["/usr/pgsql-13/bin/psql", "-l", "-h", "localhost", "--username=mbsimenvuser"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)==0:
    break
  print("Waiting for database to startup. Retry in 0.5s")
  sys.stdout.flush()
  time.sleep(0.5)

# change password if it is dummy
if env["PGPASSWORD"]=="dummy":
  if subprocess.call(["/usr/pgsql-13/bin/psql", "-h", "localhost", "--username=mbsimenvuser", "mbsimenv-service-database",
                      "-c", "ALTER USER mbsimenvuser WITH PASSWORD '%s';"% \
                      (mbsimenvSecrets.getSecrets("postgresPassword"))], env=env)!=0:
    sys.exit(1)
  env["PGPASSWORD"]=mbsimenvSecrets.getSecrets("postgresPassword")

# import data from an old postgres server:
# - dump data from old server in the old Docker container database (<pwd> is from /mbsim-config/secrets.json):
#   PGPASSWORD=<pwd> /usr/pgsql-13/bin/pg_dump --username=mbsimenvuser mbsimenv-service-database > /database/db.import
# - move db.import (on the host system)
#   mv /var/lib/docker/volumes/mbsimenv_database.staging/_data/db.import /var/lib/docker/volumes/mbsimenv_config.staging/_data/db.import 
# - stop old docker container database
# - remove the docker volume mbsimenv_database
# - start new docker container database -> this will import the data -> check the docker logs of the new container
# - REMOVE /var/lib/docker/volumes/mbsimenv_config.staging/_data/db.import and check everything!
if os.path.exists("/mbsim-config/db.import"):
  if subprocess.call(["/usr/pgsql-13/bin/psql", "-h", "localhost", "--username=mbsimenvuser", "-f", "/mbsim-config/db.import", \
                      "-d", "mbsimenv-service-database"], env=env)!=0:
    sys.exit(1)

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
django.setup()

# database migrations
django.core.management.call_command("migrate", interactive=False, traceback=True, no_color=True)

# create superuser (may fail if already exists)
try:
  django.core.management.call_command("createsuperuser", interactive=False, username="admin", email="dummy@dummy.org")
except django.core.management.base.CommandError:
  pass
# set superuser password
user=django.contrib.auth.models.User.objects.get(username='admin')
user.set_password(mbsimenvSecrets.getSecrets("djangoAdminPassword"))
user.save()

# set site-name
site=django.contrib.sites.models.Site.objects.get(id=1)
site.domain=os.environ["MBSIMENVSERVERNAME"]
site.name=os.environ["MBSIMENVSERVERNAME"]
site.save()

# create github app
sa, _=allauth.socialaccount.models.SocialApp.objects.get_or_create(provider="github")
sa.name="MBSim-Environment Build Service"
sa.client_id=mbsimenvSecrets.getSecrets("githubAppClientID")
sa.secret=mbsimenvSecrets.getSecrets("githubAppSecret")
sa.save()
sa.sites.add(django.contrib.sites.models.Site.objects.get(id=1))
sa.save()

# add master, master, master, master in CIBranches and DailyBranches, if the branch combi is empty
for model in ["CIBranches", "DailyBranches"]:
  if getattr(service.models, model).objects.count()==0:
    bc=getattr(service.models, model)()
    bc.fmatvecBranch="master"
    bc.hdf5serieBranch="master"
    bc.openmbvBranch="master"
    bc.mbsimBranch="master"
    bc.save()

# service Info
with open('/proc/1/cpuset', "r") as fid:
  containerID=fid.read().rstrip().split("/")[-1]
info, _=service.models.Info.objects.get_or_create(id=os.environ["GITCOMMITID"])
info.shortInfo="Container ID: %s\nImage ID: %s\ngit Commit ID: %s"%(containerID, os.environ["IMAGEID"], os.environ["GITCOMMITID"])
info.save()
service.models.Info.objects.exclude(id=os.environ["GITCOMMITID"]).delete() # remove everything except the current runnig Info object

# enable SSL
CERTDIR="/sslconfig/live/mbsim-env"
while not os.path.exists(CERTDIR+"/cert.pem") or not os.path.exists(CERTDIR+"/privkey.pem"):
  print("Waiting for ssl certificate.")
  time.sleep(0.5)
with open("/database/postgresql.conf", "a") as f:
  print("ssl = on", file=f)
  print("ssl_cert_file = '"+CERTDIR+"/cert.pem'", file=f)
  print("ssl_key_file = '"+CERTDIR+"/privkey.pem'", file=f)

# now allow connections from all interface (not only localhost)
with open("/database/pg_hba.conf", "a") as f:
  print("hostssl mbsimenv-service-database mbsimenvuser all md5", file=f)
subprocess.check_call(["/usr/pgsql-13/bin/pg_ctl", "-D", "/database", "reload"])
print("DB server reloaded, allow now all hostnames to connect.")
sys.stdout.flush()

# wait for server to finish
pg.wait()
sys.exit(pg.returncode)

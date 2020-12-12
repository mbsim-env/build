#!/usr/bin/python3

import sys
import subprocess
import os
import time
import fileinput
import mbsimenvSecrets

# start db server
time.sleep(5)#mfmf
if os.path.exists("/database/postmaster.pid"): os.remove("/database/postmaster.pid")
pg=subprocess.Popen(["/usr/pgsql-13/bin/postgres", "-D", "/database", "-h", "database,localhost"])

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
  env["PGPASSWORD"]=mbsimenvSecrets.getSecrets()["postgresPassword"]
  if subprocess.call(["/usr/pgsql-13/bin/psql", "-l", "-h", "localhost", "--username=mbsimenvuser"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)==0:
    break
  print("Waiting for database to startup. Retry in 0.5s")
  time.sleep(0.5)

# change password if it is dummy
if env["PGPASSWORD"]=="dummy":
  if subprocess.call(["/usr/pgsql-13/bin/psql", "-h", "localhost", "--username=mbsimenvuser", "mbsimenv-service-database",
                      "-c", "ALTER USER mbsimenvuser WITH PASSWORD '%s';"% \
                      (mbsimenvSecrets.getSecrets()["postgresPassword"])], env=env)!=0:
    sys.exit(1)
  env["PGPASSWORD"]=mbsimenvSecrets.getSecrets()["postgresPassword"]

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

# now allow connections from all interface (not only localhost)
for line in fileinput.input("/database/pg_hba.conf", inplace=True):
  if line.strip()=="host all all localhost md5":
    print("host all all 0.0.0.0/0 md5")
  else:
    print(line, end="")
subprocess.check_call(["/usr/pgsql-13/bin/pg_ctl", "-D", "/database", "reload"])

# wait for server to finish
pg.wait()
sys.exit(pg.returncode)

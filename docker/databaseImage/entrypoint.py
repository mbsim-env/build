#!/usr/bin/python3

import sys
import subprocess
import os
import time
import mbsimenvSecrets

# start db server
time.sleep(5)#mfmf
if os.path.exists("/database/postmaster.pid"): os.remove("/database/postmaster.pid")
pg=subprocess.Popen(["/usr/pgsql-9.6/bin/postgres", "-D", "/database", "-h", "database"])

# wait for server (try with dummy and real password)
env=os.environ.copy()
while True:
  if pg.poll() is not None:
    print("database failed to start.")
    sys.exit(pg.returncode)
  env["PGPASSWORD"]="dummy"
  if subprocess.call(["/usr/pgsql-9.6/bin/psql", "-l", "-h", "database", "--username=mbsimenvuser"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)==0:
    break
  env["PGPASSWORD"]=mbsimenvSecrets.getSecrets()["postgresPassword"]
  if subprocess.call(["/usr/pgsql-9.6/bin/psql", "-l", "-h", "database", "--username=mbsimenvuser"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)==0:
    break
  print("Waiting for database to startup. Retry in 0.5s")
  time.sleep(0.5)

# change password if it is dummy
if env["PGPASSWORD"]=="dummy":
  if subprocess.call(["/usr/pgsql-9.6/bin/psql", "-h", "database", "--username=mbsimenvuser", "mbsimenv-service-database",
                      "-c", "ALTER USER mbsimenvuser WITH PASSWORD '%s';"% \
                      (mbsimenvSecrets.getSecrets()["postgresPassword"])], env=env)!=0:
    sys.exit(1)

# wait for server to finish
pg.wait()
sys.exit(pg.returncode)

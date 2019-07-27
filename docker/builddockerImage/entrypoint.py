#!/usr/bin/python3

# imports
import sys
import os
import subprocess
import datetime
import setup
import argparse

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/build.")
  
argparser.add_argument("commitID", type=str, help="The commit ID to build")
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

args=argparser.parse_args()


print("Building build system from commit ID "+args.commitID)
sys.stdout.flush()

with open("/mbsim-report/builddocker.txt", "w") as f:
  
  print("Start building build system from commit ID "+args.commitID+" at "+\
        datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), file=f)
  f.flush()

  if not os.path.isdir("/mbsim-env/build"):
    subprocess.check_call(["git", "clone", "https://github.com/mbsim-env/build.git"], cwd="/mbsim-env", stdout=f, stderr=f)
  subprocess.check_call(["git", "fetch"], cwd="/mbsim-env/build", stdout=f, stderr=f)
  subprocess.check_call(["git", "checkout", args.commitID], cwd="/mbsim-env/build", stdout=f, stderr=f)
  for s in setup.allServices:
    ret=setup.build(s, args.jobs, fd=f, baseDir="/mbsim-env/build/docker")
    if ret!=0:
      sys.exit(ret)

  print("Finished building build system from commit ID "+args.commitID+" at "+\
        datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), file=f)

print("Restarting service now.")
sys.stdout.flush()
#mfmf subprocess.check_call(["systemctl", "status", "mbsimenvstaging"])

sys.exit(0)

#!/usr/bin/python3

# imports
import sys
import argparse
import io
import os
import subprocess
import setup
import traceback
import socket
import django
sys.path.append("/context/mbsimenv")
import service

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/build.")
  
argparser.add_argument("commitID", type=str, help="The commit ID to build")
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

args=argparser.parse_args()

print("Building build system from commit ID "+args.commitID)
sys.stdout.flush()

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
django.setup()

f=io.StringIO()
failed=False
try:
  print("Start building build system from commit ID "+args.commitID+" at "+\
        django.utils.timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"), file=f)
  
  if not os.path.isdir("/mbsim-env/build"):
    p=subprocess.run(["git", "clone", "https://github.com/mbsim-env/build.git"], cwd="/mbsim-env",
                     stderr=subprocess.STDOUT, stdout=subprocess.PIPE, encoding="UTF-8")
    f.write(p.stdout)
    p.check_returncode()
  p=subprocess.run(["git", "fetch"], cwd="/mbsim-env/build",
                   stderr=subprocess.STDOUT, stdout=subprocess.PIPE, encoding="UTF-8")
  f.write(p.stdout)
  p.check_returncode()
  p=subprocess.run(["git", "checkout", args.commitID], cwd="/mbsim-env/build",
                   stderr=subprocess.STDOUT, stdout=subprocess.PIPE, encoding="UTF-8")
  f.write(p.stdout)
  p.check_returncode()
  for s in setup.allServices:
    ret=setup.build(s, args.jobs, fd=f, baseDir="/mbsim-env/build/docker")
    if ret!=0:
      raise RuntimeError("Building the docker image failed.")
  
  print("Finished building build system from commit ID "+args.commitID+" at "+\
        django.utils.timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"), file=f)

except:
  print(traceback.format_exc(), file=f)
  failed=True
finally:
  print("Save build result output in database.")
  sys.stdout.flush()
  
  info, _=service.models.Info.objects.get_or_create(id=args.commitID)
  info.longInfo=f.getvalue()
  info.save()
  service.models.Info.objects.exclude(id=args.commitID).delete() # remove everything except the current runnig Info object

  django.db.connections.close_all() # close all connections before restarting

if not failed:
  print("Restart now.")
  print("Stopping service now.")
  sys.stdout.flush()
  if setup.run('service', 6, daemon="stop", keepBuildDockerContainerRunning=True)!=0:
    raise RuntimeError("Stopping service failed.")
  print("Restarting service now.")
  sys.stdout.flush()
  if setup.run('service', 6, daemon="start")!=0:
    raise RuntimeError("Starting service failed.")
  print("All done.")
  sys.stdout.flush()

import subprocess
import sys
import ctypes
import signal
import time
import os.path
import docker

webapprun=None

def terminate(a, b):
  if webapprun==None:
    return
  webapprun.stop()

signal.signal(signal.SIGUSR1, terminate)

libc=ctypes.CDLL("libc.so.6")
PR_SET_PDEATHSIG=1
if libc.prctl(PR_SET_PDEATHSIG, signal.SIGUSR1, 0, 0, 0)!=0:
  raise auth_plugins.AuthenticationError(log_msg="Cannot call prctl.")

dockerClient=docker.from_env()

# start vnc and other processes in a new container (being reachable as hostname)
networkID=sys.argv[1]
token=sys.argv[2]
hostname=sys.argv[3]
network=dockerClient.networks.get(networkID)
webapprun=dockerClient.containers.run(image="mbsimenv/webapprun",
  init=True,
  command=[token],
  volumes={
    'mbsimenv_mbsim-linux64-ci':           {"bind": "/mbsim-env-linux64-ci",           "mode": "ro"},
    'mbsimenv_mbsim-linux64-dailydebug':   {"bind": "/mbsim-env-linux64-dailydebug",   "mode": "ro"},
    'mbsimenv_mbsim-linux64-dailyrelease': {"bind": "/mbsim-env-linux64-dailyrelease", "mode": "ro"},
  },
  detach=True, stdout=True, stderr=True)
print("Started running webapprun with token "+token+" as container ID "+webapprun.id)
sys.stdout.flush()
network.connect(webapprun, aliases=[hostname])
webapprun.wait()
print("Finished running webapprun with token "+token+" as container ID "+webapprun.id)
sys.stdout.flush()

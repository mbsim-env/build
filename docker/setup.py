#!/usr/bin/python2

from __future__ import print_function # to enable the print function for backward compatiblity with python2
import argparse
import docker
import os
import json
import time
import threading
import sys
import signal



argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Manage and run the MBSim-Env docker images, containers, ...")

argparser.add_argument("command", type=str, choices=["build", "run"], help="Command to execute")
argparser.add_argument("service", nargs="*", help="Service or image to run or build")
argparser.add_argument("--servername", type=str, default=None, help="Set the hostname of webserver")
argparser.add_argument("--jobs", "-j", type=int, default=4, help="Number of jobs to run in parallel")
argparser.add_argument("--clientID", type=str, default=None, help="GitHub OAuth App client ID")
argparser.add_argument("--clientSecret", type=str, default=None, help="GitHub OAuth App client secret")
argparser.add_argument("--webhookSecret", type=str, default=None, help="GitHub web hook secret")
argparser.add_argument("--statusAccessToken", type=str, default=None, help="GitHub access token for status updates")
argparser.add_argument("--token", type=str, default=None, help="Webapprun token")

args=argparser.parse_args()



scriptdir=os.path.dirname(os.path.realpath(__file__))

dockerClient=docker.from_env()
dockerClientLL=docker.APIClient()



def syncLogBuildImage(build):
  ret=0
  for line in build:
    entry=json.loads(line)
    if "stream" in entry:
      print(entry["stream"], end="")
    if "error" in entry:
      ret=1
      print("Exited with an error")
      print(entry["error"])
      if "errorDetail" in entry and "message" in entry["errorDetail"] and entry["errorDetail"]["message"]!=entry["error"]:
        print(entry["errorDetail"])
  return ret

def asyncLogContainer(container, prefix=""):
  def worker(container):
    for line in container.logs(stream=True):
      print(prefix+line, end="")
  t=threading.Thread(target=worker, args=(container,))
  t.start()

def waitContainer(container, prefix=""):
  ret=container.wait()
  if ret["StatusCode"]!=0:
    print(prefix+"Exited with an error. Status code "+str(ret["StatusCode"]))
  if ret["Error"]!=None:
    print(prefix+ret["Error"])
  return ret["StatusCode"]

# terminate handler for command "run"
runningContainers=set()
def terminateHandler(signalnum, stack):
  print("Got "+("SIGINT" if signalnum==signal.SIGINT else "SIGTERM")+", stopping all containers")
  for container in runningContainers:
    container.stop()
  print("All containers stopped")
if args.command=="run":
  signal.signal(signal.SIGINT , terminateHandler)
  signal.signal(signal.SIGTERM, terminateHandler)



if args.command=="build":

  for s in args.service:

    if s=="base":
      build=dockerClientLL.build(tag="mbsimenv/base",
        path=scriptdir+"/baseImage",
        rm=False)
      ret=syncLogBuildImage(build)
      sys.exit(ret)

    elif s=="build":
      build=dockerClientLL.build(tag="mbsimenv/build",
        path=scriptdir+"/buildImage",
        rm=False)
      ret=syncLogBuildImage(build)
      sys.exit(ret)

    elif s=="run":
      build=dockerClientLL.build(tag="mbsimenv/run",
        path=scriptdir+"/..",
        dockerfile="docker/runImage/Dockerfile",
        nocache=True,
        rm=False)
      ret=syncLogBuildImage(build)
      sys.exit(ret)

    elif s=="autobuild":
      build=dockerClientLL.build(tag="mbsimenv/autobuild",
        path=scriptdir+"/..",
        dockerfile="docker/autobuildImage/Dockerfile",
        rm=False)
      ret=syncLogBuildImage(build)
      sys.exit(ret)

    elif s=="webserver":
      build=dockerClientLL.build(tag="mbsimenv/webserver",
        path=scriptdir+"/webserverImage",
        rm=False)
      ret=syncLogBuildImage(build)
      sys.exit(ret)

    elif s=="webapp":
      build=dockerClientLL.build(tag="mbsimenv/webapp",
        path=scriptdir+"/webappImage",
        rm=False)
      ret=syncLogBuildImage(build)
      sys.exit(ret)

    elif s=="webapprun":
      build=dockerClientLL.build(tag="mbsimenv/webapprun",
        path=scriptdir+"/webapprunImage",
        rm=False)
      ret=syncLogBuildImage(build)
      sys.exit(ret)

    else:
      raise RuntimeError("Unknown image "+s+" to build.")



if args.command=="run":

  for s in args.service:

    if s=="autobuild-linux64-ci":
      if args.servername==None:
        raise RuntimeError("Argument --servername is required.")
      autobuild=dockerClient.containers.run(image="mbsimenv/autobuild",
        init=True,
        command=["--buildType", "linux64-ci", "-j", str(args.jobs)],
        environment={"MBSIMENVSERVERNAME": args.servername},
        volumes={
          'mbsimenv_mbsim-linux64-ci':  {"bind": "/mbsim-env",    "mode": "rw"},
          'mbsimenv_report-linux64-ci': {"bind": "/mbsim-report", "mode": "rw"},
          'mbsimenv_ccache':            {"bind": "/mbsim-ccache", "mode": "rw"},
          'mbsimenv_state':             {"bind": "/mbsim-state",  "mode": "rw"},
        },
        detach=True, stdout=True, stderr=True)
      runningContainers.add(autobuild)
      asyncLogContainer(autobuild)
      ret=waitContainer(autobuild)
      sys.exit(ret)

    elif s=="autobuild-linux64-dailydebug":
      if args.servername==None:
        raise RuntimeError("Argument --servername is required.")
      autobuild=dockerClient.containers.run(image="mbsimenv/autobuild",
        init=True,
        command=["--buildType", "linux64-dailydebug", "--buildDoc", "--valgrindExamples", "-j", str(args.jobs)],
        environment={"MBSIMENVSERVERNAME": args.servername},
        volumes={
          'mbsimenv_mbsim-linux64-dailydebug':  {"bind": "/mbsim-env",    "mode": "rw"},
          'mbsimenv_report-linux64-dailydebug': {"bind": "/mbsim-report", "mode": "rw"},
          'mbsimenv_ccache':                    {"bind": "/mbsim-ccache", "mode": "rw"},
          'mbsimenv_state':                     {"bind": "/mbsim-state",  "mode": "rw"},
        },
        detach=True, stdout=True, stderr=True)
      runningContainers.add(autobuild)
      asyncLogContainer(autobuild)
      ret=waitContainer(autobuild)
      sys.exit(ret)

    elif s=="autobuild-linux64-dailyrelease":
      if args.servername==None:
        raise RuntimeError("Argument --servername is required.")
      autobuild=dockerClient.containers.run(image="mbsimenv/autobuild",
        init=True,
        command=["--buildType", "linux64-dailyrelease", "-j", str(args.jobs)],
        environment={"MBSIMENVSERVERNAME": args.servername},
        volumes={
          'mbsimenv_mbsim-linux64-dailyrelease':  {"bind": "/mbsim-env",    "mode": "rw"},
          'mbsimenv_report-linux64-dailyrelease': {"bind": "/mbsim-report", "mode": "rw"},
          'mbsimenv_ccache':                      {"bind": "/mbsim-ccache", "mode": "rw"},
          'mbsimenv_state':                       {"bind": "/mbsim-state",  "mode": "rw"},
        },
        detach=True, stdout=True, stderr=True)
      runningContainers.add(autobuild)
      asyncLogContainer(autobuild)
      ret=waitContainer(autobuild)
      sys.exit(ret)

    elif s=="service":
      if args.servername==None:
        raise RuntimeError("Argument --servername is required.")

      # network
      network=dockerClient.networks.create(name="mbsimenv_service")

      # webserver
      webserver=dockerClient.containers.run(image="mbsimenv/webserver",
        init=True,
        command=(["--clientID", args.clientID] if args.clientID!=None else [])+\
          (["--clientSecret", args.clientSecret] if args.clientSecret!=None else [])+\
          (["--webhookSecret", args.webhookSecret] if args.webhookSecret!=None else [])+\
          (["--statusAccessToken", args.statusAccessToken] if args.statusAccessToken!=None else []),
        environment={"MBSIMENVSERVERNAME": args.servername},
        volumes={
          'mbsimenv_report-linux64-ci':           {"bind": "/var/www/html/mbsim/linux64-ci",           "mode": "ro"},
          'mbsimenv_report-linux64-dailydebug':   {"bind": "/var/www/html/mbsim/linux64-dailydebug",   "mode": "ro"},
          'mbsimenv_report-linux64-dailyrelease': {"bind": "/var/www/html/mbsim/linux64-dailyrelease", "mode": "ro"},
          'mbsimenv_state':                       {"bind": "/var/www/html/mbsim/buildsystemstate",     "mode": "ro"},
          'mbsimenv_config':                      {"bind": "/mbsim-config",                            "mode": "rw"},
          'mbsimenv_releases':                    {"bind": "/var/www/html/mbsim/releases",             "mode": "rw"},
          'mbsimenv_letsencrypt':                 {"bind": "/etc/letsencrypt",                         "mode": "rw"},
        },
        hostname=args.servername,
        ports={
          80:  80,
          443: 443,
        },
        detach=True, stdout=True, stderr=True)
      runningContainers.add(webserver)
      network.connect(webserver, aliases=["webserver"])
      asyncLogContainer(webserver, "webserver: ")

      # webapp
      webapp=dockerClient.containers.run(image="mbsimenv/webapp",
        init=True,
        command=[network.id],
        environment={"MBSIMENVSERVERNAME": args.servername},
        volumes={
          '/var/run/docker.sock': {"bind": "/var/run/docker.sock", "mode": "rw"},
        },
        detach=True, stdout=True, stderr=True)
      runningContainers.add(webapp)
      network.connect(webapp, aliases=["webapp"])
      asyncLogContainer(webapp, "webapp: ")

      # wait for running containers
      retwebserver=waitContainer(webserver, "webserver: ")
      retwebapp=waitContainer(webapp, "webapp: ")
      # stop all other containers connected to network (this may be webapprun and autbuild containers)
      network.reload()
      for c in network.containers:
        c.stop()
      # remove network
      network.remove()
      sys.exit(0 if retwebserver==0 and retwebapp==0 else 1)

    elif s=="webapprun":
      if args.token==None:
        raise RuntimeError("Option --token is required.")
      webapprun=dockerClient.containers.run(image="mbsimenv/webapprun",
        init=True,
        command=[args.token],
        volumes={
          'mbsimenv_mbsim-linux64-ci':           {"bind": "/mbsim-env-linux64-ci",           "mode": "ro"},
          'mbsimenv_mbsim-linux64-dailydebug':   {"bind": "/mbsim-env-linux64-dailydebug",   "mode": "ro"},
          'mbsimenv_mbsim-linux64-dailyrelease': {"bind": "/mbsim-env-linux64-dailyrelease", "mode": "ro"},
        },
        ports={
          5901: 5901,
        },
        detach=True, stdout=True, stderr=True)
      runningContainers.add(webapprun)
      asyncLogContainer(webapprun)
      ret=waitContainer(webapprun)
      sys.exit(ret)

    else:
      raise RuntimeError("Unknown container "+s+" to run.")

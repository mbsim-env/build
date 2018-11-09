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
import multiprocessing
import math



def parseArgs():
  argparser=argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='''Manage and run the MBSim-Env docker images, containers, ...
    When using --command=run then all unknown arguments are passed to the 
    corresponding docker run CMD command. Such arguments are e.g.
    --clientID: type=str, help="GitHub OAuth App client ID"
    --clientSecret: type=str, help="GitHub OAuth App client secret"
    --webhookSecret: type=str, help="GitHub web hook secret"
    --statusAccessToken: type=str, help="GitHub access token for status updates"
    --token: type=str, help="Webapprun token"
    --forceBuild: help="run build even if it was already run"
    ''')
  
  argparser.add_argument("command", type=str, choices=["build", "run"], help="Command to execute")
  argparser.add_argument("service", nargs="+", help="Service or image to run or build (for build command 'ALL' can be used)")
  argparser.add_argument("--servername", type=str, default=None, help="Set the hostname of webserver")
  argparser.add_argument("--jobs", "-j", type=int, default=int(math.ceil(multiprocessing.cpu_count()/2)), help="Number of jobs to run in parallel")
  
  return argparser.parse_known_args()



scriptdir=os.path.dirname(os.path.realpath(__file__))

dockerClient=docker.from_env()
dockerClientLL=docker.APIClient()



def syncLogBuildImage(build):
  ret=0
  for line in build:
    entry=json.loads(line)
    if "stream" in entry:
      print(entry["stream"], end="")
      sys.stdout.flush()
    if "error" in entry:
      ret=1
      print("Exited with an error")
      print(entry["error"])
      if "errorDetail" in entry and "message" in entry["errorDetail"] and entry["errorDetail"]["message"]!=entry["error"]:
        print(entry["errorDetail"])
      sys.stdout.flush()
  return ret

def asyncLogContainer(container, prefix=""):
  def worker(container):
    for line in container.logs(stream=True):
      print(prefix+line.decode('utf-8'), end="")
      sys.stdout.flush()
  threading.Thread(target=worker, args=(container,)).start()

def waitContainer(container, prefix=""):
  ret=container.wait()
  if (3,0,0)<=docker.version_info:
    if ret["StatusCode"]!=0:
      print(prefix+"Exited with an error. Status code "+str(ret["StatusCode"]))
    if ret["Error"]!=None:
      print(prefix+ret["Error"])
    sys.stdout.flush()
    return ret["StatusCode"]
  else:
    if ret!=0:
      print(prefix+"Exited with an error. Status code "+str(ret))
    sys.stdout.flush()
    return ret



runningContainers=set()

def main():
  args, argsRest=parseArgs()

  # terminate handler for command "run"
  def terminateHandler(signalnum, stack):
    print("Got "+("SIGINT" if signalnum==signal.SIGINT else "SIGTERM")+", stopping all containers")
    sys.stdout.flush()
    for container in runningContainers:
      container.stop()
    print("All containers stopped")
    sys.stdout.flush()
  if args.command=="run":
    signal.signal(signal.SIGINT , terminateHandler)
    signal.signal(signal.SIGTERM, terminateHandler)



  if args.command=="build":
    if "ALL" in args.service:
      args.service=[ # must be in order
        "base",
        "build",
        #"run",
        "proxy",
        "autobuild",
        "autobuildwin64",
        "webserver",
        "webapp",
        "webapprun",
      ]
    for s in args.service:
      ret=build(s, args.jobs)
      if ret!=0:
        break
    return ret
  
  if args.command=="run":
    for s in args.service:
      ret=run(s, args.servername, args.jobs, addCommands=argsRest)
      if ret!=0:
        break
    return ret



def build(s, jobs=4):

  if s=="base":
    build=dockerClientLL.build(tag="mbsimenv/base",
      buildargs={"JOBS": str(jobs)},
      path=scriptdir+"/baseImage",
      rm=False)
    return syncLogBuildImage(build)

  elif s=="build":
    build=dockerClientLL.build(tag="mbsimenv/build",
      buildargs={"JOBS": str(jobs)},
      path=scriptdir+"/buildImage",
      rm=False)
    return syncLogBuildImage(build)

  elif s=="run":
    build=dockerClientLL.build(tag="mbsimenv/run",
      buildargs={"JOBS": str(jobs)},
      path=scriptdir+"/..",
      dockerfile="docker/runImage/Dockerfile",
      nocache=True,
      rm=False)
    return syncLogBuildImage(build)

  elif s=="proxy":
    build=dockerClientLL.build(tag="mbsimenv/proxy",
      path=scriptdir+"/proxyImage",
      rm=False)
    return syncLogBuildImage(build)

  elif s=="autobuild":
    build=dockerClientLL.build(tag="mbsimenv/autobuild",
      path=scriptdir+"/..",
      dockerfile="docker/autobuildImage/Dockerfile",
      rm=False)
    return syncLogBuildImage(build)

  elif s=="autobuildwin64":
    build=dockerClientLL.build(tag="mbsimenv/autobuildwin64",
      buildargs={"JOBS": str(jobs)},
      path=scriptdir+"/..",
      dockerfile="docker/autobuildwin64Image/Dockerfile",
      rm=False)
    return syncLogBuildImage(build)

  elif s=="webserver":
    build=dockerClientLL.build(tag="mbsimenv/webserver",
      path=scriptdir,
      dockerfile="webserverImage/Dockerfile",
      rm=False)
    return syncLogBuildImage(build)

  elif s=="webapp":
    build=dockerClientLL.build(tag="mbsimenv/webapp",
      path=scriptdir,
      dockerfile="webappImage/Dockerfile",
      rm=False)
    return syncLogBuildImage(build)

  elif s=="webapprun":
    build=dockerClientLL.build(tag="mbsimenv/webapprun",
      path=scriptdir+"/webapprunImage",
      rm=False)
    return syncLogBuildImage(build)

  else:
    raise RuntimeError("Unknown image "+s+" to build.")




def runWait(containers, printLog=True):
  ret=0
  for c in containers:
    ret=ret+abs(waitContainer(c))
    if not printLog:
      print("Finished running container ID "+c.id)
      sys.stdout.flush()
  return ret

def runAutobuild(s, servername, buildType, addCommand, jobs=4,
                 fmatvecBranch="master", hdf5serieBranch="master", openmbvBranch="master", mbsimBranch="master",
                 printLog=True):
  if servername==None:
    raise RuntimeError("Argument --servername is required.")

  # autobuild
  autobuild=dockerClient.containers.run(image=("mbsimenv/autobuildwin64" if buildType=="win64-dailyrelease" else "mbsimenv/autobuild"),
    init=True,
    labels={"buildtype": buildType},
    command=["--buildType", buildType, "-j", str(jobs),
             "--fmatvecBranch", fmatvecBranch,
             "--hdf5serieBranch", hdf5serieBranch,
             "--openmbvBranch", openmbvBranch,
             "--mbsimBranch", mbsimBranch]+addCommand,
    environment={"MBSIMENVSERVERNAME": servername},
    volumes={
      'mbsimenv_mbsim-'+buildType:  {"bind": "/mbsim-env",    "mode": "rw"},
      'mbsimenv_report-'+buildType: {"bind": "/mbsim-report", "mode": "rw"},
      'mbsimenv_ccache':            {"bind": "/mbsim-ccache", "mode": "rw"},
      'mbsimenv_state':             {"bind": "/mbsim-state",  "mode": "rw"},
    },
    detach=True, stdout=True, stderr=True)
  if not printLog:
    print("Started running "+s+" as container ID "+autobuild.id)
    sys.stdout.flush()
  runningContainers.add(autobuild)
  if printLog:
    asyncLogContainer(autobuild)

  # wait for running containers
  ret=runWait([autobuild], printLog=printLog)
  return ret

def run(s, servername, jobs=4,
        addCommands=[],
        fmatvecBranch="master", hdf5serieBranch="master", openmbvBranch="master", mbsimBranch="master",
        networkID=None, hostname=None,
        wait=True, printLog=True):

  if s=="autobuild-linux64-ci":
    return runAutobuild(s, servername, "linux64-ci", addCommands, jobs=jobs,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog)

  elif s=="autobuild-linux64-dailydebug":
    return runAutobuild(s, servername, "linux64-dailydebug", ["--buildDoc", "--valgrindExamples"]+addCommands, jobs=jobs,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog)

  elif s=="autobuild-linux64-dailyrelease":
    return runAutobuild(s, servername, "linux64-dailyrelease", addCommands, jobs=jobs,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog)

  elif s=="autobuild-win64-dailyrelease":
    return runAutobuild(s, servername, "win64-dailyrelease", addCommands, jobs=jobs,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog)

  elif s=="service":
    if servername==None:
      raise RuntimeError("Argument --servername is required.")

    # networks
    networki=dockerClient.networks.create(name="mbsimenv_service_intern", internal=True)
    networke=dockerClient.networks.create(name="mbsimenv_service_extern")

    # webserver
    webserver=dockerClient.containers.run(image="mbsimenv/webserver",
      init=True,
      network=networki.id,
      command=["-j", str(jobs)]+addCommands,
      environment={"MBSIMENVSERVERNAME": servername},
      volumes={
        'mbsimenv_report-linux64-ci':           {"bind": "/var/www/html/mbsim/linux64-ci",           "mode": "ro"},
        'mbsimenv_report-linux64-dailydebug':   {"bind": "/var/www/html/mbsim/linux64-dailydebug",   "mode": "ro"},
        'mbsimenv_report-linux64-dailyrelease': {"bind": "/var/www/html/mbsim/linux64-dailyrelease", "mode": "ro"},
        'mbsimenv_report-win64-dailyrelease':   {"bind": "/var/www/html/mbsim/win64-dailyrelease",   "mode": "ro"},
        'mbsimenv_state':                       {"bind": "/var/www/html/mbsim/buildsystemstate",     "mode": "ro"},
        'mbsimenv_config':                      {"bind": "/mbsim-config",                            "mode": "rw"},
        'mbsimenv_releases':                    {"bind": "/var/www/html/mbsim/releases",             "mode": "rw"},
        'mbsimenv_letsencrypt':                 {"bind": "/etc/letsencrypt",                         "mode": "rw"},
        '/var/run/docker.sock':                 {"bind": "/var/run/docker.sock", "mode": "rw"},
      },
      hostname=servername,
      ports={
        80:  80,
        443: 443,
      },
      detach=True, stdout=True, stderr=True)
    networki.disconnect(webserver)
    networki.connect(webserver, aliases=["webserver"])
    networke.connect(webserver)
    if not printLog:
      print("Started running "+s+" as container ID "+webserver.id)
      sys.stdout.flush()
    runningContainers.add(webserver)
    if printLog:
      asyncLogContainer(webserver, "webserver: ")

    # webapp
    webapp=dockerClient.containers.run(image="mbsimenv/webapp",
      init=True,
      network=networki.id,
      command=[networki.id]+addCommands,
      environment={"MBSIMENVSERVERNAME": servername},
      volumes={
        '/var/run/docker.sock': {"bind": "/var/run/docker.sock", "mode": "rw"},
      },
      detach=True, stdout=True, stderr=True)
    networki.disconnect(webapp)
    networki.connect(webapp, aliases=["webapp"])
    networke.connect(webapp)
    if not printLog:
      print("Started running "+s+" as container ID "+webapp.id)
      sys.stdout.flush()
    runningContainers.add(webapp)
    if printLog:
      asyncLogContainer(webapp, "webapp: ")

    # proxy
    proxy=dockerClient.containers.run(image="mbsimenv/proxy",
      init=True,
      network=networki.id,
      # allow access to these sites
      command=["www\\.mbsim-env\\.de\n"+
               "cdn\\.datatables\\.net\n"+
               "cdnjs\\.cloudflare\\.com\n"+
               "code\\.jquery\\.com\n"+
               "maxcdn\\.bootstrapcdn\\.com\n"+
               "www\\.anwalt\\.de\n"]+addCommands,
      detach=True, stdout=True, stderr=True)
    networki.disconnect(proxy)
    networki.connect(proxy, aliases=["proxy"])
    networke.connect(proxy)
    if not printLog:
      print("Started running "+s+" as container ID "+proxy.id)
      sys.stdout.flush()
    runningContainers.add(proxy)
    if printLog:
      asyncLogContainer(proxy, "proxy: ")

    # wait for running containers
    ret=runWait([webserver, webapp, proxy], printLog=printLog)
    # stop all other containers connected to network (this may be webapprun and autbuild containers)
    networki.reload()
    for c in networki.containers:
      c.stop()
    # remove network
    networki.remove()
    networke.remove()
    return ret

  elif s=="webapprun":
    if "--token" not in addCommands:
      raise RuntimeError("Option --token is required.")
    if networkID==None:
      raise RuntimeError("Option --networkID is required.")
    if hostname==None:
      raise RuntimeError("Option --hostname is required.")
    networki=dockerClient.networks.get(networkID)
    webapprun=dockerClient.containers.run(image="mbsimenv/webapprun",
      init=True,
      network=networki.id,
      command=addCommands,
      volumes={
        'mbsimenv_mbsim-linux64-ci':           {"bind": "/mbsim-env-linux64-ci",           "mode": "ro"},
        'mbsimenv_mbsim-linux64-dailydebug':   {"bind": "/mbsim-env-linux64-dailydebug",   "mode": "ro"},
        'mbsimenv_mbsim-linux64-dailyrelease': {"bind": "/mbsim-env-linux64-dailyrelease", "mode": "ro"},
        'mbsimenv_mbsim-win64-dailyrelease':   {"bind": "/mbsim-env-win64-dailyrelease",   "mode": "ro"},
      },
      detach=True, stdout=True, stderr=True)
    networki.disconnect(webapprun)
    networki.connect(webapprun, aliases=[hostname])
    if not printLog:
      print("Started running "+s+" as container ID "+webapprun.id)
      sys.stdout.flush()
    runningContainers.add(webapprun)
    if printLog:
      asyncLogContainer(webapprun)
    if wait:
      return runWait([webapprun], printLog=printLog)
    else:
      return [webapprun]

  else:
    raise RuntimeError("Unknown container "+s+" to run.")



# call the main routine (from command line)
if __name__=="__main__":
  ret=main()
  sys.exit(ret)

#!/usr/bin/python3

import argparse
import docker
import os
import stat
import json
import time
import threading
import sys
import signal
import multiprocessing
import re
import socket



def parseArgs():
  argparser=argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='''Manage and run the MBSim-Env docker images, containers, ...
    When using --command=run then all unknown arguments are passed to the 
    corresponding docker run CMD command. Such arguments are e.g.
    --clientID: type=str, help="GitHub OAuth App client ID"
    --clientSecret: type=str, help="GitHub OAuth App client secret"
    --webhookSecret: type=str, help="GitHub web hook secret"
    --token: type=str, help="Webapprun token"
    --forceBuild: help="run build even if it was already run"
    The environment variable MBSIMENVTAGNAME is used as tagname everywhere.
    The environment variable MBSIMENVSERVERNAME is used as the server name everywhere.
    ''')
  
  argparser.add_argument("command", type=str, choices=["build", "run", "pull", "push", "prune"], help="Command to execute")
  argparser.add_argument("service", nargs="*", help="Service or image to run or build")
  argparser.add_argument("--jobs", "-j", type=int, default=multiprocessing.cpu_count(), help="Number of jobs to run in parallel")
  argparser.add_argument("--interactive", "-i", action='store_true', help="Run container, wait and print how to attach to it")
  argparser.add_argument("--daemon", "-d", type=str, choices=["start", "status", "stop"], help="Only for 'run service'")
  
  return argparser.parse_known_args()



scriptdir=os.path.dirname(os.path.realpath(__file__))

dockerClient=docker.from_env()
dockerClientLL=docker.APIClient()


def getServername():
  if "MBSIMENVSERVERNAME" not in os.environ:
    raise RuntimeError("The MBSIMENVSERVERNAME envvar is required.")
  return os.environ["MBSIMENVSERVERNAME"]

def getTagname():
  if "MBSIMENVTAGNAME" not in os.environ:
    raise RuntimeError("The MBSIMENVTAGNAME envvar is required.")
  return os.environ["MBSIMENVTAGNAME"]

def syncLogBuildImage(build, fd=sys.stdout):
  ret=0
  for line in build:
    entry=json.loads(line.decode("UTF-8"))
    if "stream" in entry:
      print(entry["stream"], end="", file=fd)
      fd.flush()
    if "status" in entry:
      print(entry["status"]+(": "+entry["id"] if "id" in entry else "")+(": "+entry["progress"] if "progress" in entry else ""), file=fd)
      fd.flush()
    if "error" in entry:
      ret=1
      print("Exited with an error", file=fd)
      print(entry["error"], file=fd)
      if "errorDetail" in entry and "message" in entry["errorDetail"] and entry["errorDetail"]["message"]!=entry["error"]:
        print(entry["errorDetail"], file=fd)
      fd.flush()
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

allServices=[ # must be in order
  "base",
  "build",
  "buildwin64",
  "builddoc",
  #"run",
  "proxy",
  "webserver",
  "webapp",
  "webapprun",
]

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
    if len(args.service)==0:
      args.service=allServices
    for s in args.service:
      ret=build(s, args.jobs)
      if ret!=0:
        break
    return ret
  
  if args.command=="run":
    ret=0
    for s in args.service:
      ret=run(s, args.jobs, addCommands=argsRest, interactive=args.interactive, daemon=args.daemon)
      if ret!=0:
        break
    return ret

  if args.command=="pull":
    if len(args.service)==0:
      args.service=allServices
      pull=dockerClientLL.pull("centos", "centos7", stream=True)
      if syncLogBuildImage(pull)!=0:
        return 1
    for s in args.service:
      pull=dockerClientLL.pull("mbsimenv/"+s, getTagname(), stream=True)
      if syncLogBuildImage(pull)!=0:
        return 1
    return 0

  if args.command=="push":
    if len(args.service)==0:
      args.service=allServices
    for s in args.service:
      push=dockerClient.images.push("mbsimenv/"+s, getTagname(), stream=True)
      if syncLogBuildImage(push)!=0:
        return 1
    return 0

  if args.command=="prune":
    days=30
    p=dockerClient.containers.prune(filters={'until': str(days*24)+"h"})
    print("Reclaimed container space: %.1fGB (only containers older then %d days are reclaimed)"%(p["SpaceReclaimed"]/1e9, days))
    p=dockerClient.images.prune()
    print("Reclaimed image space: %.1fGB"%(p["SpaceReclaimed"]/1e9))
    return 0



def buildImage(tag, tagMultistageImage=True, fd=sys.stdout, **kwargs):
  # fix permissions (the permissions are part of the docker cache)
  for d,_,files in os.walk(kwargs["path"]):
    for f in files:
      st=stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
      if (stat.S_IMODE(os.lstat(d+"/"+f).st_mode) & stat.S_IXUSR)!=0:
        st |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
      os.chmod(d+"/"+f, st)

  if tagMultistageImage:
    if "dockerfile" in kwargs:
      dockerfile=kwargs["path"]+"/"+kwargs["dockerfile"]
    else:
      dockerfile=kwargs["path"]+"/Dockerfile"
    fromRE=re.compile("^ *FROM .* AS (.*)$")
    with open(dockerfile, "r") as f:
      for line in f.readlines():
        match=fromRE.match(line)
        if match:
          multistageName=match.group(1).lower()
          multistageImage=tag.split(':')[0]+"--"+multistageName+":"+tag.split(':')[1]
          print("Building multistage image "+multistageName+" and tag it as "+multistageImage, file=fd)
          build=dockerClientLL.build(tag=multistageImage, target=multistageName, **kwargs)
          ret=syncLogBuildImage(build, fd)
          if ret!=0:
            return ret
  build=dockerClientLL.build(tag=tag, **kwargs)
  return syncLogBuildImage(build, fd)

def build(s, jobs=4, fd=sys.stdout, baseDir=scriptdir):

  if s=="base":
    return buildImage(tag="mbsimenv/base:"+getTagname(), fd=fd,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/baseImage",
      rm=False)

  elif s=="build":
    return buildImage(tag="mbsimenv/build:"+getTagname(), fd=fd,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/buildImage/Dockerfile",
      rm=False)

  elif s=="run":
    return buildImage(tag="mbsimenv/run:"+getTagname(), fd=fd,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/runImage/Dockerfile",
      nocache=True,
      rm=False)

  elif s=="proxy":
    return buildImage(tag="mbsimenv/proxy:"+getTagname(), fd=fd,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/proxyImage",
      rm=False)

  elif s=="buildwin64":
    return buildImage(tag="mbsimenv/buildwin64:"+getTagname(), fd=fd,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/buildwin64Image/Dockerfile",
      rm=False)

  elif s=="builddoc":
    return buildImage(tag="mbsimenv/builddoc:"+getTagname(), fd=fd,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/builddocImage/Dockerfile",
      rm=False)

  elif s=="webserver":
    return buildImage(tag="mbsimenv/webserver:"+getTagname(), fd=fd,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir,
      dockerfile="webserverImage/Dockerfile",
      rm=False)

  elif s=="webapp":
    return buildImage(tag="mbsimenv/webapp:"+getTagname(), fd=fd,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir,
      dockerfile="webappImage/Dockerfile",
      rm=False)

  elif s=="webapprun":
    return buildImage(tag="mbsimenv/webapprun:"+getTagname(), fd=fd,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/webapprunImage",
      rm=False)

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

def runAutobuild(s, buildType, addCommand, jobs=4, interactive=False,
                 fmatvecBranch="master", hdf5serieBranch="master", openmbvBranch="master", mbsimBranch="master",
                 printLog=True, detach=False, statusAccessToken=""):
  updateReferences=[]
  if buildType=="linux64-dailydebug" and os.path.isfile("/mbsim-config/mbsimBuildService.conf"):
    with open("/mbsim-config/mbsimBuildService.conf", "r") as f:
      config=json.load(f)
    if len(config["checkedExamples"])>0:
      updateReferences=["--updateReferences"]+config["checkedExamples"]

  # build
  build=dockerClient.containers.run(
    image=("mbsimenv/buildwin64" if buildType=="win64-dailyrelease" else "mbsimenv/build")+":"+getTagname(),
    init=True,
    labels={"buildtype": buildType},
    entrypoint=None if not interactive else ["sleep", "infinity"],
    command=(["--buildType", buildType, "-j", str(jobs),
              "--fmatvecBranch", fmatvecBranch,
              "--hdf5serieBranch", hdf5serieBranch,
              "--openmbvBranch", openmbvBranch,
              "--mbsimBranch", mbsimBranch]+updateReferences+addCommand) if not interactive else [],
    environment={"MBSIMENVSERVERNAME": getServername(), "STATUSACCESSTOKEN": statusAccessToken, "MBSIMENVTAGNAME": getTagname()},
    volumes={
      'mbsimenv_mbsim-'+buildType+"."+getTagname():  {"bind": "/mbsim-env",    "mode": "rw"},
      'mbsimenv_report-'+buildType+"."+getTagname(): {"bind": "/mbsim-report", "mode": "rw"},
      'mbsimenv_ccache.'+getTagname():               {"bind": "/mbsim-ccache", "mode": "rw"},
      'mbsimenv_state.'+getTagname():                {"bind": "/mbsim-state",  "mode": "rw"},
    },
    detach=True, stdout=True, stderr=True)
  if interactive:
    print(build.short_id)
    print("Use")
    print("docker exec -ti %s bash"%(build.short_id))
    print("to attach to this container")
  if not printLog:
    print("Started running "+s+" as container ID "+build.id)
    sys.stdout.flush()
  if not detach:
    runningContainers.add(build)
  if printLog:
    asyncLogContainer(build)

  # wait for running containers
  if detach:
    return build
  else:
    ret=runWait([build], printLog=printLog)
    return ret

def run(s, jobs=4,
        addCommands=[],
        interactive=False,
        fmatvecBranch="master", hdf5serieBranch="master", openmbvBranch="master", mbsimBranch="master",
        networkID=None, hostname=None,
        wait=True, printLog=True, detach=False, statusAccessToken="", daemon=""):

  if detach and interactive:
    raise RuntimeError("Cannot run detached an interactively.")

  if s=="build-linux64-ci":
    return runAutobuild(s, "linux64-ci", addCommands, jobs=jobs, interactive=interactive,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, statusAccessToken=statusAccessToken)

  elif s=="build-linux64-dailydebug":
    return runAutobuild(s, "linux64-dailydebug", ["--valgrindExamples"]+addCommands,
                 jobs=jobs, interactive=interactive,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, statusAccessToken=statusAccessToken)

  elif s=="build-linux64-dailyrelease":
    return runAutobuild(s, "linux64-dailyrelease", addCommands, jobs=jobs, interactive=interactive,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, statusAccessToken=statusAccessToken)

  elif s=="build-win64-dailyrelease":
    return runAutobuild(s, "win64-dailyrelease", addCommands, jobs=jobs, interactive=interactive,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, statusAccessToken=statusAccessToken)

  elif s=="builddoc":
    builddoc=dockerClient.containers.run(image="mbsimenv/builddoc:"+getTagname(),
      init=True,
      entrypoint=None if not interactive else ["sleep", "infinity"],
      environment={"MBSIMENVSERVERNAME": getServername(), "MBSIMENVTAGNAME": getTagname()},
      volumes={
        'mbsimenv_mbsim-linux64-dailydebug.'+getTagname():  {"bind": "/mbsim-env",    "mode": "rw"},
        'mbsimenv_report-linux64-dailydebug.'+getTagname(): {"bind": "/mbsim-report", "mode": "rw"},
        'mbsimenv_state.'+getTagname():                     {"bind": "/mbsim-state",  "mode": "rw"},
      },
      detach=True, stdout=True, stderr=True)
    if interactive:
      print(builddoc.short_id)
      print("Use")
      print("docker exec -ti %s bash"%(builddoc.short_id))
      print("to attach to this container")
    if not printLog:
      print("Started running "+s+" as container ID "+builddoc.id)
      sys.stdout.flush()
    if not detach:
      runningContainers.add(builddoc)
    if printLog:
      asyncLogContainer(builddoc)

    # wait for running containers
    if detach:
      return builddoc
    else:
      ret=runWait([builddoc], printLog=printLog)
      return ret

  elif s=="service":
    getServername() # just to fail early if the envvar is not set
    if detach==True:
      raise RuntimeError("Cannot run service detached.")

    idFile="/tmp/mbsimenv-"+getTagname()+".id"

    if daemon=="stop":
      print("Stopping mbsim-env "+getTagname())
      if not os.path.exists(idFile):
        print("No id file. Nothing to do")
        return 0
      with open(idFile, "r") as f:
        dockerIDs=json.load(f)
      for containerID in dockerIDs["container"]:
        container=dockerClient.containers.get(containerID)
        print("Stopping container "+containerID)
        container.stop()
      for networkID in dockerIDs["network"]:
        network=dockerClient.networks.get(networkID)
        print("Removing network "+networkID)
        network.remove()
      os.remove(idFile)
      print("All done. id file removed")
      return 0

    if daemon=="status":
      print("Status of mbsim-env "+getTagname())
      if not os.path.exists(idFile):
        print("No id file. mbsim-env "+getTagname()+" is not running")
        return 1
      with open(idFile, "r") as f:
        dockerIDs=json.load(f)
      for containerID in dockerIDs["container"]:
        container=dockerClient.containers.get(containerID)
        if container.status=="running":
          print("Container "+containerID+" is running")
        else:
          print("Container "+containerID+" is not running")
          return 1
      for networkID in dockerIDs["network"]:
        network=dockerClient.networks.get(networkID)
        print("Network "+networkID+" exists")
      return 0

    # networks
    networki=dockerClient.networks.create(name="mbsimenv_service_intern:"+getTagname(), internal=True)
    networke=dockerClient.networks.create(name="mbsimenv_service_extern:"+getTagname())

    # port binding
    addrinfo=socket.getaddrinfo(getServername(), None, 0, socket.SOCK_STREAM)
    if len(addrinfo)==0:
      raise RuntimeError("Cannot get address of MBSIMENVSERVERNAME.")
    ports={80: [], 443: []}
    for ai in addrinfo:
      for p in [80, 443]:
        ports[p].append((ai[4][0], p))

    # webserver
    webserver=dockerClient.containers.run(image="mbsimenv/webserver:"+getTagname(),
      init=True,
      network=networki.id,
      command=["-j", str(jobs)]+addCommands,
      environment={"MBSIMENVSERVERNAME": getServername(), "MBSIMENVTAGNAME": getTagname()},
      volumes={
        'mbsimenv_report-linux64-ci.'+getTagname():           {"bind": "/var/www/html/mbsim/linux64-ci",           "mode": "ro"},
        'mbsimenv_report-linux64-dailydebug.'+getTagname():   {"bind": "/var/www/html/mbsim/linux64-dailydebug",   "mode": "ro"},
        'mbsimenv_report-linux64-dailyrelease.'+getTagname(): {"bind": "/var/www/html/mbsim/linux64-dailyrelease", "mode": "ro"},
        'mbsimenv_report-win64-dailyrelease.'+getTagname():   {"bind": "/var/www/html/mbsim/win64-dailyrelease",   "mode": "ro"},
        'mbsimenv_report-docker.'+getTagname():               {"bind": "/var/www/html/mbsim/docker",               "mode": "rw"},
        'mbsimenv_build-docker.'+getTagname():                {"bind": "/mbsim-docker",                            "mode": "rw"},
        'mbsimenv_state.'+getTagname():                       {"bind": "/var/www/html/mbsim/buildsystemstate",     "mode": "ro"},
        'mbsimenv_config.'+getTagname():                      {"bind": "/mbsim-config",                            "mode": "rw"},
        'mbsimenv_releases.'+getTagname():                    {"bind": "/var/www/html/mbsim/releases",             "mode": "rw"},
        'mbsimenv_letsencrypt.'+getTagname():                 {"bind": "/etc/letsencrypt",                         "mode": "rw"},
        '/var/run/docker.sock':                               {"bind": "/var/run/docker.sock",                     "mode": "rw"},
      },
      hostname=getServername(),
      ports=ports,
      detach=True, stdout=True, stderr=True)
    networki.disconnect(webserver)
    networki.connect(webserver, aliases=["webserver", getServername()])
    networke.connect(webserver)
    if not printLog:
      print("Started running "+s+" as container ID "+webserver.id)
      sys.stdout.flush()
    runningContainers.add(webserver)
    if printLog:
      if daemon=="":
        asyncLogContainer(webserver, "webserver: ")
      else:
        print("Started webserver in background")

    # webapp
    webapp=dockerClient.containers.run(image="mbsimenv/webapp:"+getTagname(),
      init=True,
      network=networki.id,
      command=[networki.id]+addCommands,
      environment={"MBSIMENVSERVERNAME": getServername(), "MBSIMENVTAGNAME": getTagname()},
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
      if daemon=="":
        asyncLogContainer(webapp, "webapp: ")
      else:
        print("Started webapp in background")

    # proxy
    proxy=dockerClient.containers.run(image="mbsimenv/proxy:"+getTagname(),
      init=True,
      network=networki.id,
      # allow access to these sites
      command=["www\\.mbsim-env\\.de\n"+
               "cdn\\.datatables\\.net\n"+
               "cdnjs\\.cloudflare\\.com\n"+
               "code\\.jquery\\.com\n"+
               "maxcdn\\.bootstrapcdn\\.com\n"+
               "www\\.anwalt\\.de\n"]+addCommands,
      environment={"MBSIMENVSERVERNAME": getServername(), "MBSIMENVTAGNAME": getTagname()},
      detach=True, stdout=True, stderr=True)
    networki.disconnect(proxy)
    networki.connect(proxy, aliases=["proxy"])
    networke.connect(proxy)
    if not printLog:
      print("Started running "+s+" as container ID "+proxy.id)
      sys.stdout.flush()
    runningContainers.add(proxy)
    if printLog:
      if daemon=="":
        asyncLogContainer(proxy, "proxy: ")
      else:
        print("Started proxy in background")

    if daemon=="start":
      dockerIDs={'network': [networki.id, networke.id], 'container': [webserver.id, webapp.id, proxy.id]}
      with open(idFile, "w") as f:
        json.dump(dockerIDs, f)
      print("Created id file")
      return 0
    else:
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
    if detach==True:
      raise RuntimeError("Cannot run webapprun detached.")
    networki=dockerClient.networks.get(networkID)
    webapprun=dockerClient.containers.run(image="mbsimenv/webapprun:"+getTagname(),
      init=True,
      network=networki.id,
      command=addCommands,
      environment={"MBSIMENVTAGNAME": getTagname()},
      volumes={
        'mbsimenv_mbsim-linux64-ci.'+getTagname():           {"bind": "/mbsim-env-linux64-ci",           "mode": "ro"},
        'mbsimenv_mbsim-linux64-dailydebug.'+getTagname():   {"bind": "/mbsim-env-linux64-dailydebug",   "mode": "ro"},
        'mbsimenv_mbsim-linux64-dailyrelease.'+getTagname(): {"bind": "/mbsim-env-linux64-dailyrelease", "mode": "ro"},
        'mbsimenv_mbsim-win64-dailyrelease.'+getTagname():   {"bind": "/mbsim-env-win64-dailyrelease",   "mode": "ro"},
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

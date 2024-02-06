#!/usr/bin/env python3

import argparse
import docker
import os
import stat
import json
import time
import threading
import sys
import signal
import psutil
import multiprocessing
import re
import socket
import subprocess
import uuid



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
  argparser.add_argument("--jobs", "-j", type=int, default=psutil.cpu_count(False), help="Number of jobs to run in parallel")
  argparser.add_argument("--interactive", "-i", action='store_true', help="Run container, wait and print how to attach to it")
  argparser.add_argument("--daemon", "-d", type=str, choices=["start", "status", "stop"], help="Only for 'run service'")
  argparser.add_argument("--pushPullMultistageImage", action='store_true', help="Also push/pull multistage images")
  argparser.add_argument("--cacheFromSelf", action='store_true', help="Use existing image with same name as --cache_from")
  argparser.add_argument("--enforceConfigure", action='store_true', help="Enforce configure run (only for building mbsimenv runs)")

  argparser.add_argument("--cronBuilds", action='store_true', help="Run daily and CI builds in docker containers by cron (from webserver).")

  argparser.add_argument("--bindIP", type=str, default="MBSIMENVSERVERNAME", help="Bind ports on this IP (default: MBSIMENVSERVERNAME = bind to all IP to which MBSIMENVSERVERNAME resolves).")
  argparser.add_argument("--noSSL", action='store_true', help="Disable SSL support")
  argparser.add_argument("--databasePort", type=int, default=5432, help="The database port number to use on the host side (default: 5432)")
  argparser.add_argument("--httpPort", type=int, default=80, help="The http port number to use on the host side http (default: 80)")
  argparser.add_argument("--httpsPort", type=int, default=443, help="The https port number to use on the host side; not used if --noSSL (default: 443)")
  argparser.add_argument("--filestoragePort", type=int, default=1122, help="The filestorage port number to use on the host side (default: 1122)")

  def buildConfigConvert(x):
    try:
      return json.loads(x)
    except:
      with open(x, "rt") as f:
        return json.load(f)
  argparser.add_argument("--buildConfig", type=buildConfigConvert, default={}, help="Load an additional build(/examples) configuration as json string or filename")
  
  return argparser.parse_known_args()



scriptdir=os.path.dirname(os.path.realpath(__file__))

buildTypes=["linux64-dailydebug", "linux64-dailyrelease", "win64-dailyrelease", "linux64-ci", "win64-ci"]

dockerClient=docker.from_env()
dockerClientLL=docker.APIClient()


def getServername():
  if "MBSIMENVSERVERNAME" not in os.environ:
    raise RuntimeError("The MBSIMENVSERVERNAME envvar is required.")
  return os.environ["MBSIMENVSERVERNAME"]

def getServerIP():
  if args.bindIP!="MBSIMENVSERVERNAME":
    return [args.bindIP]
  addrinfo=socket.getaddrinfo(getServername(), None, 0, socket.SOCK_STREAM)
  if len(addrinfo)==0:
    raise RuntimeError("Cannot get address of MBSIMENVSERVERNAME.")
  ips=[]
  for ai in addrinfo:
    ips.append(ai[4][0])
  return ips

def getTagname():
  if "MBSIMENVTAGNAME" not in os.environ:
    raise RuntimeError("The MBSIMENVTAGNAME envvar is required.")
  return os.environ["MBSIMENVTAGNAME"]

def syncLogBuildImage(build, fd=sys.stdout):
  ret=0
  for lines in build:
    for line in lines.splitlines():
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
    if "Error" in ret and ret["Error"] is not None:
      print(prefix+str(ret["Error"]))
    sys.stdout.flush()
    return ret["StatusCode"]
  else:
    if ret!=0:
      print(prefix+"Exited with an error. Status code "+str(ret))
    sys.stdout.flush()
    return ret



runningContainers=set()

if sys.platform=="linux":
  allServices=[ # must be in order
    "database",
    "filestorage",
    "build",
    "buildwin64",
    "builddoc",
    "builddocker",
    "proxy",
    "webserver",
    "webapp",
    "webapprun",
  ]
else:
  allServices=[ # must be in order
    "buildmsys2ucrt64",
  ]

global args
args=None

def main():
  global args
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
      ret=build(s, args.jobs, cacheFromSelf=args.cacheFromSelf)
      if ret!=0:
        break
    return ret
  
  if args.command=="run":
    ret=0
    for s in args.service:
      ret=run(s, args.jobs, addCommands=argsRest, interactive=args.interactive, daemon=args.daemon,
              enforceConfigure=args.enforceConfigure, buildConfig=args.buildConfig)
      if ret!=0:
        break
    return ret

  if args.command=="pull":
    if len(args.service)==0:
      args.service=allServices
      pull=dockerClientLL.pull("centos", "centos7", stream=True)
      if syncLogBuildImage(pull)!=0:
        return 1
    if args.pushPullMultistageImage:
      import requests
      url='https://hub.docker.com/v2/repositories/mbsimenv'
      rs=requests.Session()
      while True:
        response=rs.get(url)
        if response.status_code!=200:
          raise RuntimeError("Cannot get repositories on dockerhub in mbsimenv.")
        data=response.json()
        for image in data["results"]:
          if '.' not in image["name"]: 
            continue
          pull=dockerClientLL.pull("mbsimenv/"+image["name"], getTagname(), stream=True)
          if syncLogBuildImage(pull)!=0:
            return 1
        url=data["next"]
        if url is None:
          break
    for s in args.service:
      pull=dockerClientLL.pull("mbsimenv/"+s, getTagname(), stream=True)
      if syncLogBuildImage(pull)!=0:
        return 1
    return 0

  if args.command=="push":
    if len(args.service)==0:
      args.service=allServices
    if args.pushPullMultistageImage:
      images=dockerClient.images.list()
    for s in args.service:
      if args.pushPullMultistageImage:
        for i in images:
          for t in i.tags:
            if t.startswith("mbsimenv/"+s+".") and t.endswith(":"+getTagname()):
              print("Pushing multistage image "+t.split(":")[0]+":"+getTagname())
              push=dockerClient.images.push(t.split(":")[0], getTagname(), stream=True)
              if syncLogBuildImage(push)!=0:
                return 1
      print("Pushing image "+"mbsimenv/"+s+":"+getTagname())
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



def buildImage(tag, tagMultistageImage=True, fd=sys.stdout, path=None, dockerfile=None, cacheFromSelf=False, **kwargs):
  # MISSING BEGIN: this is a workaround for docker-py bug https://github.com/docker/docker-py/pull/2391
  def createTarContext(path, dockerfile):
    try:
      import tempfile
      import tarfile
      dockerignore = os.path.join(path, '.dockerignore')
      exclude = None
      if os.path.exists(dockerignore):
          with open(dockerignore, 'r') as f:
              exclude = list(filter(bool, f.read().splitlines()))
      fileobj = docker.utils.tar(
          path, exclude=exclude, dockerfile=(dockerfile, None) if docker.version_info>=(3,0,0) else dockerfile, gzip=False
      )
      tar=tarfile.open(fileobj=fileobj)
      fileobjNew=tempfile.NamedTemporaryFile()
      tarNew=tarfile.open(mode='w', fileobj=fileobjNew)
      for ti in tar.getmembers():
        memberFileObj=tar.extractfile(ti)
        ti.uid=0
        ti.gid=0
        ti.uname="root"
        ti.gname="root"
        tarNew.addfile(ti, memberFileObj)
      tar.close()
      tarNew.close()
      fileobjNew.seek(0)
      return {"custom_context": True, "fileobj": fileobjNew, "dockerfile": dockerfile}
    except:
      print("WARNING: The workaround for docker-py bug https://github.com/docker/docker-py/pull/2391 does not work, skipping it; uid and gui are not adapted which may lead to unexpected docker build cache invalidations.")
      return {"path": path, "dockerfile": dockerfile}
  # MISSING END: this is a workaround for docker-py bug https://github.com/docker/docker-py/pull/2391
  # fix permissions (the permissions are part of the docker cache)
  for d,_,files in os.walk(path):
    st=stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    if (stat.S_IMODE(os.lstat(d).st_mode) & stat.S_IXUSR)!=0:
      st |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    os.chmod(d, st)
    for f in files:
      st=stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
      if (stat.S_IMODE(os.lstat(d+"/"+f).st_mode) & stat.S_IXUSR)!=0:
        st |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
      os.chmod(d+"/"+f, st)

  extraArgs={}
  if cacheFromSelf:
    extraArgs={"cache_from": [tag]}
  if tagMultistageImage:
    fromRE=re.compile("^ *FROM .* AS (.*)$")
    multistageNameImage=[]
    with open(path+"/"+dockerfile if dockerfile else path+"/Dockerfile", "rt") as f:
      for line in f:
        match=fromRE.match(line)
        if match:
          multistageName=match.group(1).lower()
          multistageImage=tag.split(':')[0]+"."+multistageName+":"+tag.split(':')[1]
          multistageNameImage.append((multistageName, multistageImage))
          if cacheFromSelf:
            extraArgs["cache_from"].append(multistageImage)
    for mni in multistageNameImage:
      print("Building multistage image "+mni[0]+" and tag it as "+mni[1], file=fd)
      build=dockerClientLL.build(tag=mni[1], target=mni[0],
                                 **createTarContext(path=path, dockerfile=dockerfile), **kwargs, **extraArgs)
      ret=syncLogBuildImage(build, fd)
      if ret!=0:
        return ret
  build=dockerClientLL.build(tag=tag, **createTarContext(path=path, dockerfile=dockerfile), **kwargs, **extraArgs)
  return syncLogBuildImage(build, fd)

def build(s, jobs=psutil.cpu_count(False), fd=sys.stdout, baseDir=scriptdir, cacheFromSelf=False):

  if s=="database":
    gitCommitID=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=baseDir).decode("UTF-8").rstrip()
    return buildImage(tag="mbsimenv/database:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      labels={"gitCommitID": gitCommitID},
      path=baseDir+"/..",
      dockerfile="docker/databaseImage/Dockerfile",
      rm=False)

  if s=="filestorage":
    return buildImage(tag="mbsimenv/filestorage:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/filestorageImage/Dockerfile",
      rm=False)

  if s=="build":
    return buildImage(tag="mbsimenv/build:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/buildImage/Dockerfile",
      rm=False)

  elif s=="proxy":
    return buildImage(tag="mbsimenv/proxy:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/proxyImage",
      rm=False)

  elif s=="buildwin64":
    return buildImage(tag="mbsimenv/buildwin64:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/buildwin64Image/Dockerfile",
      rm=False)

  elif s=="buildmsys2ucrt64":
    return buildImage(tag="mbsimenv/buildmsys2ucrt64:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"JOBS": str(jobs), "MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/buildmsys2ucrt64Image/Dockerfile",
      rm=False)

  elif s=="builddoc":
    return buildImage(tag="mbsimenv/builddoc:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/builddocImage/Dockerfile",
      rm=False)

  elif s=="builddocker":
    return buildImage(tag="mbsimenv/builddocker:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/builddockerImage/Dockerfile",
      rm=False)

  elif s=="webserver":
    return buildImage(tag="mbsimenv/webserver:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir+"/..",
      dockerfile="docker/webserverImage/Dockerfile",
      rm=False)

  elif s=="webapp":
    return buildImage(tag="mbsimenv/webapp:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
      buildargs={"MBSIMENVTAGNAME": getTagname()},
      path=baseDir,
      dockerfile="webappImage/Dockerfile",
      rm=False)

  elif s=="webapprun":
    return buildImage(tag="mbsimenv/webapprun:"+getTagname(), fd=fd, cacheFromSelf=cacheFromSelf,
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

def renameStoppedContainer(name):
  try:
    c=dockerClient.containers.get(name+getTagname())
    if c.status=="exited" or c.status=="dead" or c.status=="created" or c.status=="removing":
      c.rename(uuid.uuid4().hex)
  except docker.errors.NotFound:
    pass

def runAutobuild(s, buildType, addCommand, jobs=psutil.cpu_count(False), interactive=False, enforceConfigure=False,
                 fmatvecBranch="master", hdf5serieBranch="master", openmbvBranch="master", mbsimBranch="master",
                 printLog=True, detach=False, buildConfig={}):
  stopDatabase=False
  if len(dockerClient.networks.list(names="mbsimenv_service_intern:"+getTagname()))==1 and \
     len(dockerClient.networks.list(names="mbsimenv_service_intern:"+getTagname()))==1 and \
     dockerClient.containers.get('mbsimenv.database.'+getTagname()) is not None and \
     dockerClient.containers.get('mbsimenv.database.'+getTagname()).status=="running":
    networki=dockerClient.networks.get("mbsimenv_service_intern:"+getTagname())
    networke=dockerClient.networks.get("mbsimenv_service_extern:"+getTagname())
    database=dockerClient.containers.get('mbsimenv.database.'+getTagname())
  else:
    if detach:
      raise RuntimeError("Cannot run with --detach")
    networki, networke, database=runNetworkAndDatabase(printLog, "")
    stopDatabase=True

  # build
  renameStoppedContainer('mbsimenv.build.'+buildType+'.')
  imageName=(buildConfig.get("buildwin64Image", "mbsimenv/buildwin64") if buildType.startswith("win64-") else buildConfig.get("buildImage", "mbsimenv/build"))+":"+getTagname()
  imageID=dockerClient.images.get(imageName).id
  build=dockerClient.containers.run(
    image=imageName,
    init=True, name='mbsimenv.build.'+buildType+'.'+getTagname(),
    network=networki.id,
    labels={"buildtype": buildType},
    entrypoint=None if not interactive else ["sleep", "infinity"],
    command=([ "--buildType", buildType, "-j", str(jobs),
               "--executor", '<span class="MBSIMENV_EXECUTOR_MBSIMENV">MBSim-Env</span>',
               "--fmatvecBranch", fmatvecBranch,
               "--hdf5serieBranch", hdf5serieBranch,
               "--openmbvBranch", openmbvBranch,
               "--mbsimBranch", mbsimBranch,
               "--buildConfig", json.dumps(buildConfig)]+\
             addCommand+(["--enforceConfigure"] if enforceConfigure else [])
            ) if not interactive else [],
    environment={"MBSIMENVSERVERNAME": getServername(), "MBSIMENVTAGNAME": getTagname(), "MBSIMENVIMAGEID": imageID},
    volumes={
      'mbsimenv_mbsim-'+buildType+"."+getTagname():  {"bind": "/mbsim-env",       "mode": "rw"},
      'mbsimenv_ccache.'+getTagname():               {"bind": "/mbsim-ccache",    "mode": "rw"},
      'mbsimenv_config.'+getTagname():               {"bind": "/mbsim-config",    "mode": "ro"},
    },
    detach=True, stdout=True, stderr=True)
  networki.disconnect(build)
  networki.connect(build)
  networke.connect(build)
  if interactive:
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
    if stopDatabase:
      database.stop()
    return ret

def runNetworkAndDatabase(printLog, daemon):
  # networks (try to remove existing ones. if this fails and none except builddocker is connected reuse it
  for nn in ["mbsimenv_service_extern", "mbsimenv_service_intern"]:
    n=None
    try:
      n=dockerClient.networks.get(nn+":"+getTagname())
      try:
        n.remove()
        n=None
      except docker.errors.APIError:
        if any(map(lambda c: c.name!="mbsimenv.builddocker."+getTagname(), n.containers)):
          raise RuntimeError("Network "+nn+" exists but cannot be removed since containers other than builddocker are connected: "+
                             ", ".join(map(lambda c: c.name, n.containers)))
    except docker.errors.NotFound:
      pass
    if nn=="mbsimenv_service_extern":
      networke=n if n is not None else dockerClient.networks.create(name="mbsimenv_service_extern:"+getTagname())
    if nn=="mbsimenv_service_intern":
      networki=n if n is not None else dockerClient.networks.create(name="mbsimenv_service_intern:"+getTagname(), internal=True)

  # port binding
  ports={5432: []}
  for ip in getServerIP():
    ports[5432].append((ip, args.databasePort))
  if getServername()=="wwwstaging.mbsim-env.de": # special handling for external docker builds which cannot use ipv6 only staging ip address
    ports[5432].append(("www.mbsim-env.de", 15432))

  # database
  renameStoppedContainer('mbsimenv.database.')
  databaseImage=dockerClient.images.get("mbsimenv/database:"+getTagname())
  volumes={
    'mbsimenv_config.'+getTagname():                      {"bind": "/mbsim-config", "mode": "ro"},
    'mbsimenv_database.'+getTagname():                    {"bind": "/database",     "mode": "rw"},
  }
  if not args.noSSL:
    volumes['mbsimenv_letsencrypt.'+getTagname()]=        {"bind": "/sslconfig",    "mode": "ro"}
  database=dockerClient.containers.run(image="mbsimenv/database:"+getTagname(),
    init=True, name='mbsimenv.database.'+getTagname(),
    hostname="database", # reverse DNS must work for "database"
    network=networki.id,
    command=(["--noSSL"] if args.noSSL else [])+\
            ["--dockerSubnet", networki.attrs["IPAM"]["Config"][0]["Subnet"], networke.attrs["IPAM"]["Config"][0]["Subnet"]],
    environment={"MBSIMENVSERVERNAME": getServername(), "GITCOMMITID": databaseImage.labels["gitCommitID"], "IMAGEID": databaseImage.id},
    volumes=volumes,
    ports=ports,
    detach=True, stdout=True, stderr=True)
  networki.disconnect(database)
  networki.connect(database, aliases=["database"])
  networke.connect(database)
  if not printLog:
    print("Started running "+s+" as container ID "+database.id)
    sys.stdout.flush()
  runningContainers.add(database)
  if printLog:
    if daemon=="":
      asyncLogContainer(database, "database: ")
    else:
      print("Started database in background")
  return networki, networke, database

def run(s, jobs=psutil.cpu_count(False),
        addCommands=[],
        interactive=False,
        enforceConfigure=False,
        fmatvecBranch="master", hdf5serieBranch="master", openmbvBranch="master", mbsimBranch="master",
        builddockerBranch="master", keepBuildDockerContainerRunning=False,
        networkID=None, hostname=None,
        wait=True, printLog=True, detach=False, daemon="", buildConfig={}):

  if detach and interactive:
    raise RuntimeError("Cannot run detached an interactively.")

  if s=="build-linux64-ci":
    return runAutobuild(s, "linux64-ci", addCommands, jobs=jobs, interactive=interactive, enforceConfigure=enforceConfigure,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, buildConfig=buildConfig)

  elif s=="build-win64-ci":
    return runAutobuild(s, "win64-ci", addCommands, jobs=jobs, interactive=interactive, enforceConfigure=enforceConfigure,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, buildConfig=buildConfig)

  elif s.startswith("build-linux64-dailydebug"):
    buildTypeSuffix=s[len("build-linux64-dailydebug"):]
    return runAutobuild(s, "linux64-dailydebug"+buildTypeSuffix, ["--valgrindExamples"]+addCommands,
                 jobs=jobs, interactive=interactive, enforceConfigure=enforceConfigure,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, buildConfig=buildConfig)

  elif s.startswith("build-linux64-dailyrelease"):
    buildTypeSuffix=s[len("build-linux64-dailyrelease"):]
    return runAutobuild(s, "linux64-dailyrelease"+buildTypeSuffix, addCommands,
                 jobs=jobs, interactive=interactive, enforceConfigure=enforceConfigure,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, buildConfig=buildConfig)

  elif s.startswith("build-win64-dailyrelease"):
    buildTypeSuffix=s[len("build-win64-dailyrelease"):]
    return runAutobuild(s, "win64-dailyrelease"+buildTypeSuffix, addCommands, jobs=jobs,
                 interactive=interactive, enforceConfigure=enforceConfigure,
                 fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                 printLog=printLog, detach=detach, buildConfig=buildConfig)

  elif s=="builddoc":
    stopDatabase=False
    if len(dockerClient.networks.list(names="mbsimenv_service_intern:"+getTagname()))==1:
      networki=dockerClient.networks.get("mbsimenv_service_intern:"+getTagname())
      networke=dockerClient.networks.get("mbsimenv_service_extern:"+getTagname())
      database=dockerClient.containers.get('mbsimenv.database.'+getTagname())
    else:
      if detach:
        raise RuntimeError("Cannot run with --detach")
      networki, networke, database=runNetworkAndDatabase(printLog, "")
      stopDatabase=True

    # build
    renameStoppedContainer('mbsimenv.builddoc.')
    builddoc=dockerClient.containers.run(image="mbsimenv/builddoc:"+getTagname(),
      init=True, name='mbsimenv.builddoc.'+getTagname(),
      network=networki.id,
      entrypoint=None if not interactive else ["sleep", "infinity"],
      environment={"MBSIMENVSERVERNAME": getServername(), "MBSIMENVTAGNAME": getTagname()},
      volumes={
        'mbsimenv_mbsim-linux64-dailydebug.'+getTagname():  {"bind": "/mbsim-env",       "mode": "rw"},
        'mbsimenv_config.'+getTagname():                    {"bind": "/mbsim-config",    "mode": "ro"},
      },
      detach=True, stdout=True, stderr=True)
    networki.disconnect(builddoc)
    networki.connect(builddoc)
    networke.connect(builddoc)
    if interactive:
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
      if stopDatabase:
        database.stop()
      return ret

  elif s=="builddocker":
    stopDatabase=False
    if len(dockerClient.networks.list(names="mbsimenv_service_intern:"+getTagname()))==1:
      networki=dockerClient.networks.get("mbsimenv_service_intern:"+getTagname())
      networke=dockerClient.networks.get("mbsimenv_service_extern:"+getTagname())
      database=dockerClient.containers.get('mbsimenv.database.'+getTagname())
    else:
      if detach:
        raise RuntimeError("Cannot run with --detach")
      networki, networke, database=runNetworkAndDatabase(printLog, "")
      stopDatabase=True

    # build
    renameStoppedContainer('mbsimenv.builddocker.')
    builddocker=dockerClient.containers.run(image="mbsimenv/builddocker:"+getTagname(),
      init=True, name='mbsimenv.builddocker.'+getTagname(),
      network=networki.id,
      entrypoint=None if not interactive else ["sleep", "infinity"],
      environment={"MBSIMENVSERVERNAME": getServername(), "MBSIMENVTAGNAME": getTagname()},
      command=["-j", str(jobs), builddockerBranch],
      volumes={
        'mbsimenv_mbsim-builddocker.'+getTagname():  {"bind": "/mbsim-env",           "mode": "rw"},
        '/var/run/docker.sock':                      {"bind": "/var/run/docker.sock", "mode": "rw"},
        'mbsimenv_config.'+getTagname():             {"bind": "/mbsim-config",        "mode": "ro"},
      },
      detach=True, stdout=True, stderr=True)
    networki.disconnect(builddocker)
    networki.connect(builddocker)
    networke.connect(builddocker)
    if interactive:
      print("Use")
      print("docker exec -ti %s bash"%(builddocker.short_id))
      print("to attach to this container")
    if not printLog:
      print("Started running "+s+" as container ID "+builddocker.id)
      sys.stdout.flush()
    if not detach:
      runningContainers.add(builddocker)
    if printLog:
      asyncLogContainer(builddocker)

    # wait for running containers
    if detach:
      return builddocker
    else:
      ret=runWait([builddocker], printLog=printLog)
      if stopDatabase:
        database.stop()
      return ret

  elif s=="service":
    getServername() # just to fail early if the envvar is not set
    if detach==True:
      raise RuntimeError("Cannot run service detached.")

    if daemon=="stop":
      print("Stopping of mbsim-env "+getTagname())
      for c in dockerClient.containers.list(filters={"label": 'mbsimenv.webapprun.'+getTagname()}):
        if c.status=="created":
          c.remove()
        if c.status!="exited" and c.status!="dead":
          c.stop()
          print("Container mbsimenv/webapprun:"+getTagname()+" "+c.name+" stopped (id="+c.id+")")
      for cn in list(map(lambda x: 'mbsimenv.build.'+x+'.', buildTypes))+['mbsimenv.builddoc.',
                 'mbsimenv.proxy.', 'mbsimenv.webapp.', 'mbsimenv.webserver.', 'mbsimenv.filestorage.', 'mbsimenv.database.']+\
                 (['mbsimenv.builddocker.'] if not keepBuildDockerContainerRunning else []):
        try:
          c=dockerClient.containers.get(cn+getTagname())
          if c.status=="created":
            c.remove()
            print("Container "+cn+getTagname()+" removed (id="+c.id+")")
          if c.status!="exited" and c.status!="dead":
            c.stop()
            print("Container "+cn+getTagname()+" stopped (id="+c.id+")")
        except docker.errors.NotFound:
          print("Container "+cn+getTagname()+" cannot be stopped")
      for n in dockerClient.networks.list(names=["mbsimenv_service_extern:"+getTagname(), "mbsimenv_service_intern:"+getTagname()]):
        try:
          n.remove()
          print("Network "+n.name+" removed (id="+n.id+")")
        except docker.errors.APIError:
          print("Network "+n.name+" cannot be removed (id="+n.id+")")
      return 0

    if daemon=="status":
      print("Status of mbsim-env "+getTagname())
      for c in dockerClient.containers.list(filters={"label": 'mbsimenv.webapprun.'+getTagname()}):
        if c.status!="exited" and c.status!="dead":
          print("Container mbsimenv/webapprun:"+getTagname()+" "+c.name+" is "+c.status+" (id="+c.id+")")
      for cn in list(map(lambda x: 'mbsimenv.build.'+x+'.', buildTypes))+['mbsimenv.builddoc.', 'mbsimenv.builddocker.',
                 'mbsimenv.proxy.', 'mbsimenv.webapp.', 'mbsimenv.webserver.', 'mbsimenv.filestorage.', 'mbsimenv.database.']:
        try:
          c=dockerClient.containers.get(cn+getTagname())
          if c.status!="exited" and c.status!="dead":
            print("Container "+cn+getTagname()+" is "+c.status+" (id="+c.id+")")
        except docker.errors.NotFound:
          pass
      for n in dockerClient.networks.list(names=["mbsimenv_service_extern:"+getTagname(), "mbsimenv_service_intern"+getTagname()]):
        print("Network "+n.name+" exists (id="+n.id+")")
      return 0

    # port binding
    ports={80: []}
    if not args.noSSL:
      ports[443]=[]
    for ip in getServerIP():
      ports[80].append((ip, args.httpPort))
      if not args.noSSL:
        ports[443].append((ip, args.httpsPort))
    if getServername()=="wwwstaging.mbsim-env.de": # special handling for external docker builds which cannot use ipv6 only staging ip address
      ports[80].append(("www.mbsim-env.de", 10080))
      ports[443].append(("www.mbsim-env.de", 10443))

    networki, networke, database=runNetworkAndDatabase(printLog, daemon)

    # webserver
    renameStoppedContainer('mbsimenv.webserver.')
    volumes={
      'mbsimenv_config.'+getTagname():                      {"bind": "/mbsim-config",        "mode": "ro"},
      'mbsimenv_webserverstatic.'+getTagname():             {"bind": "/webserverstatic",     "mode": "ro"}, # xmldoc and doxydoc
      '/var/run/docker.sock':                               {"bind": "/var/run/docker.sock", "mode": "rw"},
    }
    if not args.noSSL:
      volumes['mbsimenv_letsencrypt.'+getTagname()]=        {"bind": "/etc/letsencrypt",     "mode": "rw"}
    environment={"MBSIMENVSERVERNAME": getServername(), "MBSIMENVTAGNAME": getTagname()}
    if "MBSIMENVDEBUG" in os.environ:
      environment["MBSIMENVDEBUG"]="1"
    webserver=dockerClient.containers.run(image="mbsimenv/webserver:"+getTagname(),
      init=True, name='mbsimenv.webserver.'+getTagname(),
      network=networki.id,
      command=["-j", str(jobs), "--buildConfig", json.dumps(buildConfig)]+\
              (["--noSSL"] if args.noSSL else [])+\
              (["--cronBuilds"] if args.cronBuilds else [])+\
              addCommands,
      environment=environment,
      volumes=volumes,
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
    renameStoppedContainer('mbsimenv.webapp.')
    webapp=dockerClient.containers.run(image="mbsimenv/webapp:"+getTagname(),
      init=True, name='mbsimenv.webapp.'+getTagname(),
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
    renameStoppedContainer('mbsimenv.proxy.')
    proxy=dockerClient.containers.run(image="mbsimenv/proxy:"+getTagname(),
      init=True, name='mbsimenv.proxy.'+getTagname(),
      network=networki.id,
      # allow access to these sites
      command=["www\\.mbsim-env\\.de\n"+
               "webserver\n"+ # docker hostname for the webserver container
               "github\\.com\n"+
               "cdn\\.jsdelivr\\.net\n"+
               "code\\.highcharts\\.com\n"+
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

    # filestorage

    # port binding
    ports={1122: []}
    for ip in getServerIP():
      ports[1122].append((ip, args.filestoragePort))
    if getServername()=="wwwstaging.mbsim-env.de": # special handling for external docker builds which cannot use ipv6 only staging ip address
      ports[1122].append(("www.mbsim-env.de", 11122))

    renameStoppedContainer('mbsimenv.filestorage.')
    filestorage=dockerClient.containers.run(image="mbsimenv/filestorage:"+getTagname(),
      init=True, name='mbsimenv.filestorage.'+getTagname(),
      network=networki.id,
      ports=ports,
      volumes={
        'mbsimenv_config.'+getTagname():                      {"bind": "/mbsim-config",         "mode": "ro"},
        'mbsimenv_databasemedia.'+getTagname():               {"bind": "/data/databasemedia",   "mode": "rw"}, # django DB files
        'mbsimenv_webserverstatic.'+getTagname():             {"bind": "/data/webserverstatic", "mode": "rw"}, # xmldoc and doxydoc
      },
      detach=True, stdout=True, stderr=True)
    networki.disconnect(filestorage)
    networki.connect(filestorage, aliases=["filestorage"])
    networke.connect(filestorage)
    if not printLog:
      print("Started running "+s+" as container ID "+filestorage.id)
      sys.stdout.flush()
    runningContainers.add(filestorage)
    if printLog:
      if daemon=="":
        asyncLogContainer(filestorage, "filestorage: ")
      else:
        print("Started filestorage in background")

    if daemon=="start":
      print("mbsim-env "+getTagname()+" started")
      return 0
    else:
      # wait for running containers
      ret=runWait([filestorage, database, webserver, webapp, proxy], printLog=printLog)
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
    if networkID is None:
      raise RuntimeError("Option --networkID is required.")
    if hostname is None:
      raise RuntimeError("Option --hostname is required.")
    if detach==True:
      raise RuntimeError("Cannot run webapprun detached.")
    networki=dockerClient.networks.get(networkID)
    webapprun=dockerClient.containers.run(image="mbsimenv/webapprun:"+getTagname(),
      init=True, labels=['mbsimenv.webapprun.'+getTagname()],
      network=networki.id,
      command=addCommands,
      environment={"MBSIMENVTAGNAME": getTagname()},
      volumes={
        'mbsimenv_webapprun.'+getTagname(): {"bind": "/mbsim-env", "mode": "rw"},
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

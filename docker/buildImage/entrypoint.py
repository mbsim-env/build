#!/usr/bin/env python3

# imports
import argparse
import os
import subprocess
import sys
import datetime
import codecs
import json
import re
import time
import glob
import django
import hashlib
sys.path.append("/context/mbsimenv")
import runexamples
import service
import base
import psutil

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/build.")
  
argparser.add_argument("--buildType", type=str, required=True, help="The build type")
argparser.add_argument("--executor", type=str, required=True, help="The executor of this build")
argparser.add_argument("--enforceConfigure", action="store_true", help="Enforce the configure step")
argparser.add_argument("--fmatvecBranch", type=str, default="master", help="fmatvec branch")
argparser.add_argument("--hdf5serieBranch", type=str, default="master", help="hdf5serie branch")
argparser.add_argument("--openmbvBranch", type=str, default="master", help="openmbv branch")
argparser.add_argument("--mbsimBranch", type=str, default="master", help="mbsim branch")
argparser.add_argument("--jobs", "-j", type=int, default=psutil.cpu_count(False), help="Number of jobs to run in parallel")
argparser.add_argument('--forceBuild', action="store_true", help="Passed to buily.py if existing")
argparser.add_argument("--valgrindExamples", action="store_true", help="Run examples also with valgrind.")
argparser.add_argument("--ccacheSize", default=10, type=int, help="Maximal ccache size in GB.")
argparser.add_argument("--disableRunExamples", action="store_true", help="Do not run examples")
argparser.add_argument("--buildConfig", type=json.loads, default={}, help="Load an additional build(/examples) configuration as json string")

runExamplesGroup=argparser.add_mutually_exclusive_group()
runExamplesGroup.add_argument("--runExamplesPre", action="store_true", help="Init a partitioned runExamples run")
runExamplesGroup.add_argument("--runExamplesPartition", action="store_true", help="Run a partitioned runExamples run")
runExamplesGroup.add_argument("--runExamplesPost", action="store_true", help="Finalize a partitioned runExamples run")
argparser.add_argument("--buildRunID", default=None, type=int, help="The id of the builds.model.Run dataset this example run belongs to.")
argparser.add_argument("--runID", default=None, type=int, help="The id of the runexamples.model.Run dataset this example run belongs to.")

args=argparser.parse_args()
build=not args.runExamplesPre and not args.runExamplesPartition and not args.runExamplesPost

ret=0

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")
if "MBSIMENVTAGNAME" not in os.environ or os.environ["MBSIMENVTAGNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVTAGNAME is not defined.")

# check buildtype
if args.buildType != "linux64-ci" and not args.buildType.startswith("linux64-dailydebug") and \
   not args.buildType.startswith("linux64-dailyrelease"):
  raise RuntimeError("Unknown build type "+args.buildType+".")

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
django.setup()

# wait for database server
while True:
  try:
    django.db.connections['default'].cursor()
    break
  except django.db.utils.OperationalError:
    print("Waiting for database to startup. Retry in 0.5s")
    time.sleep(0.5)
django.db.connections.close_all()

# run

if build:
  # clone repos if needed
  for repo in [
                "https://github.com/mbsim-env/fmatvec.git",
                "https://github.com/mbsim-env/hdf5serie.git",
                "https://github.com/mbsim-env/openmbv.git",
                "https://github.com/mbsim-env/mbsim.git",
              ]+args.buildConfig.get("buildRepos", [])+args.buildConfig.get("exampleRepos", []):
    localDir=repo.split("/")[-1][0:-4]
    if not os.path.isdir("/mbsim-env/"+localDir):
      subprocess.check_call(["git", "clone", "-q", "--depth", "1", repo], cwd="/mbsim-env",
        stdout=sys.stdout, stderr=sys.stderr)

# compile flags
if args.buildType == "linux64-ci" or args.buildType.startswith("linux64-dailydebug"):
  BUILDTYPE="Debug"
  os.environ["CXXFLAGS"]="-O0 -g"
  os.environ["CFLAGS"]="-O0 -g"
  os.environ["FFLAGS"]="-O0 -g"
elif args.buildType.startswith("linux64-dailyrelease"):
  BUILDTYPE="Release"
  os.environ["CXXFLAGS"]="-g -O2 -DNDEBUG"
  os.environ["CFLAGS"]="-g -O2 -DNDEBUG"
  os.environ["FFLAGS"]="-g -O2 -DNDEBUG"
else:
  raise RuntimeError("Unknown build type "+args.buildType)

def isMaster(branch):
  return branch=="master" or branch.startswith("master*")

if build:
  # args
  if args.buildType == "linux64-ci":
    ARGS=["--disableDoxygen", "--disableXMLDoc"]
    RUNEXAMPLESARGS=["--disableMakeClean", "--checkGUIs"]
    RUNEXAMPLESFILTER=["--filter", "'basic' in labels"]
  
    # get current/last image ID
    curImageID=os.environ.get("MBSIMENVIMAGEID", None)
    if curImageID is not None:
      info=service.models.Info.objects.all().first()
      lastImageID=info.buildImageID if info is not None else ""
      # configure needed?
      if lastImageID==curImageID and not args.enforceConfigure:
        ARGS.append("--disableConfigure")
      # save build image id
      info.buildImageID=curImageID
      info.save()
  elif args.buildType.startswith("linux64-dailydebug"):
    ARGS=["--coverage", "--enableDistribution"]
    RUNEXAMPLESARGS=["--checkGUIs"]
    RUNEXAMPLESFILTER=(["--filter", "'basic' in labels"] \
      if os.environ["MBSIMENVTAGNAME"]=="staging" or \
         not isMaster(args.fmatvecBranch) or not isMaster(args.hdf5serieBranch) or not isMaster(args.openmbvBranch) or not isMaster(args.mbsimBranch) \
         else ["--filter", "'nightly' in labels"])
  elif args.buildType.startswith("linux64-dailyrelease"):
    ARGS=["--enableDistribution"]
    RUNEXAMPLESARGS=["--disableCompare", "--disableValidate", "--checkGUIs"]
    RUNEXAMPLESFILTER=["--filter", "'basic' in labels"]
  
  # pass arguments to build.py
  if args.forceBuild:
    ARGS.append('--forceBuild')

# env
os.environ['PKG_CONFIG_PATH']=((os.environ['PKG_CONFIG_PATH']+":") if 'PKG_CONFIG_PATH' in os.environ else "")+\
                              "/mbsim-env/local/lib/pkgconfig:/mbsim-env/local/lib64/pkgconfig"

subprocess.call(["ccache", "-M", str(args.ccacheSize)+"G"])

if build or args.runExamplesPre:
  # update references of examples
  if args.buildType=="linux64-dailydebug" and \
     isMaster(args.fmatvecBranch) and isMaster(args.hdf5serieBranch) and \
     isMaster(args.openmbvBranch) and isMaster(args.mbsimBranch):
    runCur=runexamples.models.Run.objects.filter(buildType=args.buildType,
                                                       build_run__fmatvecBranch="master", build_run__hdf5serieBranch="master",
                                                       build_run__openmbvBranch="master", build_run__mbsimBranch="master").\
                                          order_by("-startTime").first()
    if runCur is not None:
      for exStatic in runexamples.models.ExampleStatic.objects.filter(update=True):
        print("Updating example "+exStatic.exampleName+" with example runID="+str(runCur.id))
        exCur=runCur.examples.get(exampleName=exStatic.exampleName)
        if exCur is None:
          continue
        # delete references not in current
        keepFilename=[]
        rfCurs=exCur.resultFiles.all()
        for rfCur in rfCurs:
          if rfCur.h5FileName is None:
            firstRes=rfCur.results.all().first()
            if firstRes is None or firstRes.result!=runexamples.models.CompareResult.Result.FILENOTINCUR:
              keepFilename.append(rfCur.h5Filename)
        delete=[]
        for rfStatic in exStatic.references.all():
          if rfStatic.h5FileName not in keepFilename:
            delete.append(rfStatic)
        exStatic.references.filter(id__in=[d.id for d in delete]).delete()
        # add/update new references
        for rfCur in rfCurs:
          if rfCur.h5FileName is None: # if nothing is different in a file the file is even not stored in rfCur! -> skip this rfCur
            continue
          ref=runexamples.models.ExampleStaticReference()
          ref.exampleStatic=exStatic
          ref.h5FileName=rfCur.h5FileName
          with rfCur.h5File.open("rb") as fi:
            with ref.h5File.open("wb") as fo:
              ref.h5FileSHA1=base.helper.copyFile(fi, fo, returnSHA1HexDigest=True)
          ref.save()
        # set ref time
        exStatic.refTime=exCur.time
        # clear update flag
        exStatic.update=False
        exStatic.save()
        # force a new build if an example has been updated
        if "--forceBuild" not in ARGS:
          ARGS.append('--forceBuild')
  
if build:
  if args.disableRunExamples:
    ARGS.append("--disableRunExamples")
  
  print("Zeroing ccache statistics.")
  subprocess.call(["ccache", "-z"])

  if args.buildRunID is not None:
    ARGS.append("--buildRunID")
    ARGS.append(str(args.buildRunID))
  
  # run build
  os.environ["LDFLAGS"]="-L/usr/lib64/boost169" # use boost 1.69 libraries (and includes, see --with-boost-inc)
  localRet=subprocess.call(
    ["/context/mbsimenv/build.py"]+ARGS+[
    "--sourceDir", "/mbsim-env", "--binSuffix=-build", "--prefix", "/mbsim-env/local", "-j", str(args.jobs), "--buildSystemRun",
    "--fmatvecBranch", args.fmatvecBranch,
    "--hdf5serieBranch", args.hdf5serieBranch, "--openmbvBranch", args.openmbvBranch,
    "--mbsimBranch", args.mbsimBranch, "--enableCleanPrefix",
    "--buildType", args.buildType,
    "--executor", args.executor,
    "--buildConfig", args.buildConfig,
    "--passToConfigure", "--disable-static",
    "--enable-python", "--with-qwt-inc-prefix=/3rdparty/local/include", "--with-qwt-lib-prefix=/3rdparty/local/lib",
    "--with-boost-inc=/usr/include/boost169",
    "--with-hdf5-prefix=/3rdparty/local",
    "--with-mkoctfile=/3rdparty/local/bin/mkoctfile",
    "--with-qwt-lib-name=qwt", "--with-qmake=qmake-qt5", "COIN_CFLAGS=-I/3rdparty/local/include",
    "COIN_LIBS=-L/3rdparty/local/lib64 -lCoin", "SOQT_CFLAGS=-I/3rdparty/local/include",
    "SOQT_LIBS=-L/3rdparty/local/lib64 -lSoQt",
    "--passToCMake", "-DBOOST_INCLUDEDIR=/usr/include/boost169", "-DBOOST_LIBRARYDIR=/usr/lib64/boost169",
    "-DCMAKE_BUILD_TYPE="+BUILDTYPE,
    "-DCMAKE_CXX_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["CXXFLAGS"],
    "-DCMAKE_C_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["CFLAGS"],
    "-DCMAKE_Fortran_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["FFLAGS"],
    "-DARPACK_INCLUDE_DIRS=/3rdparty/local/include/arpack", "-DARPACK_LIBRARIES=/3rdparty/local/lib64/libarpack.so",
    "-DSPOOLES_INCLUDE_DIRS=/3rdparty/local/include/spooles", "-DSPOOLES_LIBRARIES=/3rdparty/local/lib/spooles.a",
    "-DBLAS_LIBRARIES=/usr/lib64/libopenblas.so.0", "-DLAPACK_LIBRARIES=/usr/lib64/libopenblas.so.0",
    "--passToRunexamples", "--buildType", args.buildType]+\
    RUNEXAMPLESARGS+RUNEXAMPLESFILTER,
    stdout=sys.stdout, stderr=sys.stderr)
  
  print("Dump ccache statistics:")
  subprocess.call(["ccache", "-s"])
  sys.stdout.flush()
  
  # read build info
  with open("/mbsim-env/local/.buildInfo.json", "r") as f:
    buildInfo=json.load(f)
  
  if localRet!=0:
    ret=ret+1
    print("build.py failed.")
    sys.stdout.flush()
  
  if args.valgrindExamples:
    # run examples with valgrind
  
    for repo in ["https://github.com/mbsim-env/mbsim.git"]+args.buildConfig.get("exampleRepos", []):
      localDir=repo.split("/")[-1][0:-4]
      if not os.path.isdir("/mbsim-env/"+localDir+"-valgrind"):
        subprocess.check_call(["git", "clone", "-q", "--depth", "1", repo], cwd="/mbsim-env",
          stdout=sys.stdout, stderr=sys.stderr)
    
    # update
    CURDIR=os.getcwd()
    os.chdir("/mbsim-env/mbsim-valgrind/examples")
  
    mbsimBranchSplit=args.mbsimBranch.split("*")
    sha=mbsimBranchSplit[1 if len(mbsimBranchSplit)>=2 and mbsimBranchSplit[1]!="" else 0]
    if subprocess.call(["git", "checkout", "-q", "HEAD~0"])!=0:
      ret=ret+1
      print("git checkout detached failed.")
    if subprocess.call(["git", "fetch", "-q", "--depth", "1", "origin", sha+":"+sha])!=0:
      ret=ret+1
      print("git fetch failed.")
    if subprocess.call(["git", "checkout", "-q", sha])!=0:
      ret=ret+1
      print("git checkout of branch "+args.mbsimBranch+" failed.")
    for repo in args.buildConfig.get("exampleRepos", []):
      localDir=repo.split("/")[-1][0:-4]
      os.chdir("/mbsim-env/"+localDir+"-valgrind")
      print('Update remote repository '+repo+":")
      if subprocess.call(["git", "checkout", "-q", "HEAD~0"])!=0:
        ret=ret+1
      if subprocess.call(["git", "fetch", "-q", "--depth", "1", "origin", "master:master"])!=0:
        ret=ret+1
      if subprocess.call(["git", "checkout", "-q", "master"])!=0:
        ret=ret+1
    sys.stdout.flush()
    valgrindEnv=os.environ.copy()
    valgrindEnv["MBSIM_SET_MINIMAL_TEND"]="1"
    valgrindEnv["HDF5SERIE_FIXAFTER"]=str(10*60*1000)#10min
    # build
    RUNEXAMPLESFILTER=(["--filter", "'basic' in labels"] \
      if os.environ["MBSIMENVTAGNAME"]=="staging" or
         not isMaster(args.fmatvecBranch) or not isMaster(args.hdf5serieBranch) or not isMaster(args.openmbvBranch) or not isMaster(args.mbsimBranch) \
         else ["--filter", "'nightly' in labels"])
    localRet=subprocess.call(["python3", "/context/mbsimenv/runexamples.py", "--checkGUIs", "--disableCompare", "--disableValidate", "--buildConfig", args.buildConfig,
      "--buildType", args.buildType+"-valgrind", "--executor", args.executor, "--buildSystemRun", "-j", str(args.jobs),
      "--buildRunID", str(buildInfo["buildRunID"])]+\
      (["--coverage", "--sourceDir", "/mbsim-env", "--binSuffix=-build", "--prefix", "/mbsim-env/local",
        "--baseExampleDir", "/mbsim-env/mbsim-valgrind/examples"] if "--coverage" in ARGS else [])+\
      ["--prefixSimulationKeyword=VALGRIND", "--prefixSimulation",
      "valgrind --trace-children=yes --trace-children-skip=*/rm,*/dbus-launch,*/ldconfig,*/sh "+\
      "--child-silent-after-fork=yes --num-callers=50 --gen-suppressions=all "+\
      "--suppressions=/mbsim-env/mbsim/thirdparty/valgrind/valgrind-mbsim.supp "+\
      "--suppressions=/mbsim-build/build/misc/valgrind-python.supp --leak-check=full"]+RUNEXAMPLESFILTER
      , env=valgrindEnv)
    if localRet!=0:
      ret=ret+1
      print("running examples with valgrind failed.")
      sys.stdout.flush()
    os.chdir(CURDIR)



def runExamplesPartition(ARGS, pullExampleRepos, pullAll):
  ret=0
  CURDIR=os.getcwd()

  repos=set()
  if pullExampleRepos:
    repos.add("https://github.com/mbsim-env/mbsim.git")
    repos.update(args.buildConfig.get("exampleRepos", []))
  if pullAll:
    repos.update(["https://github.com/mbsim-env/fmatvec.git",
                  "https://github.com/mbsim-env/hdf5serie.git",
                  "https://github.com/mbsim-env/openmbv.git",
                  "https://github.com/mbsim-env/mbsim.git"])
    repos.update(args.buildConfig.get("exampleRepos", []))
    repos.update(args.buildConfig.get("buildRepos", []))
  for repo in repos:
    localDir=repo.split("/")[-1][0:-4]
    # clone if needed
    if not os.path.isdir("/mbsim-env/"+localDir):
      subprocess.check_call(["git", "clone", "-q", "--depth", "1", repo, localDir], cwd="/mbsim-env",
        stdout=sys.stdout, stderr=sys.stderr)
    
    # update
    os.chdir("/mbsim-env/"+localDir)
    
    if localDir in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
      branch=getattr(args, localDir+"Branch")
    else:
      branch="master"
    branchSplit=branch.split("*")
    sha=branchSplit[1 if len(branchSplit)>=2 and branchSplit[1]!="" else 0]
    if subprocess.call(["git", "checkout", "-q", "HEAD~0"])!=0:
      ret=ret+1
      print("git checkout detached failed.")
    if subprocess.call(["git", "fetch", "-q", "--depth", "1", "origin", sha+":"+sha])!=0:
      ret=ret+1
      print("git fetch failed.")
    if subprocess.call(["git", "checkout", "-q", sha])!=0:
      ret=ret+1
      print("git checkout of branch "+branch+" failed.")
    sys.stdout.flush()

  os.makedirs("/mbsim-env/mbsim/examples", exist_ok=True)
  os.chdir("/mbsim-env/mbsim/examples")
  runexamplesEnv=os.environ.copy()
  if args.valgrindExamples:
    runexamplesEnv["MBSIM_SET_MINIMAL_TEND"]="1"
    runexamplesEnv["HDF5SERIE_FIXAFTER"]=str(10*60*1000)#10min
  # build
  RUNEXAMPLESFILTER=(["--filter", "'basic' in labels"] \
    if os.environ["MBSIMENVTAGNAME"]=="staging" or \
       not isMaster(args.fmatvecBranch) or not isMaster(args.hdf5serieBranch) or not isMaster(args.openmbvBranch) or not isMaster(args.mbsimBranch) \
       else ["--filter", "'nightly' in labels"])
  localRet=subprocess.call(["python3", "/context/mbsimenv/runexamples.py", "--checkGUIs",
    "--buildType", args.buildType+("-valgrind" if args.valgrindExamples else ""), "--executor", args.executor,
    "--buildSystemRun", "-j", str(args.jobs),
    "--buildRunID", str(args.buildRunID), "--runID", str(args.runID),
    "--coverage", "--sourceDir", "/mbsim-env", "--binSuffix=-build", "--prefix", "/mbsim-env/local", "--buildConfig", args.buildConfig,
    "--baseExampleDir", "/mbsim-env/mbsim/examples"]+\
    (["--disableCompare", "--disableValidate",
    "--prefixSimulationKeyword=VALGRIND", "--prefixSimulation",
    "valgrind --trace-children=yes --trace-children-skip=*/rm,*/dbus-launch,*/ldconfig,*/sh "+\
    "--child-silent-after-fork=yes --num-callers=50 --gen-suppressions=all "+\
    "--suppressions=/mbsim-env/mbsim/thirdparty/valgrind/valgrind-mbsim.supp "+\
    "--suppressions=/mbsim-build/build/misc/valgrind-python.supp --leak-check=full"] if args.valgrindExamples else [])+\
    ARGS+RUNEXAMPLESFILTER,
    env=runexamplesEnv)
  if localRet!=0:
    ret=ret+1
    print("running examples failed.")
    sys.stdout.flush()
  os.chdir(CURDIR)
  return ret

if args.runExamplesPre:
  ret+=runExamplesPartition(["--pre"], pullExampleRepos=True, pullAll=False)

if args.runExamplesPartition:
  ret+=runExamplesPartition(["--partition"], pullExampleRepos=True, pullAll=True)

if args.runExamplesPost:
  ret+=runExamplesPartition(["--post"], pullExampleRepos=True, pullAll=True)

sys.exit(ret)

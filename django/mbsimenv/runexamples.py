#!/usr/bin/env python3

# imports
import sys
import argparse
import fnmatch
import os
from os.path import join as pj
import subprocess
import datetime
import fileinput
import glob
import shutil
import functools
import multiprocessing
import psutil
import traceback
import re
import hashlib
import codecs
import time
import zipfile
import tempfile
import urllib.request
import urllib.parse
import django
import base.helper
import mbsimenvSecrets
import runexamples
import builds
import json
import io

if django.VERSION[0]!=3:
  print("Need django version 3. This is django version "+django.__version__)
  sys.exit(1)
import octicons
if not hasattr(octicons, '__version__') or hasattr(octicons, 'default_app_config'):
  print("The Python module 'octicons' seems not to be the correct 'django-octicons' package!")
  if hasattr(octicons, 'default_app_config'):
    print("It seems to be the 'octicons' package.")
  print("Please ensure that you have installed the package 'django-octicons' not 'octicons' or any other.")
  print("These two packages provide the same Pyhton module 'octicons' and cannot be installed at the same time.")
  sys.exit(1)

# global variables (all these must be handled special before multiprocessing worker start and in runExample(...), runExampleOuter(...))
mbsimBinDir=None
canCompare=True # True if numpy and h5py are found
mbxmlutilsvalidate=None
xmlCatalog=None
displayNR=None
directories=list() # a list of all examples sorted in descending order (filled recursively (using the filter) by --directories)

# MBSim Modules
mbsimModules=["mbsimControl", "mbsimElectronics", "mbsimFlexibleBody",
              "mbsimHydraulics", "mbsimInterface", "mbsimPowertrain"]

# command line option definition
argparser = argparse.ArgumentParser(
  formatter_class=argparse.RawTextHelpFormatter,
  description='''
Run MBSim examples.
This script runs the action given by --action on all specified directories recursively.
However only examples of the type matching --filter are executed. The specified directories are
processed from left to right.
The type of an example is defined dependent on some key files in the corrosponding example directory:
- If a file named 'Makefile' exists, than it is treated as a SRC example.
- If a file named '*.flat.mbsx' exists, then it is treated as a FLATXML example.
- If a file named '*.mbsx' exists, then it is treated as a XML example (if its not a *.flat.xml, FMI.mbsx or FMI_cosim.mbsx file)
  which run throught the MBXMLUtils preprocessor first.
- If a file named 'FMI.mbsx' exists, then it is treated as a FMI ME XML export example. Beside running the file
  by mbsimxml also mbsimCreateFMU is run to export the model as a FMU and the FMU is run by fmuCheck.<PLATFORM>.
- If a file named 'Makefile_FMI' exists, then it is treated as a FMI ME source export example. Beside compiling the
  source examples also mbsimCreateFMU is run to export the model as a FMU and the FMU is run by fmuCheck.<PLATFORM>.
- If a file named 'FMI_cosim.mbsx' exists, then it is treated as a FMI Cosim XML export example. Beside running the file
  by mbsimxml also mbsimCreateFMU is run to export the model as a FMU and the FMU is run by fmuCheck.<PLATFORM>.
- If a file named 'Makefile_FMI_cosim' exists, then it is treated as a FMI Cosim source export example. Beside compiling the
  source examples also mbsimCreateFMU is run to export the model as a FMU and the FMU is run by fmuCheck.<PLATFORM>.
If more then one of these files exist the behaviour is undefined.
The 'Makefile' of a SRC example must build the example and must create an executable named 'main'.
'''
)

mainOpts=argparser.add_argument_group('Main Options')
mainOpts.add_argument("directories", nargs="*", default=[],
  help="A directory to run (recursively). If prefixed with '^' remove the directory form the current list [default: %(default)s]")
mainOpts.add_argument("--action", default="report", type=str,
  help='''The action of this script: [default: %(default)s]
- 'report'          Run examples and report results
- 'copyToReference' Copy results in current directories to reference
- 'updateReference' Update references from build system
- 'list'            List directories to be run''')
mainOpts.add_argument("-j", default=psutil.cpu_count(False), type=int,
  help="Number of jobs to run in parallel (applies only to the action 'report') [default: %(default)s]")
mainOpts.add_argument("--filter", default="'basic' in labels", type=str,
  help='''Filter the specifed directories using the given Python code. If not given all directories with the
label 'basic' are used [default: %(default)s]
A directory is processed if the provided Python code evaluates to True where the following variables are defined:
- src      Is True if the directory is a source code example
- flatxml  Is True if the directory is a xml flat example
- ppxml    Is True if the directory is a preprocessing xml example
- xml      Is True if the directory is a flat or preprocessing xml example
- fmi      Is True if the directory is a FMI export example (source or XML)
- labels   A list of labels (defined by the 'labels' file, being a space separated list of labels).
           The labels defined in the 'labels' file are extended automatically by the MBSim module
           labels: '''+str(mbsimModules)+'''
           The special label 'willfail' defines examples which are not reported as errors if they fail.
           If no labels file exists in a directory a labels file with the content "nightly" is assumed.
Example: --filter "xml and 'mbsimControl' not in labels or 'basic' in labels"
         run xml examples not requiring mbsimControl or all examples having the label "basic"''')

cfgOpts=argparser.add_argument_group('Configuration Options')
cfgOpts.add_argument("--atol", default=2e-5, type=float,
  help="Absolute tolerance. Channel comparing failed if for at least ONE datapoint the abs. AND rel. toleranz is violated [default: %(default)s]")
cfgOpts.add_argument("--rtol", default=2e-5, type=float,
  help="Relative tolerance. Channel comparing failed if for at least ONE datapoint the abs. AND rel. toleranz is violated [default: %(default)s]")
cfgOpts.add_argument("--disableRun", action="store_true", help="disable running the example on action 'report'")
cfgOpts.add_argument("--disableMakeClean", action="store_true", help="disable make clean on action 'report'")
cfgOpts.add_argument("--checkGUIs", action="store_true", help="Try to check/start the GUIs and exit after a short time.")
cfgOpts.add_argument("--disableCompare", action="store_true", help="disable comparing the results on action 'report'")
cfgOpts.add_argument("--disableValidate", action="store_true", help="disable validating the XML files on action 'report'")
cfgOpts.add_argument("--printToConsole", action='store_const', const=sys.stdout, help="print all output also to the console")
cfgOpts.add_argument("--buildType", default="local", type=str, help="Description of the build type (e.g: linux64-dailydebug) [default: %(default)s]")
cfgOpts.add_argument("--executor", default='<span class="MBSIMENV_EXECUTOR_LOCAL">local</span>', type=str, help="The executor of this run (can contain simple HTML a-elements)")
cfgOpts.add_argument("--prefixSimulation", default=[], type=lambda x: x.split(" "),
  help="prefix the simulation command (./main, mbsimflatxml, mbsimxml) with this string: e.g. 'valgrind --tool=callgrind'")
cfgOpts.add_argument("--prefixSimulationKeyword", default=None, type=str,
  help="VALGRIND: add special arguments and handling for valgrind")
cfgOpts.add_argument("--exeExt", default="", type=str, help="File extension of cross compiled executables (wine is used if set)")
cfgOpts.add_argument("--maxExecutionTime", default=30, type=float, help="The time in minutes after started program timed out [default: %(default)s]")
cfgOpts.add_argument("--coverage", action="store_true", help='Enable coverage analyzis using gcov/lcov')
cfgOpts.add_argument("--sourceDir", default=None, type=str, help='[needed by coverage and valgrind]')
cfgOpts.add_argument("--binSuffix", default="", type=str, help='[needed by coverage]')
cfgOpts.add_argument("--prefix", default=None, type=str, help='Used to extend PKG_CONFIG_PATH and [needed by coverage and valgrind]')
cfgOpts.add_argument("--baseExampleDir", default=None, type=str, help='[needed by coverage]')
cfgOpts.add_argument("--buildSystemRun", action="store_true", help='Run in build system mode.')
cfgOpts.add_argument("--localServerPort", type=int, default=27583, help='Port for local server, if started automatically.')
cfgOpts.add_argument("--updateURL", type=str, default="https://www.mbsim-env.de", help='Base url of server used to pull references.')
cfgOpts.add_argument("--buildConfig", type=json.loads, default={}, help="Load an additional build(/examples) configuration as json string")

outOpts=argparser.add_argument_group('Output Options')
outOpts.add_argument("--removeOlderThan", default=3 if os.environ.get("MBSIMENVTAGNAME", "")=="staging" else 30,
                     type=int, help="Remove all examples reports older than X days but keep at least the last X.")

debugOpts=argparser.add_argument_group('Debugging and other Options')
debugOpts.add_argument("--debugDisableMultiprocessing", action="store_true",
  help="disable the -j option and run always in a single process/thread")
debugOpts.add_argument("--buildRunID", default=None, type=int, help="The id of the builds.model.Run dataset this example run belongs to.")

partitionGroup=argparser.add_mutually_exclusive_group()
partitionGroup.add_argument("--pre", action="store_true", help="Init a partitioned runExamples run")
partitionGroup.add_argument("--partition", action="store_true", help="Run a partitioned runExamples run")
partitionGroup.add_argument("--post", action="store_true", help="Finalize a partitioned runExamples run")
debugOpts.add_argument("--runID", default=None, type=int, help="The id of the runexamples.model.Run dataset.")

# parse command line options
args = argparser.parse_args()
normalRun=not args.pre and not args.post and not args.partition

# override args.filter if given in buildConfig
exampleFilters = args.buildConfig.get("exampleFilters", None)
if exampleFilters is not None:
  exampleFilter = exampleFilters.get(args.buildType, None)
  if exampleFilter is not None:
    args.filter = exampleFilter
  else:
    exampleFilter = exampleFilters.get("ALL", None)
    if exampleFilter is not None:
      args.filter = exampleFilter

windowsOutputStopRE=re.compile("Application tried to create a window, but no driver could be loaded")
def guiEnvVars(displayNR):
  denv=os.environ.copy()
  denv["DISPLAY"]=":"+str(displayNR)
  denv["COIN_FULL_INDIRECT_RENDERING"]="1"
  denv["QT_X11_NO_MITSHM"]="1"
  return denv

mbsimenvSecrets.getSecrets()
if args.buildSystemRun:
  os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
else:
  if os.path.isfile("/.dockerenv"):
    os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_localdocker"
  else:
    os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_local"
django.setup()

# close unusable connections before model save()
# (to avoid connection failures between two save() on the same model when a large time is in-between;
#  e.g. firewalls may drop such TCP connections)
def closeUnusableConnection(**kwargs):
  connection=django.db.connections[kwargs["using"]]
  connection.ensure_connection()
  if not connection.is_usable():
    connection.close()
django.db.models.signals.pre_save.connect(closeUnusableConnection)

def removeOldBuilds():
  olderThan=django.utils.timezone.now()-datetime.timedelta(days=args.removeOlderThan)
  keep=runexamples.models.Run.objects.all().order_by('-startTime')[0:args.removeOlderThan].values("id")
  nrDeleted=runexamples.models.Run.objects.filter(startTime__lt=olderThan).exclude(id__in=keep).delete()[0]
  if nrDeleted>0:
    print("Deleted %d example runs being older than %d days!"%(nrDeleted, args.removeOlderThan))
    sys.stdout.flush()

# the main routine being called ones
def main():
  # check arguments
  if not (args.action=="report" or args.action=="copyToReference" or
          args.action=="updateReference" or
          args.action=="list"):
    argparser.print_usage()
    print("error: unknown argument --action "+args.action+" (see -h)")
    return -1

  if args.prefix is not None:
    if "PKG_CONFIG_PATH" in os.environ:
      os.environ["PKG_CONFIG_PATH"]=os.environ["PKG_CONFIG_PATH"]+os.pathsep+args.prefix+"/lib/pkgconfig"
    else:
      os.environ["PKG_CONFIG_PATH"]=args.prefix+"/lib/pkgconfig"

  if os.name=="nt":
    os.environ["PLATFORM"]="Windows"

  if normalRun or args.pre:
    removeOldBuilds()

  # check if the numpy and h5py modules exists. If not disable compare
  try: 
    import numpy
    import h5py
  except ImportError: 
    print("WARNING!")
    print("The python module numpy and h5py is required for full functionallity of this script.")
    print("However at least one of these modules are not found. Hence comparing the results will be disabled.\n")
    sys.stdout.flush()
    global canCompare
    canCompare=False

  # check args.directories
  for d in args.directories:
    dd=d
    if dd[0]=="^":
      dd=d[1:]
    if not os.path.isdir(dd):
      print("The positional argument (directory) "+d+" does not exist.")
      return -1

  # if no directory is specified use the current dir (all examples) filter by --filter
  dirs=args.directories+args.buildConfig.get("examples", [])
  if len(dirs)==0:
    dirs=[os.curdir]
  # loop over all directories on command line and add subdir which match the filter
  directoriesSet=set()
  for d in dirs:
    addExamplesByFilter(d, directoriesSet)

  # sort directories in descending order of simulation time (reference time)
  sortDirectories(directoriesSet, directories)

  # copy the current solution to the reference directory
  if args.action=="copyToReference":
    copyToReference()
    return 0

  # apply (unpack) a reference archive
  if args.action=="updateReference":
    updateReference()
    return 0

  # list directories to run
  if args.action=="list":
    listExamples()
    return 0

  # args.action = "report"

  if normalRun or args.pre:
    # create example run
    exRun=runexamples.models.Run()
    if args.buildRunID is not None:
      exRun.build_run=builds.models.Run.objects.get(id=args.buildRunID)
    exRun.buildType=args.buildType
    exRun.executor=args.executor
    exRun.command=" ".join(sys.argv)
    exRun.startTime=django.utils.timezone.now()
    exRun.save()
    if args.prefix is not None:
      os.makedirs(args.prefix, exist_ok=True)
      with open(args.prefix+"/.runexamplesInfo.json", "w") as f:
        json.dump({"runID": exRun.id}, f)

    # update status on commitid
    setGithubStatus(exRun, "pending")
  else:
    exRun=runexamples.models.Run.objects.filter(id=args.runID).select_related("build_run").get()

  if django.conf.settings.MBSIMENV_TYPE=="local" or django.conf.settings.MBSIMENV_TYPE=="localdocker":
    s=base.helper.startLocalServer(args.localServerPort, django.conf.settings.MBSIMENV_TYPE=="localdocker")
    print("Runexample info is avaiable at: http://%s:%d%s"%(s["hostname"], s["port"],
          django.urls.reverse("runexamples:current_buildtype", args=[args.buildType])))
    print("                              = http://%s:%d%s"%(s["hostname"], s["port"],
          django.urls.reverse("runexamples:run", args=[exRun.id])))
    print("")
    sys.stdout.flush()

  mainRet=0

  # enable coverage
  if args.coverage:
    if not "CFLAGS" in os.environ: os.environ["CFLAGS"]=""
    if not "CXXFLAGS" in os.environ: os.environ["CXXFLAGS"]=""
    if not "LDFLAGS"  in os.environ: os.environ["LDFLAGS" ]=""
    os.environ["CFLAGS"]=os.environ["CFLAGS"]+" --coverage"
    os.environ["CXXFLAGS"]=os.environ["CXXFLAGS"]+" --coverage"
    os.environ["LDFLAGS" ]=os.environ["LDFLAGS" ]+" --coverage -lgcov"

    if normalRun:
      # backup the coverage files in the build directories
      coverageBackupRestore('backup')
      # remove all "*.gcno", "*.gcda" files in ALL the examples
      for d,_,files in os.walk(args.baseExampleDir):
        for f in files:
          if os.path.splitext(f)[1]==".gcno": os.remove(pj(d, f))
          if os.path.splitext(f)[1]==".gcda": os.remove(pj(d, f))

  if args.pre:
    # create all examples in ExampleStatic
    esl=[]
    for example in directories:
      es=runexamples.models.ExampleStatic(exampleName=example)
      esl.append(es)
    # update "queued" flag to True
    base.helper.bulk_create(runexamples.models.ExampleStatic, esl, refresh=False)
    for es in esl:
      es.queued=True
    # needes since django.db.models.signals.pre_save.connect(...) is not called by bulk_update
    connection=django.db.connections["default"]
    connection.ensure_connection()
    if not connection.is_usable(): connection.close()
    runexamples.models.ExampleStatic.objects.bulk_update(esl, ["queued"])
    # exit pre step
    return 0

  if normalRun or args.partition:
    # get mbxmlutilsvalidate program
    global mbxmlutilsvalidate, xmlCatalog
    mbxmlutilsvalidate=pj(pkgconfig("mbxmlutils", ["--variable=BINDIR"]), "mbxmlutilsvalidate"+args.exeExt)
    if not os.path.isfile(mbxmlutilsvalidate):
      mbxmlutilsvalidate="mbxmlutilsvalidate"+args.exeExt
    # set global dirs
    global mbsimBinDir
    mbsimBinDir=pkgconfig("mbsim", ["--variable=bindir"])
    # get schema files
    # create mbsimxml schema
    xmlCatalog="/tmp/.runexamples.catalog.xml"
    if subprocess.call(exePrefix()+[pj(mbsimBinDir, "mbsimxml"+args.exeExt), "--dumpXMLCatalog", exePathConvert(xmlCatalog)])!=0:
      xmlCatalog=None
      print("Error: 'mbsimxml --dumpXMLCatalog <file>' failed. Trying to continue without schema files.", file=sys.stderr)

    if args.checkGUIs and os.name!="nt":
      # start vnc server on a free display
      global displayNR
      displayNR=3
      while subprocess.call(["vncserver", ":"+str(displayNR), "-noxstartup", "-SecurityTypes", "None"], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))!=0:
        displayNR=displayNR+1
        if displayNR>100:
          raise RuntimeError("Cannot find a free DISPLAY for vnc server.")
      if exePrefix()==["wine"]:
        print("Starting a dummy Windows GUI program (h5plotserie) and close it again. " \
              "This is needed to avoid failures in wine if the first GUI program is started while a none GUI program is running. " \
              "(This is a strange 'bug' in wine)")
        ret=base.helper.subprocessCall(exePrefix()+[pj(mbsimBinDir, "h5plotserie"+args.exeExt), "--autoExit"], open(os.devnull, 'w'), env=guiEnvVars(displayNR), maxExecutionTime=5, stopRE=windowsOutputStopRE)
        if ret!=0:
          print("Failed to start the dummy Windows GUI program. Return code: "+str(ret))

    try:
      multiprocessing.set_start_method('spawn') # use same method on Window and Linux (= python>=3.14 default)
      globalVars={
        "mbsimBinDir": mbsimBinDir,
        "canCompare": canCompare,
        "mbxmlutilsvalidate": mbxmlutilsvalidate,
        "xmlCatalog": xmlCatalog,
        "displayNR": displayNR,
        "directories": directories,
      }
      if args.partition:
        pList=[]
        django.db.connections.close_all() # multiprocessing forks on Linux which cannot be done with open database connections
        with multiprocessing.Pool(args.j) as pool:
          for i in range(0,args.j):
            pList.append(pool.apply_async(func=functools.partial(runExampleOuter, exRun, globalVars)))
          retAll=[]
          for p in pList:
            retAll.extend(p.get())
        django.db.connections.close_all() # close connections before finishing a process
      elif not args.debugDisableMultiprocessing:
        # init mulitprocessing handling and run in parallel
        django.db.connections.close_all() # multiprocessing forks on Linux which cannot be done with open database connections
        with multiprocessing.Pool(args.j) as pool:
          poolResult=pool.map_async(functools.partial(runExample, exRun, globalVars), directories, 1)
          # wait for pool to finish and get result
          retAll=poolResult.get()
        django.db.connections.close_all() # close connections before finishing a process
      else: # debugging
        import queue
        poolResult=queue.Queue()
        poolResult.put(list(map(functools.partial(runExample, exRun, globalVars), directories)))
        # wait for pool to finish and get result
        retAll=poolResult.get()

    finally:
      exRun.examplesFailed=exRun.examples.filterFailed().count()
      exRun.save()
      if args.checkGUIs and os.name!="nt":
        # kill vnc server
        if subprocess.call(["vncserver", "-kill", ":"+str(displayNR)], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))!=0:
          print("Cannot close vnc server on :%d but continue."%(displayNR))

    # set global result and add failedExamples and print exception from examples
    failedExamples=[]
    for retAlli in retAll:
      retAllInt, exampleName, excStr=retAlli
      willFail=False
      if os.path.isfile(pj(exampleName, "labels")):
        willFail='willfail' in codecs.open(pj(exampleName, "labels"), "r", encoding="utf-8").read().rstrip().split(' ')
      if retAllInt!=0 and not willFail:
        if mainRet==0:
          mainRet=1
        failedExamples.append(exampleName)
      if excStr is not None:
        mainRet=-1
        print("\n\n\nException from runExample "+exampleName)
        print(excStr)

  if args.partition:
    import uuid
    localRet=coverage(None, args.prefix+"/cov.trace.final.part."+args.buildType+"."+str(uuid.uuid4()))
    if localRet!=0 or mainRet<0:
      return -1
    return 0
  if args.post:
    exRun.examplesFailed=exRun.examples.filterFailed().count()
    exRun.save()

  # coverage analyzis (postpare)
  coverageAll=0
  coverageFailed=0
  if args.coverage:
    coverageAll=1
    print("Create coverage analyzis")
    sys.stdout.flush()
    coverageFailed=coverage(exRun)
    if normalRun:
      # restore the coverage files in the build directories
      coverageBackupRestore('restore')

  # set end time
  exRun.endTime=django.utils.timezone.now()
  exRun.save()

  # update status on commitid
  setGithubStatus(exRun, "success" if exRun.examplesFailed==0 and coverageFailed==0 else "failure")

  if normalRun:
    # print result summary to console
    if len(failedExamples)>0:
      print('\nERROR: '+str(len(failedExamples))+' of '+str(len(retAll))+' examples have failed.')
      sys.stdout.flush()
    if coverageFailed!=0:
      if mainRet==0:
        mainRet=1
      print('\nERROR: Coverage analyzis generation failed.')
      sys.stdout.flush()

  return mainRet



#####################################################################################
# from now on only functions follow and at the end main is called
#####################################################################################



def setGithubStatus(run, state):
  # skip for none build system runs
  if not args.buildSystemRun:
    return

  import github
  if state=="pending":
    description="Runexamples started at %s"%(run.startTime.isoformat())
  elif state=="failure":
    description="Runexamples failed after %.1f min"%((run.endTime-run.startTime).total_seconds()/60)
  elif state=="success":
    description="Runexamples passed after %.1f min"%((run.endTime-run.startTime).total_seconds()/60)
  else:
    raise RuntimeError("Unknown state "+state+" provided")
  try:
    gh=github.Github(mbsimenvSecrets.getSecrets("githubAccessToken"))
    for repo in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
      commit=gh.get_repo("mbsim-env/"+repo).get_commit(getattr(run.build_run, repo+"UpdateCommitID"))
      django.db.close_old_connections() # needed since run.build_run may create a new DB query
      if os.environ["MBSIMENVTAGNAME"]=="latest":
        commit.create_status(state, "https://"+os.environ['MBSIMENVSERVERNAME']+django.urls.reverse("runexamples:run", args=[run.id]),
          description, "runexamples/%s/%s/%s/%s/%s"%(run.buildType, run.build_run.fmatvecBranch, run.build_run.hdf5serieBranch,
                                                                    run.build_run.openmbvBranch, run.build_run.mbsimBranch))
      else:
        print("Skipping setting github status, this is the staging system!")
  except:
    if django.conf.settings.DEBUG:
      raise
    else:
      base.helper.handleRecoverableError("runexamples_setGithubStatus", "Original exception avoided to ensure that no secret is printed.")

def pkgconfig(module, options):
  comm=["pkg-config", module]
  comm.extend(options)
  try:
    output=subprocess.check_output(comm).rstrip().decode("utf-8")
  except subprocess.CalledProcessError as ex:
    if ex.returncode==0:
      raise
    else:
      print("Error: pkg-config module "+module+" not found. Trying to continue.", file=sys.stderr)
      output="pkg_config_"+module+"_not_found"
  return output.rstrip()



def sortDirectories(directoriesSet, dirs):
  unsortedDir=[]
  for example in directoriesSet:
    try:
      ex=runexamples.models.ExampleStatic.objects.get(exampleName=example)
      refTime=ex.refTime.total_seconds()
    except (runexamples.models.ExampleStatic.DoesNotExist, AttributeError):
      refTime=float("inf") # use very long time if unknown to force it to run early
    unsortedDir.append([example, refTime])
  dirs.extend(map(lambda x: x[0], sorted(unsortedDir, key=lambda x: x[1], reverse=True)))



# the labels: returns all labels defined in the labels file and append the special labels detected automatically
def getLabels(directory):
  labels=[]
  if os.path.isfile(pj(directory, "labels")):
    labels=codecs.open(pj(directory, "labels"), "r", encoding="utf-8").read().rstrip().split(' ')
  else:
    labels=['nightly'] # nightly is the default label if no labels file exist
  # check for MBSim modules in src examples
  src=os.path.isfile(pj(directory, "Makefile")) or os.path.isfile(pj(directory, "Makefile_FMI")) or os.path.isfile(pj(directory, "Makefile_FMI_cosim"))
  if src:
    makefile="Makefile" if os.path.isfile(pj(directory, "Makefile")) else \
             ("Makefile_FMI" if os.path.isfile(pj(directory, "Makefile_FMI")) else "Makefile_FMI_cosim")
    filecont=codecs.open(pj(directory, makefile), "r", encoding="utf-8").read()
    for m in mbsimModules:
      if re.search("\\b"+m+"\\b", filecont): labels.append(m)
  # check for MBSim modules in xml and flatxml examples
  else:
    for filedir, _, filenames in os.walk(directory):
      if "tmp_fmuCheck" in filedir.split('/') or "tmp_mbsimTestFMU" in filedir.split('/'): # skip temp fmu directories
        continue
      for filename in fnmatch.filter(filenames, "*.xml"):
        filecont=codecs.open(pj(filedir, filename), "r", encoding="utf-8").read()
        for m in mbsimModules:
          if re.search('=\\s*"http://[^"]*'+m+'"', filecont, re.I): labels.append(m)
  return labels



def ppxmlFile(root=None):
  if root is None:
    root=os.getcwd()
  if os.path.isfile(pj(root, "FMI.mbsx")): return None
  if os.path.isfile(pj(root, "FMI_cosim.mbsx")): return None
  if len(glob.glob(pj(root, "*.flat.mbsx")))>0: return None
  ppxmlFiles=glob.glob(pj(root, "*.mbsx")) 
  if len(ppxmlFiles)!=1: return None
  return ppxmlFiles[0]
def flatxmlFile(root=None):
  if root is None:
    root=os.getcwd()
  flatxmlFiles=glob.glob(pj(root, "*.flat.mbsx")) 
  if len(flatxmlFiles)!=1: return None
  return flatxmlFiles[0]
def fmiFile(root=None):
  if root is None:
    root=os.getcwd()
  if os.path.isfile(pj(root, "FMI.mbsx")):
    return pj(root, "FMI.mbsx")
  return None
def fmiCosimFile(root=None):
  if root is None:
    root=os.getcwd()
  if os.path.isfile(pj(root, "FMI_cosim.mbsx")):
    return pj(root, "FMI_cosim.mbsx")
  return None

# handle the --filter option: add/remove to directoriesSet
def addExamplesByFilter(baseDir, directoriesSet):
  if baseDir[0]!="^": # add dir
    addOrDiscard=directoriesSet.add
  else: # remove dir
    baseDir=baseDir[1:] # remove the leading "^"
    addOrDiscard=directoriesSet.discard
  # make baseDir a relative path
  baseDir=os.path.relpath(baseDir)
  for root, dirs, _ in os.walk(baseDir):
    ppxml=ppxmlFile(root) is not None
    flatxml=flatxmlFile(root) is not None
    xml=ppxml or flatxml
    src=os.path.isfile(pj(root, "Makefile")) or os.path.isfile(pj(root, "Makefile_FMI")) or os.path.isfile(pj(root, "Makefile_FMI_cosim"))
    fmi=fmiFile(root) is not None or os.path.isfile(pj(root, "Makefile_FMI")) or \
        fmiCosimFile(root) is not None or os.path.isfile(pj(root, "Makefile_FMI_cosim"))
    # skip none examples directories
    if(not ppxml and not flatxml and not src and not fmi):
      continue
    dirs=[]

    labels=getLabels(root)
    # evaluate filter
    try:
      filterResult=eval(args.filter,
        {'ppxml': ppxml, 'flatxml': flatxml, 'xml': xml, 'src': src, 'fmi': fmi, 'labels': labels})
    except:
      print("Unable to evaluate the filter:\n"+args.filter)
      sys.exit(1)
    if type(filterResult)!=bool:
      print("The filter does not return a bool value:\n"+args.filter)
      sys.exit(1)
    path=os.path.normpath(root)
    if filterResult and not "tmp_mbsimTestFMU" in path.split(os.sep) and not "tmp_fmuCheck" in path.split(os.sep):
      addOrDiscard(path)



# run the given example
def runExample(exRun, globalVars, example):
  print("Started example "+example)

  global mbsimBinDir, canCompare, mbxmlutilsvalidate, xmlCatalog, displayNR, directories
  mbsimBinDir=globalVars["mbsimBinDir"]
  canCompare=globalVars["canCompare"]
  mbxmlutilsvalidate=globalVars["mbxmlutilsvalidate"]
  xmlCatalog=globalVars["xmlCatalog"]
  displayNR=globalVars["displayNR"]
  directories=globalVars["directories"]

  sys.stdout.flush()
  savedDir=os.getcwd()
  runExampleRet=0 # run ok
  executeFD=base.helper.MultiFile(args.printToConsole)
  exRunOutputWritten=False
  excStr=None
  try:
    os.chdir(example)

    willFail=False
    if os.path.isfile("labels"):
      willFail='willfail' in codecs.open("labels", "r", encoding="utf-8").read().rstrip().split(' ')

    # create example run
    ex=runexamples.models.Example()
    ex.run=exRun
    ex.exampleName=example
    ex.willFail=willFail
    ex.webappHdf5serie=False
    ex.webappOpenmbv=False
    ex.webappMbsimgui=False
    ex.save()

    # execute the example
    executeRet=0
    if not args.disableRun:
      # remove lock from all h5 file, just to avoid the the results depend on crashes of previous runs
      lockFiles=glob.glob("*.ombvh5")+glob.glob("*.mbsh5")
      if len(lockFiles)>0:
        base.helper.subprocessCall(exePrefix()+[pj(mbsimBinDir, "h5lockserie"+args.exeExt), "--remove"]+exePathConvert(lockFiles),
                                   executeFD, maxExecutionTime=1)

      # clean output of previous run
      list(map(os.remove, glob.glob("*.fmuh5")))
      list(map(os.remove, glob.glob("*.mbsh5")))
      list(map(os.remove, glob.glob("*.ombvh5")))

      dt=0
      if os.path.isfile("Makefile"):
        executeRet, dt=executeSrcExample(ex, executeFD)
      elif ppxmlFile() is not None:
        executeRet, dt=executeXMLExample(ex, executeFD)
      elif flatxmlFile() is not None:
        executeRet, dt=executeFlatXMLExample(ex, executeFD)
      elif fmiFile() is not None or fmiCosimFile() is not None:
        executeRet, dt=executeFMIXMLExample(ex, executeFD)
      elif os.path.isfile("Makefile_FMI") or os.path.isfile("Makefile_FMI_cosim"):
        executeRet, dt=executeFMISrcExample(ex, executeFD)
      else:
        print("Unknown example type in directory "+example+" found.", file=executeFD)
        executeRet=1
        dt=0
      ex.time=datetime.timedelta(seconds=dt)
      executeFD.close()
      ex.runOutput=executeFD.getData().replace("\0", "&#00;");
      exRunOutputWritten=True
      ex.runResult=runexamples.models.Example.RunResult.WARNING if base.helper.subprocessOtherFailure(executeRet) else \
                   (runexamples.models.Example.RunResult.FAILED if executeRet!=0 else runexamples.models.Example.RunResult.PASSED)
      ex.save()
    if executeRet!=0: runExampleRet=1
    # get reference time

    if args.checkGUIs:
      # get files to load
      ombvFiles=mainFiles(glob.glob("*.ombvx"), ".", ".ombvx")
      h5pFiles=mainFiles(glob.glob("*.mbsh5"), ".", ".mbsh5")
      guiFile=None
      if ppxmlFile() is not None:
        guiFile=ppxmlFile()
      elif flatxmlFile() is not None:
        guiFile=flatxmlFile()
      elif fmiFile() is not None:
        guiFile=fmiFile()
      elif fmiCosimFile() is not None:
        guiFile=fmiCosimFile()
      # run gui tests
      def runGUI(files, tool, ex, exOK, exOutput):
        if len(files)==0:
          return []
        # at least on Windows (wine) the DISPLAY is not found sometimes (unknown why). Hence, try this number of times before reporting an error
        tries=20 if exePrefix()==["wine"] else 1
        outFD=base.helper.MultiFile(args.printToConsole)
        comm=[pj(mbsimBinDir, tool+args.exeExt), "--autoExit"]+exePathConvert(files)
        # if this string is found in the output (wine output) then stop the execution immediately
        ret=0
        for t in range(0, tries):
          print("Starting (try %d/%d):\n"%(t+1, tries)+"\n\n", file=outFD)
          ret=base.helper.subprocessCall(prefixSimulation(tool)+exePrefix()+comm, outFD, env=guiEnvVars(displayNR), maxExecutionTime=(20 if args.prefixSimulationKeyword=='VALGRIND' else 5), stopRE=windowsOutputStopRE)
          print("\n\nReturned with "+str(ret), file=outFD)
          if ret==0 or not base.helper.subprocessOtherFailure(ret): # OK or real error -> stop more tries
            break
          if t+1<tries: time.sleep(10) # wait some time, a direct next test will likely also fail (see above)
        retv=valgrindOutputAndAdaptRet("guitest_"+tool, ex)
        if retv!=0: ret=1
        if ret!=0:
          runExampleRet=1
        outFD.close()
        setattr(ex, exOK, runexamples.models.Example.GUITestResult.PASSED if ret==0 else (runexamples.models.Example.GUITestResult.WARNING if base.helper.subprocessOtherFailure(ret) else runexamples.models.Example.GUITestResult.FAILED))
        setattr(ex, exOutput, outFD.getData().replace("\0", "&#00;"))
        ex.save()
      runGUI(ombvFiles, "openmbv", ex, "guiTestOpenmbvOK", "guiTestOpenmbvOutput")
      runGUI(h5pFiles, "h5plotserie", ex, "guiTestHdf5serieOK", "guiTestHdf5serieOutput")
      runGUI([guiFile] if guiFile else [], "mbsimgui", ex, "guiTestMbsimguiOK", "guiTestMbsimguiOutput")

    if not args.disableCompare and canCompare:
      # compare the result with the reference
      if compareExample(ex)!=0: runExampleRet=1

    # check for deprecated features
    if not args.disableRun:
      ex.deprecatedNr=len(re.findall("Deprecated feature called:", executeFD.getData()))
      ex.save()

    # validate XML
    if not args.disableValidate:
      if validateXML(ex)>0:
        runExampleRet=1

  except:
    with io.StringIO() as excF:
      traceback.print_exception(*sys.exc_info(), file=excF)
      excStr=excF.getvalue().rstrip()
    if not exRunOutputWritten:
      executeFD.close()
      ex.runOutput=executeFD.getData().replace("\0", "&#00;");
    ex.runOutput+="\n\n\nFatal Test-Script Bug/Error! See console output!"
    ex.runResult=runexamples.models.Example.RunResult.FAILED
    ex.save()
    runExampleRet=1
  finally:
    os.chdir(savedDir)
    if runExampleRet==0:
      print("Passed example "+example)
    else:
      print("Failed example "+example)
    sys.stdout.flush()
    return runExampleRet, example, excStr

# helper function for runExample for args.partition
# this function must be at global scope
def runExampleOuter(exRun, globalVars):
  global mbsimBinDir, canCompare, mbxmlutilsvalidate, xmlCatalog, displayNR, directories
  mbsimBinDir=globalVars["mbsimBinDir"]
  canCompare=globalVars["canCompare"]
  mbxmlutilsvalidate=globalVars["mbxmlutilsvalidate"]
  xmlCatalog=globalVars["xmlCatalog"]
  displayNR=globalVars["displayNR"]
  directories=globalVars["directories"]

  dirs=ExampleServerQueue("totalTimeValgrind" if args.prefixSimulationKeyword=='VALGRIND' else "totalTimeNormal")
  retAllPerThread=[]
  for d in dirs:
    retAllPerThread.append(runExample(exRun, globalVars, d))
  django.db.connections.close_all() # close connections before finishing a process
  return retAllPerThread



def mainFiles(fl, example, suffix):
  ret=fl
  for f in fl:
    ret=list(filter(lambda r: not (r.startswith(f[0:-len(suffix)]+'.') and len(r)>len(f)), ret))
  ret=list(map(lambda x: example+'/'+x, ret))
  ret.sort(key=lambda a: os.path.basename(a))
  return ret

# if args.exeEXt is set we must prefix every command with wine
def exePrefix():
  if args.exeExt=="":
    return []
  else:
    return ["wine"]
# if args.exeEXt is set we must convert every path to a Windows path
def exePathConvert(path):
  if exePrefix()==["wine"]:
    def convert(p):
        return "z:"+p.replace("/", "\\") if os.path.isabs(p) else p.replace("/", "\\")
    if type(path)==str:
      return convert(path)
    else:
      return list(map(lambda p: convert(p), path))   

  if os.name!="nt" or shutil.which("cygpath") is None:
    return path

  def convert(p):
    if not os.path.isabs(p):
      return p
    else:
      return subprocess.check_output(["cygpath", "-w", p]).rstrip().decode("utf-8")
  if type(path)==str:
    return convert(path)
  else:
    return list(map(lambda p: convert(p), path))   


# prefix the simultion with this parameter.
# this is normaly just args.prefixSimulation but may be extended by keywords of args.prefixSimulationKeyword.
def prefixSimulation(id):
  # handle VALGRIND
  if args.prefixSimulationKeyword=='VALGRIND':
    # remove valgrind output
    for xmlFile in glob.glob("valgrind.*.xml"):
      os.remove(xmlFile)
    return args.prefixSimulation+['--xml=yes', '--xml-file='+os.getcwd()+'/valgrind.%%p.%s.xml'%(id)]
  return args.prefixSimulation

# get additional output files of simulations.
# these are all dependent on the keyword of args.prefixSimulationKeyword.
# additional output files must be placed in the args.reportOutDir and here only the basename must be returned.
def valgrindOutputAndAdaptRet(programType, ex):
  # handle VALGRIND
  ret=0
  if args.prefixSimulationKeyword=='VALGRIND':
    import xml.etree.cElementTree as ET

    headerMap=getHeaderMap()
    # get out files
    # and adapt the return value if errors in valgrind outputs are detected
    xmlFiles=glob.glob("valgrind.*.xml")
    i=0
    vgs=[]
    ers=[]
    wss=[]
    frs=[]
    for xmlFile in xmlFiles:
      # global
      vg=runexamples.models.Valgrind()
      vgs.append(vg)
      vg.example=ex
      vg.programType=programType

      try:
        valgrindoutput=ET.parse(xmlFile).getroot()
      except ET.ParseError:
        os.remove(xmlFile)
        continue

      programCmd=[valgrindoutput.find("args").find("argv").find("exe").text]
      for arg in valgrindoutput.find("args").find("argv").findall("arg"):
        programCmd.append(arg.text)
      vg.programCmd=" ".join(programCmd)
      valgrindCmd=[valgrindoutput.find("args").find("vargv").find("exe").text]
      for arg in valgrindoutput.find("args").find("vargv").findall("arg"):
        valgrindCmd.append(arg.text)
      vg.valgrindCmd=" ".join(valgrindCmd)

      # errors
      wsNr=0
      for error in valgrindoutput.findall("error"):
        ret=1
        wsNr=wsNr+1

        er=runexamples.models.ValgrindError()
        ers.append(er)
        er.valgrind=vg
        er.kind=error.find("kind").text
        er.suppressionRawText=error.find("suppression").find("rawtext").text

        # what and stack
        ws=runexamples.models.ValgrindWhatAndStack()
        wss.append(ws)
        ws.valgrindError=er
        ws.nr=wsNr
        if error.find("what") is not None: ws.what=error.find("what").text
        if error.find("xwhat") is not None: ws.what=error.find("xwhat").find("text").text
    
        # frame
        frNr=0
        for frame in error.find("stack").findall("frame"):
          frNr=frNr+1

          fr=runexamples.models.ValgrindFrame()
          frs.append(fr)
          fr.whatAndStack=ws
          fr.nr=frNr
          if frame.find("obj") is not None: fr.obj=frame.find("obj").text
          if frame.find("fn") is not None: fr.fn=frame.find("fn").text
          if frame.find("dir") is not None: fr.dir=frame.find("dir").text
          if frame.find("file") is not None: fr.file=frame.find("file").text
          if frame.find("line") is not None: fr.line=int(frame.find("line").text)
          # adapt file path of a header in args.prefix to the corresponding header in the repo source dir
          newPath=headerMap.get(fr.dir+"/"+fr.file, None)
          if newPath is not None:
            fr.dir=os.path.dirname(newPath)
            fr.file=os.path.basename(newPath)
      os.remove(xmlFile)
    # now save all new datasets at once
    base.helper.bulk_create(runexamples.models.Valgrind, vgs, refresh=True)
    base.helper.bulk_create(runexamples.models.ValgrindError, ers, refresh=True)
    base.helper.bulk_create(runexamples.models.ValgrindWhatAndStack, wss, refresh=True)
    base.helper.bulk_create(runexamples.models.ValgrindFrame, frs, refresh=False)
  return ret


# execute the source code example in the current directory (write everything to fd executeFD)
def executeSrcExample(ex, executeFD):
  print("Running commands:", file=executeFD)
  print("make clean && make && "+pj(os.curdir, "main"), file=executeFD)
  print("", file=executeFD)
  executeFD.flush()
  ex.webappHdf5serie=True
  ex.webappOpenmbv=True
  if not args.disableMakeClean:
    if base.helper.subprocessCall(["make", "clean"], executeFD)!=0: return 1, 0
  if base.helper.subprocessCall(["make"], executeFD)!=0: return 1, 0
  # append $prefix/lib to LD_LIBRARY_PATH/PATH to find lib by main of the example
  if os.name=="posix":
    NAME="LD_LIBRARY_PATH"
    SUBDIR="lib"
  elif os.name=="nt":
    NAME="PATH"
    SUBDIR="bin"
  mainEnv=os.environ.copy()
  libDir=pj(mbsimBinDir, os.pardir, SUBDIR)
  if NAME in mainEnv:
    mainEnv[NAME]=mainEnv[NAME]+os.pathsep+libDir
  else:
    mainEnv[NAME]=libDir
  # run main
  t0=datetime.datetime.now()
  ret=abs(base.helper.subprocessCall(prefixSimulation('source')+exePrefix()+[pj(os.curdir, "main"+args.exeExt)], executeFD,
                         env=mainEnv, maxExecutionTime=args.maxExecutionTime))
  t1=datetime.datetime.now()
  dt=(t1-t0).total_seconds()
  retv=valgrindOutputAndAdaptRet("example_src", ex)
  if retv!=0: ret=1

  return ret, dt



# execute the XML example in the current directory (write everything to fd executeFD)
def executeXMLExample(ex, executeFD, env=os.environ):
  # we handle MBS.mbsx, MBS.flat.mbsx, FMI.mbsx, and FMI_cosim.mbsx files here
  if   ppxmlFile() is not None:    prjFile=ppxmlFile()
  elif flatxmlFile() is not None:  prjFile=flatxmlFile()
  elif fmiFile() is not None:      prjFile=fmiFile()
  elif fmiCosimFile() is not None: prjFile=fmiCosimFile()
  else: raise RuntimeError("Internal error: Unknown ppxml file.")

  print("Running command:", file=executeFD)
  list(map(lambda x: print(x, end=" ", file=executeFD), [pj(mbsimBinDir, "mbsimxml")]+[prjFile]))
  print("\n", file=executeFD)
  ex.webappHdf5serie=True
  ex.webappOpenmbv=True
  ex.webappMbsimgui=True
  executeFD.flush()
  t0=datetime.datetime.now()
  ret=abs(base.helper.subprocessCall(prefixSimulation('mbsimxml')+exePrefix()+[pj(mbsimBinDir, "mbsimxml"+args.exeExt)]+
                         exePathConvert([prjFile]), executeFD, env=env, maxExecutionTime=args.maxExecutionTime))
  t1=datetime.datetime.now()
  dt=(t1-t0).total_seconds()
  retv=valgrindOutputAndAdaptRet("example_xml", ex)
  if retv!=0: ret=1

  return ret, dt



# execute the flat XML example in the current directory (write everything to fd executeFD)
def executeFlatXMLExample(ex, executeFD):
  # first simple run the example as a preprocessing xml example
  minimalTEndEnv=os.environ.copy()
  minimalTEndEnv["MBSIM_SET_MINIMAL_TEND"]="1"
  ret1, dt=executeXMLExample(ex, executeFD, env=minimalTEndEnv)

  print("\n\n\n", file=executeFD)
  print("Running command:", file=executeFD)
  list(map(lambda x: print(x, end=" ", file=executeFD), [pj(mbsimBinDir, "mbsimflatxml"), flatxmlFile()]))
  print("\n", file=executeFD)
  ex.webappHdf5serie=True
  ex.webappOpenmbv=True
  ex.webappMbsimgui=True
  executeFD.flush()
  t0=datetime.datetime.now()
  ret2=abs(base.helper.subprocessCall(prefixSimulation('mbsimflatxml')+exePrefix()+[pj(mbsimBinDir, "mbsimflatxml"+args.exeExt),
       exePathConvert(flatxmlFile())], executeFD, maxExecutionTime=args.maxExecutionTime))
  t1=datetime.datetime.now()
  dt=(t1-t0).total_seconds()
  retv=valgrindOutputAndAdaptRet("example_flatxml", ex)
  if retv!=0: ret2=1

  # return
  if ret1==base.helper.subprocessCall.timedOutErrorCode or ret2==base.helper.subprocessCall.timedOutErrorCode:
    ret=base.helper.subprocessCall.timedOutErrorCode
  elif ret1==base.helper.subprocessCall.stopByREErrorCode or ret2==base.helper.subprocessCall.stopByREErrorCode:
    ret=base.helper.subprocessCall.stopByREErrorCode
  else:
    ret=abs(ret1)+abs(ret2)
  return ret, dt



# helper function for executeFMIXMLExample and executeFMISrcExample
def executeFMIExample(ex, executeFD, fmiInputFile, cosim):
  ex.webappHdf5serie=True
  ex.webappOpenmbv=True
  ### create the FMU
  # run mbsimCreateFMU to export the model as a FMU
  # use option --nocompress, just to speed up mbsimCreateFMU
  print("\n\n\n", file=executeFD)
  print("Running command:", file=executeFD)
  labels=getLabels(os.getcwd())
  cosimArg=[]
  if cosim: cosimArg=['--cosim']
  noparamArg=[]
  if "noparam" in labels: noparamArg=['--noparam']
  comm=exePrefix()+[pj(mbsimBinDir, "mbsimCreateFMU"+args.exeExt), '--nocompress']+cosimArg+noparamArg+[exePathConvert(fmiInputFile)]
  ret1=abs(base.helper.subprocessCall(prefixSimulation('mbsimCreateFMU')+comm, executeFD, maxExecutionTime=args.maxExecutionTime))
  retv=valgrindOutputAndAdaptRet("example_fmi_create", ex)
  if retv!=0: ret1=1

  ### run using fmuChecker
  # get fmuChecker executable
  fmuCheck=glob.glob(pj(mbsimBinDir, "fmuCheck.*"))
  if len(fmuCheck)!=1:
    print("ERROR: None or more than one fmuCheck.* executlabe found!", file=executeFD)
    fmuCheck="/bin/fmu_check_NOT_FOUND"
  else:
    fmuCheck=fmuCheck[0]
  # run fmuChecker
  print("\n\n\n", file=executeFD)
  print("Running command:", file=executeFD)
  # adapt end time if MBSIM_SET_MINIMAL_TEND is set
  endTime=[]
  if 'MBSIM_SET_MINIMAL_TEND' in os.environ:
    endTime=['-s', '0.01']
  if os.path.isdir("tmp_fmuCheck"): shutil.rmtree("tmp_fmuCheck")
  os.mkdir("tmp_fmuCheck")
  comm=exePrefix()+[pj(mbsimBinDir, fmuCheck)]+endTime+["-f", "-l", "4", "-o", "fmuCheck.result.csv", "-z", "tmp_fmuCheck", "mbsim.fmu"]
  t0=datetime.datetime.now()
  ret2=abs(base.helper.subprocessCall(prefixSimulation('fmuCheck')+comm, executeFD, maxExecutionTime=args.maxExecutionTime))
  t1=datetime.datetime.now()
  dt=(t1-t0).total_seconds()
  retv=valgrindOutputAndAdaptRet("example_fmi_fmuCheck", ex)
  if retv!=0: ret2=1
  # convert fmuCheck result csv file to h5 format (this is then checked as usual by compareExample)
  if canCompare:
    try:
      print("Convert fmuCheck csv file to h5:\n", file=executeFD)
      import h5py
      import numpy
      data=numpy.genfromtxt("fmuCheck.result.csv", dtype=float, delimiter=",", skip_header=1) # get data from csv
      header=open("fmuCheck.result.csv", "r").readline().rstrip().split(',') # get header from csv
      header=list(map(lambda x: x[1:-1], header)) # remove leading/trailing " form each header
      with h5py.File("fmuCheck.result.fmuh5", "w") as f: # create h5 file
        d=f.create_dataset("fmuCheckResult", dtype='d', data=data) # create dataset with data
        d.attrs.create("Column Label", dtype=h5py.special_dtype(vlen=bytes), data=header) # create Column Label attr with header
    except:
      print(traceback.format_exc(), file=executeFD)
      print("Failed.\n", file=executeFD)
    else:
      print("Done.\n", file=executeFD)
  # remove unpacked fmu
  if os.path.isdir("tmp_fmuCheck"): shutil.rmtree("tmp_fmuCheck")

  ### run using mbsimTestFMU
  # unpack FMU
  if os.path.isdir("tmp_mbsimTestFMU"): shutil.rmtree("tmp_mbsimTestFMU")
  try:
    print("Unzip mbsim.fmu for mbsimTestFMU:\n", file=executeFD)
    zipfile.ZipFile("mbsim.fmu").extractall("tmp_mbsimTestFMU")
  except:
    print(traceback.format_exc(), file=executeFD)
    print("Failed.\n", file=executeFD)
  else:
    print("Done.\n", file=executeFD)
  # run mbsimTestFMU
  print("\n\n\n", file=executeFD)
  print("Running command:", file=executeFD)
  cosimArg=['--me']
  if cosim: cosimArg=['--cosim']
  comm=exePrefix()+[pj(mbsimBinDir, "mbsimTestFMU"+args.exeExt)]+cosimArg+["tmp_mbsimTestFMU"]
  ret3=abs(base.helper.subprocessCall(prefixSimulation('mbsimTestFMU')+comm, executeFD, maxExecutionTime=args.maxExecutionTime))
  retv=valgrindOutputAndAdaptRet("example_fmi_mbsimTestFMU", ex)
  if retv!=0: ret3=1
  # remove unpacked fmu
  if os.path.isdir("tmp_mbsimTestFMU"): shutil.rmtree("tmp_mbsimTestFMU")

  # remove the generated fmu (just to save disk space)
  if os.path.isfile("mbsim.fmu"): os.remove("mbsim.fmu")

  # return
  if ret1==base.helper.subprocessCall.timedOutErrorCode or ret2==base.helper.subprocessCall.timedOutErrorCode or ret3==base.helper.subprocessCall.timedOutErrorCode:
    ret=base.helper.subprocessCall.timedOutErrorCode
  elif ret1==base.helper.subprocessCall.stopByREErrorCode or ret2==base.helper.subprocessCall.stopByREErrorCode or ret3==base.helper.subprocessCall.stopByREErrorCode:
    ret=base.helper.subprocessCall.stopByREErrorCode
  else:
    ret=abs(ret1)+abs(ret2)+abs(ret3)

  return ret, dt

# execute the FMI XML export example in the current directory (write everything to fd executeFD)
def executeFMIXMLExample(ex, executeFD):
  ex.webappHdf5serie=True
  ex.webappOpenmbv=True
  ex.webappMbsimgui=True
  # first simple run the example as a preprocessing xml example
  minimalTEndEnv=os.environ.copy()
  minimalTEndEnv["MBSIM_SET_MINIMAL_TEND"]="1"
  ret1, dt=executeXMLExample(ex, executeFD, env=minimalTEndEnv)
  # create and run FMU
  basename=fmiFile() if fmiFile() is not None else fmiCosimFile()
  cosim=False if fmiFile() is not None else True
  ret2, dt=executeFMIExample(ex, executeFD, basename, cosim)
  # return
  if ret1==base.helper.subprocessCall.timedOutErrorCode or ret2==base.helper.subprocessCall.timedOutErrorCode:
    ret=base.helper.subprocessCall.timedOutErrorCode
  elif ret1==base.helper.subprocessCall.stopByREErrorCode or ret2==base.helper.subprocessCall.stopByREErrorCode:
    ret=base.helper.subprocessCall.stopByREErrorCode
  else:
    ret=abs(ret1)+abs(ret2)
  return ret, dt

# execute the FMI source export example in the current directory (write everything to fd executeFD)
def executeFMISrcExample(ex, executeFD):
  basename="Makefile_FMI" if os.path.isfile("Makefile_FMI") else "Makefile_FMI_cosim"
  cosim=False if os.path.isfile("Makefile_FMI") else True
  # compile examples
  print("Running commands:", file=executeFD)
  print("make -f "+basename+" clean && make -f "+basename, file=executeFD)
  print("", file=executeFD)
  executeFD.flush()
  if not args.disableMakeClean:
    if base.helper.subprocessCall(["make", "-f", basename, "clean"], executeFD)!=0: return 1, 0
  if base.helper.subprocessCall(["make", "-f", basename], executeFD)!=0: return 1, 0
  # create and run FMU
  if os.name=="nt" or args.exeExt==".exe":
    dllExt=".dll"
  else:
    dllExt=".so"
  return executeFMIExample(ex, executeFD, "mbsimfmi_model"+dllExt, cosim)



# return column col from arr as a column Vector if asColumnVector == True or as a row vector
# arr may be of shape vector or a matrix
def getColumn(arr, col, asColumnVector=True):
  if len(arr.shape)==2:
    if asColumnVector:
      return arr[:,col]
    else:
      return arr[:,col:col+1]
  elif len(arr.shape)==1 and col==0:
    if asColumnVector:
      return arr[:]
    else:
      return arr[:][:,None]
  else:
    raise IndexError("Only HDF5 datasets of shape vector and matrix can be handled.")
def compareDatasetVisitor(h5CurFile, ex, nrFailed, refMemberNames, cmpResFile, cmpRess, datasetName, refObj):
  import numpy
  import h5py

  def saveFileIfNotAlreadyDone(cmpResFile, h5CurFile):
    if not cmpResFile.h5File:
      # save the file only the first time
      cmpResFile.h5FileName=cmpResFile.h5Filename # this calls save on the dataset cmpResFile -> it will be skipped for bulk_create later on 
      with cmpResFile.h5File.open("wb") as fw:
        with open(h5CurFile.filename, "rb") as fr:
          base.helper.copyFile(fr, fw)
      cmpResFile.save()

  if isinstance(refObj, h5py.Dataset):
    # add to refMemberNames
    refMemberNames.add(datasetName)
    # the corresponding curObj to refObj
    try:
      curObj=h5CurFile[datasetName]
    except KeyError:
      cmpRes=runexamples.models.CompareResult()
      cmpRess.append(cmpRes)
      cmpRes.compareResultFile=cmpResFile
      cmpRes.dataset=datasetName
      cmpRes.result=runexamples.models.CompareResult.Result.DATASETNOTINCUR
      nrFailed[0]+=1
      return
    # get shape
    refObjCols=refObj.shape[1] if len(refObj.shape)==2 else 1
    curObjCols=curObj.shape[1] if len(curObj.shape)==2 else 1
    def toUTF8(x):
      return x.decode("utf-8") if type(x)==bytes else x
    # get labels from reference
    try:
      refLabels=list(map(lambda x: toUTF8(x), refObj.attrs["Column Label"]))
      # append missing dummy labels
      for x in range(len(refLabels), refObjCols):
        refLabels.append('<no label in ref. for col. '+str(x+1)+'>')
    except KeyError:
      refLabels=list(map(
        lambda x: '<no label for col. '+str(x+1)+'>',
        range(refObjCols)))
    # get labels from current
    try:
      curLabels=list(map(lambda x: toUTF8(x), curObj.attrs["Column Label"]))
      # append missing dummy labels
      for x in range(len(curLabels), curObjCols):
        curLabels.append('<no label in cur. for col. '+str(x+1)+'>')
    except KeyError:
      curLabels=list(map(
        lambda x: '<no label for col. '+str(x+1)+'>',
        range(refObjCols)))
    # loop over all columns
    for column in range(refObjCols):
      cmpRes=runexamples.models.CompareResult()
      cmpRess.append(cmpRes)
      cmpRes.compareResultFile=cmpResFile
      cmpRes.dataset=datasetName
      cmpRes.label=refLabels[column]
      cmpRes.result=runexamples.models.CompareResult.Result.PASSED
      # if if curObj[:,column] does not exitst
      if column>=curObjCols:
        cmpRes.result=runexamples.models.CompareResult.Result.LABELNOTINCUR
        saveFileIfNotAlreadyDone(cmpResFile, h5CurFile)
        nrFailed[0]+=1
      if not column<curObjCols or refLabels[column]!=curLabels[column]:
        cmpRes.result=runexamples.models.CompareResult.Result.LABELDIFFER
        saveFileIfNotAlreadyDone(cmpResFile, h5CurFile)
        nrFailed[0]+=1
      if column>=curObjCols or curObj.shape[0]<=0 or curObj.shape[0]<=0: # not row in curObj or refObj
        cmpRes.result=runexamples.models.CompareResult.Result.LABELMISSING
        saveFileIfNotAlreadyDone(cmpResFile, h5CurFile)
        nrFailed[0]+=1
      else: # only if curObj and refObj contains data (rows)
        # check for difference
        refObjCol=getColumn(refObj,column)
        curObjCol=getColumn(curObj,column)
        if refObjCol.shape[0]!=curObjCol.shape[0] or not numpy.all(numpy.isclose(curObjCol, refObjCol, rtol=args.rtol,
                         atol=args.atol, equal_nan=True)):
          nrFailed[0]+=1
          cmpRes.result=runexamples.models.CompareResult.Result.FAILED
          saveFileIfNotAlreadyDone(cmpResFile, h5CurFile)
    # check for labels/columns in current but not in reference
    for label in curLabels[len(refLabels):]:
      cmpRes=runexamples.models.CompareResult()
      cmpRess.append(cmpRes)
      cmpRes.compareResultFile=cmpResFile
      cmpRes.dataset=datasetName
      cmpRes.label=label
      cmpRes.result=runexamples.models.CompareResult.Result.LABELNOTINREF
      saveFileIfNotAlreadyDone(cmpResFile, h5CurFile)
      nrFailed[0]+=1

def appendDatasetName(curMemberNames, datasetName, curObj):
  import h5py
  if isinstance(curObj, h5py.Dataset):
    # add to curMemberNames
    curMemberNames.add(datasetName)

# compare the example with the reference solution
def compareExample(ex):
  import h5py

  nrFailed=[0]
  try:
    refFiles=runexamples.models.ExampleStatic.objects.get(exampleName=ex.exampleName).references.all()
  except runexamples.models.ExampleStatic.DoesNotExist:
    refFiles=[]
  cmpResFiles=[]
  cmpRess=[]
  for refFile in refFiles:
    # open h5 files
    with refFile.h5File.open("rb") as djangoF:
      try:
        tempF=tempfile.NamedTemporaryFile(mode='wb', delete=False)
        base.helper.copyFile(djangoF, tempF)
        tempF.close()
        h5RefFile=h5py.File(tempF.name, "r")
        cmpResFile=runexamples.models.CompareResultFile()
        cmpResFiles.append(cmpResFile) # -> append to bulk_create later on
        cmpResFile.example=ex
        cmpResFile.h5Filename=refFile.h5FileName
        try:
          h5CurFile=h5py.File(refFile.h5FileName, "r")
        except IOError:
          cmpRes=runexamples.models.CompareResult()
          cmpRess.append(cmpRes)
          cmpRes.compareResultFile=cmpResFile
          cmpRes.result=runexamples.models.CompareResult.Result.FILENOTINCUR
          nrFailed[0]+=1
        else:
          # process h5 file
          refMemberNames=set()
          # bind arguments h5CurFile, ex, example, nrFailed in order (nrFailed as lists to pass by reference)
          dummyFctPtr = functools.partial(compareDatasetVisitor, h5CurFile, ex,
                                          nrFailed, refMemberNames, cmpResFile, cmpRess)
          h5RefFile.visititems(dummyFctPtr) # visit all dataset
          # check for datasets in current but not in reference
          curMemberNames=set()
          h5CurFile.visititems(functools.partial(appendDatasetName, curMemberNames)) # get all dataset names in cur
          for datasetName in curMemberNames-refMemberNames:
            cmpRes=runexamples.models.CompareResult()
            cmpRess.append(cmpRes)
            cmpRes.compareResultFile=cmpResFile
            cmpRes.dataset=datasetName
            cmpRes.result=runexamples.models.CompareResult.Result.DATASETNOTINREF
            nrFailed[0]+=1
          # close h5 files
          h5CurFile.close()
      finally:
        h5RefFile.close()
        os.unlink(tempF.name)
  base.helper.bulk_create(runexamples.models.CompareResultFile, cmpResFiles, refresh=True)
  # files in current but not in reference
  curFiles=[]
  curFiles.extend(glob.glob("*.fmuh5"))
  curFiles.extend(glob.glob("*.mbsh5"))
  curFiles.extend(glob.glob("*.ombvh5"))
  for curFile in curFiles:
    if not any(map(lambda x: x.h5FileName==curFile, refFiles)):
      cmpResFile=runexamples.models.CompareResultFile()
      cmpResFile.example=ex
      cmpResFile.h5Filename=curFile
      cmpResFile.h5FileName=cmpResFile.h5Filename # this calls save on the dataset cmpResFile -> no bulk_create
      with cmpResFile.h5File.open("wb") as fw:
        with open(curFile, "rb") as fr:
          base.helper.copyFile(fr, fw)
      cmpResFile.save()

      cmpRes=runexamples.models.CompareResult()
      cmpRess.append(cmpRes)
      cmpRes.compareResultFile=cmpResFile
      cmpRes.result=runexamples.models.CompareResult.Result.FILENOTINREF
      nrFailed[0]+=1
  base.helper.bulk_create(runexamples.models.CompareResult, cmpRess, refresh=False)
  ex.resultsFailed=0
  for rf in ex.resultFiles.all():
    ex.resultsFailed+=rf.results.filterFailed().count()
  ex.save()

  return 1 if nrFailed[0]>0 else 0

def copyToReference():
  for example in directories:
    sys.stdout.flush()
    try:
      exSt=runexamples.models.ExampleStatic.objects.get(exampleName=example)
    except runexamples.models.ExampleStatic.DoesNotExist:
      exSt=runexamples.models.ExampleStatic()
      exSt.exampleName=example
    try:
      ex=runexamples.models.Run.objects.getCurrent(args.buildType).examples.get(exampleName=example)
      print("Copy to reference: "+example)
    except:
      print("Skipping: "+example)
      continue
    exSt.references.all().delete()
    exSt.refTime=ex.time
    exSt.save()
    for fnglob in ["*.fmuh5", "*.mbsh5", "*.ombvh5"]:
      for fn in glob.glob(pj(example, fnglob)):
        ref=runexamples.models.ExampleStaticReference()
        ref.exampleStatic=exSt
        ref.h5FileName=os.path.basename(fn)
        with open(fn, "rb") as l:
          data=l.read()
        ref.h5FileSHA1=hashlib.sha1(data).hexdigest()
        ref.save()
        with ref.h5File.open("wb") as f:
          with open(fn, "rb") as l:
            base.helper.copyFile(l, f)
        ref.save()

def updateReference():
  import requests
  rs=requests.Session()

  print('Downloading metadata for all references from %s\n'%(args.updateURL))
  sys.stdout.flush()

  # get metadata of all static examples (does not get any reference file)
  response=rs.get(args.updateURL+django.urls.reverse("runexamples:allExampleStatic"))
  if response.status_code!=200:
    raise RuntimeError("Cannot get allExampleStatic")
  serverAllExampleStatic=response.json()

  # loop over all examples
  for example in directories:
    # skip examples not on server
    if example not in serverAllExampleStatic:
      print('%s: SKIPPING, does not exist on server'%(example))
      sys.stdout.flush()
      continue
    # get server and local example
    serverExampleStatic=serverAllExampleStatic[example]
    localExampleStatic, _=runexamples.models.ExampleStatic.objects.get_or_create(exampleName=example)
    # set refTime from server
    localExampleStatic.refTime=datetime.timedelta(seconds=serverExampleStatic["refTime"]) \
                               if serverExampleStatic["refTime"] is not None else None
    # loop over all reference files
    for serverReference in serverExampleStatic["references"]:
      # get/create local reference (skip if already up to date)
      localReference=next((l for l in localExampleStatic.references.all() if l.h5FileName==serverReference["h5FileName"]), None)
      if localReference is None:
        localReference=runexamples.models.ExampleStaticReference()
        localReference.exampleStatic=localExampleStatic
      elif serverReference["h5FileSHA1"]==localReference.h5FileSHA1:
        print(example+": "+serverReference["h5FileName"]+": SKIPPING, already up to date")
        sys.stdout.flush()
        continue
      # newer reference exists -> download
      print(example+": "+serverReference["h5FileName"]+": DOWNLOADING new reference file ...")
      sys.stdout.flush()
      # set new SHA1 and delete old file
      localReference.h5FileSHA1=serverReference["h5FileSHA1"]
      localReference.h5File.delete(False)
      # set, download and save new file
      localReference.h5FileName=serverReference["h5FileName"]
      localReference.save()
      response=rs.get(args.updateURL+django.urls.reverse("base:fileDownloadFromDB",
                      args=["runexamples", "ExampleStaticReference", serverReference["id"], "h5File"]))
      if response.status_code!=200:
        raise RuntimeError("Download of reference file failed.")
      with localReference.h5File.open("wb") as f:
        base.helper.copyFile(response.content, f)
      localReference.save()
    # save local example
    localExampleStatic.save()
    # search for local reference files not on server -> delete these
    for localReference in localExampleStatic.references.all():
      if next((x for x in serverExampleStatic["references"] if x["h5FileName"]==localReference.h5FileName), None) is None:
        print(example+": "+localReference.h5FileName+": REMOVED, does not exist on server")
        sys.stdout.flush()
        localReference.delete()



def listExamples():
  print('The following examples will be run:\n')
  for example in directories:
    print(example)
  sys.stdout.flush()



def validateXML(ex):
  nrFailed=0
  types=["*.ombvx", # validate openmbv files generated by MBSim
         "*.flat.mbsx"] # validate user mbsim flat xml files
  for root, _, filenames in os.walk(os.curdir):
    for typesKey in types:
      for filename in fnmatch.filter(filenames, typesKey):
        xmlOut=runexamples.models.XMLOutput()
        xmlOut.example=ex
        xmlOut.filename=filename

        outputFD=base.helper.MultiFile(args.printToConsole)
        print("Running command:", file=outputFD)
        xmlOut.resultOK=True
        if base.helper.subprocessCall(exePrefix()+[mbxmlutilsvalidate]+\
           (["--xmlCatalog", exePathConvert(xmlCatalog)] if xmlCatalog else [])+\
           [pj(root, filename)], outputFD)!=0:
          nrFailed+=1
          xmlOut.resultOK=False
        outputFD.close()
        xmlOut.resultOutput=outputFD.getData().replace("\0", "&#00;")
        xmlOut.save()
  ex.xmlOutputsFailed=ex.xmlOutputs.filterFailed().count()
  ex.save()
  return nrFailed

@functools.lru_cache(maxsize=1)
def getHeaderMap():
  # collect all header files in repos and hash it
  repoHeader={}
  repos=["fmatvec", "hdf5serie", "openmbv", "mbsim"]
  for repo in repos:
    for root, _, files in os.walk(pj(args.sourceDir, repo)):
      for f in files:
        if f.endswith(".h"):
          repoHeader[hashlib.sha1(codecs.open(pj(root, f), "r", encoding="utf-8").read().encode("utf-8")).hexdigest()]=pj(root, f)
  # loop over all header files in local and create mapping (using the hash)
  headerMap={}
  for root, _, files in os.walk(pj(args.prefix, "include")):
    for f in files:
      if f.endswith(".h"):
        h=hashlib.sha1(codecs.open(pj(root, f), "r", encoding="utf-8").read().encode("utf-8")).hexdigest()
        if h in repoHeader:
          headerMap[pj(root, f)]=repoHeader[h]
  return headerMap

# restore or backup the coverage files in the build directories
def coverageBackupRestore(variant):
  for t in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
    d=pj(args.sourceDir, t+args.binSuffix)
    for root, _, files in os.walk(d):
      for f in sorted(files):
        if variant=="backup":
          if f.endswith(".gcda"):
            shutil.copyfile(pj(root, f), pj(root, f+".beforeRunexamples"))
        if variant=="restore":
          if f.endswith(".gcda"): # is processed before .gcda.beforeRunexamples: files is sotred
            os.remove(pj(root, f))
          if f.endswith(".gcda.beforeRunexamples"): # is processed after .gcda: files is sotred
            shutil.move(pj(root, f), pj(root, os.path.splitext(f)[0]))
def coverage(exRun, lcovResultFile=None):
  import requests

  # buildRepos
  buildRepos=[
    {"gitURL": "https://github.com/mbsim-env/fmatvec.git", "sourcefileURL": "https://raw.githubusercontent.com/mbsim-env/fmatvec/{sha}/{repofile}"},
    {"gitURL": "https://github.com/mbsim-env/hdf5serie.git", "sourcefileURL": "https://raw.githubusercontent.com/mbsim-env/hdf5serie/{sha}/{repofile}"},
    {"gitURL": "https://github.com/mbsim-env/openmbv.git", "sourcefileURL": "https://raw.githubusercontent.com/mbsim-env/openmbv/{sha}/{repofile}"},
    {"gitURL": "https://github.com/mbsim-env/mbsim.git", "sourcefileURL": "https://raw.githubusercontent.com/mbsim-env/mbsim/{sha}/{repofile}"},
  ]
  buildRepos+=args.buildConfig.get("buildRepos", [])

  ret=0
  lcovFD=base.helper.MultiFile(args.printToConsole)
  # lcov "-d" arguments
  dirs=map(lambda x: ["-d", pj(args.sourceDir, x),
                      "-d", pj(args.sourceDir, x+args.binSuffix)],
                     list(map(lambda repo: repo["gitURL"].split("/")[-1][0:-4], buildRepos)))
  dirs=["-d", args.prefix]+[v for il in dirs for v in il]

  # replace header map in lcov trace file
  def lcovAdjustFileNames(lcovFilename):
    headerMap=getHeaderMap()
    for line in fileinput.FileInput(lcovFilename, inplace=1):
      if line.startswith("SF:"):
        oldFilename=line[len("SF:"):].rstrip()
        newFilename=headerMap.get(oldFilename, oldFilename)
        line="SF:"+newFilename+"\n"
      print(line, end="")

  tempDir=tempfile.mkdtemp()
  try:
    # run lcov: init counters
    ret=ret+abs(base.helper.subprocessCall(["lcov", "-q", "-c", "--no-external", "-i", "--ignore-errors", "graph", "-o", pj(tempDir, "cov.trace.base")]+dirs, lcovFD))
    lcovAdjustFileNames(pj(tempDir, "cov.trace.base"))
    # run lcov: count
    ret=ret+abs(base.helper.subprocessCall(["lcov", "-q", "-c", "--no-external", "-o", pj(tempDir, "cov.trace.test")]+dirs, lcovFD))
    lcovAdjustFileNames(pj(tempDir, "cov.trace.test"))
    # run lcov: combine counters
    ret=ret+abs(base.helper.subprocessCall(["lcov", "-q", "-a", pj(tempDir, "cov.trace.base"), "-a", pj(tempDir, "cov.trace.test"), "-o", pj(tempDir, "cov.trace.total")], lcovFD))
    # add coverage date from partitioned run
    if args.post:
      for covPartFinal in glob.glob(pj(args.prefix, "cov.trace.final.part."+args.buildType+".*")):
        shutil.move(pj(tempDir, "cov.trace.total"), pj(tempDir, "cov.trace.total-part"))
        ret=ret+abs(base.helper.subprocessCall(["lcov", "-q", "-a", pj(tempDir, "cov.trace.total-part"), "-a",
                    covPartFinal, "-o", pj(tempDir, "cov.trace.total")], lcovFD))
    # run lcov: remove counters
    ret=ret+abs(base.helper.subprocessCall(["lcov", "-r", pj(tempDir, "cov.trace.total"),
      "/mbsim-env/mbsim-*/kernel/swig/*", "/mbsim-env/openmbv-*/openmbvcppinterface/swig/java/*", # SWIG generated
      "/mbsim-env/openmbv-*/openmbvcppinterface/swig/octave/*", "/mbsim-env/openmbv-*/openmbvcppinterface/swig/python/*", # SWIG generated
      "/mbsim-env/openmbv-*/mbxmlutils/mbxmlutils/*", # SWIG generated
      "/mbsim-env/mbsim*/thirdparty/nurbs++/*/*", "*/include/nurbs++/*", "/mbsim-env/mbsim*/kernel/mbsim/numerics/csparse.*", # 3rd party
      "/mbsim-env/mbsim*/examples/*", # mbsim examples
      "*.moc.cc", # mbsim generated
      "/mbsim-env/*/CMakeFiles/*", "/mbsim-env/*/CMakeFiles/*/*", "/mbsim-env/*/CMakeFiles/*/*/*", # cmake generated
      "/mbsim-env/hdf5serie*/h5plotserie/h5plotserie/*", "/mbsim-env/openmbv*/openmbv/openmbv/*", "/mbsim-env/mbsim*/mbsimgui/mbsimgui/*", # GUI (untested)
      "/mbsim-env/mbsim*/modules/mbsimInterface/mbsimInterface/*" # other untested features
      ]+args.buildConfig.get("coverageExcludes", [])+\
      ["-o", pj(tempDir, "cov.trace.final")], lcovFD))
    if lcovResultFile is not None:
      shutil.copyfile(pj(tempDir, "cov.trace.final"), lcovResultFile)
      return 0

    # get coverage rate
    covRate=0
    linesRE=re.compile("^ *lines\.*: *([0-9]+\.[0-9]+)% ")
    for line in reversed(lcovFD.getData().splitlines()):
      m=linesRE.match(line)
      if m is not None:
        covRate=float(m.group(1))
        break

    # set coverage info on exRun
    lcovFD.close()
    exRun.coverageOK=ret==0
    exRun.coverageRate=covRate
    exRun.coverageOutput=lcovFD.getData().replace("\0", "&#00;")
    exRun.coverageFileName="cov.trace.final"
    exRun.save()
    with exRun.coverageFile.open("wb") as fo:
      with open(pj(tempDir, exRun.coverageFileName), "rb") as fi:
        base.helper.copyFile(fi, fo)

    # save coverage file to prefix dir
    shutil.copyfile(pj(tempDir, "cov.trace.final"), args.prefix+"/cov.trace.final")

    return 1 if ret!=0 else 0
  finally:
    if not os.path.isfile("/.dockerenv"): # keep the temp dir when running in docker
      shutil.rmtree(tempDir)

# An iterable of all examples using server side dynamic queueing.
class ExampleServerQueue:
  def __init__(self, field):
    self.field=field
  def __iter__(self):
    self.startTime=None
    return self
  def __next__(self):
    if self.startTime is not None:
      endTime=datetime.datetime.now()
      setattr(self.es, self.field, endTime-self.startTime)
      self.es.save()
    with django.db.transaction.atomic():
      self.es=runexamples.models.ExampleStatic.objects.filter(exampleName__in=directories, queued=True).select_for_update().\
          order_by(django.db.models.F(self.field).desc(nulls_first=True)).first()
      if self.es is None:
        raise StopIteration
      self.es.queued=False
      self.es.save()
    self.startTime=datetime.datetime.now()
    return self.es.exampleName



#####################################################################################
# call the main routine
#####################################################################################

if __name__=="__main__":
  mainRet=main()
  django.db.connections.close_all()
  if mainRet<0: # fatal error
    sys.exit(1)
  sys.exit(0)

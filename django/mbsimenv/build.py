#!/usr/bin/env python3

# imports
import sys
import os
import argparse
from os.path import join as pj
import subprocess
import re
import datetime
import shutil
import json
import io
import django
import base.helper
import mbsimenvSecrets
import builds
import tempfile
import psutil
import copy
import multiprocessing

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

# global variables
toolDependencies=dict()
docDir=None
args=None

def parseArguments():
  # command line option definition
  argparser=argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='''Building the MBSim-Environment.
  
  After building this script can also run the examples.
  All unknown options are passed to the run example script.'''
  )
  
  mainOpts=argparser.add_argument_group('Main Options')
  mainOpts.add_argument("--sourceDir", type=str, required=True,
    help="The base source/build directory (see --binSuffix for VPATH builds")
  configOpts=mainOpts.add_mutually_exclusive_group(required=True)
  configOpts.add_argument("--prefix", type=str, help="run configure using this directory as prefix option")
  configOpts.add_argument("--recheck", action="store_true",
    help="run config.status --recheck instead of configure")
  
  cfgOpts=argparser.add_argument_group('Configuration Options')
  cfgOpts.add_argument("-j", default=max(1,min(round(psutil.virtual_memory().total/pow(1024,3)/2),psutil.cpu_count(False))), type=int, help="Number of jobs to run in parallel (for make and examples)")
  cfgOpts.add_argument("--toolJobs", default=1, type=int, help="Number of tools to run in parallel (tool parallelization)")
  cfgOpts.add_argument("--forceBuild", action="store_true", help="Force building even if --buildSystemRun is used and no new commits exist")
  cfgOpts.add_argument("--buildTools", action="append", type=str, help="The list of tools to build. Build all tools if not specified.")
  
  cfgOpts.add_argument("--enableCleanPrefix", action="store_true", help="Remove the prefix dir completely before starting")
  cfgOpts.add_argument("--disableUpdate", action="store_true", help="Do not update repositories")
  cfgOpts.add_argument("--disablePreConfigure", action="store_true", help="Do not manually run autotool (aclocal, libtoolize, ...). 'make' may still trigger it")
  cfgOpts.add_argument("--disableConfigure", action="store_true", help="Do not manually configure. 'make' may still trigger it")
  cfgOpts.add_argument("--disableMakeClean", action="store_true", help="Do not 'make clean'")
  cfgOpts.add_argument("--disableMakeInstall", action="store_true", help="Do not 'make install'")
  cfgOpts.add_argument("--disableMake", action="store_true", help="Do not 'make clean', 'make' and 'make install'")
  cfgOpts.add_argument("--disableMakeCheck", action="store_true", help="Do not 'make check'")
  cfgOpts.add_argument("--disableDoxygen", action="store_true", help="Do not build the doxygen doc")
  cfgOpts.add_argument("--disableXMLDoc", action="store_true", help="Do not build the XML doc")
  cfgOpts.add_argument("--disableRunExamples", action="store_true", help="Do not run examples")
  cfgOpts.add_argument("--enableDistribution", action="store_true", help="Create a release distribution archive (only usefull on the buildsystem)")
  cfgOpts.add_argument("--binSuffix", default="", help='base tool name suffix for the binary (build) dir in --sourceDir (default: "" = no VPATH build)')
  cfgOpts.add_argument("--fmatvecBranch", default="", help='fmatvec branch[*SHA[*T]] to use (T:Triggered this build else not triggered)')
  cfgOpts.add_argument("--hdf5serieBranch", default="", help='hdf5serierepo branch[*SHA[*T]] to use (T:Triggered this build else not triggered)')
  cfgOpts.add_argument("--openmbvBranch", default="", help='openmbv branch[*SHA[*T]] to use (T:Triggered this build else not triggered)')
  cfgOpts.add_argument("--mbsimBranch", default="", help='mbsim branch[*SHA[*T]] to use (T:Triggered this build else not triggered)')
  cfgOpts.add_argument("--buildSystemRun", action="store_true", help='Run in build system mode: generate build system state files.')
  cfgOpts.add_argument("--localServerPort", type=int, default=27583, help='Port for local server, if started automatically.')
  cfgOpts.add_argument("--coverage", action="store_true", help='Enable coverage analyzis using gcov/lcov.')
  cfgOpts.add_argument("--buildFailedExit", default=None, type=int, help='Define the exit code when the build fails.')
  cfgOpts.add_argument("--buildRunID", default=None, type=int, help='Internal: use a already created Run ID.')
  cfgOpts.add_argument("--makeProg", default=shutil.which("make"), type=str, help='Program to use as make (should be a gmake compatible make)')
  cfgOpts.add_argument("--buildConfig", type=json.loads, default={}, help="Load an additional build(/examples) configuration as json string")
  
  outOpts=argparser.add_argument_group('Output Options')
  outOpts.add_argument("--buildType", default="local", type=str, help="A description of the build type (e.g: linux64-dailydebug)")
  outOpts.add_argument("--executor", default='<span class="MBSIMENV_EXECUTOR_LOCAL">local</span>', type=str, help="The executor of this run (can contain simple HTML a-elements)")
  outOpts.add_argument("--removeOlderThan", default=3 if os.environ.get("MBSIMENVTAGNAME", "")=="staging" else 30,
                       type=int, help="Remove all build reports older than X days but keep at least the last X.")
  
  passOpts=argparser.add_argument_group('Options beeing passed to other commands')
  passOpts.add_argument("--passToRunexamples", default=list(), nargs=argparse.REMAINDER,#mfmf replace this option by buildConfig?
    help="pass all following options, up to but not including the next --passTo* argument, to run examples.")
  passOpts.add_argument("--passToConfigure", default=list(), nargs=argparse.REMAINDER,#mfmf replace this option by buildConfig?
    help="pass all following options, up to but not including the next --passTo* argument, to configure.")
  passOpts.add_argument("--passToCMake", default=list(), nargs=argparse.REMAINDER,#mfmf replace this option by buildConfig?
    help="pass all following options, up to but not including the next --passTo* argument, to configure.")
  
  # parse command line options:
   
  def firstPassToIndex(args):
    arg=next(filter(lambda x: x.startswith("--passTo"), args), None)
    if arg is None:
      return len(args)
    return args.index(arg)

  # parse all options before --passToConfigure, --passToCMake, --passToRunexamples by argparser. 
  global args
  args=argparser.parse_args(args=sys.argv[1:firstPassToIndex(sys.argv)])
  if base.helper.getExecutorID(args.executor)=="LOCAL" and args.disableUpdate==False:
    print("Adding --disableUpdate to arguments: git update is not supported for local builds.")
    args.disableUpdate=True
  restArgs=sys.argv[firstPassToIndex(sys.argv):]
  # extract --passTo* args
  while True:
    if len(restArgs)>0:
      nextPassTo=firstPassToIndex(restArgs[1:])+1
      setattr(args, restArgs[0][2:], restArgs[1:nextPassTo])
      restArgs=restArgs[firstPassToIndex(restArgs[1:])+1:]
    else:
      break

# create main documentation page
def mainDocPage():
  if not args.buildSystemRun or args.buildType!="linux64-dailydebug":
    return

  print("Copy documentation")
  def rsyncToFileStorage(src, dst, msg=""):
    params=django.conf.settings.SIMPLE_SFTP_STORAGE_PARAMS
    with tempfile.NamedTemporaryFile(mode='wt') as pwfile:
      pwfile.write(params["password"])
      pwfile.flush()
      if subprocess.call(["sshpass", "-f"+pwfile.name, "rsync", "-a", "--delete",
                          "-e", "ssh -p "+str(params["port"])+" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
                          src+"/",
                          params["username"]+"@"+params["hostname"]+":"+dst+"/"],
                          stderr=subprocess.STDOUT)!=0:
        raise RuntimeError("rsync failed: "+msg)

  staticRuntimeDir="/data/webserverstatic"
  # copy xmldoc
  os.makedirs(os.path.normpath(docDir), exist_ok=True)
  rsyncToFileStorage(os.path.normpath(docDir), pj(staticRuntimeDir, "xmlReference"), "copy xmldoc")
  # copy doc
  os.makedirs(os.path.normpath(pj(docDir, os.pardir, os.pardir, "doc")), exist_ok=True)
  rsyncToFileStorage(os.path.normpath(pj(docDir, os.pardir, os.pardir, "doc")), pj(staticRuntimeDir, "doxygenReference"), "copy doxydoc")

def setGithubStatus(run, state):
  # skip for none build system runs
  if not args.buildSystemRun:
    return

  import github
  if state=="pending":
    description="Build started at %s"%(run.startTime.isoformat())
  elif state=="failure":
    description="Build failed after %.1f min"%((run.endTime-run.startTime).total_seconds()/60)
  elif state=="success":
    description="Build passed after %.1f min"%((run.endTime-run.startTime).total_seconds()/60)
  else:
    raise RuntimeError("Unknown state "+state+" provided")
  try:
    gh=github.Github(mbsimenvSecrets.getSecrets("githubAccessToken"))
    for repo in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
      commit=gh.get_repo("mbsim-env/"+repo).get_commit(getattr(run, repo+"UpdateCommitID"))
      django.db.close_old_connections()
      if os.environ["MBSIMENVTAGNAME"]=="latest":
        commit.create_status(state, "https://"+os.environ['MBSIMENVSERVERNAME']+django.urls.reverse("builds:run", args=[run.id]),
          description, "builds/%s/%s/%s/%s/%s"%(run.buildType, run.fmatvecBranch, run.hdf5serieBranch, run.openmbvBranch, run.mbsimBranch))
      else:
        print("Skipping setting github status, this is the staging system!")
  except:
    if django.conf.settings.DEBUG:
      raise
    else:
      base.helper.handleRecoverableError("build_setGithubStatus", "Original exception avoided to ensure that no secret is printed.")

def removeOldBuilds():
  olderThan=django.utils.timezone.now()-datetime.timedelta(days=args.removeOlderThan)
  keep=builds.models.Run.objects.all().order_by('-startTime')[0:args.removeOlderThan].values("id")
  nrDeleted=builds.models.Run.objects.filter(startTime__lt=olderThan).exclude(id__in=keep).delete()[0]
  if nrDeleted>0:
    print("Deleted %d build runs being older than %d days!"%(nrDeleted, args.removeOlderThan))

# the main routine being called ones
parseArguments()
args.sourceDir=os.path.abspath(args.sourceDir)

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
  if not connection.is_usable(): connection.close()
django.db.models.signals.pre_save.connect(closeUnusableConnection)



def main():

  if django.conf.settings.MBSIMENV_TYPE=="local" or django.conf.settings.MBSIMENV_TYPE=="localdocker":
    localServer=base.helper.startLocalServer(args.localServerPort, django.conf.settings.MBSIMENV_TYPE=="localdocker")

  removeOldBuilds()

  # all tools to be build including the tool dependencies
  global toolDependencies

  toolDependencies={
    #   |ToolName   |WillFail (if WillFail is true no Atom Feed error is reported if this Tool fails somehow)
    'fmatvec': {"willFail": False, "dependsOn": [ # depends on
      ]},
    'hdf5serie/h5plotserie': {"willFail": False, "dependsOn": [ # depends on
        'hdf5serie/hdf5serie',
      ]},
    'hdf5serie/hdf5serie': {"willFail": False, "dependsOn": [ # depends on
        'fmatvec',
      ]},
    'openmbv/mbxmlutils': {"willFail": False, "dependsOn": [ # depends on
        'fmatvec',
      ]},
    'openmbv/openmbv': {"willFail": False, "dependsOn": [ # depends on
        'openmbv/openmbvcppinterface',
        'hdf5serie/hdf5serie',
      ]},
    'openmbv/openmbvcppinterface': {"willFail": False, "dependsOn": [ # depends on
        'hdf5serie/hdf5serie',
        'openmbv/mbxmlutils',
      ]},
    'mbsim/kernel': {"willFail": False, "dependsOn": [ # depends on
        'fmatvec',
        'openmbv/openmbvcppinterface',
      ]},
    'mbsim/modules/mbsimHydraulics': {"willFail": False, "dependsOn": [ # depends on
        'mbsim/kernel',
        'mbsim/modules/mbsimControl',
      ]},
    'mbsim/modules/mbsimFlexibleBody': {"willFail": False, "dependsOn": [ # depends on
        'mbsim/kernel',
        'mbsim/thirdparty/nurbs++',
      ]},
    'mbsim/thirdparty/nurbs++': {"willFail": False, "dependsOn": [ # depends on
      ]},
    'mbsim/modules/mbsimElectronics': {"willFail": False, "dependsOn": [ # depends on
        'mbsim/kernel',
        'mbsim/modules/mbsimControl',
      ]},
    'mbsim/modules/mbsimControl': {"willFail": False, "dependsOn": [ # depends on
        'mbsim/kernel',
      ]},
    'mbsim/modules/mbsimPhysics': {"willFail": False, "dependsOn": [ # depends on
        'mbsim/kernel',
      ]},
    'mbsim/modules/mbsimInterface': {"willFail": False, "dependsOn": [ # depends on
        'mbsim/kernel',
        'mbsim/modules/mbsimControl',
      ]},
    'mbsim/mbsimxml': {"willFail": False, "dependsOn": [ # depends on
        'mbsim/kernel',
        'openmbv/openmbvcppinterface',
        'openmbv/mbxmlutils',
        # dependencies to mbsim modules are only required for correct xmldoc generation and for testing
        'mbsim/modules/mbsimHydraulics',
        'mbsim/modules/mbsimFlexibleBody',
        'mbsim/modules/mbsimElectronics',
        'mbsim/modules/mbsimControl',
        'mbsim/modules/mbsimPhysics',
        'mbsim/modules/mbsimInterface',
      ]},
    'mbsim/mbsimgui': {"willFail": False, "dependsOn": [ # depends on
        'openmbv/openmbv',
        'openmbv/mbxmlutils',
        'mbsim/mbsimxml',
      ]},
    'mbsim/mbsimfmi': {"willFail": False, "dependsOn": [ # depends on
        'mbsim/kernel',
        'mbsim/mbsimxml',
        'mbsim/modules/mbsimControl',
      ]},
  }
  # add command line tools
  toolDependencies.update(copy.deepcopy(args.buildConfig.get("tools", {})))
  # convert dependent list to set (since json does not support sets)
  for t in toolDependencies:
    toolDependencies[t]["dependsOn"]=set(toolDependencies[t]["dependsOn"])

  # set docDir
  global docDir
  docDir=pj(args.prefix, "share", "mbxmlutils", "doc")

  # enable coverage
  if args.coverage:
    os.environ["CFLAGS"]=os.environ.get("CFLAGS", "")+" --coverage"
    os.environ["CXXFLAGS"]=os.environ.get("CXXFLAGS", "")+" --coverage"
    os.environ["LDFLAGS" ]=os.environ.get("LDFLAGS", "")+" --coverage -lgcov"

  # start messsage
  print("Started build process.")
  sys.stdout.flush()

  # clean prefix dir
  if args.enableCleanPrefix and os.path.isdir(args.prefix if args.prefix is not None else args.prefixAuto):
    shutil.rmtree(args.prefix if args.prefix is not None else args.prefixAuto)
  os.makedirs(args.prefix if args.prefix is not None else args.prefixAuto, exist_ok=True)

  if args.buildRunID is None:
    run=builds.models.Run()
  else:
    run=builds.models.Run.objects.get(id=args.buildRunID)
    if run.buildType!=args.buildType or base.helper.getExecutorID(run.executor)!=base.helper.getExecutorID(args.executor) or \
       run.fmatvecUpdateCommitID!=args.fmatvecBranch.split("*")[1] or \
       run.hdf5serieUpdateCommitID!=args.hdf5serieBranch.split("*")[1] or \
       run.openmbvUpdateCommitID!=args.openmbvBranch.split("*")[1] or \
       run.mbsimUpdateCommitID!=args.mbsimBranch.split("*")[1]:
      raise RuntimeError("The externally created Run ID is not valid!")
  run.buildType=args.buildType
  run.executor=args.executor
  run.command=" ".join(sys.argv)
  run.startTime=django.utils.timezone.now()
  run.save()
  # write build info (only build.run.id)
  buildInfo={"buildRunID": run.id}
  with open((args.prefix if args.prefix is not None else args.prefixAuto)+"/.buildInfo.json", "w") as f:
    json.dump(buildInfo, f, indent=2)

  nrFailed=0
  nrRun=0
  # update all repositories
  if not args.disableUpdate:
    nrRun+=1
  localRet, commitidfull=repoUpdate(run, buildInfo)
  if localRet!=0: nrFailed+=1
  # rewrite build info (build.run.id + repo-sha1)
  with open((args.prefix if args.prefix is not None else args.prefixAuto)+"/.buildInfo.json", "w") as f:
    json.dump(buildInfo, f, indent=2)

  if django.conf.settings.MBSIMENV_TYPE=="local" or django.conf.settings.MBSIMENV_TYPE=="localdocker":
    print("Build info is avaiable at: http://%s:%d%s"%(localServer["hostname"], localServer["port"],
          django.urls.reverse("builds:current_buildtype_branch", args=[run.buildType,
            run.fmatvecBranch, run.hdf5serieBranch, run.openmbvBranch, run.mbsimBranch])))
    print("                         = http://%s:%d%s"%(localServer["hostname"], localServer["port"],
          django.urls.reverse("builds:run", args=[run.id])))
    print("")
    sys.stdout.flush()

  # set status on commit
  setGithubStatus(run, "pending")

  # remove all "*.gcno", "*.gcda" files
  if not args.disableMake and not args.disableMakeClean and args.coverage:
    for e in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
      for d,_,files in os.walk(pj(args.sourceDir, e+args.binSuffix)):
        for f in files:
          if os.path.splitext(f)[1]==".gcno": os.remove(pj(d, f))
          if os.path.splitext(f)[1]==".gcda": os.remove(pj(d, f))

  # set default for buildTools
  if args.buildTools is None:
    args.buildTools = list(toolDependencies)

  multiprocessing.set_start_method('spawn') # use same method on Window and Linux (= python>=3.14 default)
  toolPoolCondVar=multiprocessing.Condition() # condition variable to notify about changes in toolPoolJobs
  toolPoolJobs=multiprocessing.Value("i", lock=False) # the lock from the Condition variable one line above guards this
  toolPoolJobs.value=0
  # extend the tool list with the required variables to handle the parallelization
  for toolName in toolDependencies:
    toolDependencies[toolName]["toolCondVar"]=multiprocessing.Condition() # condition variable to notify about changes when a tool is done
    toolDependencies[toolName]["toolDone"]=multiprocessing.Value("b", lock=False) # the lock from the Condition variable one line above guards this
    toolDependencies[toolName]["toolDone"].value=False
    toolDependencies[toolName]["toolNeedsBuild"]=False
    toolDependencies[toolName]["nrFailed"]=multiprocessing.Value("i", lock=False) # no lock needed
    toolDependencies[toolName]["nrRun"]=multiprocessing.Value("i", lock=False) # no lock needed
  # set the toolNeedsBuild flag for all tools and its dependencies to True
  # (this is just needed to check of this tool can be skipped or not)
  def toolNeedsBuild(toolName):
    toolDependencies[toolName]["toolNeedsBuild"]=True
    for dep in toolDependencies[toolName]["dependsOn"]:
      toolNeedsBuild(dep)
  for toolName in args.buildTools:
    toolNeedsBuild(toolName)
  # create the worker thread for each tool ...
  t_=[]
  globalVars={ # can only contain read only variables or shared memory variables
    "toolDependencies": toolDependencies,
    "toolPoolCondVar": toolPoolCondVar,
    "toolPoolJobs": toolPoolJobs,
    "args": args,
    "run": run,
  }
  django.db.connections.close_all() # multiprocessing forks on Linux which cannot be done with open database connections
  for toolName in toolDependencies:
    t=multiprocessing.Process(target=toolWorker, args=(toolName,globalVars))
    t.start()
    t_.append(t)
  # ... and wait for all thread to finish
  for t in t_:
    t.join()
  django.db.connections.close_all() # close connections before finishing a process
  for toolName in toolDependencies:
    nrFailed+=toolDependencies[toolName]["nrFailed"].value
    nrRun+=toolDependencies[toolName]["nrRun"].value

  # update toolsFailed (added to database for performance reasons)
  run.toolsFailed=run.tools.filterFailed().count()
  run.save()

  # write main doc file
  mainDocPage()

  # create distribution
  if args.enableDistribution:
    nrRun=nrRun+1
    print("Create distribution")
    sys.stdout.flush()
    cdRet=createDistribution(run)
    if cdRet!=0:
      nrFailed=nrFailed+1

  run.endTime=django.utils.timezone.now()
  run.save()

  # update status on commitid
  setGithubStatus(run, "success" if nrFailed==0 else "failure")

  if nrFailed>0:
    print("\nERROR: %d of %d build parts failed!!!!!"%(nrFailed, nrRun));
    sys.stdout.flush()

  # run examples
  runExamplesErrorCode=0
  if not args.disableRunExamples:
    savedDir=os.getcwd()
    os.chdir(pj(args.sourceDir, "mbsim", "examples"))
    print("Running examples in "+os.getcwd())
    sys.stdout.flush()
    runExamplesErrorCode=runexamples(run)
    os.chdir(savedDir)

  if runExamplesErrorCode!=0: # fatal error
    return -1
  if nrFailed>0:
    return 1 # build failed
  return 0 # all passed



#####################################################################################
# from now on only functions follow and at the end main is called
#####################################################################################



# this worker thread is created for each tool in parallel ...
def toolWorker(toolName, globalVars):
  global toolDependencies, toolPoolCondVar, toolPoolJobs, args, run
  toolDependencies = globalVars["toolDependencies"]
  toolPoolCondVar = globalVars["toolPoolCondVar"]
  toolPoolJobs = globalVars["toolPoolJobs"]
  args = globalVars["args"]
  run = globalVars["run"]
  nrFailed=0
  nrRun=0
  # ... and waits until the toolDone flag of all dependent tools is True (to ensure the dependent tools are build before) ...
  for dep in toolDependencies[toolName]["dependsOn"]:
    with toolDependencies[dep]["toolCondVar"]:
      while toolDependencies[dep]["toolDone"].value==False:
        toolDependencies[dep]["toolCondVar"].wait()
  # ... than it waits until less then args.toolJobs build jobs are running ...
  with toolPoolCondVar:
    while toolPoolJobs.value>=args.toolJobs:
      toolPoolCondVar.wait()
    # ... if so, the number of running jobs in the build pool is incremented and the build is run ...
    toolPoolJobs.value+=1
  if toolName in args.buildTools or toolDependencies[toolName]["toolNeedsBuild"]:
    # ... by calling build(...) if the tool need to be build ...
    if toolName in args.buildTools:
      print(f"Building {toolName}: requested by user")
    else:
      print(f"Building {toolName}: needed as dependency")
    # build toolName
    nrFailedLocal, nrRunLocal=build(toolName, run)
    if toolDependencies[toolName]["willFail"]==False:
      nrFailed+=nrFailedLocal
      nrRun+=nrRunLocal
  else:
    # ... or by just recording the tool in the DB if the tool does not need to be build ...
    print(f"Building {toolName}: skipped, not requested by user and not needed as dependency")
    sys.stdout.flush()
    tool=builds.models.Tool()
    tool.run=run
    tool.toolName=toolName
    tool.willFail=toolDependencies[toolName]["willFail"]
    tool.save()
  # ... when the build is finished, the buildDon flag of the tool is set a all waiting thread are notified ...
  with toolDependencies[toolName]["toolCondVar"]:
    toolDependencies[toolName]["toolDone"].value=True
    toolDependencies[toolName]["toolCondVar"].notify_all()
  # ... at the end the running jobs in the build pool is decremented and one other thread in the pool is notified
  print(f"Finished {toolName}")
  with toolPoolCondVar:
    toolPoolJobs.value-=1
    toolPoolCondVar.notify()
  toolDependencies[toolName]["nrFailed"]=nrFailed
  toolDependencies[toolName]["nrRun"]=nrRun
  django.db.connections.close_all() # close connections before finishing a process



def buildTool(toolName):
  t=toolName.split(os.path.sep)
  t[0]=t[0]+args.binSuffix
  return os.path.sep.join(t)

def repoUpdate(run, buildInfo):
  ret=0
  savedDir=os.getcwd()
  if not args.disableUpdate:
    print('Updating repositories: ', end="")
    sys.stdout.flush()

  # allRepos
  allRepos=[
    { "gitURL": "https://github.com/mbsim-env/fmatvec.git", # */<localname>.git -> localname is the directory name of the repo
      "sourcefileURL": "https://raw.githubusercontent.com/mbsim-env/fmatvec/{sha}/{repofile}",
      "sourcefilelineURL": "https://github.com/mbsim-env/fmatvec/blob/{sha}/{repofile}#L{line}",
      "repoURL": "https://github.com/mbsim-env/fmatvec",
      "commitURL": "https://github.com/mbsim-env/fmatvec/commit/{sha}",
      "branchURL": "https://github.com/mbsim-env/fmatvec/tree/{branch}",
    },
    { "gitURL": "https://github.com/mbsim-env/hdf5serie.git", # */<localname>.git -> localname is the directory name of the repo
      "sourcefileURL": "https://raw.githubusercontent.com/mbsim-env/hdf5serie/{sha}/{repofile}",
      "sourcefilelineURL": "https://github.com/mbsim-env/hdf5serie/blob/{sha}/{repofile}#L{line}",
      "repoURL": "https://github.com/mbsim-env/hdf5serie",
      "commitURL": "https://github.com/mbsim-env/hdf5serie/commit/{sha}",
      "branchURL": "https://github.com/mbsim-env/hdf5serie/tree/{branch}",
    },
    { "gitURL": "https://github.com/mbsim-env/openmbv.git", # */<localname>.git -> localname is the directory name of the repo
      "sourcefileURL": "https://raw.githubusercontent.com/mbsim-env/openmbv/{sha}/{repofile}",
      "sourcefilelineURL": "https://github.com/mbsim-env/openmbv/blob/{sha}/{repofile}#L{line}",
      "repoURL": "https://github.com/mbsim-env/openmbv",
      "commitURL": "https://github.com/mbsim-env/openmbv/commit/{sha}",
      "branchURL": "https://github.com/mbsim-env/openmbv/tree/{branch}",
    },
    { "gitURL": "https://github.com/mbsim-env/mbsim.git", # */<localname>.git -> localname is the directory name of the repo
      "sourcefileURL": "https://raw.githubusercontent.com/mbsim-env/mbsim/{sha}/{repofile}",
      "sourcefilelineURL": "https://github.com/mbsim-env/mbsim/blob/{sha}/{repofile}#L{line}",
      "repoURL": "https://github.com/mbsim-env/mbsim",
      "commitURL": "https://github.com/mbsim-env/mbsim/commit/{sha}",
      "branchURL": "https://github.com/mbsim-env/mbsim/tree/{branch}",
    },
  ]
  allRepos+=args.buildConfig.get("addRepos", [])

  commitidfull={}
  buildInfo["repo"]={}
  for repoDict in allRepos:
    repo=repoDict["gitURL"].split("/")[-1][0:-4]
    os.chdir(pj(args.sourceDir, repo))
    # update
    repoUpdFD=io.StringIO()
    retlocal=0

    # workaround for a git bug when using with an unknown user (fixed with git >= 2.6)
    os.environ["GIT_COMMITTER_NAME"]="dummy"
    os.environ["GIT_COMMITTER_EMAIL"]="dummy"

    branchSplit=getattr(args, repo+"Branch", "master").split("*")
    if not args.disableUpdate:
      # write repUpd output to report dir
      print('Fetch remote repository '+repo+":", file=repoUpdFD)
      repoUpdFD.flush()
      branch=branchSplit[0]
      sha=branchSplit[1 if len(branchSplit)>=2 and branchSplit[1]!="" else 0]
      retlocal+=abs(base.helper.subprocessCall(["git", "checkout", "-q", "HEAD~0"], repoUpdFD))
      base.helper.subprocessCall(["git", "branch", "-q", "-D", branch], repoUpdFD)
      retlocal+=abs(base.helper.subprocessCall(["git", "fetch", "-q", "-f", "--depth", "1", "origin", sha+":"+branch], repoUpdFD))
      # set branch based on args
      if getattr(args, repo+'Branch', "master")!="":
        branch=branchSplit[0]
        print('Checkout branch '+getattr(args, repo+'Branch', "master")+' in repository '+repo+":", file=repoUpdFD)
        retlocal+=abs(base.helper.subprocessCall(["git", "checkout", "-q", branch], repoUpdFD))
        repoUpdFD.flush()
    # get branch and commit
    branch=base.helper.subprocessCheckOutput(["git", "rev-parse", "--abbrev-ref", "HEAD"], repoUpdFD).rstrip()
    commitidfull[repo]=base.helper.subprocessCheckOutput(["git", "log", "-n", "1", "--format=%H", "HEAD"], repoUpdFD).rstrip()
    commitsub=base.helper.subprocessCheckOutput(["git", "log", "-n", "1", "--format=%s", "HEAD"], repoUpdFD).rstrip()
    authorName=base.helper.subprocessCheckOutput(["git", "log", "-n", "1", "--format=%an", "HEAD"], repoUpdFD).rstrip()
    authorDate=base.helper.subprocessCheckOutput(["git", "log", "-n", "1", "--format=%aI", "HEAD"], repoUpdFD).rstrip()
    ret+=retlocal
    # save
    # NOTE the following fields are currently stored redundant, see models.py
    if repo in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
      setattr(run, repo+"Branch", branch)
      setattr(run, repo+"Triggered", getattr(run, repo+"Triggered") or (len(branchSplit)>2 and branchSplit[2]=="T"))
      if not args.disableUpdate:
        setattr(run, repo+"UpdateOK", retlocal==0)
      setattr(run, repo+"UpdateOutput", repoUpdFD.getvalue().replace("\0", "&#00;"))
      setattr(run, repo+"UpdateCommitID", commitidfull[repo])
      setattr(run, repo+"UpdateMsg", commitsub.encode("utf-8")[:builds.models.Run._meta.get_field(repo+"UpdateMsg").max_length].decode("utf-8", "ignore"))
      setattr(run, repo+"UpdateAuthor", authorName)
      authorDatePy36=re.sub("(:[0-9][0-9][+-][0-9][0-9]):([0-9][0-9])$", "\\1\\2", authorDate) # fix authorDate for Python 3.6
      setattr(run, repo+"UpdateDate", datetime.datetime.strptime(authorDatePy36, '%Y-%m-%dT%H:%M:%S%z'))

    repos=builds.models.Repos()
    repos.run=run
    repos.repoName=repo
    repos.branch=branch
    repos.triggered=getattr(run, repo+"Triggered", False) or repos.triggered or (len(branchSplit)>2 and branchSplit[2]=="T")
    if not args.disableUpdate:
      repos.updateOK=retlocal==0
    repos.updateOutput=repoUpdFD.getvalue().replace("\0", "&#00;")
    repos.updateCommitID=commitidfull[repo]
    repos.updateMsg=commitsub.encode("utf-8")[:builds.models.Repos._meta.get_field("updateMsg").max_length].decode("utf-8", "ignore")
    repos.updateAuthor=authorName
    authorDatePy36=re.sub("(:[0-9][0-9][+-][0-9][0-9]):([0-9][0-9])$", "\\1\\2", authorDate) # fix authorDate for Python 3.6
    repos.updateDate=datetime.datetime.strptime(authorDatePy36, '%Y-%m-%dT%H:%M:%S%z')
    repos.gitURL=repoDict["gitURL"]
    repos.sourcefileURL=repoDict["sourcefileURL"]
    repos.sourcefilelineURL=repoDict["sourcefilelineURL"]
    repos.repoURL=repoDict["repoURL"]
    repos.commitURL=repoDict["commitURL"]
    repos.branchURL=repoDict["branchURL"]
    repos.save()
    # NOTE end
    run.save()
    repoUpdFD.close()
    buildInfo["repo"][repo]=branch+"*"+commitidfull[repo]
  # for daily builds set the triggered flag for every repo with a change wrt the last daily build
  if "daily" in args.buildType:
    previousRun=run.getPrevious()
    for repo in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
      if getattr(previousRun, repo+"UpdateCommitID")!=commitidfull[repo]:
        setattr(run, repo+"Triggered", True)#mfmf
        run.save()
        try:
          r = run.repos.get(repoName=repo)
          r.triggered=True
          r.save()
        except builds.models.Repos.DoesNotExist:
          pass

  if not args.disableUpdate:
    if ret>0:
      print('failed')
    else:
      print('passed')
    sys.stdout.flush()

  os.chdir(savedDir)
  return ret, commitidfull



def build(toolName, run):
  nrFailed=0
  nrRun=0

  tool=builds.models.Tool()
  tool.run=run
  tool.toolName=toolName
  tool.willFail=toolDependencies[toolName]["willFail"]
  tool.save()

  savedDir=os.getcwd()
  if not os.path.exists(pj(args.sourceDir, buildTool(tool.toolName))): os.makedirs(pj(args.sourceDir, buildTool(tool.toolName)))

  # configure
  failed, run=configure(tool)
  nrFailed+=failed
  nrRun+=run

  # cd to build dir
  os.chdir(savedDir)
  os.chdir(pj(args.sourceDir, buildTool(tool.toolName)))

  # make
  failed, run=make(tool)
  nrFailed+=failed
  nrRun+=run

  # make check
  failed, run=check(tool)
  nrFailed+=failed
  nrRun+=run

  # doxygen
  failed, run=doc(tool, args.disableDoxygen, "doc")
  nrFailed+=failed
  nrRun+=run

  # xmldoc
  failed, run=doc(tool, args.disableXMLDoc, "xmldoc")
  nrFailed+=failed
  nrRun+=run

  os.chdir(savedDir)

  return nrFailed, nrRun



def configure(tool):
  configureFD=io.StringIO()
  savedDir=os.getcwd()
  cmake=not os.path.exists(pj(args.sourceDir, tool.toolName, "configure.ac"))
  run=0
  try:
    if not cmake and (not args.disableConfigure or not os.path.exists(pj(args.sourceDir, buildTool(tool.toolName), "config.status"))):
      run=1
      # pre configure
      if not args.disablePreConfigure or not os.path.exists(pj(args.sourceDir, buildTool(tool.toolName), "config.status")):
        os.chdir(savedDir)
        os.chdir(pj(args.sourceDir, tool.toolName))
        print("\n\nRUNNING aclocal\n", file=configureFD); configureFD.flush()
        if base.helper.subprocessCall(["aclocal", "--force"], configureFD, runInBash=True)!=0:
          raise RuntimeError("aclocal failed")
        print("\n\nRUNNING autoheader\n", file=configureFD); configureFD.flush()
        if base.helper.subprocessCall(["autoheader", "--force"], configureFD, runInBash=True)!=0:
          raise RuntimeError("autoheader failed")
        print("\n\nRUNNING libtoolize\n", file=configureFD); configureFD.flush()
        if base.helper.subprocessCall(["libtoolize", "-c", "--force"], configureFD, runInBash=True)!=0:
          raise RuntimeError("libtoolize failed")
        print("\n\nRUNNING automake\n", file=configureFD); configureFD.flush()
        if base.helper.subprocessCall(["automake", "-a", "-c", "-f"], configureFD, runInBash=True)!=0:
          raise RuntimeError("automake failed")
        print("\n\nRUNNING autoconf\n", file=configureFD); configureFD.flush()
        if base.helper.subprocessCall(["autoconf", "--force"], configureFD, runInBash=True)!=0:
          raise RuntimeError("autoconf failed")
        print("\n\nRUNNING autoreconf\n", file=configureFD); configureFD.flush()
        if base.helper.subprocessCall(["autoreconf", "--force"], configureFD, runInBash=True)!=0:
          raise RuntimeError("autoreconf failed")
      # configure
      os.chdir(savedDir)
      os.chdir(pj(args.sourceDir, buildTool(tool.toolName)))
      print("\n\nRUNNING configure\n", file=configureFD); configureFD.flush()
      if args.prefix is None:
        if base.helper.subprocessCall(["./config.status", "--recheck"], configureFD, runInBash=True)!=0:
          raise RuntimeError("configure failed")
      else:
        command=[os.path.relpath(pj(args.sourceDir, tool.toolName, "configure")), "--prefix", args.prefix] # use relpath to configure script to avoid Windows/Unix path problems with msys2
        command.extend(args.passToConfigure)
        pkgConfigDir=os.path.normpath(pj(args.prefix, "lib", "pkgconfig"))
        if "PKG_CONFIG_PATH" in os.environ:
          pkgConfigDir=pkgConfigDir+os.pathsep+os.environ["PKG_CONFIG_PATH"]
        if base.helper.subprocessCall(command+["PKG_CONFIG_PATH="+pkgConfigDir], configureFD, runInBash=True)!=0:
          raise RuntimeError("configure failed")
    elif cmake and (not args.disableConfigure or not os.path.exists(pj(args.sourceDir, buildTool(tool.toolName), "CMakeCache.txt"))):
      run=1
      os.chdir(savedDir)
      os.chdir(pj(args.sourceDir, buildTool(tool.toolName)))
      # run cmake
      print("\n\nRUNNING cmake\n", file=configureFD); configureFD.flush()
      if os.path.exists(pj(args.sourceDir, buildTool(tool.toolName), "CMakeCache.txt")):
        os.remove(pj(args.sourceDir, buildTool(tool.toolName), "CMakeCache.txt"))
      if args.prefix is None:
        raise RuntimeError("Rerun cmake not supported. You must provide --prefix.")
      else:
        cmakeCmd=shutil.which("cmake3")
        if cmakeCmd is None: cmakeCmd="cmake"
        command=[cmakeCmd, pj(args.sourceDir, tool.toolName), "-GNinja", "-DCMAKE_INSTALL_PREFIX="+args.prefix]
        command.extend(args.passToCMake)
        command.extend(args.buildConfig.get("cmake", []))
        if base.helper.subprocessCall(command, configureFD)!=0:
          raise RuntimeError("configure failed")
    else:
      print("configure disabled", file=configureFD); configureFD.flush()

    result="done"
  except Exception as ex:
    result=str(ex)
  if not args.disableConfigure:
    filename="config.log" if not cmake else "CMakeCache.txt"
    print("\n\n\n\n\nCONTENT OF %s\n"%(filename), file=configureFD)
    try:
      with open(filename, "r") as f:
        configureFD.write(f.read())
    except:
      pass
    tool.configureOK=result=="done"
  tool.configureOutput=configureFD.getvalue().replace("\0", "&#00;")
  tool.save()
  configureFD.close()
  os.chdir(savedDir)

  if result!="done":
    return 1, run
  return 0, run



def make(tool):
  makeFD=io.StringIO()
  run=0
  cmake=not os.path.exists(pj(args.sourceDir, tool.toolName, "configure.ac"))
  buildCmd=[args.makeProg] if not cmake else ["ninja", "-v"]
  try:
    if not args.disableMake:
      run=1
      # build
      errStr=""
      if not args.disableMakeClean:
        print("\n\nRUNNING clean\n", file=makeFD); makeFD.flush()
        if base.helper.subprocessCall(buildCmd+["clean"], makeFD)!=0:
          errStr=errStr+"clean failed; "
      print("\n\nRUNNING build\n", file=makeFD); makeFD.flush()
      if base.helper.subprocessCall(buildCmd+["-k"]+([] if not cmake else [str(1000000)])+["-j", str(args.j)],
                         makeFD)!=0:
        errStr=errStr+"build failed; "
      if not args.disableMakeInstall:
        print("\n\nRUNNING install\n", file=makeFD); makeFD.flush()
        if base.helper.subprocessCall(buildCmd+["-k"]+([] if not cmake else [str(1000000)])+["install"], makeFD)!=0:
          errStr=errStr+"install failed; "
      if errStr!="": raise RuntimeError(errStr)
    else:
      print("make disabled", file=makeFD); makeFD.flush()

    result="done"
  except Exception as ex:
    result=str(ex)
  if not args.disableMake:
    tool.makeOK=result=="done"
  # configure was disable but needs to be run then ...
  if tool.configureOK is None and tool.configureOutput!="":
    # ... copy the output from configureOutput to makeOutput and append the output of make
    tool.makeOutput=tool.configureOutput+"\n\n\n\n\n"+makeFD.getvalue().replace("\0", "&#00;")
    tool.configureOutput=""
  else:
    # ... else just use the output of make
    tool.makeOutput=makeFD.getvalue().replace("\0", "&#00;")
  tool.save()
  makeFD.close()
  ret=0
  if result!="done":
    ret=ret+1
  return ret, run



# return true for autotools build and true for cmake builds if a target named target exits
def existsTarget(tool, target):
  cmake=not os.path.exists(pj(args.sourceDir, tool.toolName, "configure.ac"))
  targetExists=True
  if cmake:
    targetExists=False
    try:
      for line in base.helper.subprocessCheckOutput(["ninja", "-t", "targets"]).splitlines():
        if line.startswith(target+":"):
          targetExists=True;
          break
    except:
      pass
  return targetExists



def check(tool):
  checkFD=io.StringIO()
  run=0
  cmake=not os.path.exists(pj(args.sourceDir, tool.toolName, "configure.ac"))
  buildCmd=[args.makeProg] if not cmake else ["ninja", "-v"]
  if not args.disableMakeCheck:
    run=1
    # check
    print("RUNNING check\n", file=checkFD); checkFD.flush()
    if existsTarget(tool, "check"):
      if base.helper.subprocessCall(buildCmd+["-k"]+([] if not cmake else [str(1000000)])+["-j", str(args.j), "check"], checkFD)==0:
        result="done"
      else:
        result="failed"
    else:
      checkFD.write("No check target");
      result="done"
  else:
    print("make check disabled", file=checkFD); checkFD.flush()
    result="done"

  if not cmake:
    for rootDir,_,files in os.walk('.'): # append all .log files of all tests
      for f in files:
        if f.endswith(".trs"):
          fLog=f[0:-4]+".log"
          checkFD.write('\n\n\n\n\nCONTENT OF '+pj(rootDir, fLog)+"\n\n")
          with open(pj(rootDir, fLog), "r") as f:
            checkFD.write(f.read())
  if not args.disableMakeCheck:
    tool.makeCheckOK=result=="done"
  tool.makeCheckOutput=checkFD.getvalue().replace("\0", "&#00;")
  tool.save()
  checkFD.close()

  if result!="done":
    return 1, run
  return 0, run



def doc(tool, disabled, docDirName):
  if not os.path.isdir(pj(args.sourceDir, tool.toolName, docDirName)):
    return 0, 0
  cmake=not os.path.exists(pj(args.sourceDir, tool.toolName, "configure.ac"))

  docFD=io.StringIO()
  savedDir=os.getcwd()
  run=0
  try:
    if not cmake and not disabled:
      os.chdir(pj(args.sourceDir, buildTool(tool.toolName), docDirName))
      run=1
      # make doc
      errStr=""
      print("\n\nRUNNING make clean\n", file=docFD); docFD.flush()
      if base.helper.subprocessCall([args.makeProg, "clean"], docFD)!=0:
        errStr=errStr+"make clean failed; "
      # "make install" calls "make" calling both may run "make" twice -> to avoid this we just run "make install"
      print("\n\nRUNNING make install\n", file=docFD); docFD.flush()
      if base.helper.subprocessCall([args.makeProg, "-k", "install"], docFD)!=0:
        errStr=errStr+"make install failed; "
      if errStr!="": raise RuntimeError(errStr)
    elif cmake and not disabled:
      os.chdir(pj(args.sourceDir, buildTool(tool.toolName)))
      run=1
      # make doc
      errStr=""
      print("\n\nRUNNING ninja %s-clean\n"%(docDirName), file=docFD); docFD.flush()
      if existsTarget(tool, "doc-clean"):
        if base.helper.subprocessCall(["ninja", "-v", "%s-clean"%(docDirName)], docFD)!=0:
          errStr=errStr+"ninja %s-clean failed; "%(docDirName)
        # "make install" calls "make" calling both may run "make" twice -> to avoid this we just run "make install"
        print("\n\nRUNNING ninja %s-install\n"%(docDirName), file=docFD); docFD.flush()
        if base.helper.subprocessCall(["ninja", "-v", "-k", "1000000", "%s-install"%(docDirName)], docFD)!=0:
          errStr=errStr+"ninja %s-install failed; "%(docDirName)
        if errStr!="": raise RuntimeError(errStr)
      else:
        docFD.write("No doc target");
    else:
      print(docDirName+" disabled", file=docFD); docFD.flush()

    result="done"
  except Exception as ex:
    result=str(ex)
  os.chdir(savedDir)
  if not disabled:
    setattr(tool, docDirName+"OK", result=="done")
  setattr(tool, docDirName+"Output", docFD.getvalue().replace("\0", "&#00;"))
  tool.save()
  docFD.close()

  if result!="done":
    return 1, run
  return 0, run



def runexamples(run):
  if args.disableRunExamples:
    return 0

  # run example command
  command=[sys.executable, os.path.dirname(os.path.realpath(__file__))+"/runexamples.py", "-j", str(args.j), "--buildConfig", json.dumps(args.buildConfig)]
  if args.prefix is not None:
    command.extend(["--prefix", args.prefix])
  if args.coverage:
    command.extend(["--coverage", "--sourceDir", args.sourceDir]+(["--binSuffix="+args.binSuffix] if args.binSuffix!="" else [])+\
                   ["--baseExampleDir", pj(args.sourceDir, "mbsim", "examples")])
  if args.buildSystemRun:
    command.extend(["--buildSystemRun"])
  if args.localServerPort:
    command.extend(["--localServerPort", str(args.localServerPort)])
  command.extend(["--buildRunID", str(run.id)])
  command.extend(["--buildType", args.buildType])
  command.extend(["--executor", args.executor])
  command.extend(args.passToRunexamples)

  print("")
  print("")
  print("Output of run example")
  print("")
  sys.stdout.flush()
  return subprocess.call(command, stderr=subprocess.STDOUT)



def createDistribution(run):
  distArchiveName="failed"

  with tempfile.TemporaryDirectory() as tempDir:
    distLog=io.StringIO()
    distributeErrorCode=base.helper.subprocessCall([sys.executable, os.path.dirname(os.path.realpath(__file__))+"/../distribute.py",
                          "--outDir", tempDir, "--buildConfig", json.dumps(args.buildConfig), args.prefix if args.prefix is not None else args.prefixAuto], distLog)
    run.distributionOK=distributeErrorCode==0
    run.distributionOutput=distLog.getvalue().replace("\0", "&#00;")
    distLog.close()
    if distributeErrorCode==0:
      lines=run.distributionOutput.splitlines()
      run.distributionFileName=[x[len("distArchiveName="):] for x in lines if x.startswith("distArchiveName=")][0].rstrip()
      run.distributionDebugFileName=[x[len("debugArchiveName="):] for x in lines if x.startswith("debugArchiveName=")][0].rstrip()
      run.save()
      with run.distributionFile.open("wb") as fo:
        with open(tempDir+"/"+run.distributionFileName, "rb") as fi:
          base.helper.copyFile(fi, fo)
      with run.distributionDebugFile.open("wb") as fo:
        with open(tempDir+"/"+run.distributionDebugFileName, "rb") as fi:
          base.helper.copyFile(fi, fo)
    return distributeErrorCode



#####################################################################################
# call the main routine
#####################################################################################

if __name__=="__main__":
  mainRet=main()
  django.db.connections.close_all()
  if mainRet<0: # fatal error -> exit with 1
    sys.exit(1)
  if args.buildFailedExit is not None and mainRet!=0: # build/example errors and buildFailedExit set -> exit with buildFailedExit
    sys.exit(args.buildFailedExit)
  sys.exit(0) # all OK or only build/example errors -> exit with 0

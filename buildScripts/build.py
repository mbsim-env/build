#! /usr/bin/python

# imports
from __future__ import print_function # to enable the print function for backward compatiblity with python2
import sys
import os
scriptdir=os.path.dirname(os.path.realpath(__file__))
sys.path.append(scriptdir+'/../buildSystem/scripts')
import argparse
from os.path import join as pj
import subprocess
import re
import glob
import datetime
import fileinput
import shutil
import codecs
import simplesandbox
import hashlib
import hmac
import json
import fcntl
if sys.version_info[0]==2: # to unify python 2 and python 3
  import urllib as myurllib
else:
  import urllib.request as myurllib

# global variables
toolDependencies=dict()
docDir=None
timeID=None
args=None

# pass these envvar to simplesandbox.call
simplesandboxEnvvars=["PKG_CONFIG_PATH", "CPPFLAGS", "CXXFLAGS", "CFLAGS", "FFLAGS", "LDFLAGS", # general required envvars
                      "MBSIM_SWIG", # MBSim required envvars
                      "LD_LIBRARY_PATH", # Linux specific required envvars
                      "WINEPATH", "PLATFORM", "CXX", "MOC", "UIC", "RCC"] # Windows specific required envvars

def parseArguments():
  # command line option definition
  argparser=argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='''Building the MBSim-Environment.
  
  After building, runexamples.py is called by this script.
  All unknown options are passed to runexamples.py.'''
  )
  
  mainOpts=argparser.add_argument_group('Main Options')
  mainOpts.add_argument("--sourceDir", type=str, required=True,
    help="The base source/build directory (see --binSuffix for VPATH builds")
  configOpts=mainOpts.add_mutually_exclusive_group(required=True)
  configOpts.add_argument("--prefix", type=str, help="run configure using this directory as prefix option")
  configOpts.add_argument("--recheck", action="store_true",
    help="run config.status --recheck instead of configure")
  
  cfgOpts=argparser.add_argument_group('Configuration Options')
  cfgOpts.add_argument("-j", default=1, type=int, help="Number of jobs to run in parallel (applies only make and runexamples.py)")
  cfgOpts.add_argument("--forceBuild", action="store_true", help="Force building even if --buildSystemRun is used and no new commits exist")
  
  cfgOpts.add_argument("--enableCleanPrefix", action="store_true", help="Remove the prefix dir completely before starting")
  cfgOpts.add_argument("--disableUpdate", action="store_true", help="Do not update repositories")
  cfgOpts.add_argument("--disableConfigure", action="store_true", help="Do not manually configure. 'make' may still trigger it")
  cfgOpts.add_argument("--disableMakeClean", action="store_true", help="Do not 'make clean'")
  cfgOpts.add_argument("--disableMakeInstall", action="store_true", help="Do not 'make install'")
  cfgOpts.add_argument("--disableMake", action="store_true", help="Do not 'make clean', 'make' and 'make install'")
  cfgOpts.add_argument("--disableMakeCheck", action="store_true", help="Do not 'make check'")
  cfgOpts.add_argument("--disableDoxygen", action="store_true", help="Do not build the doxygen doc")
  cfgOpts.add_argument("--disableXMLDoc", action="store_true", help="Do not build the XML doc")
  cfgOpts.add_argument("--disableRunExamples", action="store_true", help="Do not execute runexamples.py")
  cfgOpts.add_argument("--enableDistribution", action="store_true", help="Create a release distribution archive (only usefull on the buildsystem)")
  cfgOpts.add_argument("--binSuffix", default="", help='base tool name suffix for the binary (build) dir in --sourceDir (default: "" = no VPATH build)')
  cfgOpts.add_argument("--fmatvecBranch", default="", help='In the fmatvec repo checkout the branch FMATVECBRANCH')
  cfgOpts.add_argument("--hdf5serieBranch", default="", help='In the hdf5serierepo checkout the branch HDF5SERIEBRANCH')
  cfgOpts.add_argument("--openmbvBranch", default="", help='In the openmbv repo checkout the branch OPENMBVBRANCH')
  cfgOpts.add_argument("--mbsimBranch", default="", help='In the mbsim repo checkout the branch MBSIMBRANCH')
  cfgOpts.add_argument("--buildSystemRun", action="store_true", help='Run in build system mode: generate build system state files and run with simplesandbox.')
  cfgOpts.add_argument("--coverage", action="store_true", help='Enable coverage analyzis using gcov/lcov.')
  cfgOpts.add_argument("--staticCodeAnalyzis", action="store_true", help='Enable static code analyzis using LLVM Clang Analyzer.')
  cfgOpts.add_argument("--webapp", action="store_true", help='Just passed to runexamples.py.')
  cfgOpts.add_argument("--buildFailedExit", default=None, type=int, help='Define the exit code when the build fails - e.g. use --buildFailedExit 125 to skip a failed build when running as "git bisect run".')
  
  outOpts=argparser.add_argument_group('Output Options')
  outOpts.add_argument("--reportOutDir", default="build_report", type=str, help="the output directory of the report")
  outOpts.add_argument("--docOutDir", type=str,
    help="Copy the documention to this directory. If not given do not copy")
  outOpts.add_argument("--url", type=str, help="the URL where the report output is accessible (without the trailing '/index.html'. Only used for the Atom feed")
  outOpts.add_argument("--buildType", default="local", type=str, help="A description of the build type (e.g: linux64-dailydebug)")
  outOpts.add_argument("--rotate", default=3, type=int, help="keep last n results and rotate them")
  
  passOpts=argparser.add_argument_group('Options beeing passed to other commands')
  passOpts.add_argument("--passToRunexamples", default=list(), nargs=argparse.REMAINDER,
    help="pass all following options, up to but not including the next --passToConfigure argument, to runexamples.py.")
  passOpts.add_argument("--passToConfigure", default=list(), nargs=argparse.REMAINDER,
    help="pass all following options, up to but not including the next --passToRunexamples argument, to configure.")
  
  # parse command line options:
   
  # parse all options before --passToConfigure and/or --passToRunexamples by argparser. 
  passTo1=min(sys.argv.index("--passToConfigure"  ) if "--passToConfigure"   in sys.argv else len(sys.argv),
              sys.argv.index("--passToRunexamples") if "--passToRunexamples" in sys.argv else len(sys.argv))
  passTo2=max(sys.argv.index("--passToConfigure"  ) if "--passToConfigure"   in sys.argv else len(sys.argv),
              sys.argv.index("--passToRunexamples") if "--passToRunexamples" in sys.argv else len(sys.argv))
  global args
  args=argparser.parse_args(args=sys.argv[1:passTo1]) # do not pass REMAINDER arguments
  # assign the options after --passToConfigure and/or --passToRunexamples to args.passTo...
  if "--passToConfigure" in sys.argv[passTo1:passTo2]:
    args.passToConfigure=sys.argv[passTo1+1:passTo2]
  if "--passToRunexamples" in sys.argv[passTo1:passTo2]:
    args.passToRunexamples=sys.argv[passTo1+1:passTo2]
  if "--passToConfigure" in sys.argv[passTo2:]:
    args.passToConfigure=sys.argv[passTo2+1:]
  if "--passToRunexamples" in sys.argv[passTo2:]:
    args.passToRunexamples=sys.argv[passTo2+1:]

def htmlEscape(text):
  htmlEscapeTable={
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
  }
  return "".join(htmlEscapeTable.get(c,c) for c in text)

# rotate
def rotateOutput():
  # create output dir
  if not os.path.isdir(args.reportOutDir): os.makedirs(args.reportOutDir)

  # get result IDs of last runs
  resultID=[]
  for curdir in glob.glob(pj(args.reportOutDir, "result_*")):
    currentID=1
    # skip all except result_[0-9]+
    try: currentID=int(curdir[len(pj(args.reportOutDir, "result_")):])
    except ValueError: continue
    # skip symbolic links
    if os.path.islink(curdir):
      os.remove(curdir)
      continue
    # add to resultID
    resultID.append(currentID);
  # sort resultID
  resultID=sorted(resultID)

  # calculate ID for this run
  if len(resultID)>0:
    currentID=resultID[-1]+1
  else:
    currentID=1

  # check if the last build was the same
  lastcommitidfull={}
  try:
    with codecs.open(pj(args.reportOutDir, "result_%010d"%(currentID-1), "repoState.json"), "r", encoding="utf-8") as f:
      lastcommitidfull=json.load(f)
  except:
    pass

  # only keep args.rotate old results
  delFirstN=len(resultID)-args.rotate
  if delFirstN>0:
    for delID in resultID[0:delFirstN]:
      shutil.rmtree(pj(args.reportOutDir, "result_%010d"%(delID)))
    resultID=resultID[delFirstN:]

  # create link for very last result
  lastLinkID=1
  if len(resultID)>0:
    lastLinkID=resultID[0]
  try: os.remove(pj(args.reportOutDir, "result_%010d"%(lastLinkID-1)))
  except OSError: pass
  os.symlink("result_%010d"%(lastLinkID), pj(args.reportOutDir, "result_%010d"%(lastLinkID-1)))
  # create link for very first result
  try: os.remove(pj(args.reportOutDir, "result_%010d"%(currentID+1)))
  except OSError: pass
  os.symlink("result_%010d"%(currentID), pj(args.reportOutDir, "result_%010d"%(currentID+1)))
  # create link for current result
  try: os.remove(pj(args.reportOutDir, "result_current"))
  except OSError: pass
  os.symlink("result_%010d"%(currentID), pj(args.reportOutDir, "result_current"))

  # fix reportOutDir, create and clean output dir
  args.reportOutDir=pj(args.reportOutDir, "result_%010d"%(currentID))
  if os.path.isdir(args.reportOutDir): shutil.rmtree(args.reportOutDir)
  os.makedirs(args.reportOutDir)
  return currentID, lastcommitidfull

# create main documentation page
def mainDocPage():
  if args.docOutDir==None:
    return

  # copy xmldoc
  if os.path.isdir(pj(args.docOutDir, "xmldoc")): shutil.rmtree(pj(args.docOutDir, "xmldoc"))
  shutil.copytree(os.path.normpath(docDir), pj(args.docOutDir, "xmldoc"), symlinks=True)

  # copy doc
  if os.path.isdir(pj(args.docOutDir, "doc")): shutil.rmtree(pj(args.docOutDir, "doc"))
  shutil.copytree(os.path.normpath(pj(docDir, os.pardir, os.pardir, "doc")), pj(args.docOutDir, "doc"), symlinks=True)

  args.docOutDir=os.path.abspath(args.docOutDir)
  if not os.path.isdir(pj(args.docOutDir, "xmldoc")): os.makedirs(pj(args.docOutDir, "xmldoc"))
  if not os.path.isdir(pj(args.docOutDir, "doc")): os.makedirs(pj(args.docOutDir, "doc"))
  # create doc entry html
  docFD=codecs.open(pj(args.docOutDir, "index.html"), "w", encoding="utf-8")
  print('<!DOCTYPE html>', file=docFD)
  print('<html lang="en">', file=docFD)
  print('<head>', file=docFD)
  print('  <META http-equiv="Content-Type" content="text/html; charset=UTF-8">', file=docFD)
  print('  <meta name="viewport" content="width=device-width, initial-scale=1.0" />', file=docFD)
  print('  <title>Documentation of the MBSim-Environment</title>', file=docFD)
  print('  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css"/>', file=docFD)
  print('  <link rel="shortcut icon" href="/mbsim/html/mbsimenv.ico" type="image/x-icon"/>', file=docFD)
  print('  <link rel="icon" href="/mbsim/html/mbsimenv.ico" type="image/x-icon"/>', file=docFD)
  print('</head>', file=docFD)
  print('<body style="margin:0.5em">', file=docFD)
  print('<script type="text/javascript" src="https://code.jquery.com/jquery-2.1.4.min.js"> </script>', file=docFD)
  print('<script type="text/javascript" src="/mbsim/html/cookiewarning.js"> </script>', file=docFD)
  print('<h1>Documentation of the MBSim-Environment</h1>', file=docFD)
  print('<div class="panel panel-success">', file=docFD)
  print('  <div class="panel-heading"><span class="glyphicon glyphicon-question-sign"></span>&nbsp;XML Documentation</div>', file=docFD)
  print('  <ul class="list-group">', file=docFD)
  print('    <li class="list-group-item"><a href="'+myurllib.pathname2url(pj("xmldoc", "http___www_mbsim-env_de_MBSimXML", "mbsimxml.html"))+'">MBSimXML</a></li>', file=docFD)
  print('  </ul>', file=docFD)
  print('</div>', file=docFD)
  print('<div class="panel panel-info">', file=docFD)
  print('  <div class="panel-heading"><span class="glyphicon glyphicon-question-sign"></span>&nbsp;Doxygen Documentation</div>', file=docFD)
  print('  <ul class="list-group">', file=docFD)
  for d in sorted(os.listdir(os.path.normpath(pj(docDir, os.pardir, os.pardir, "doc")))):
    print('    <li class="list-group-item"><a href="'+myurllib.pathname2url(pj("doc", d, "index.html"))+'">'+d+'</a></li>', file=docFD)
  print('  </ul>', file=docFD)
  print('</div>', file=docFD)
  print('<hr/>', file=docFD)
  print('<span class="pull-left small">', file=docFD)
  print('  <a href="/mbsim/html/impressum_disclaimer_datenschutz.html#impressum">Impressum</a> /', file=docFD)
  print('  <a href="/mbsim/html/impressum_disclaimer_datenschutz.html#disclaimer">Disclaimer</a> /', file=docFD)
  print('  <a href="/mbsim/html/impressum_disclaimer_datenschutz.html#datenschutz">Datenschutz</a>', file=docFD)
  print('</span>', file=docFD)
  print('<span class="pull-right small">', file=docFD)
  print('  Generated on %s'%(str(timeID)), file=docFD)
  print('  <a href="/">Home</a>', file=docFD)
  print('</span>', file=docFD)
  print('</body>', file=docFD)
  print('</html>', file=docFD)
  docFD.close()

# read config file
def readConfigFile():
  configFilename="/home/mbsim/BuildServiceConfig/mbsimBuildService.conf"
  fd=open(configFilename, 'r')
  fcntl.lockf(fd, fcntl.LOCK_SH)
  config=json.load(fd)
  fcntl.lockf(fd, fcntl.LOCK_UN)
  fd.close()
  return config
def setStatus(commitidfull, state, currentID, timeID, target_url, buildType, endTime=None):
  import requests
  for repo in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
    # create github status (for linux64-ci build on all master branch)
    data={
      "state": state,
      "target_url": target_url,
    }
    if buildType=="linux64-dailydebug" or buildType=="linux64-dailyrelease" or \
       buildType=="win64-dailyrelease" or buildType=="linux64-dailydebug-valgrind":
      data["context"]="mbsim-env/%s"%(buildType)
    elif buildType=="linux64-ci":
      data["context"]="mbsim-env/linux64-ci/"+args.fmatvecBranch+"/"+args.hdf5serieBranch+"/"+args.openmbvBranch+"/"+args.mbsimBranch
    else:
      raise RuntimeError("Unknown buildType "+buildType+" provided")
    # note description must be less than 140 characters
    if state=="pending":
      data["description"]="Building since %s on MBSim-Env (%s)"%(str(timeID), buildType)
    elif state=="failure":
      data["description"]="Failed after %.1f min on MBSim-Env (%s)"%((endTime-timeID).total_seconds()/60, buildType)
    elif state=="success":
      data["description"]="Passed after %.1f min on MBSim-Env (%s)"%((endTime-timeID).total_seconds()/60, buildType)
    else:
      raise RuntimeError("Unknown state "+state+" provided")
    # call github api
    config=readConfigFile()
    headers={'Authorization': 'token '+config["status_access_token"],
             'Accept': 'application/vnd.github.v3+json'}
    response=requests.post('https://api.github.com/repos/mbsim-env/'+repo+'/statuses/'+commitidfull[repo],
                           headers=headers, data=json.dumps(data))
    if response.status_code!=201:
      print("Warning: failed to create github status on repo "+repo+":")
      if "message" in response.json(): print(response.json()["message"])
      if "errors" in response.json():
        for e in response.json()['errors']:
          if 'message' in e: print(e["message"])

# the main routine being called ones
def main():
  parseArguments()
  args.sourceDir=os.path.abspath(args.sourceDir)
  args.reportOutDir=os.path.abspath(args.reportOutDir)

  # all tools to be build including the tool dependencies
  global toolDependencies

  toolDependencies={
    #   |ToolName   |WillFail (if WillFail is true no Atom Feed error is reported if this Tool fails somehow)
    pj('fmatvec'): [False, set([ # depends on
      ])],
    pj('hdf5serie', 'h5plotserie'): [False, set([ # depends on
        pj('hdf5serie', 'hdf5serie')
      ])],
    pj('hdf5serie', 'hdf5serie'): [False, set([ # depends on
        pj('fmatvec')
      ])],
    pj('openmbv', 'mbxmlutils'): [False, set([ # depends on
        pj('fmatvec')
      ])],
    pj('openmbv', 'openmbv'): [False, set([ # depends on
        pj('openmbv', 'openmbvcppinterface'),
        pj('hdf5serie', 'hdf5serie')
      ])],
    pj('openmbv', 'openmbvcppinterface'): [False, set([ # depends on
        pj('hdf5serie', 'hdf5serie'),
        pj('openmbv', 'mbxmlutils')
      ])],
    pj('mbsim', 'kernel'): [False, set([ # depends on
        pj('fmatvec'),
        pj('openmbv', 'openmbvcppinterface')
      ])],
    pj('mbsim', 'modules', 'mbsimHydraulics'): [False, set([ # depends on
        pj('mbsim', 'kernel'),
        pj('mbsim', 'modules', 'mbsimControl')
      ])],
    pj('mbsim', 'modules', 'mbsimFlexibleBody'): [False, set([ # depends on
        pj('mbsim', 'kernel'),
        pj('mbsim', 'thirdparty', 'nurbs++')
      ])],
    pj('mbsim', 'thirdparty', 'nurbs++'): [False, set([ # depends on
      ])],
    pj('mbsim', 'modules', 'mbsimPowertrain'): [False, set([ # depends on
        pj('mbsim', 'kernel')
      ])],
    pj('mbsim', 'modules', 'mbsimElectronics'): [False, set([ # depends on
        pj('mbsim', 'kernel'),
        pj('mbsim', 'modules', 'mbsimControl')
      ])],
    pj('mbsim', 'modules', 'mbsimControl'): [False, set([ # depends on
        pj('mbsim', 'kernel')
      ])],
    pj('mbsim', 'modules', 'mbsimInterface'): [False, set([ # depends on
        pj('mbsim', 'kernel'),
        pj('mbsim', 'modules', 'mbsimControl')
      ])],
    pj('mbsim', 'mbsimxml'): [False, set([ # depends on
        pj('mbsim', 'kernel'),
        pj('openmbv', 'openmbvcppinterface'),
        pj('openmbv', 'mbxmlutils'),
        # dependencies to mbsim modules are only required for correct xmldoc generation 
        pj('mbsim', 'modules', 'mbsimHydraulics'),
        pj('mbsim', 'modules', 'mbsimFlexibleBody'),
        pj('mbsim', 'modules', 'mbsimPowertrain'),
        pj('mbsim', 'modules', 'mbsimElectronics'),
        pj('mbsim', 'modules', 'mbsimControl'),
        pj('mbsim', 'modules', 'mbsimInterface')
      ])],
    pj('mbsim', 'mbsimgui'): [False, set([ # depends on
        pj('openmbv', 'openmbv'),
        pj('openmbv', 'mbxmlutils'),
        pj('mbsim', 'mbsimxml')
      ])],
    pj('mbsim', 'mbsimfmi'): [False, set([ # depends on
        pj('mbsim', 'kernel'),
        pj('mbsim', 'mbsimxml'),
        pj('mbsim', 'modules', 'mbsimControl')
      ])],
  }

  # extend the dependencies recursively
  addAllDepencencies()

  # set docDir
  global docDir
  if args.prefix==None:
    raise RuntimeError("MISSING: calling without --prefix is currently not supported. sandboxing is missing")
    output=subprocess.check_output([pj(args.sourceDir, "openmbv"+args.binSuffix, "mbxmlutils", "config.status"), "--config"]).decode("utf-8")
    for opt in output.split():
      match=re.search("'?--prefix[= ]([^']*)'?", opt)
      if match!=None:
        docDir=pj(match.expand("\\1"), "share", "mbxmlutils", "doc")
        args.prefixAuto=match.expand("\\1")
        break
  else:
    docDir=pj(args.prefix, "share", "mbxmlutils", "doc")
  # append path to PKG_CONFIG_PATH to find mbxmlutils and co. by runexmaples.py
  pkgConfigDir=os.path.normpath(pj(docDir, os.pardir, os.pardir, os.pardir, "lib", "pkgconfig"))
  if "PKG_CONFIG_PATH" in os.environ:
    os.environ["PKG_CONFIG_PATH"]=pkgConfigDir+os.pathsep+os.environ["PKG_CONFIG_PATH"]
  else:
    os.environ["PKG_CONFIG_PATH"]=pkgConfigDir

  global timeID
  timeID=datetime.datetime.now()
  timeID=datetime.datetime(timeID.year, timeID.month, timeID.day, timeID.hour, timeID.minute, timeID.second)

  # enable coverage
  if args.coverage:
    if not "CPPFLAGS" in os.environ: os.environ["CPPFLAGS"]=""
    if not "LDFLAGS"  in os.environ: os.environ["LDFLAGS" ]=""
    os.environ["CPPFLAGS"]=os.environ["CPPFLAGS"]+" --coverage"
    os.environ["LDFLAGS" ]=os.environ["LDFLAGS" ]+" --coverage -lgcov"

  # start messsage
  print("Started build process.")
  print("See the log file "+pj(args.reportOutDir, "result_current", "index.html")+" for detailed results.")
  if args.docOutDir!=None:
    print("See also the generated documentation "+pj(args.docOutDir, "index.html")+".\n")

  # rotate (modifies args.reportOutDir)
  currentID, lastcommitidfull=rotateOutput()

  # create index.html
  mainFD=codecs.open(pj(args.reportOutDir, "index.html"), "w", encoding="utf-8")
  print('''<!DOCTYPE html>
<html lang="en">
<head>
  <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Build Results of MBSim-Env: <small>%s</small></title>
  <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/s/bs-3.3.5/jq-2.1.4,dt-1.10.10/datatables.min.css"/>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/octicons/3.5.0/octicons.min.css"/>
  <link rel="shortcut icon" href="/mbsim/html/mbsimenv.ico" type="image/x-icon"/>
  <link rel="icon" href="/mbsim/html/mbsimenv.ico" type="image/x-icon"/>
</head>
<body style="margin:0.5em">
<script type="text/javascript" src="https://cdn.datatables.net/s/bs-3.3.5/jq-2.1.4,dt-1.10.10/datatables.min.js"> </script>
<script type="text/javascript" src="/mbsim/html/cookiewarning.js"> </script>
<script type="text/javascript" src="../../../html/mbsimBuildServiceClient.js"></script>
<script type="text/javascript">
  $(document).ready(function() {
    $.fn.dataTableExt.sErrMode = 'throw';
    $('#SortThisTable').dataTable({'lengthMenu': [ [1, 5, 10, 25, -1], [1, 5, 10, 25, 'All'] ], 'pageLength': -1, 'aaSorting': [], stateSave: true});'''%(args.buildType), file=mainFD)

  if args.enableDistribution:
    releaseGeneration1(mainFD)

  print('''  } );
</script>

<h1>Build Results of MBSim-Env: <small>%s</small></h1>

<dl class="dl-horizontal">
<dt>Called Command</dt><dd><div class="dropdown">
  <button class="btn btn-default btn-xs" id="calledCommandID" data-toggle="dropdown">show <span class="caret"></span>
  </button>
  <code class="dropdown-menu" style="padding-left: 0.5em; padding-right: 0.5em;" aria-labelledby="calledCommandID">'''%(args.buildType), file=mainFD)
  for argv in sys.argv: print(argv.replace('/', u'/\u200B')+' ', file=mainFD)
  print('</code></div></dd>', file=mainFD)
  print('  <dt>Time ID</dt><dd>'+str(timeID)+'</dd>', file=mainFD)
  print('  <dt>End time</dt><dd><span id="STILLRUNNINGORABORTED" class="text-danger"><b>still running or aborted</b></span><!--E_ENDTIME--></dd>', file=mainFD)
  print('  <dt>Navigate</dt><dd><a class="btn btn-info btn-xs" href="../result_%010d/index.html"><span class="glyphicon glyphicon-step-backward"></span>&nbsp;previous</a>'%(currentID-1), file=mainFD)
  print('                    <a class="btn btn-info btn-xs" href="../result_%010d/index.html"><span class="glyphicon glyphicon-step-forward"></span>&nbsp;next</a>'%(currentID+1), file=mainFD)
  print('                    <a class="btn btn-info btn-xs" href="../result_current/index.html"><span class="glyphicon glyphicon-fast-forward"></span>&nbsp;newest</a>', file=mainFD)
  print('                    </dd>', file=mainFD)
  print('</dl>', file=mainFD)
  print('<hr/>', file=mainFD)

  nrFailed=0
  nrRun=0
  # update all repositories
  if not args.disableUpdate:
    nrRun+=1
  localRet, commitidfull=repoUpdate(mainFD, currentID)
  if localRet!=0: nrFailed+=1

  # check if last build was the same as this build
  if not args.forceBuild and args.buildSystemRun and lastcommitidfull==commitidfull:
    print('Skipping this build: the last build was exactly the same.')
    # revert the outdir
    args.reportOutDir=os.path.sep.join(args.reportOutDir.split(os.path.sep)[0:-1])
    shutil.rmtree(pj(args.reportOutDir, "result_%010d"%(currentID)))
    os.remove(pj(args.reportOutDir, "result_%010d"%(currentID+1)))
    os.remove(pj(args.reportOutDir, "result_current"))
    os.symlink("result_%010d"%(currentID-1), pj(args.reportOutDir, "result_%010d"%(currentID)))
    os.symlink("result_%010d"%(currentID-1), pj(args.reportOutDir, "result_current"))
    return 255 # build skipped, same as last build

  # set status on commit
  if args.buildSystemRun:
    setStatus(commitidfull, "pending", currentID, timeID,
      "https://www.mbsim-env.de/mbsim/%s/report/result_%010d/index.html"%(args.buildType, currentID), args.buildType)

  # clean prefix dir
  if args.enableCleanPrefix and os.path.isdir(args.prefix if args.prefix!=None else args.prefixAuto):
    shutil.rmtree(args.prefix if args.prefix!=None else args.prefixAuto)
    os.makedirs(args.prefix if args.prefix!=None else args.prefixAuto)

  # a sorted list of all tools te be build (in the correct order according the dependencies)
  orderedBuildTools=list()
  sortBuildTools(set(toolDependencies), orderedBuildTools)

  print('<h2>Build Status</h2>', file=mainFD)
  print('<p><span class="glyphicon glyphicon-info-sign"></span>&nbsp;Failures in the following table should be fixed from top to bottom since a error in one tool may cause errors on dependent tools.<br/>', file=mainFD)
  print('<span class="glyphicon glyphicon-info-sign"></span>&nbsp;A tool name in gray color is a tool which may fail and is therefore not reported as an error in the Atom feed.</p>', file=mainFD)

  print('<table id="SortThisTable" class="table table-striped table-hover table-bordered table-condensed">', file=mainFD)
  print('<thead><tr>', file=mainFD)
  print('<th><span class="glyphicon glyphicon-folder-open"></span>&nbsp;Tool</th>', file=mainFD)
  if not args.disableConfigure:
    print('<th><span class="glyphicon glyphicon-wrench"></span>&nbsp;Configure</th>', file=mainFD)
  if not args.disableMake:
    print('<th><span class="glyphicon glyphicon-repeat"></span>&nbsp;Make</th>', file=mainFD)
    if args.staticCodeAnalyzis:
      print('<th data-toggle="tooltip" data-placement="bottom" title="Static Code Analyzis"><span class="glyphicon glyphicon-search"></span>&nbsp;SCA</th>', file=mainFD)
  if not args.disableMakeCheck:
    print('<th><span class="glyphicon glyphicon-ok-circle"></span>&nbsp;Make Check</th>', file=mainFD)
  if not args.disableDoxygen:
    print('<th><span class="glyphicon glyphicon-question-sign"></span>&nbsp;Doxygen Doc.</th>', file=mainFD)
  if not args.disableXMLDoc:
    print('<th><span class="glyphicon glyphicon-question-sign"></span>&nbsp;XML Doc.</th>', file=mainFD)
  print('</tr></thead><tbody>', file=mainFD)

  # list tools which are not updated and must not be rebuild according dependencies
  for tool in set(toolDependencies)-set(orderedBuildTools):
    print('<tr>', file=mainFD)
    print('<td>'+tool.replace('/', u'/\u200B')+'</td>', file=mainFD)
    for i in range(0, 6-sum([args.disableConfigure, args.disableMake, not args.staticCodeAnalyzis, args.disableMakeCheck, args.disableDoxygen, args.disableXMLDoc])):
      print('<td>-</td>', file=mainFD)
    print('</tr>', file=mainFD)
  mainFD.flush()

  # build the other tools in order
  nr=1
  for tool in orderedBuildTools:
    nrFailedLocal, nrRunLocal=build(nr, len(orderedBuildTools), tool, mainFD)
    if toolDependencies[tool][0]==False:
      nrFailed+=nrFailedLocal
      nrRun+=nrRunLocal
    nr+=1

  # write main doc file
  mainDocPage()

  # run examples
  runExamplesErrorCode=0
  if not args.disableRunExamples:
    savedDir=os.getcwd()
    os.chdir(pj(args.sourceDir, "mbsim", "examples"))
    print("Run runexamples.py in "+os.getcwd()); sys.stdout.flush()
    runExamplesErrorCode=runexamples(mainFD)
    os.chdir(savedDir)

  # create distribution
  if args.enableDistribution:
    nrRun=nrRun+1
    print("Create distribution"); sys.stdout.flush()
    cdRet, distArchiveName=createDistribution(mainFD)
    if cdRet!=0:
      nrFailed=nrFailed+1

  print('</tbody></table>', file=mainFD)

  if args.enableDistribution and nrFailed==0 and runExamplesErrorCode==0:
    releaseGeneration2(mainFD, distArchiveName)

  print('<hr/>', file=mainFD)
  print('<span class="pull-left small">', file=mainFD)
  print('  <a href="/mbsim/html/impressum_disclaimer_datenschutz.html#impressum">Impressum</a> /', file=mainFD)
  print('  <a href="/mbsim/html/impressum_disclaimer_datenschutz.html#disclaimer">Disclaimer</a> /', file=mainFD)
  print('  <a href="/mbsim/html/impressum_disclaimer_datenschutz.html#datenschutz">Datenschutz</a>', file=mainFD)
  print('</span>', file=mainFD)
  print('<span class="pull-right small">', file=mainFD)
  print('  Generated on %s'%(str(timeID)), file=mainFD)
  print('  <a href="/">Home</a>', file=mainFD)
  print('</span>', file=mainFD)
  print('</body>', file=mainFD)
  print('</html>', file=mainFD)

  mainFD.close()
  # replace <span id="STILLRUNNINGORABORTED"...</span> in index.html
  for line in fileinput.FileInput(pj(args.reportOutDir, "index.html"),inplace=1):
    endTime=datetime.datetime.now()
    endTime=datetime.datetime(endTime.year, endTime.month, endTime.day, endTime.hour, endTime.minute, endTime.second)
    line=re.sub('<span id="STILLRUNNINGORABORTED".*?</span>', str(endTime), line)
    print(line, end="")

  # update build system state
  if args.buildSystemRun:
    sys.path.append(scriptdir+'/../buildSystem/scripts')
    import buildSystemState
    buildSystemState.update(args.buildType+"-build", "Build Failed: "+args.buildType,
                            "%d of %d build parts failed."%(nrFailed, nrRun),
                            args.url+"/result_%010d"%(currentID)+"/index.html",
                            nrFailed, nrRun)

  # update status on commitid
  if args.buildSystemRun:
    setStatus(commitidfull, "success" if nrFailed+abs(runExamplesErrorCode)==0 else "failure", currentID, timeID,
      "https://www.mbsim-env.de/mbsim/%s/report/result_%010d/index.html"%(args.buildType, currentID), args.buildType, endTime)

  if nrFailed>0:
    print("\nERROR: %d of %d build parts failed!!!!!"%(nrFailed, nrRun));

  # dump the repo state (commitid) to a file
  with codecs.open(pj(args.reportOutDir, "repoState.json"), "w", encoding="utf-8") as f:
    json.dump(commitidfull, f, indent=2)

  if nrFailed>0:
    return 1 # build failed
  if abs(runExamplesErrorCode)>0:
    return 2 # examples failed
  return 0 # all passed



#####################################################################################
# from now on only functions follow and at the end main is called
#####################################################################################



def addAllDepencencies():
  rec=False
  for t in toolDependencies:
    add=set()
    oldLength=len(toolDependencies[t][1])
    for d in toolDependencies[t][1]:
      for a in toolDependencies[d][1]:
        add.add(a)
    for a in add:
      toolDependencies[t][1].add(a)
    newLength=len(toolDependencies[t][1])
    if newLength>oldLength:
      rec=True
  if rec:
    addAllDepencencies()


 
def sortBuildTools(buildTools, orderedBuildTools):
  upToDate=set(toolDependencies)-buildTools
  for bt in buildTools:
    if len(toolDependencies[bt][1]-upToDate)==0:
      orderedBuildTools.append(bt)
      upToDate.add(bt)
  buildTools-=set(orderedBuildTools)
  if len(buildTools)>0:
    sortBuildTools(buildTools, orderedBuildTools)



def buildTool(tool):
  t=tool.split(os.path.sep)
  t[0]=t[0]+args.binSuffix
  return os.path.sep.join(t)

def repoUpdate(mainFD, currentID):
  ret=0
  savedDir=os.getcwd()
  if not args.disableUpdate:
    print('Updating repositories: ', end="")

  print('<h2>Repository State</h2>', file=mainFD)
  print('<table style="width:auto;" class="table table-striped table-hover table-bordered table-condensed">', file=mainFD)
  print('<thead><tr>', file=mainFD)
  print('<th><span class="octicon octicon-repo"></span>&nbsp;Repository</th>', file=mainFD)
  print('<th><span class="octicon octicon-git-branch"></span>&nbsp;Branch</th>', file=mainFD)
  if not args.disableUpdate:
    print('<th><span class="glyphicon glyphicon-refresh"></span>&nbsp;Update</th>', file=mainFD)
  print('<th><span class="octicon octicon-git-commit"></span>&nbsp;Commit</th>', file=mainFD)
  print('</tr></thead><tbody>', file=mainFD)

  commitidfull={}
  for repo in ["fmatvec", "hdf5serie", "openmbv", "mbsim"]:
    os.chdir(pj(args.sourceDir, repo))
    # update
    repoUpdFD=codecs.open(pj(args.reportOutDir, "repo-update-"+repo+".txt"), "w", encoding="utf-8")
    retlocal=0

    # workaround for a git bug when using with an unknown user (fixed with git >= 2.6)
    env=os.environ
    env["GIT_COMMITTER_NAME"]="dummy"
    env["GIT_COMMITTER_EMAIL"]="dummy"

    if not args.disableUpdate:
      # write repUpd output to report dir
      print('Fetch remote repository '+repo+":", file=repoUpdFD)
      repoUpdFD.flush()
      retlocal+=abs(subprocess.call(["git", "fetch"], stdout=repoUpdFD, stderr=repoUpdFD))
    # set branch based on args
    if eval('args.'+repo+'Branch')!="":
      print('Checkout branch '+eval('args.'+repo+'Branch')+' in repository '+repo+":", file=repoUpdFD)
      retlocal+=abs(subprocess.call(["git", "checkout", eval('args.'+repo+'Branch')], stdout=repoUpdFD, stderr=repoUpdFD))
      repoUpdFD.flush()
    if not args.disableUpdate:
      print('Pull current branch', file=repoUpdFD)
      repoUpdFD.flush()
      retlocal+=abs(subprocess.call(["git", "pull"], stdout=repoUpdFD, stderr=repoUpdFD))
    # get branch and commit
    branch=subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stderr=repoUpdFD).decode('utf-8').rstrip()
    commitid=subprocess.check_output(['git', 'log', '-n', '1', '--format=%h', 'HEAD'], stderr=repoUpdFD).decode('utf-8').rstrip()
    commitidfull[repo]=subprocess.check_output(['git', 'log', '-n', '1', '--format=%H', 'HEAD'], stderr=repoUpdFD).decode('utf-8').rstrip()
    commitsub=subprocess.check_output(['git', 'log', '-n', '1', '--format=%s', 'HEAD'], stderr=repoUpdFD).decode('utf-8').rstrip()
    commitshort='<a href="https://github.com/mbsim-env/'+repo+'/commit/'+commitidfull[repo]+'"><code>'+commitid+'</code></a>: '+htmlEscape(commitsub)
    commitlong=subprocess.check_output(['git', 'log', '-n', '1', '--format=Commit: %H%nAuthor: %an%nDate:   %ad%n%s%n%b', 'HEAD'], stderr=repoUpdFD).decode('utf-8')
    commitlong=htmlEscape(commitlong)
    repoUpdFD.close()
    ret+=retlocal
    # output
    print('<tr>', file=mainFD)
    print('  <td><a href="https://github.com/mbsim-env/'+repo+'"><span class="label label-success"><span class="octicon octicon-repo"></span>&nbsp;'+repo+'</span></a></td>', file=mainFD)
    print('  <td><a href="https://github.com/mbsim-env/'+repo+'/tree/'+branch+'"><span class="label label-primary"><span class="octicon octicon-git-branch"></span>&nbsp;'+branch+'</span></a></td>', file=mainFD)
    if not args.disableUpdate:
      print('<td class="%s"><span class="glyphicon glyphicon-%s"></span>&nbsp;<a href="repo-update-%s.txt">%s</a></td>'%(
        "success" if retlocal==0 else "danger",
        "ok-sign alert-success" if retlocal==0 else "exclamation-sign alert-danger",
        repo,
        "passed" if retlocal==0 else "failed"), file=mainFD)
    print('  <td data-toggle="tooltip" data-placement="bottom" title="'+commitlong+'">'+commitshort+
          '<span id="COMMITID_%s" style="display:none">%s</span></td>'%(repo, commitidfull[repo]), file=mainFD)
    print('</tr>', file=mainFD)

  print('</tbody></table>', file=mainFD)
  mainFD.flush()

  if not args.disableUpdate:
    if ret>0:
      print('failed')
    else:
      print('passed')

  os.chdir(savedDir)
  return ret, commitidfull



def build(nr, nrAll, tool, mainFD):
  print("Building "+str(nr)+"/"+str(nrAll)+": "+tool+": ", end=""); sys.stdout.flush()

  nrFailed=0
  nrRun=0

  # start row, including tool name
  if toolDependencies[tool][0]==False:
    print('<tr>', file=mainFD)
  else:
    print('<tr class="text-muted">', file=mainFD)
  print('<td>'+tool.replace('/', u'/\u200B')+'</td>', file=mainFD)
  mainFD.flush()

  savedDir=os.getcwd()

  # configure
  print("configure", end=""); sys.stdout.flush()
  failed, run=configure(tool, mainFD)
  nrFailed+=failed
  nrRun+=run

  # cd to build dir
  os.chdir(savedDir)
  os.chdir(pj(args.sourceDir, buildTool(tool)))

  # make
  print(", make", end=""); sys.stdout.flush()
  failed, run=make(tool, mainFD)
  nrFailed+=failed
  nrRun+=run

  # make check
  print(", check", end=""); sys.stdout.flush()
  failed, run=check(tool, mainFD)
  nrFailed+=failed
  nrRun+=run

  # doxygen
  print(", doxygen-doc", end=""); sys.stdout.flush()
  failed, run=doc(tool, mainFD, args.disableDoxygen, "doc")
  nrFailed+=failed
  nrRun+=run

  # xmldoc
  print(", xml-doc", end=""); sys.stdout.flush()
  failed, run=doc(tool, mainFD, args.disableXMLDoc, "xmldoc")
  nrFailed+=failed
  nrRun+=run

  os.chdir(savedDir)

  print("")
  print('</tr>', file=mainFD)
  mainFD.flush()

  return nrFailed, nrRun



def configure(tool, mainFD):
  if not os.path.isdir(pj(args.reportOutDir, tool)): os.makedirs(pj(args.reportOutDir, tool))
  configureFD=codecs.open(pj(args.reportOutDir, tool, "configure.txt"), "w", encoding="utf-8")
  copyConfigLog=False
  savedDir=os.getcwd()
  run=0
  try:
    if not args.disableConfigure:
      run=1
      # pre configure
      os.chdir(pj(args.sourceDir, tool))
      print("\n\nRUNNING aclocal\n", file=configureFD); configureFD.flush()
      if simplesandbox.call(["aclocal"], envvar=simplesandboxEnvvars, shareddir=["."],
                            stderr=subprocess.STDOUT, stdout=configureFD, buildSystemRun=args.buildSystemRun)!=0:
        raise RuntimeError("aclocal failed")
      print("\n\nRUNNING autoheader\n", file=configureFD); configureFD.flush()
      if simplesandbox.call(["autoheader"], envvar=simplesandboxEnvvars, shareddir=["."],
                            stderr=subprocess.STDOUT, stdout=configureFD, buildSystemRun=args.buildSystemRun)!=0:
        raise RuntimeError("autoheader failed")
      print("\n\nRUNNING libtoolize\n", file=configureFD); configureFD.flush()
      if simplesandbox.call(["libtoolize", "-c"], envvar=simplesandboxEnvvars, shareddir=["."],
                            stderr=subprocess.STDOUT, stdout=configureFD, buildSystemRun=args.buildSystemRun)!=0:
        raise RuntimeError("libtoolize failed")
      print("\n\nRUNNING automake\n", file=configureFD); configureFD.flush()
      if simplesandbox.call(["automake", "-a", "-c"], envvar=simplesandboxEnvvars, shareddir=["."],
                            stderr=subprocess.STDOUT, stdout=configureFD, buildSystemRun=args.buildSystemRun)!=0:
        raise RuntimeError("automake failed")
      print("\n\nRUNNING autoconf\n", file=configureFD); configureFD.flush()
      if simplesandbox.call(["autoconf"], envvar=simplesandboxEnvvars, shareddir=["."],
                            stderr=subprocess.STDOUT, stdout=configureFD, buildSystemRun=args.buildSystemRun)!=0:
        raise RuntimeError("autoconf failed")
      print("\n\nRUNNING autoreconf\n", file=configureFD); configureFD.flush()
      if simplesandbox.call(["autoreconf"], envvar=simplesandboxEnvvars, shareddir=["."],
                            stderr=subprocess.STDOUT, stdout=configureFD, buildSystemRun=args.buildSystemRun)!=0:
        raise RuntimeError("autoreconf failed")
      # configure
      os.chdir(savedDir)
      if not os.path.exists(pj(args.sourceDir, buildTool(tool))): os.makedirs(pj(args.sourceDir, buildTool(tool)))
      os.chdir(pj(args.sourceDir, buildTool(tool)))
      copyConfigLog=True
      print("\n\nRUNNING configure\n", file=configureFD); configureFD.flush()
      if args.prefix==None:
        print(" ".join(["./config.status", "--recheck"]), file=configureFD); configureFD.flush()
        if simplesandbox.call(["./config.status", "--recheck"], envvar=simplesandboxEnvvars, shareddir=["."],
                              stderr=subprocess.STDOUT, stdout=configureFD, buildSystemRun=args.buildSystemRun)!=0:
          raise RuntimeError("configure failed")
      else:
        command=[pj(args.sourceDir, tool, "configure"), "--prefix", args.prefix]
        command.extend(args.passToConfigure)
        print(" ".join(command), file=configureFD); configureFD.flush()
        if simplesandbox.call(command, envvar=simplesandboxEnvvars, shareddir=["."],
                              stderr=subprocess.STDOUT, stdout=configureFD, buildSystemRun=args.buildSystemRun)!=0:
          raise RuntimeError("configure failed")
    else:
      print("configure disabled", file=configureFD); configureFD.flush()

    result="done"
  except RuntimeError as ex:
    result=str(ex)
  if not args.disableConfigure:
    print('<td data-order="%d" class="%s"><span class="glyphicon glyphicon-%s"></span>&nbsp;'%(int(result!="done"), "success" if result=="done" else "danger",
      "ok-sign alert-success" if result=="done" else "exclamation-sign alert-danger"), file=mainFD)
    print('  <a href="'+myurllib.pathname2url(pj(tool, "configure.txt"))+'">'+result+'</a>', file=mainFD)
    if copyConfigLog:
      shutil.copyfile("config.log", pj(args.reportOutDir, tool, "config.log.txt"))
      print('  <a href="'+myurllib.pathname2url(pj(tool, "config.log.txt"))+'">config.log</a>', file=mainFD)
    print('</td>', file=mainFD)
  configureFD.close()
  mainFD.flush()
  os.chdir(savedDir)

  if result!="done":
    return 1, run
  return 0, run



def make(tool, mainFD):
  makeFD=codecs.open(pj(args.reportOutDir, tool, "make.txt"), "w", encoding="utf-8")
  run=0
  try:
    if not args.disableMake:
      run=1
      staticCodeAnalyzeDir=[]
      staticCodeAnalyzeComm=[]
      if args.staticCodeAnalyzis and tool != "mbsim/thirdparty/nurbs++": # skip nurbs++ being a 3rd party tool
        staticCodeAnalyzeDir=[pj(args.reportOutDir, tool, "static-code-analyze")]
        if not os.path.exists(staticCodeAnalyzeDir[0]): os.mkdir(staticCodeAnalyzeDir[0])
        staticCodeAnalyzeComm=[scriptdir+"/scan-build", "-analyze-headers",
           "--exclude", "*_swig_python.cc", "--exclude", "*_swig_octave.cc", "--exclude", "*_swig_java.cc",
           "--exclude", "/usr/include/*", "--exclude", "/home/mbsim/3rdparty/*",
           "--exclude", "*/mbsim/kernel/mbsim/numerics/csparse.*",
           "-o", staticCodeAnalyzeDir[0], "--html-title", tool+" - Static Code Analyzis"]
      # make
      errStr=""
      if not args.disableMakeClean:
        print("\n\nRUNNING make clean\n", file=makeFD); makeFD.flush()
        if simplesandbox.call(["make", "clean"], envvar=simplesandboxEnvvars, shareddir=["."],
                              stderr=subprocess.STDOUT, stdout=makeFD, buildSystemRun=args.buildSystemRun)!=0:
          errStr=errStr+"make clean failed; "
        if args.coverage:
          # remove all "*.gcno", "*.gcda" files
          for d,_,files in os.walk('.'):
            for f in files:
              if os.path.splitext(f)[1]==".gcno": os.remove(pj(d, f))
              if os.path.splitext(f)[1]==".gcda": os.remove(pj(d, f))
      print("\n\nRUNNING make -k\n", file=makeFD); makeFD.flush()
      if simplesandbox.call(staticCodeAnalyzeComm+["make", "-k", "-j", str(args.j)], envvar=simplesandboxEnvvars, shareddir=["."]+staticCodeAnalyzeDir,
                            stderr=subprocess.STDOUT, stdout=makeFD, buildSystemRun=args.buildSystemRun)!=0:
        errStr=errStr+"make failed; "
      if not args.disableMakeInstall:
        print("\n\nRUNNING make install\n", file=makeFD); makeFD.flush()
        if simplesandbox.call(["make", "-k", "install"], envvar=simplesandboxEnvvars,
                              shareddir=[".", args.prefix if args.prefix!=None else args.prefixAuto],
                              stderr=subprocess.STDOUT, stdout=makeFD, buildSystemRun=args.buildSystemRun)!=0:
          errStr=errStr+"make install failed; "
      if errStr!="": raise RuntimeError(errStr)
    else:
      print("make disabled", file=makeFD); makeFD.flush()

    result="done"
  except RuntimeError as ex:
    result=str(ex)
  makeFD.close()
  if not args.disableMake:
    print('<td data-order="%d" class="%s"><span class="glyphicon glyphicon-%s"></span>&nbsp;'%(int(result!="done"), "success" if result=="done" else "danger",
      "ok-sign alert-success" if result=="done" else "exclamation-sign alert-danger"), file=mainFD)
    print('  <a href="'+myurllib.pathname2url(pj(tool, "make.txt"))+'">'+result+'</a>', file=mainFD)
    print('</td>', file=mainFD)
    if args.staticCodeAnalyzis:
      if tool != "mbsim/thirdparty/nurbs++": # skip nurbs++ being a 3rd party tool
        d=""
        numErr=0
        try:
          d=os.path.basename(glob.glob(pj(args.reportOutDir, tool, "static-code-analyze", "*"))[0])
          # search "scan-build: 2 bugs found." in index.html
          linesRE=re.compile("^scan-build: ([0-9]+) bugs found.$")
          for line in fileinput.FileInput(pj(args.reportOutDir, tool, "make.txt")):
            m=linesRE.match(line)
            if m!=None:
              numErr=int(m.group(1))
              break
        except:
          pass
        print('<td data-order="%d" class="%s"><span class="glyphicon glyphicon-%s"></span>&nbsp;'%(numErr==0, "success" if numErr==0 else "warning",
          "ok-sign alert-success" if numErr==0 else "warning-sign alert-warning"), file=mainFD)
        print('  <a href="%s">%s</a>'%(myurllib.pathname2url(pj(tool, "static-code-analyze", d, "")),
          "passed" if numErr==0 else 'error&nbsp;<span class="badge">%d</span>'%(numErr)), file=mainFD)
        print('</td>', file=mainFD)
      else:
        print('<td data-order="0">-</td>', file=mainFD)
  mainFD.flush()

  if result!="done":
    return 1, run
  return 0, run



def check(tool, mainFD):
  checkFD=codecs.open(pj(args.reportOutDir, tool, "check.txt"), "w", encoding="utf-8")
  run=0
  if not args.disableMakeCheck:
    run=1
    # make check
    print("RUNNING make check\n", file=checkFD); checkFD.flush()
    if simplesandbox.call(["make", "-k", "-j", str(args.j), "check"], envvar=simplesandboxEnvvars, shareddir=["."],
                          stderr=subprocess.STDOUT, stdout=checkFD, buildSystemRun=args.buildSystemRun)==0:
      result="done"
    else:
      result="failed"
  else:
    print("make check disabled", file=checkFD); checkFD.flush()
    result="done"

  foundTestSuiteLog=False
  testSuiteLogFD=codecs.open(pj(args.reportOutDir, tool, "test-suite.log.txt"), "w", encoding="utf-8")
  for rootDir,_,files in os.walk('.'): # append all test-suite.log files
    if "test-suite.log" in files:
      testSuiteLogFD.write('\n\n')
      testSuiteLogFD.write(open(pj(rootDir, "test-suite.log")).read())
      foundTestSuiteLog=True
  testSuiteLogFD.close()
  if not args.disableMakeCheck:
    print('<td data-order="%d" class="%s"><span class="glyphicon glyphicon-%s"></span>&nbsp;'%(int(result!="done"), "success" if result=="done" else "danger",
      "ok-sign alert-success" if result=="done" else "exclamation-sign alert-danger"), file=mainFD)
    print('  <a href="'+myurllib.pathname2url(pj(tool, "check.txt"))+'">'+result+'</a>', file=mainFD)
    if foundTestSuiteLog:
      print('  <a href="'+myurllib.pathname2url(pj(tool, "test-suite.log.txt"))+'">test-suite.log</a>', file=mainFD)
    print('</td>', file=mainFD)
  checkFD.close()
  mainFD.flush()

  if result!="done":
    return 1, run
  return 0, run



def doc(tool, mainFD, disabled, docDirName):
  if not os.path.isdir(docDirName):
    if docDirName=="doc" and not args.disableDoxygen or \
       docDirName=="xmldoc" and not args.disableXMLDoc:
      print('<td data-order="1">not available</td>', file=mainFD)
    mainFD.flush()
    return 0, 0

  docFD=codecs.open(pj(args.reportOutDir, tool, docDirName+".txt"), "w", encoding="utf-8")
  savedDir=os.getcwd()
  os.chdir(docDirName)
  run=0
  try:
    if not disabled:
      run=1
      # make doc
      errStr=""
      print("\n\nRUNNING make clean\n", file=docFD); docFD.flush()
      if simplesandbox.call(["make", "clean"], envvar=simplesandboxEnvvars, shareddir=["."],
                            stderr=subprocess.STDOUT, stdout=docFD, buildSystemRun=args.buildSystemRun)!=0:
        errStr=errStr+"make clean failed; "
      print("\n\nRUNNING make\n", file=docFD); docFD.flush()
      if simplesandbox.call(["make", "-k"], envvar=simplesandboxEnvvars,
                            shareddir=[".", args.prefix if args.prefix!=None else args.prefixAuto],
                            stderr=subprocess.STDOUT, stdout=docFD, buildSystemRun=args.buildSystemRun)!=0:
        errStr=errStr+"make failed; "
      print("\n\nRUNNING make install\n", file=docFD); docFD.flush()
      if simplesandbox.call(["make", "-k", "install"], envvar=simplesandboxEnvvars,
                            shareddir=[".", args.prefix if args.prefix!=None else args.prefixAuto],
                            stderr=subprocess.STDOUT, stdout=docFD, buildSystemRun=args.buildSystemRun)!=0:
        errStr=errStr+"make install failed; "
      if errStr!="": raise RuntimeError(errStr)
    else:
      print(docDirName+" disabled", file=docFD); docFD.flush()

    result="done"
  except RuntimeError as ex:
    result=str(ex)
  finally:
    os.chdir(savedDir)
  if docDirName=="doc" and not args.disableDoxygen or \
     docDirName=="xmldoc" and not args.disableXMLDoc:
    print('<td data-order="%d" class="%s"><span class="glyphicon glyphicon-%s"></span>&nbsp;'%(int(result!="done"), "success" if result=="done" else "danger",
      "ok-sign alert-success" if result=="done" else "exclamation-sign alert-danger"), file=mainFD)
    print('  <a href="'+myurllib.pathname2url(pj(tool, docDirName+".txt"))+'">'+result+'</a>', file=mainFD)
    print('</td>', file=mainFD)
  docFD.close()
  mainFD.flush()

  if result!="done":
    return 1, run
  return 0, run



def runexamples(mainFD):
  if args.disableRunExamples:
    mainFD.flush()
    return 0

  print('<tr><td>Run examples</td>', file=mainFD); mainFD.flush()

  # runexamples.py command
  currentID=int(os.path.basename(args.reportOutDir)[len("result_"):])
  command=["./runexamples.py", "-j", str(args.j)]
  if args.url!=None:
    command.extend(["--url", args.url+"/result_%010d/runexamples_report"%(currentID)])
  command.extend(["--buildType", args.buildType])
  command.extend(["--reportOutDir", pj(args.reportOutDir, "runexamples_report")])
  command.extend(["--currentID", str(currentID)])
  command.extend(["--timeID", timeID.strftime("%Y-%m-%dT%H:%M:%S")])
  if args.buildSystemRun:
    command.extend(["--buildSystemRun", scriptdir+"/../buildSystem/scripts"])
  if args.coverage:
    command.extend(["--coverage", args.sourceDir+":"+args.binSuffix+":"+args.prefix])
  if args.webapp:
    command.extend(["--webapp"])
  command.extend(args.passToRunexamples)

  print("")
  print("")
  print("Output of runexamples.py")
  print("")
  if not os.path.isdir(pj(args.reportOutDir, "runexamples_report")): os.makedirs(pj(args.reportOutDir, "runexamples_report"))
  ret=abs(simplesandbox.call(command, envvar=simplesandboxEnvvars, shareddir=[".", pj(args.reportOutDir, "runexamples_report"),
                             "/var/www/html/mbsim/buildsystemstate"]+
                             list(map(lambda x: pj(args.sourceDir, x+args.binSuffix), ["fmatvec", "hdf5serie", "openmbv", "mbsim"])),
                             stderr=subprocess.STDOUT, buildSystemRun=args.buildSystemRun))

  if ret==0:
    print('<td class="success"><span class="glyphicon glyphicon-ok-sign alert-success"></span>&nbsp;<a href="'+myurllib.pathname2url(pj("runexamples_report", "result_current", "index.html"))+
      '">all examples passed</a></td>', file=mainFD)
  else:
    print('<td class="danger"><span class="glyphicon glyphicon-exclamation-sign alert-danger"></span>&nbsp;<a href="'+myurllib.pathname2url(pj("runexamples_report", "result_current", "index.html"))+
      '">examples failed</a></td>', file=mainFD)
  for i in range(0, 5-sum([args.disableConfigure, args.disableMake, not args.staticCodeAnalyzis, args.disableMakeCheck, args.disableDoxygen, args.disableXMLDoc])):
    print('<td>-</td>', file=mainFD)
  print('</tr>', file=mainFD)

  mainFD.flush()

  return ret



def createDistribution(mainFD):
  print('<tr><td>Create distribution</td>', file=mainFD); mainFD.flush()
  os.mkdir(pj(args.reportOutDir, "distribute"))
  distLog=codecs.open(pj(args.reportOutDir, "distribute", "log.txt"), "w", encoding="utf-8")
  distArchiveName="failed"
  distributeErrorCode=simplesandbox.call([pj(scriptdir, "../buildSystem/scripts/distribute.py"), "--outDir", pj(args.reportOutDir, "distribute"),
                                         args.prefix if args.prefix!=None else args.prefixAuto],
                                         buildSystemRun=args.buildSystemRun, shareddir=[pj(args.reportOutDir, "distribute")],
                                         stderr=subprocess.STDOUT, stdout=distLog)
  distLog.close()
  if distributeErrorCode==0:
    lines=codecs.open(pj(args.reportOutDir, "distribute", "log.txt"), "r", encoding="utf-8").readlines()
    distArchiveName=[x[len("distArchiveName="):] for x in lines if x.startswith("distArchiveName=")][0].rstrip()
    debugArchiveName=[x[len("debugArchiveName="):] for x in lines if x.startswith("debugArchiveName=")][0].rstrip()
    print('<td class="success"><span class="glyphicon glyphicon-ok-sign alert-success"></span>&nbsp;'+
          '<a href="'+myurllib.pathname2url(pj("distribute", "log.txt"))+'">done</a> - '+
          '<a href="'+myurllib.pathname2url(pj("distribute", distArchiveName))+'"><b>Download</b></a> - '+
          '<a href="'+myurllib.pathname2url(pj("distribute", debugArchiveName))+'">Debug-Info</a>'+
          '</td>', file=mainFD)
  else:
    print('<td class="danger"><span class="glyphicon glyphicon-exclamation-sign alert-danger"></span>&nbsp;'+
          '<a href="'+myurllib.pathname2url(pj("distribute", "log.txt"))+'">failed</a>'+
          '</td>', file=mainFD)
  for i in range(0, 5-sum([args.disableConfigure, args.disableMake, not args.staticCodeAnalyzis, args.disableMakeCheck, args.disableDoxygen, args.disableXMLDoc])):
    print('<td>-</td>', file=mainFD)
  print('</tr>', file=mainFD); mainFD.flush()

  return distributeErrorCode, distArchiveName



def releaseGeneration1(mainFD):
  print('''    // no initial communication needed -> set OK status
    statusMessage({success: true, message: "ready"}); // no initial communication needed -> set OK status
    // when a release version is entered update the button text
    $("#RELEASEVERSION").keyup(function() {
      curRelStr=$("#RELEASEVERSION").val();
      $(".RELSTR").each(function() {
        $(this).text(curRelStr);
      })
    });
    // when the release button is clicked
    $("#RELEASEBUTTON").click(function() {
      // check if all checkboxes are checked
      checkBoxUnchecked=false;
      $(".RELEASECHECK").each(function() {
        if(!$(this).prop("checked"))
          checkBoxUnchecked=true;
      });
      // get data
      var data={distArchiveName: $("#DISTARCHIVENAME").text(),
                reportOutDir: $("#REPORTOUTDIR").text(),
                relStr: $("#RELEASEVERSION").val(),
                commitid: {fmatvec:   $("#COMMITID_fmatvec").text(),
                           hdf5serie: $("#COMMITID_hdf5serie").text(),
                           openmbv:   $("#COMMITID_openmbv").text(),
                           mbsim:     $("#COMMITID_mbsim").text()}};
      if(checkBoxUnchecked || data.relStr=="")
        statusMessage({success: false, message: "You must first check all checklist items above and define the release string!"});
      else {
        statusCommunicating();
        // send data to server
        $.ajax({url: cgiPath+"/releasedistribution", xhrFields: {withCredentials: true}, dataType: "json", type: "POST",
                data: JSON.stringify(data)}).done(function(response) {
          statusMessage(response);
        });
      }
    });''', file=mainFD)

def releaseGeneration2(mainFD, distArchiveName):
  # default values
  relStr="x.y"
  relArchiveNamePostfix=re.sub("mbsim-env-(.*)-shared-build-xxx(\..*)", "\\1\\2",  distArchiveName)
  tagNamePostfix=re.sub("mbsim-env-(.*)-shared-build-xxx\..*", "\\1", distArchiveName)

  print('''<div class="panel panel-warning">
  <div class="panel-heading"><span class="glyphicon glyphicon-cloud-upload"></span>&nbsp;<span class="octicon octicon-tag"></span>&nbsp;<a data-toggle="collapse" href="#collapseReleaseGeneration">
 Release this distribution<span class="caret"> </span></a></div>
  <div class="panel-body panel-collapse collapse" id="collapseReleaseGeneration">
    <p>Releasing this distribution will</p>
    <ul>
      <li>tag the commits of the repositories, shown at the top, on GitHub.</li>
      <li>copy the above distribution (<b>Download</b> - Debug-Info) to the <a href="../../../releases">release directory</a>.</li>
    </ul>
    <p>When releasing a distribution you have</p>
    <div style="margin-left:1.5em">
      <div class="checkbox"><label>
        <input type="checkbox" class="RELEASECHECK"/>
        first to check that the corresponding debug build works including all examples.
      </label></div>
      <div class="checkbox"><label>
        <input type="checkbox" class="RELEASECHECK"/>
        first to check that the corresponging valgrind-examples of the debug build works.
      </label></div>
      <div class="checkbox"><label>
        <input type="checkbox" class="RELEASECHECK"/>
        first to download the distribution and check it manually on a native OS (at least
        using the test script .../mbsim-env/bin/mbsim-env-test[.bat]).
      </label></div>
      <div class="checkbox"><label>
        <input type="checkbox" class="RELEASECHECK"/>
        to release the Windows and Linux release builds at the same commit state using the same "release version" string!
      </label></div>
    </div>
    <div>
      <span id="DISTARCHIVENAME" style="display:none">%s</span>
      <span id="REPORTOUTDIR" style="display:none">%s</span>
      <div>
        <label for="RELEASEVERSION">Release version: </label>
        <input type="text" class="form-control" id="RELEASEVERSION" placeholder="%s">
      </div>
    </div>
    <div style="margin-top:0.5em">
      <button id="RELEASEBUTTON" type="button" disabled="disabled" class="_DISABLEONCOMM btn btn-default"><span class="glyphicon glyphicon-cloud-upload"></span>&nbsp;Release as <b>mbsim-env-release-<span class="RELSTR">%s</span>-%s</b> and <span class="octicon octicon-tag"></span>&nbsp;tag as <b>release/<span class="RELSTR">%s</span>-%s</b></button>
    </div>
    <p><small>(NOTE! This will create an annotated git tag with your username and email on the public MBSim-Env repositories on GitHub!)</small></p>
  </div>
</div>
<div id="STATUSPANEL" class="panel panel-info">
  <div class="panel-heading"><span class="glyphicon glyphicon-info-sign">
    </span>&nbsp;<span class="glyphicon glyphicon-exclamation-sign"></span>&nbsp;Status message</div>
  <div class="panel-body">
    <span id="STATUSMSG">Communicating with server, please wait. (reload page if hanging)</span>
  </div>
</div>'''%(distArchiveName, args.reportOutDir, relStr, relStr, relArchiveNamePostfix,
           relStr, tagNamePostfix), file=mainFD)



#####################################################################################
# call the main routine
#####################################################################################

if __name__=="__main__":
  mainRet=main()
  # 0 -> all passed
  # 1 -> build failed
  # 2 -> examples failed
  # 255 -> build skipped, same as last build
  if args.buildFailedExit and mainRet==1:
    mainRet=args.buildFailedExit
  exit(mainRet)

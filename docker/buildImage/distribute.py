#!/usr/bin/env python3

# imports
import argparse
import os
import sys
import fnmatch
import subprocess
import re
import shutil
import tempfile
import codecs

def octVersion():
  if sys.platform=="win32":
    return "9.1.0"
  return "4.4.1"

def pyVersion():
  if sys.platform=="win32":
    return "3.11"
  return "3.6"

args=None
platform=None
distArchive=None
debugArchive=None

# a ZipFile like class for 7z (but only for compression and it writes first to a temp-dir and compresses at close())
class SevenZipFile:
  def __init__(self, file, mode="r"):
    self.file = None
    if mode!="w":
      raise RuntimeError("SevenZipFile only support mode='w'")
    self.file = file
    self.tmpdir = tempfile.TemporaryDirectory()
  def __enter__(self):
    return self
  def __del__(self):
    if self.file is not None:
      self.close()
  def __exit__(self, type, value, traceback):
    if self.file is not None:
      self.close()
  def close(self):
    if os.path.exists(self.file):
      os.remove(self.file)
    subprocess.check_call(["7z", "a", os.path.abspath(self.file), "."], cwd=self.tmpdir.name, stdout=subprocess.DEVNULL)
    self.file=None
    self.tmpdir=None
  def _createDir(self, arcname):
    os.makedirs(self.tmpdir.name+os.path.sep+os.path.dirname(arcname), exist_ok=True)
  def add(self, name, arcname):
    self._createDir(arcname)
    shutil.copyfile(name, self.tmpdir.name+os.path.sep+arcname, follow_symlinks=False)
    shutil.copymode(name, self.tmpdir.name+os.path.sep+arcname, follow_symlinks=False)
  write = add
  def writestr(self, arcname, string):
    self._createDir(arcname)
    with open(self.tmpdir.name+os.path.sep+arcname, "wt") as f:
      f.write(string)

def config():
  # detect platform
  global platform
  if os.path.exists(args.prefix+"/bin/openmbv.exe"):
    platform="win"
  elif os.path.exists(args.prefix+"/bin/openmbv"):
    platform="linux"
  else:
    raise RuntimeError("Unknown platform")

  # find "import deplibs"
  sys.path.append(args.prefix+"/share/mbxmlutils/python")



def parseArguments():
  argparser=argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description="Create a Distribution of the MBSim-Environment.")
  
  argparser.add_argument("prefix", type=str, help="The directory to distribute (the --prefix dir)")
  argparser.add_argument("--outDir", type=str, required=True, help="Output dir of the distribution archive")

  global args
  args=argparser.parse_args()
  args.prefix=os.path.abspath(args.prefix)
  args.outDir=os.path.abspath(args.outDir)



def addDepsFor(name):
  noDepsForFile=[ # do not add deplibs for SWIG python libs
    "*/_OpenMBV.so",
    "*/_OpenMBV.pyd",
    "*/_fmatvec.so",
    "*/_fmatvec.pyd",
    "*/_mbsim.so",
    "*/_mbsim.pyd",
    "*/_OpenMBV.so",
    "*/_OpenMBV.pyd",
    "*/__mbsim_part*.so",
    "*/__mbsim_part*.pyd",
    "*/libqgtk3.so",
  ]
  noDepsForDir=[
  ]
  if any(map(lambda d: name.startswith(d), noDepsForDir)): return False
  if any(map(lambda g: fnmatch.fnmatch(name, g), noDepsForFile)): return False
  return True

def adaptRPATH(name, orgName):
  fnull=open(os.devnull, 'w')
  try:
    # remove all abs path from RPATH and add relative path to prefix/lib
    rpath=subprocess.check_output(["patchelf", "--print-rpath", name]).decode('utf-8').rstrip()
    vnewrpath=["$ORIGIN/"+os.path.relpath(args.prefix+"/lib", os.path.dirname(orgName))]
    if len(rpath)>0:
      for p in rpath.split(':'):
        if p[0]!='/':
          vnewrpath.append(p)
    if subprocess.call(["patchelf", "--force-rpath", "--set-rpath",
                        ":".join(vnewrpath), name], stdout=fnull)!=0:
      raise RuntimeError("patchelf failed")
  except subprocess.CalledProcessError as ex:
    pass

def addFileToDist(name, arcname, addDepLibs=True):
  import deplibs
  # do not add a file more than once
  if arcname in addFileToDist.content:
    return
  addFileToDist.content.add(arcname)
  # add

  # dir link -> error
  if os.path.islink(name) and os.path.isdir(name):
    raise RuntimeError("Directory links are not supported.")
  # file link -> add as link and also add the dereferenced file
  if os.path.islink(name):
    if platform=="win":
      return
    distArchive.write(name, arcname) # add link
    link=os.readlink(name) # add also the reference
    if "/" in link: # but only if to the same dire
      raise RuntimeError("Only links to the same dir are supported but "+name+" points to "+link+".")
    addFileToDist(os.path.dirname(name)+"/"+link, os.path.dirname(arcname)+"/"+link) # recursive call
  # file -> add as file
  elif os.path.isfile(name):
    # file type
    content=subprocess.check_output(["file", name]).decode('utf-8')
    if (platform=="linux" and re.search('ELF [0-9]+-bit LSB', content) is not None) or \
       (platform=="win"   and re.search('PE32\+? executable', content) is not None):
      # binary file
      # fix rpath (remove all absolute componentes from rpath; delete all RUNPATH)
      basename=os.path.basename(name)
      tmpDir=tempfile.mkdtemp()
      try:
        # strip or not
        if ((re.search('ELF [0-9]+-bit LSB', content) is not None and re.search('not stripped', content) is not None) or \
            (re.search('PE32\+? executable', content) is not None and re.search('stripped to external PDB', content) is None)) and \
           not name.startswith("/3rdparty/local/python-win64/"):# do not strip python files (these are not build with mingw)
          # not stripped binary file
          try:
            subprocess.check_call(["objcopy", "--only-keep-debug", name, tmpDir+"/"+basename+".debug"], stdout=subprocess.DEVNULL)
            subprocess.check_call(["objcopy", "--strip-all", name, tmpDir+"/"+basename], stdout=subprocess.DEVNULL)
            subprocess.check_call(["objcopy", "--add-gnu-debuglink="+tmpDir+"/"+basename+".debug", tmpDir+"/"+basename], stdout=subprocess.DEVNULL)
            if platform=="linux":
              if re.search('ELF [0-9]+-bit LSB', content) is not None:
                adaptRPATH(tmpDir+"/"+basename, name)
            distArchive.write(tmpDir+"/"+basename, arcname)
            # only add debug files of mbsim-env
            if name.startswith("/mbsim-env/"):
              debugArchive.write(tmpDir+"/"+basename+".debug", arcname+".debug")
          except:
            print("Failed to strip: "+name+". Adding unstripped.")
            distArchive.write(name, arcname)
          finally:
            if os.path.exists(tmpDir+"/"+basename): os.remove(tmpDir+"/"+basename)
            if os.path.exists(tmpDir+"/"+basename+".debug"): os.remove(tmpDir+"/"+basename+".debug")
        else:
          # stripped binary file
          # copy to tmp dir (to avoid modifying the original file)
          shutil.copy(name, tmpDir+"/"+basename)
          if platform=="linux":
            if re.search('ELF [0-9]+-bit LSB', content) is not None:
              adaptRPATH(tmpDir+"/"+basename, name)
          distArchive.write(tmpDir+"/"+basename, arcname)
      finally:
        shutil.rmtree(tmpDir)
      # add also all dependent libs to the lib/bin dir
      if addDepLibs and addDepsFor(name):
        for deplib in deplibs.depLibs(name):
          if platform=="linux":
            subdir="lib"
          if platform=="win":
            subdir="bin"
          addFileToDist(deplib, "mbsim-env/"+subdir+"/"+os.path.basename(deplib), False)
    else:
      # none binary file
      distArchive.write(name, arcname)
  # dir -> add recursively
  elif os.path.isdir(name):
    for dirpath, dirnames, filenames in os.walk(name):
      for file in filenames:
        addFileToDist(dirpath+"/"+file, arcname+dirpath[len(name):]+"/"+file)
  else:
    raise RuntimeError("Unknown file type: "+name)
addFileToDist.content=set()

def addStrToDist(text, arcname, exeBit=False):
  try:
    tempF=tempfile.NamedTemporaryFile(mode='wt', delete=False)
    tempF.write(text)
    tempF.close()
    if platform=="linux":
      if exeBit:
        os.chmod(tempF.name, 0o755)
    distArchive.write(tempF.name, arcname)
  finally:
    os.unlink(tempF.name)



def addReadme():
  print("Add README.txt file")
  sys.stdout.flush()

  if platform=="linux":
    note="This binary Linux64 build requires a Linux 64-bit operating system."
    scriptExt=""
  if platform=="win":
    note="This binary Win64 build requires a Windows 64-bit operating system."
    scriptExt=".bat"

  text='''Using the MBSim-Environment:
============================

NOTE:
%s

- Unpack the archive to an arbitary directory (already done)
  (Note: It is recommended, that the full directory path where the archive
  is unpacked does not contain any spaces.)
- Test the installation:
  1) Run the program <install-dir>/mbsim-env/bin/mbsim-env-test%s to check the
     installation. This will run some MBSim examples, some OpenMBVC++Interface
     SWIG examples and the programs h5plotserie, openmbv and mbsimgui.
  2) To Enable also the OpenMBVC++Interface SWIG python example ensure that
     "python" is in your PATH and set the envvar MBSIMENV_TEST_PYTHON=1.
     To Enable also the OpenMBVC++Interface SWIG java example ensure that
     "java" is in your PATH and set the envvar MBSIMENV_TEST_JAVA=1.
- Try any of the programs in <install-dir>/mbsim-env/bin
- Build your own models using XML and run it with
  <install-dir>/mbsim-env/bin/mbsimxml <mbsim-project-file.xml>
  View the plots with h5plotserie and view the animation with openmbv.
- Build your own models using the GUI: <install-dir>/mbsim-env/bin/mbsimgui

Have fun!
'''%(note, scriptExt)

  addStrToDist(text, 'mbsim-env/README.txt')



def addMBSimEnvTestExampleLinux(ex):
  text=r'''echo "%s"
cd $INSTDIR/examples/%s
''' % (ex, ex)
  if os.path.exists(args.prefix+"/../mbsim/examples/"+ex+"/MBS.flat.mbsx"):
    text+=r'''$INSTDIR/bin/mbsimflatxml MBS.flat.mbsx || ERROR="$ERROR %s"''' % (ex) + '\n'
  elif os.path.exists(args.prefix+"/../mbsim/examples/"+ex+"/MBS.mbsx"):
    text+=r'''$INSTDIR/bin/mbsimxml MBS.mbsx || ERROR="$ERROR %s"''' % (ex) + '\n'
  elif os.path.exists(args.prefix+"/../mbsim/examples/"+ex+"/FMI.mbsx"):
    text+=r'''$INSTDIR/bin/mbsimCreateFMU --nocompress FMI.mbsx || ERROR="$ERROR fmucre_%s"''' % (ex) + '\n'
    text+=r'''$INSTDIR/bin/fmuCheck.linux64 -f -l 5 mbsim.fmu || ERROR="$ERROR fmuchk_%s"''' % (ex) + '\n'
  elif os.path.exists(args.prefix+"/../mbsim/examples/"+ex+"/FMI_cosim.mbsx"):
    text+=r'''$INSTDIR/bin/mbsimCreateFMU --nocompress FMI_cosim.mbsx || ERROR="$ERROR fmucre_%s"''' % (ex) + '\n'
    text+=r'''$INSTDIR/bin/fmuCheck.linux64 -f -l 5 mbsim.fmu || ERROR="$ERROR fmuchk_%s"''' % (ex) + '\n'
  text+=r'''echo "DONE"
'''
  return text
def addMBSimEnvTestExampleWin(ex):
  text=r'''echo %s
cd "%%INSTDIR%%\examples\%s"
''' % (ex, ex)
  if os.path.exists(args.prefix+"/../mbsim/examples/"+ex+"/MBS.flat.mbsx"):
    text+=r'''call "%INSTDIR%\bin\mbsimflatxml" MBS.flat.mbsx'''+'\n'+\
          r'''IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% %s''' % (ex) + '\n'
  elif os.path.exists(args.prefix+"/../mbsim/examples/"+ex+"/MBS.mbsx"):
    text+=r'''call "%INSTDIR%\bin\mbsimxml" MBS.mbsx'''+'\n'+\
          r'''IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% %s''' % (ex) + '\n'
  elif os.path.exists(args.prefix+"/../mbsim/examples/"+ex+"/FMI.mbsx"):
    text+=r'''call "%INSTDIR%\bin\mbsimCreateFMU" --nocompress FMI.mbsx'''+'\n'+\
          r'''IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% fmucre_%s''' % (ex) + '\n'
    text+=r'''call "%INSTDIR%\bin\fmuCheck.win64" -f -l 5 mbsim.fmu'''+'\n'+\
          r'''IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% fmuch_%s''' % (ex) + '\n'
  elif os.path.exists(args.prefix+"/../mbsim/examples/"+ex+"/FMI_cosim.mbsx"):
    text+=r'''call "%INSTDIR%\bin\mbsimCreateFMU" --nocompress FMI_cosim.mbsx'''+'\n'+\
          r'''IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% fmucre_%s''' % (ex) + '\n'
    text+=r'''call "%INSTDIR%\bin\fmuCheck.win64" -f -l 5 mbsim.fmu'''+'\n'+\
          r'''IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% fmuch_%s''' % (ex) + '\n'
  text+=r'''echo DONE
'''
  return text
def addMBSimEnvTest():
  print("Add test script mbsim-env-test[.bat]")
  sys.stdout.flush()

  if platform=="linux":
    text=r'''#!/bin/bash

INSTDIR="$(readlink -f $(dirname $0)/..)"

ERROR=""

%s

export OPENMBVCPPINTERFACE_PREFIX="$INSTDIR"

echo "OPENMBVCPPINTERFACE_SWIG_OCTAVE"
cd $INSTDIR/share/openmbvcppinterface/examples/swig
$INSTDIR/bin/octave-cli octavetest.m || ERROR="$ERROR OPENMBVCPPINTERFACE_SWIG_OCTAVE"
echo "DONE"

echo "OPENMBVCPPINTERFACE_SWIG_PYTHON"
cd $INSTDIR/share/openmbvcppinterface/examples/swig
$INSTDIR/bin/python pythontest.py || ERROR="$ERROR OPENMBVCPPINTERFACE_SWIG_PYTHON"
echo "DONE"

if [ "_$MBSIMENV_TEST_JAVA" == "_1" ]; then
  echo "OPENMBVCPPINTERFACE_SWIG_JAVA"
  cd $INSTDIR/share/openmbvcppinterface/examples/swig
  java -classpath .:$INSTDIR/bin/openmbv.jar javatest || ERROR="$ERROR OPENMBVCPPINTERFACE_SWIG_JAVA"
  echo "DONE"
fi


echo "H5PLOTSERIE"
cd $INSTDIR/examples/xml/hierachical_modelling
$INSTDIR/bin/h5plotserie MBS.mbsim.mbsh5 || ERROR="$ERROR H5PLOTSERIE"
echo "DONE"

echo "OPENMBV"
cd $INSTDIR/examples/xml/hierachical_modelling
$INSTDIR/bin/openmbv MBS.mbsim.ombvx || ERROR="$ERROR OPENMBV"
echo "DONE"

echo "MBSIMGUI"
cd $INSTDIR/examples/xml/hierachical_modelling
$INSTDIR/bin/mbsimgui MBS.mbsx || ERROR="$ERROR MBSIMGUI"
echo "DONE"

if [ -z "$ERROR" ]; then
  echo "ALL TESTS PASSED"
else
  echo "THE FOLLOWING TESTS FAILED:"
  echo "$ERROR"
fi
''' % ('\n'.join(map(addMBSimEnvTestExampleLinux, basicExamples())))

  if platform=="win":
    text=r'''@echo off

set PWD=%%CD%%

set INSTDIR=%%~dp0..

set ERROR=

%s

set OPENMBVCPPINTERFACE_PREFIX=%%INSTDIR%%

echo OPENMBVCPPINTERFACE_SWIG_OCTAVE
cd "%%INSTDIR%%\share\openmbvcppinterface\examples\swig"
call "%%INSTDIR%%\bin\octave-cli" octavetest.m
IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% OPENMBVCPPINTERFACE_SWIG_OCTAVE
echo DONE

echo OPENMBVCPPINTERFACE_SWIG_PYTHON
cd "%%INSTDIR%%\share\openmbvcppinterface\examples\swig"
call "%%INSTDIR%%\bin\python" pythontest.py
IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% OPENMBVCPPINTERFACE_SWIG_PYTHON
echo DONE

IF "%%MBSIMENV_TEST_JAVA%%"=="1" (
  echo OPENMBVCPPINTERFACE_SWIG_JAVA
  cd "%%INSTDIR%%\share\openmbvcppinterface\examples\swig"
  call java -classpath .;%%INSTDIR%%/bin/openmbv.jar javatest
  IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% OPENMBVCPPINTERFACE_SWIG_JAVA
  echo DONE
)


echo H5PLOTSERIE
cd "%%INSTDIR%%\examples\xml\hierachical_modelling"
call "%%INSTDIR%%\bin\h5plotserie" MBS.mbsim.mbsh5
IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% H5PLOTSERIE
echo DONE

echo OPENMBV
cd "%%INSTDIR%%\examples\xml\hierachical_modelling"
call "%%INSTDIR%%\bin\openmbv" MBS.mbsim.ombvx
IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% OPENMBV
echo DONE

echo MBSIMGUI
cd "%%INSTDIR%%\examples\xml\hierachical_modelling"
call "%%INSTDIR%%\bin\mbsimgui" MBS.mbsx
IF %%ERRORLEVEL%% NEQ 0 set ERROR=%%ERROR%% MBSIMGUI
echo DONE

if "%%ERROR%%"=="" (
  echo ALL TESTS PASSED
) else (
  echo THE FOLLOWING TESTS FAILED:
  echo %%ERROR%%
)

cd "%%PWD%%"
''' % ('\n'.join(map(addMBSimEnvTestExampleWin, basicExamples())))

  addStrToDist(text, 'mbsim-env/bin/mbsim-env-test'+('.bat' if platform=="win" else ""), True)



def addOctave():
  print("Add octave share dir")
  sys.stdout.flush()

  if os.path.isdir("/3rdparty/local/share/octave"):
    addFileToDist("/3rdparty/local/share/octave", "mbsim-env/share/octave")
  if os.path.isdir("c:/msys64/ucrt64/share/octave"):
    addFileToDist("c:/msys64/ucrt64/share/octave", "mbsim-env/share/octave")

  print("Add octave executable")
  sys.stdout.flush()

  if platform=="linux":
    tmpDir=tempfile.mkdtemp()
    shutil.copy(f"/3rdparty/local/bin/octave-cli-{octVersion()}", tmpDir+"/octave-cli")
    subprocess.check_call(["patchelf", "--force-rpath", "--set-rpath", "$ORIGIN/../lib", tmpDir+"/octave-cli"])
    addFileToDist(tmpDir+"/octave-cli", "mbsim-env/bin/octave-cli")
  if platform=="win":
    if os.path.exists(f"/3rdparty/local/bin/octave-cli-{octVersion()}.exe"):
      addFileToDist(f"/3rdparty/local/bin/octave-cli-{octVersion()}.exe", "mbsim-env/bin/octave-cli.exe")
    if os.path.exists("c:/msys64/ucrt64/bin/octave-cli.exe"):
      addFileToDist("c:/msys64/ucrt64/bin/octave-cli.exe", "mbsim-env/bin/octave-cli.exe")

  print("Add octave oct files")
  sys.stdout.flush()

  if platform=="linux":
    addFileToDist(f"/3rdparty/local/lib/octave/{octVersion()}/oct/x86_64-pc-linux-gnu", f"mbsim-env/lib/octave/{octVersion()}/oct/x86_64-pc-linux-gnu")
  if platform=="win":
    if os.path.isdir(f"/3rdparty/local/lib/octave/{octVersion()}/oct/x86_64-w64-mingw32"):
      addFileToDist(f"/3rdparty/local/lib/octave/{octVersion()}/oct/x86_64-w64-mingw32", f"mbsim-env/lib/octave/{octVersion()}/oct/x86_64-w64-mingw32")
    if os.path.isdir(f"c:/msys64/ucrt64/lib/octave/{octVersion()}/oct/x86_64-w64-mingw32"):
      addFileToDist(f"c:/msys64/ucrt64/lib/octave/{octVersion()}/oct/x86_64-w64-mingw32", f"mbsim-env/lib/octave/{octVersion()}/oct/x86_64-w64-mingw32")



def addPython():
  print("Add python files")
  sys.stdout.flush()

  if platform=="linux":
    subdir=f"lib64/python{pyVersion()}"
    pysrcdirs=[f"/usr/local/lib/python{pyVersion()}", f"/usr/lib64/python{pyVersion()}", f"/usr/lib/python{pyVersion()}", ] # search packages in this order
  if platform=="win":
    subdir="lib"
    if os.path.isdir("/3rdparty/local/python-win64/Lib"):
      pysrcdirs=["/3rdparty/local/python-win64/Lib"] # search packages in this order
    if os.path.isdir(f"c:/msys64/ucrt64/lib/python{pyVersion()}/"):
      pysrcdirs=[f"c:/msys64/ucrt64/lib/python{pyVersion()}/"] # search packages in this order
  sitePackages=[["pip", False],
                ["setuptools", False],
                ["numpy", False],
                ["sympy", False],
                ["mpmath", False]]
  for pysrcdir in pysrcdirs:
    # everything in pysrcdir except some special dirs
    for d in os.listdir(pysrcdir):
      if d=="site-packages": # some subdirs of site-packages are added later
        continue
      if d=="config": # not required and contains links not supported by addFileToDist
        continue
      addFileToDist(pysrcdir+"/"+d, "mbsim-env/"+subdir+"/"+d)
    for sp in sitePackages:
      if sp[1]==False and os.path.exists(pysrcdir+"/site-packages/"+sp[0]):
        sp[1]=True
        addFileToDist(pysrcdir+"/site-packages/"+sp[0], "mbsim-env/"+subdir+"/site-packages/"+sp[0])

    # on Windows copy also the DLLs dir
    if platform=="win":
      if os.path.isdir(pysrcdir+"/../DLLs"):
        for f in os.listdir(pysrcdir+"/../DLLs"):
          addFileToDist(pysrcdir+"/../DLLs/"+f, "mbsim-env/DLLs/"+f)

  # add python executable
  if platform=="linux":
    pythonData='''#!/bin/bash
INSTDIR="$(readlink -f $(dirname $0)/..)"
export LD_LIBRARY_PATH="$INSTDIR/lib"
export PYTHONHOME=$INSTDIR
export PYTHONPATH=$INSTDIR/../mbsim-env-python-site-packages
$INSTDIR/bin/.python-envvar "$@"
'''
    addStrToDist(pythonData, "mbsim-env/bin/python", True)
    addFileToDist(f"/usr/bin/python{pyVersion()}", "mbsim-env/bin/.python-envvar")
  if platform=="win":
    pythonData=r'''@echo off
set INSTDIR=%~dp0..
set PYTHONHOME=%INSTDIR%
set PYTHONPATH=%INSTDIR%\..\mbsim-env-python-site-packages;%INSTDIR%\lib;%INSTDIR%\lib\lib-dynload;%INSTDIR%\lib\site-packages
"%INSTDIR%\bin\.python-envvar.exe" %*
'''
    addStrToDist(pythonData, "mbsim-env/bin/python.bat", True)
    if os.path.exists("/3rdparty/local/python-win64/python.exe"):
      addFileToDist("/3rdparty/local/python-win64/python.exe", "mbsim-env/bin/.python-envvar.exe")
    if os.path.exists("c:/msys64/ucrt64/bin/python.exe"):
      addFileToDist("c:/msys64/ucrt64/bin/python.exe", "mbsim-env/bin/.python-envvar.exe")

  # add pip executable
  if platform=="linux":
    pipData='''#!/bin/bash
INSTDIR="$(readlink -f $(dirname $0)/..)"
export PIP_TARGET=$INSTDIR/../mbsim-env-python-site-packages
export PYTHONHOME=$INSTDIR
export PYTHONPATH=$INSTDIR/../mbsim-env-python-site-packages
$INSTDIR/bin/python -m pip "$@"
'''
    addStrToDist(pipData, "mbsim-env/bin/pip", True)
  if platform=="win":
    pipData=r'''@echo off
set INSTDIR=%~dp0..
set PIP_TARGET=%INSTDIR%\..\mbsim-env-python-site-packages
set PYTHONHOME=%INSTDIR%
set PYTHONPATH=%INSTDIR%\..\mbsim-env-python-site-packages;%INSTDIR%\lib;%INSTDIR%\lib\lib-dynload;%INSTDIR%\lib\site-packages
"%INSTDIR%\bin\.python-envvar.exe" -m pip %*
'''
    addStrToDist(pipData, "mbsim-env/bin/pip.bat", True)



# return all basic examples except source examples
def basicExamples():
  ret=[]
  for dirpath, dirnames, filenames in os.walk(args.prefix+"/../mbsim/examples"):
    if 'labels' in filenames:
      if not os.path.isfile(dirpath+"/Makefile") and not os.path.isfile(dirpath+"/Makefile_FMI") and \
        'basic' in codecs.open(dirpath+"/labels", "r", encoding="utf-8").read().rstrip().split(' '):
        ret.append(dirpath[len(args.prefix+"/../mbsim/examples")+1:])
  return ret

def addExamples():
  print("Add some examples") # all examples with label "basic"
  sys.stdout.flush()

  for ex in basicExamples():
    for file in subprocess.check_output(["git", "ls-files"], cwd=args.prefix+"/../mbsim/examples/"+ex).decode('utf-8').rstrip().splitlines():
      addFileToDist(args.prefix+"/../mbsim/examples/"+ex+"/"+file, "mbsim-env/examples/"+ex+"/"+file)



def main():
  parseArguments()

  config()

  # open archives
  print("Create binary distribution")
  print("")
  sys.stdout.flush()

  global distArchive, debugArchive
  if platform=="linux":
    distArchiveName="mbsim-env-linux64-shared-build-xxx.7z"
    debugArchiveName="mbsim-env-linux64-shared-build-xxx-debug.7z"
  if platform=="win":
    distArchiveName="mbsim-env-win64-shared-build-xxx.7z"
    debugArchiveName="mbsim-env-win64-shared-build-xxx-debug.7z"
  distArchive=SevenZipFile(args.outDir+"/"+distArchiveName, mode='w')
  debugArchive=SevenZipFile(args.outDir+"/"+debugArchiveName, mode='w')
 
  # add special files
  addReadme()
  addMBSimEnvTest()

  # add prefix
  print("Add prefix dir of mbsim-env")
  sys.stdout.flush()
  addFileToDist(args.prefix, "mbsim-env")
  # add octave
  addOctave()
  # add python
  addPython()

  # add some examples
  addExamples()

  # close archives
  print("")
  print("Finished")
  sys.stdout.flush()
  distArchive.close()
  debugArchive.close()

  return distArchiveName, debugArchiveName



if __name__=="__main__":
  distArchiveName, debugArchiveName=main()
  print("distArchiveName="+distArchiveName)
  print("debugArchiveName="+debugArchiveName)
  sys.stdout.flush()

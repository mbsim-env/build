#!/usr/bin/python

from __future__ import print_function # to enable the print function for backward compatiblity with python2
import os
import glob
import buildSystemState
import subprocess
import datetime
import sys
import shutil

stateDir=sys.argv[1]
inDir=sys.argv[2]
outDir=sys.argv[3]

def buildLatex(f):
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  if len(glob.glob("*.bib"))>0:
    subprocess.check_call(["bibtex", "main"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)

if not os.path.isdir(outDir):
  os.makedirs(outDir)

scriptdir=os.path.dirname(os.path.realpath(__file__))

os.chdir(inDir)
curdir=os.getcwd()

nrDocFailed=0
f=open(outDir+"/manualsbuild.log", "w")
print("Logfile of the build process of the manuals. Generated on "+str(datetime.datetime.now()), file=f)
print("", file=f)
f.flush()
mainFiles=glob.glob("*/main.tex")
for texMain in mainFiles:
  os.chdir(os.path.dirname(texMain))

  print("", file=f)
  print("", file=f)
  print("Building in directory "+os.getcwd(), file=f)
  print("", file=f)
  f.flush()

  try:
    buildLatex(f)
    shutil.copyfile("main.pdf", outDir+"/"+os.path.dirname(texMain)+".pdf")
  except subprocess.CalledProcessError as ex:
    print(ex)
    print(ex.output)
    nrDocFailed+=1
  f.flush()

  os.chdir(curdir)
f.close()

buildSystemState.update(stateDir, "build-manuals", "Building Manuals Failed",
                        str(nrDocFailed)+" of "+str(len(mainFiles))+" manuals failed to build.",
                        "https://www.mbsim-env.de/mbsim/html/manuals/", nrDocFailed, len(mainFiles))

sys.exit(nrDocFailed)

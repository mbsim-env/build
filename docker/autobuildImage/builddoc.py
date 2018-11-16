#!/usr/bin/python

from __future__ import print_function # to enable the print function for backward compatiblity with python2
import os
import glob
import sys
sys.path.append("/context")
import buildSystemState
import subprocess
import datetime
import shutil

inDir=sys.argv[1]
outDir=sys.argv[2]

def buildLatex(f):
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  if len(glob.glob("*.bib"))>0:
    subprocess.check_call(["bibtex", "main"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)

if not os.path.isdir(outDir):
  os.makedirs(outDir)

os.chdir(inDir)
curdir=os.getcwd()

nrDocFailed=0
f=open(outDir+"/manualsbuild.log", "w")
print("Logfile of the build process of the manuals. Generated on "+datetime.datetime.utcnow()+"+00:00", file=f)
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
    sys.stdout.flush()
    nrDocFailed+=1
  f.flush()

  os.chdir(curdir)
f.close()

buildSystemState.update("build-manuals", "Building Manuals Failed",
                        str(nrDocFailed)+" of "+str(len(mainFiles))+" manuals failed to build.",
                        "https://"+os.environ['MBSIMENVSERVERNAME']+"/mbsim/html/manuals/", nrDocFailed, len(mainFiles))

sys.exit(nrDocFailed)

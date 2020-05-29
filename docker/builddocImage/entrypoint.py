#!/usr/bin/python3

import os
import glob
import sys
sys.path.append("/context")
import subprocess
import datetime
import shutil

outDir="/mbsim-report/manuals"

def buildLatex(f):
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  if len(glob.glob("*.bib"))>0:
    subprocess.check_call(["bibtex", "main"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)
  subprocess.check_call(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], stderr=subprocess.STDOUT, stdout=f)

if not os.path.isdir(outDir):
  os.makedirs(outDir)

os.chdir("/mbsim-env/mbsim/manuals")
curdir=os.getcwd()

nrDocFailed=0
f=open(outDir+"/manualsbuild.log", "w")
print("Logfile of the build process of the manuals. Generated on "+datetime.datetime.utcnow().isoformat()+"Z", file=f)
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

sys.exit(nrDocFailed)

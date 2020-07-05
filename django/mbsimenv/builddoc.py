#!/usr/bin/python3

import os
import glob
import datetime
import io
import django
os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings"
django.setup()
import base.helper
import service

def buildLatex(f):
  if base.helper.subprocessCall(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], f)!=0:
    return 1
  if len(glob.glob("*.bib"))>0:
    if base.helper.subprocessCall(["bibtex", "main"], f)!=0:
      return 1
  if base.helper.subprocessCall(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], f)!=0:
    return 1
  if base.helper.subprocessCall(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], f)!=0:
    return 1
  if base.helper.subprocessCall(["pdflatex", "-halt-on-error", "-file-line-error", "main.tex"], f)!=0:
    return 1
  return 0

curdir=os.getcwd()
curManualIDs=set()
for texMain in glob.glob("*/main.tex"):
  idName=os.path.dirname(texMain)
  os.chdir(idName)

  f=io.StringIO()
  print("Logfile of the build process of manual "+os.path.dirname(texMain)+". Generated on "+datetime.datetime.utcnow().isoformat()+"Z", file=f)
  print("", file=f)

  ret=buildLatex(f)

  curManualIDs.add(idName)
  manual, created=service.models.Manual.objects.get_or_create(id=idName, defaults={
    "manualName": idName,
    "resultOK": ret==0,
    "resultOutput": f.getvalue(),
  })
  if not created:
    manual.manualName=idName
    manual.resultOK=ret==0
    manual.resultOutput=f.getvalue()
  manual.manualFileName=idName+".pdf"
  manual.save()
  with manual.manualFile.open("wb") as fo:
    with open("main.pdf", "rb") as fi:
      fo.write(fi.read())
  f.close()

  os.chdir(curdir)

service.models.Manual.objects.exclude(id__in=curManualIDs).delete()

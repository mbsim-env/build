import sys
import subprocess

#mfmf
import shutil
print(shutil.which("gcc"))
import os
print(os.environ.get("CHERE_INVOKING", "notfound"))
print(os.environ.get("MSYSTEM", "notfound"))
#mfmf
quoteChars=["$", "`", "\\", "\n"]
argStr = ""
for a in sys.argv[1:]:
  for qc in quoteChars:
    a = a.replace(qc, "\\"+qc)
  argStr += ' "'+a.replace('"', '\\"')+'"'
sys.exit(subprocess.call(["c:/msys64/usr/bin/bash.exe", "-l", "-c"]+[argStr]))

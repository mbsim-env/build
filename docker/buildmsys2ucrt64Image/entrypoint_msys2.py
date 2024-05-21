import sys
import subprocess

quoteChars=["$", "`", "\\", "\n"]
argStr = ""
for a in sys.argv[1:]:
  for qc in quoteChars:
    a = a.replace(qc, "\\"+qc)
  argStr += ' "'+a.replace('"', '\\"')+'"'
sys.exit(subprocess.call(["c:/msys64/usr/bin/bash.exe", "-l", "-c"]+[argStr]))

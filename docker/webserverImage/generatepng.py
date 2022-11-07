import os
import subprocess
import octicons.templatetags.octicons

DIR="/tmp/generatepng"
os.mkdir(DIR)
DIR+="/"

for OCTICON in ['gear', 'beaker']:
  with open(DIR+OCTICON+".svg", "w") as f:
    f.write(octicons.templatetags.octicons.octicon(OCTICON))
  subprocess.check_call(["rsvg-convert", "-f", "png", "-w", "50", "-h", "50", DIR+OCTICON+".svg", "-o", DIR+OCTICON+".png"])

#!/usr/bin/env python3

import subprocess
import sys
sys.path.append("/context/mbsimenv")
import mbsimenvSecrets

# change password for dockeruser
p=subprocess.Popen(["/usr/sbin/chpasswd"], stdin=subprocess.PIPE)    
pw=mbsimenvSecrets.getSecrets("filestoragePassword")
p.communicate(input=("dockeruser:"+pw).encode("UTF-8"))
p.wait()

# run sshd
ret=subprocess.call(["/usr/sbin/sshd", "-D", "-e"])
sys.exit(ret)

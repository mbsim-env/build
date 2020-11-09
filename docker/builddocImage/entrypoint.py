#!/usr/bin/python3

import subprocess

subprocess.check_call(["/context/mbsimenv/builddoc.py", "--buildSystemRun"], cwd="/mbsim-env/mbsim/manuals")

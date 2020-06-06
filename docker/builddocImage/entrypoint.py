#!/usr/bin/python3

import subprocess

subprocess.check_call(["/context/mbsimenv/builddoc.py"], cwd="/mbsim-env/mbsim/manuals")

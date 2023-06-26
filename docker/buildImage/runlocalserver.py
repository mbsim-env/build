#!/usr/bin/env python3

import os
import sys
import django
import argparse
sys.path.append("/mbsim-env/build/django/mbsimenv")
import base

argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Run a local django server in docker container.")
argparser.add_argument("--localServerPort", type=int, default=27583, help='Port for local server')
args=argparser.parse_args()

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_localdocker"
django.setup()

s=base.helper.startLocalServer(args.localServerPort)
if s["process"] is None:
  sys.exit(0)
else:
  sys.stdout.flush()
  sys.exit(s["process"].wait())

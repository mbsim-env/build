#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import fmpy
import os
import importlib.util

argparser = argparse.ArgumentParser()
argparser.add_argument("unzipdir", type=os.path.abspath)
meOrCosim = argparser.add_mutually_exclusive_group()
meOrCosim.add_argument('--me', action='store_true')
meOrCosim.add_argument('--cosim', action='store_false')

# argument completion in bash
if importlib.util.find_spec("argcomplete") is not None:
  import argcomplete
  argcomplete.autocomplete(argparser)

args = argparser.parse_args()

md = fmpy.read_model_description("mbsim.fmu")
if args.me:
  fmu = fmpy.fmi1.FMU1Model(guid=md.guid, modelIdentifier=md.modelExchange.modelIdentifier, unzipDirectory=args.unzipdir)
else:
  fmu = fmpy.fmi1.FMU1Slave(guid=md.guid, modelIdentifier=md.coSimulation.modelIdentifier, unzipDirectory=args.unzipdir)
fmu.instantiate()

outputVR =0 # the VR of the "Output directory"
fmu.setString([outputVR], ["fmuPyOutput"])

fmu.initialize()
fmu.terminate()
fmu.freeInstance()

#!/usr/bin/env python3

import argparse
import fmpy
import os

argparser = argparse.ArgumentParser()
argparser.add_argument("unzipdir", type=os.path.abspath)
meOrCosim = argparser.add_mutually_exclusive_group()
meOrCosim.add_argument('--me', action='store_true')
meOrCosim.add_argument('--cosim', action='store_false')
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

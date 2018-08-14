#!/usr/bin/python

#mfmf
#import subprocess
#import os
#
#scriptdir=os.path.dirname(os.path.realpath(__file__))
#
#if subprocess.call([scriptdir+"/linux64-dailydebug.py"])!=0:
#  print("linux64-dailydebug.py failed.")
#
#if subprocess.call([scriptdir+"/linux64-dailyrelease.py"])!=0:
#  print("linux64-dailyrelease.sh failed.")
#
#if subprocess.call([scriptdir+"/win64-dailyrelease.py"])!=0:
#  print("win64-dailyrelease.sh failed.")

# linux64-ci
#sudo docker run --rm -v /home/markus/docker/tmp/mbsim-env:/mbsim-env -v /home/markus/docker/tmp/mbsim-ccache:/mbsim-ccache -v /home/markus/docker/tmp:/mbsim-report -v /home/markus/docker/tmp/mbsim-state:/mbsim-state -v /home/markus/docker/tmp/mbsim-config:/mbsim-config mbsimenv/mbsim-env-autobuild -j 8 --buildType linux64-ci

# linux64-dailyrelease
#sudo docker run --rm -v /home/markus/docker/tmp/mbsim-env:/mbsim-env -v /home/markus/docker/tmp/mbsim-ccache:/mbsim-ccache -v /home/markus/docker/tmp:/mbsim-report -v /home/markus/docker/tmp/mbsim-state:/mbsim-state -v /home/markus/docker/tmp/mbsim-config:/mbsim-config mbsimenv/mbsim-env-autobuild -j 8 --buildType linux64-dailyrelease

# linux64-dailydebug
#sudo docker run --rm -v /home/markus/docker/tmp/mbsim-env:/mbsim-env -v /home/markus/docker/tmp/mbsim-ccache:/mbsim-ccache -v /home/markus/docker/tmp:/mbsim-report -v /home/markus/docker/tmp/mbsim-state:/mbsim-state -v /home/markus/docker/tmp/mbsim-config:/mbsim-config mbsimenv/mbsim-env-autobuild -j 8 --buildType linux64-dailydebug --forceBuild --buildDoc --valgrindExamples --updateReferences xml/hierachical_modelling

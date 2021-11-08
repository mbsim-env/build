#!/bin/bash

SCRIPTDIR=$(readlink -m $(dirname $0))
MBSIMENVDIR=$(readlink -f "$SCRIPTDIR"/../../..)

# help
for A in "$@"; do
  if [ "$A" == "-h" -o "$A" == "--help" ]; then
    echo "This script runs the runexamples.py script from mbsim-env in a mbsimenv/build Docker container."
    echo "If you don't know Docker consider a mbsimenv/build container as a virtual machine with mbsimenv installed."
    echo "All arguments to this script are passed (added) to runexamples.py."
    echo ""
    break
  fi
done

MBSIMENVTAGNAME=${MBSIMENVTAGNAME:-latest}
docker run -d --init --entrypoint= --rm \
  --user $(id -u):$(id -g) \
  -v "$MBSIMENVDIR":/mbsim-env \
  --net=host \
  mbsimenv/build:$MBSIMENVTAGNAME \
  /mbsim-env/build/docker/buildImage/runlocalserver.py > /dev/null
# wait until localserver.json exists to avoid a race-condition between containers
while [ ! -e $MBSIMENVDIR/build/django/mbsimenv/localserver.json ]; do sleep 0.1; done

# run using mbsbd with all required args all all user args appended
"$SCRIPTDIR"/mbsbd "$MBSIMENVDIR"/build/django/mbsimenv/runexamples.py --buildType localDocker "$@"

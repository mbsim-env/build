#!/bin/bash

SCRIPTDIR=$(readlink -m $(dirname $0))
MBSIMENVDIR=$(readlink -f "$SCRIPTDIR"/../../..)

# help
for A in "$@"; do
  if [ "$A" == "-h" -o "$A" == "--help" ]; then
    echo "This script runs the runexamples.py script from mbsim-env."
    echo "All arguments to this script are passed to runexamples.py."
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

# run using mbsbd with all required args all all user args appended
"$SCRIPTDIR"/mbsbd "$MBSIMENVDIR"/build/django/mbsimenv/runexamples.py --buildType localDockerWin64 "$@"

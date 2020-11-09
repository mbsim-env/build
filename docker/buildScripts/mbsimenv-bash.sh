#!/bin/bash

SCRIPTDIR=$(readlink -m $(dirname $0))
MBSIMENVDIR=$(readlink -f "$SCRIPTDIR"/../../..)

# help
for A in "$@"; do
  if [ "$A" == "-h" -o "$A" == "--help" ]; then
    echo "This script starts an interactive bash in the mbsim-env win64 Docker container."
    echo "Your build directory $MBSIMENVDIR is mounted at /mbsim-env inside the container."
    echo ""
    break
  fi
done

# run using mbsbd with all required args all all user args appended
"$SCRIPTDIR"/mbsbd MBSIMENV_INTERACTIVE bash

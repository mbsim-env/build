#!/bin/bash

echo "MFMF: untested"

set -e
set -o pipefail

SCRIPTDIR=$(readlink -m $(dirname $0))
MBSIMENVDIR=$(readlink -f "$SCRIPTDIR"/../../..)

# help
echo "Starting an interactive bash in a mbsimenv/buildmsys2ucrt64 Docker container."
echo "If you don't know Docker consider a mbsimenv/buildmsys2ucrt64 container as a virtual machine with mbsimenv installed."
echo "Your local directory $MBSIMENVDIR is mounted at /mbsim-env inside the container."
echo "The home directory in the container /tmp/home corresponds to the local directory $MBSIMENVDIR/.home"
echo "Type 'exit' to exit this container."
echo ""

# run using mbsbd with all required args all all user args appended
"$SCRIPTDIR"/mbsbd MBSIMENV_INTERACTIVE c:/msys64/usr/bin/bash.exe -l

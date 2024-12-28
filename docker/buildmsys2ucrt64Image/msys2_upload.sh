#!/bin/bash

set -e
set -o pipefail

export SSHPASS=$mbsimenvsec_filestoragePassword

echo "upload $MSYS2INSTALLERRSYNCURI/db.tar.gz"
sshpass -e rsync -e "ssh -p $MSYS2INSTALLERRSYNCPORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" /db.tar.gz    $MSYS2INSTALLERRSYNCURI
echo "upload $MSYS2INSTALLERRSYNCURI/cache.tar.gz"
sshpass -e rsync -e "ssh -p $MSYS2INSTALLERRSYNCPORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" /cache.tar.gz $MSYS2INSTALLERRSYNCURI

#!/bin/bash

set -e
set -o pipefail

export SSHPASS=$mbsimenvsec_filestoragePassword

sshpass -e rsync -e "ssh -p $MSYS2INSTALLERRSYNCPORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" /db.tar.gz    $MSYS2INSTALLERRSYNCURI
sshpass -e rsync -e "ssh -p $MSYS2INSTALLERRSYNCPORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" /cache.tar.gz $MSYS2INSTALLERRSYNCURI

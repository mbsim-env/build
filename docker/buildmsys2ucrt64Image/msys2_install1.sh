#!/bin/bash

set -e
set -o pipefail

if [ $MSYS2INSTALLERDOWNLOAD -eq 1 ]; then
  # download/install msys2 package db
  echo "Download and extract $MSYS2INSTALLERURI/db.tar.gz"
  wget --no-verbose $MSYS2INSTALLERURI/db.tar.gz
  tar -C /var/lib/pacman/sync/ -xzf $PWD/db.tar.gz
  rm -f db.tar.gz

  # download/install msys2 package cache
  echo "Download and extract $MSYS2INSTALLERURI/cache.tar.gz"
  wget --no-verbose $MSYS2INSTALLERURI/cache.tar.gz
  tar -C /var/cache/pacman/pkg/ -xzf $PWD/cache.tar.gz
  rm -f cache.tar.gz
fi

# update install msys2 packages according package db
if [ $MSYS2INSTALLERUPDATEBYPUBLIC -eq 1 ]; then
  echo "pacman -Syuu (first stage)"
  pacman --noconfirm -Syuu
else
  echo "pacman -Suu (first stage)"
  pacman --noconfirm -Suu
fi

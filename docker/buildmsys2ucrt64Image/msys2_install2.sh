#!/bin/bash

set -e
set -o pipefail

if [ -e /msys2_install1.sh.error ]; then
  echo "msys2_install1.sh failed, see above"
  exit 1
fi

# update install msys2 packages according package db
if [ $MSYS2INSTALLERUPDATEBYPUBLIC -eq 1 ]; then
  echo "pacman -Syuu (second stage)"
  pacman --noconfirm -Syuu
else
  echo "pacman -Suu (second stage)"
  pacman --noconfirm -Suu
fi

# update install new mys2 packages according package db
echo "pacman -S <package_list>"
pacman --noconfirm -S "$@"

if [ $MSYS2INSTALLERUPLOAD -eq 1 ]; then
  # pack and store msys2 package cache
  echo "create tar /cache.tar.gz"
  tar -C /var/cache/pacman/pkg/ -czf /cache.tar.gz .

  # pack and store msys2 package db
  echo "create tar /db.tar.gz"
  tar -C /var/lib/pacman/sync/ -czf /db.tar.gz .
fi

# remove msys2 cache
echo "pacman -Scc"
pacman --noconfirm -Scc

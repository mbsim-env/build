#!/bin/bash

scl enable devtoolset-7 "PATH=/usr/lib64/ccache:\$PATH /context/entrypoint.py $*"

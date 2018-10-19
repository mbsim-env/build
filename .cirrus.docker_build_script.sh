#!/bin/sh

RET=0

docker pull mbsimenv/base:$CIRRUS_BRANCH
docker build --cache-from mbsimenv/base:$CIRRUS_BRANCH --tag mbsimenv/base:$CIRRUS_BRANCH --build-arg=JOBS=$JOBS docker/baseImage
test $? != 0 && RET=1

docker pull mbsimenv/build:$CIRRUS_BRANCH
docker build --cache-from mbsimenv/build:$CIRRUS_BRANCH --tag mbsimenv/build:$CIRRUS_BRANCH --build-arg=JOBS=$JOBS docker/buildImage
test $? != 0 && RET=1

#docker build --no-cache --tag mbsimenv/run:$CIRRUS_BRANCH --build-arg=JOBS=$JOBS -f docker/runImage/Dockerfile docker/..
#test $? != 0 && RET=1

docker pull mbsimenv/proxy:$CIRRUS_BRANCH
docker build --cache-from mbsimenv/proxy:$CIRRUS_BRANCH --tag mbsimenv/proxy:$CIRRUS_BRANCH docker/proxyImage
test $? != 0 && RET=1

docker pull mbsimenv/autobuild:$CIRRUS_BRANCH
docker build --cache-from mbsimenv/autobuild:$CIRRUS_BRANCH --tag mbsimenv/autobuild:$CIRRUS_BRANCH -f docker/autobuildImage/Dockerfile docker/..
test $? != 0 && RET=1

docker pull mbsimenv/webserver:$CIRRUS_BRANCH
docker build --cache-from mbsimenv/webserver:$CIRRUS_BRANCH --tag mbsimenv/webserver:$CIRRUS_BRANCH -f webserverImage/Dockerfile docker/.
test $? != 0 && RET=1

docker pull mbsimenv/webapp:$CIRRUS_BRANCH
docker build --cache-from mbsimenv/webapp:$CIRRUS_BRANCH --tag mbsimenv/webapp:$CIRRUS_BRANCH -f webappImage/Dockerfile docker/.
test $? != 0 && RET=1

docker pull mbsimenv/webapprun:$CIRRUS_BRANCH
docker build --cache-from mbsimenv/webapprun:$CIRRUS_BRANCH --tag mbsimenv/webapprun:$CIRRUS_BRANCH docker/webappImage
test $? != 0 && RET=1

exit $RET

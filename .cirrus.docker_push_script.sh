#!/bin/sh

RET=0

docker push mbsimenv/base:$CIRRUS_BRANCH
test $? != 0 && RET=1

docker push mbsimenv/build:$CIRRUS_BRANCH
test $? != 0 && RET=1

#docker push-tag mbsimenv/run:$CIRRUS_BRANCH
#test $? != 0 && RET=1

docker push mbsimenv/proxy:$CIRRUS_BRANCH
test $? != 0 && RET=1

docker push mbsimenv/autobuild:$CIRRUS_BRANCH
test $? != 0 && RET=1

docker push mbsimenv/webserver:$CIRRUS_BRANCH
test $? != 0 && RET=1

docker push mbsimenv/webapp:$CIRRUS_BRANCH
test $? != 0 && RET=1

docker push mbsimenv/webapprun:$CIRRUS_BRANCH
test $? != 0 && RET=1

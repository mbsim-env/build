#!/bin/bash

docker run --rm --entrypoint rpm centos:centos7 -qa > /tmp/rpm-centos
docker run --rm --entrypoint rpm mbsimenv/base -qa > /tmp/rpm-base
docker run --rm --entrypoint rpm mbsimenv/build -qa > /tmp/rpm-build
docker run --rm --entrypoint rpm mbsimenv/buildwin64 -qa > /tmp/rpm-buildwin64
#docker run --rm --entrypoint rpm mbsimenv/run -qa > /tmp/rpm-run
docker run --rm --entrypoint rpm mbsimenv/webserver -qa > /tmp/rpm-webserver
docker run --rm --entrypoint rpm mbsimenv/webapp -qa > /tmp/rpm-webapp
docker run --rm --entrypoint rpm mbsimenv/webapprun -qa > /tmp/rpm-webapprun
docker run --rm --entrypoint rpm mbsimenv/proxy -qa > /tmp/rpm-proxy

cp /tmp/rpm-centos /tmp/rpm-centos_
cat /tmp/rpm-base /tmp/rpm-centos | sort | uniq -u > /tmp/rpm-base_
cat /tmp/rpm-build /tmp/rpm-base | sort | uniq -u > /tmp/rpm-build_
cat /tmp/rpm-buildwin64 /tmp/rpm-centos | sort | uniq -u > /tmp/rpm-buildwin64_
#cat /tmp/rpm-run /tmp/rpm-base | sort | uniq -u > /tmp/rpm-run_
cat /tmp/rpm-webserver /tmp/rpm-centos | sort | uniq -u > /tmp/rpm-webserver_
cat /tmp/rpm-webapp /tmp/rpm-centos | sort | uniq -u > /tmp/rpm-webapp_
cat /tmp/rpm-proxy /tmp/rpm-centos | sort | uniq -u > /tmp/rpm-proxy_

AI=""
AI="$AI /tmp/rpm-centos_"
AI="$AI /tmp/rpm-base_"
AI="$AI /tmp/rpm-build_"
AI="$AI /tmp/rpm-buildwin64_"
#AI="$AI /tmp/rpm-run_"
AI="$AI /tmp/rpm-webserver_"
AI="$AI /tmp/rpm-webapp_"
AI="$AI /tmp/rpm-webapprun_"
AI="$AI /tmp/rpm-proxy_"
i1=0
for I1 in $AI; do
  i1=$[$i1+1]
  i2=0
  for I2 in $AI; do
    i2=$[$i2+1]
    test $i2 -ge $i1 && continue
    test $(cat $I1 $I2 | sort | uniq -d | wc -l) -eq 0 && continue
    echo
    echo DUP in $I1 and $I2
    cat $I1 $I2 | sort | uniq -d
  done
done

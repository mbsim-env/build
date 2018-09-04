# get noVNC
FROM centos:centos7 AS temp
ARG NOVNCBRANCH=v0.6.2
RUN yum install -y git && yum clean all
# install noVNC (the package from yum is to old)
WORKDIR /tmp
RUN git clone https://github.com/novnc/noVNC.git
WORKDIR /tmp/noVNC
RUN git checkout $NOVNCBRANCH



# use the build image as base
FROM centos:centos7

# install software
RUN yum install -y epel-release && yum install -y \
  httpd \
  mod_ssl \
  python2-certbot \
  cronie \
  && yum clean all

# a webserver is running on port 80
EXPOSE 80/tcp 443/tcp

COPY --from=temp /tmp/noVNC/include /var/www/html/noVNC/include

# copy cgi script
COPY cgi-bin/mbsimBuildServiceServer.py /var/www/cgi-bin/mbsimBuildServiceServer.py
# copy html script
COPY html /var/www/html/mbsim/html
# copy entrypoint
COPY entrypoint.py /context/entrypoint.py
COPY cron-daily.py /context/cron-daily.py

# configure web server
# add top level config (stored in docker/webserverImage/httpd_toplevel.conf)
COPY conf/httpd_toplevel.conf /tmp/httpd_toplevel.conf
RUN cat /tmp/httpd_toplevel.conf /etc/httpd/conf/httpd.conf > /etc/httpd/conf/httpd.conf.new && \
  mv /etc/httpd/conf/httpd.conf.new /etc/httpd/conf/httpd.conf && \
  rm -f /tmp/httpd_toplevel.conf
# replace <Directory "/var/www/html"> with docker/webserverImage/httpd_rootdir.conf
COPY conf/httpd_rootdir.conf /tmp/httpd_rootdir.conf
RUN set -o pipefail && \
  B=$(sed -rn '/^ *< *Directory +"\/var\/www\/html" *> *(#.*)?$/=' /etc/httpd/conf/httpd.conf | head -n 1); \
  O=$(sed -rn "$[$B+1],\$p" /etc/httpd/conf/httpd.conf | sed -rn '/^ *< *\/ *Directory *> *(#.*)?/=' | head -n 1); \
  sed -rn "1,$[$B-1]p;$[$B+$O+1],\$p" /etc/httpd/conf/httpd.conf > /etc/httpd/conf/httpd.conf.new && \
  cat /etc/httpd/conf/httpd.conf.new /tmp/httpd_rootdir.conf > /etc/httpd/conf/httpd.conf && \
  rm -f /etc/httpd/conf/httpd.conf.new /tmp/httpd_rootdir.conf

# webserver SSL
RUN set -o pipefail && \
  sed -r "s|^( *< *VirtualHost +_default_ *: *443 *> *(#.*)?)$|\1\nServerName \${MBSIMENVSERVERNAME}\n|" /etc/httpd/conf.d/ssl.conf > \
  /etc/httpd/conf.d/ssl.conf.new && \
  mv -f /etc/httpd/conf.d/ssl.conf.new /etc/httpd/conf.d/ssl.conf
COPY conf/mpm_prefork.conf /etc/httpd/cond.d/
COPY conf/le-redirect-mbsim-env.conf /etc/httpd/conf.d/

# set crontab for
# - cert updates
RUN echo '35 20,8 * * * /usr/bin/certbot-2 renew --webroot -w /var/www/html --post-hook "httpd -k graceful"' | crontab /dev/stdin

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/webserver" \
  org.label-schema.description="Webserver for MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/webserverImage" \
  org.label-schema.vendor="MBSim-Environment"

# Check apache user and group id (must be in sync with the one in autobuildImage)
# Add user dockeruser, create volumes and set volume ownership and permissions
RUN test $(id -u apache) -eq 48 && test $(id -g apache) -eq 48 && \
  groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir -p /var/www/html/mbsim/linux64-ci /var/www/html/mbsim/linux64-dailydebug \
    /var/www/html/mbsim/linux64-dailyrelease /var/www/html/mbsim/buildsystemstate \
    /etc/letsencrypt /var/www/html/mbsim/releases /mbsim-config && \
  chown dockeruser:dockeruser /var/www/html/mbsim/linux64-ci /var/www/html/mbsim/linux64-dailydebug \
    /var/www/html/mbsim/linux64-dailyrelease /var/www/html/mbsim/buildsystemstate && \
  chown apache:apache /var/www/html/mbsim/releases && \
  chown dockeruser:apache /mbsim-config && chmod ug+rw /mbsim-config
  # chown root:root /etc/letsencrypt # not needed

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]

# get noVNC
FROM centos:centos7 AS temp
ARG NOVNCBRANCH=v0.6.2
RUN yum --setopt=skip_missing_names_on_install=False -y install \
  git \
  librsvg2-tools \
  python3-pip \
  && yum clean all
RUN pip3 install django-octicons==1.0
# install noVNC (the package from yum is to old)
WORKDIR /tmp
RUN git clone https://github.com/novnc/noVNC.git
WORKDIR /tmp/noVNC
RUN git checkout $NOVNCBRANCH
# build png icons
COPY docker/webserverImage/generatepng.py /tmp/generatepng.py
RUN python3 /tmp/generatepng.py



# use the build image as base
FROM centos:centos7

# install software
RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release centos-release-scl && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  httpd24-httpd \
  httpd24-mod_ssl \
  python2-certbot \
  rh-python36-mod_wsgi \
  cronie \
  python36-docker \
  python36-pygithub \
  python36-pytz \
  python36-defusedxml \
  python3-psycopg2 \
  python3-humanize \
  sudo \
  && yum clean all
RUN python3 -m pip install --upgrade pip && pip3 install django==3.2 django-allauth==0.48 django-octicons==1.0 h5py==2.9.0 paramiko==2.9

# a webserver is running on port 80
EXPOSE 80/tcp 443/tcp

COPY --from=temp /tmp/noVNC/include /var/www/html/noVNC/include

# copy django
COPY django/mbsimenv /context/mbsimenv

# copy entrypoint
COPY docker/webserverImage/entrypoint.py /context/entrypoint.py
COPY docker/webserverImage/cron-daily.py /context/cron-daily.py
COPY docker/webserverImage/cron-ci.py /context/cron-ci.py
COPY docker/setup.py /context/setup.py

# configure web server
# add top level config (stored in docker/webserverImage/httpd_toplevel.conf)
COPY docker/webserverImage/conf/httpd_toplevel.conf /tmp/httpd_toplevel.conf
RUN cat /tmp/httpd_toplevel.conf /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf > /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf.new && \
  mv /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf.new /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf && \
  rm -f /tmp/httpd_toplevel.conf
# replace <Directory "/var/www/html"> with docker/webserverImage/httpd_rootdir.conf
COPY docker/webserverImage/conf/httpd_rootdir.conf /tmp/httpd_rootdir.conf
RUN set -o pipefail && \
  B=$(sed -rn '/^ *< *Directory +"\/opt\/rh\/httpd24\/root\/var\/www\/html" *> *(#.*)?$/=' /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf | head -n 1); \
  O=$(sed -rn "$[$B+1],\$p" /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf | sed -rn '/^ *< *\/ *Directory *> *(#.*)?/=' | head -n 1); \
  sed -rn "1,$[$B-1]p;$[$B+$O+1],\$p" /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf > /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf.new && \
  cat /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf.new /tmp/httpd_rootdir.conf > /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf && \
  rm -f /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf.new /tmp/httpd_rootdir.conf
RUN mkdir -p /opt/rh/httpd24/root/var/log/httpd
# configure LogFormat
RUN sed -i -re "s+^( *LogFormat.*)%h(.*)$+\1<IP>\2+;s+^( *LogFormat.*)%\{Referer\}i(.*)$+\1<REFERER>\2+;s+^( *LogFormat.*)%\{User-Agent\}i(.*)$+\1<USERAGENT>\2+" /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf

# configure MPM
RUN sed -i -re "s/^.*LoadModule +mpm_prefork_module.*$/#/" /opt/rh/httpd24/root/etc/httpd/conf.modules.d/00-mpm.conf && \
    sed -i -re "s/^.*LoadModule +mpm_event_module/LoadModule mpm_event_module/" /opt/rh/httpd24/root/etc/httpd/conf.modules.d/00-mpm.conf

# webserver SSL
RUN sed -i -r "s|^( *< *VirtualHost +_default_ *: *443 *> *(#.*)?)$|\1\nServerName \${MBSIMENVSERVERNAME}\nCustomLog logs/ssl_error_log common\nCustomLog logs/ssl_access_log common\n|" /opt/rh/httpd24/root/etc/httpd/conf.d/ssl.conf
RUN sed -i -r "/^ *CustomLog +logs\/ssl_request_log *\\\ *$/N;s|^ *CustomLog +logs\/ssl_request_log.*|CustomLog logs/ssl_request_log common|" /opt/rh/httpd24/root/etc/httpd/conf.d/ssl.conf
COPY docker/webserverImage/conf/mpm_event.conf /opt/rh/httpd24/root/etc/httpd/conf.d/
COPY docker/webserverImage/conf/le-redirect-mbsim-env.conf /opt/rh/httpd24/root/etc/httpd/conf.d/

# static django files
RUN mkdir /var/www/html/static
RUN DJANGO_SETTINGS_MODULE=mbsimenv.settings_buildsystem python3 /context/mbsimenv/manage.py collectstatic --noinput
COPY --from=temp /tmp/generatepng/*.png /var/www/html/static/octiconpng/

# set crontab for
# - cert updates (once a day at arbitary time)
# - django clear expired sessions (once a day)
RUN mkdir /var/www/html/certbot
RUN echo -e 'SHELL=/bin/bash\n\
1 0 * * * python3 -c "import time; import random; time.sleep(random.randint(0,24*60*60-100))"; \
sudo -u dockeruser /usr/bin/certbot-2 renew --work-dir /tmp/certbotwork --logs-dir /tmp/certbotlog --webroot -w /var/www/html/certbot --post-hook "httpd -k graceful" \
2> >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/2) > >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/1)\n\
39 7 * * * DJANGO_SETTINGS_MODULE=mbsimenv.settings_buildsystem python3 /context/mbsimenv/manage.py clearsessions' \
| crontab /dev/stdin

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/webserver" \
  org.label-schema.description="Webserver for MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/webserverImage" \
  org.label-schema.vendor="MBSim-Environment"

# user/group handling
# - check apache user/group id
# - create dockeruser
# - create volume mount dirs
# - set permissions of volume mount dirs
RUN test $(id -u apache) -eq 48 && test $(id -g apache) -eq 48 && \
  useradd --no-log-init -u 1065 dockeruser && \
  mkdir /etc/letsencrypt /var/www/html/certbot/.well-known /webserverstatic && \
  chown dockeruser:dockeruser /etc/letsencrypt /var/www/html/certbot/.well-known

HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
  CMD curl -f https://${MBSIMENVSERVERNAME} || exit 1

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]

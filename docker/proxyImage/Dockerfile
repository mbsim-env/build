FROM centos:centos7

# install tinyproxy
RUN yum -y install epel-release && \
  yum -y install \
  python34 \
  tinyproxy \
  && yum clean all

# allow connection from everywhere
RUN sed -i -re "s/^( *Allow .*)/#\1/" /etc/tinyproxy/tinyproxy.conf

# configure tinyproxy
RUN echo -e '\
Filter "/etc/tinyproxy/filter"\n\
FilterCaseSensitive Yes\n\
FilterDefaultDeny Yes\n\
FilterURLs No\n\
FilterExtended Yes\n\
' >> /etc/tinyproxy/tinyproxy.conf

COPY entrypoint.py /context/entrypoint.py

HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
  CMD curl -I --proxy proxy:8888 https://www.mbsim-env.de || exit 1

# start tinyproxy
ENTRYPOINT ["/context/entrypoint.py"]
CMD [""]

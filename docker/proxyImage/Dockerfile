FROM centos:centos7

# install tinyproxy
RUN yum -y install epel-release && \
  yum -y install \
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

# start tinyproxy
ENTRYPOINT ["/context/entrypoint.py"]
CMD [""]

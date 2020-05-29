FROM centos:centos7

# install software
RUN yum --setopt=skip_missing_names_on_install=False install -y epel-release && \
  yum --setopt=skip_missing_names_on_install=False install -y \
  texlive-latex-bin-bin \
  texlive-bibtex-bin \
  texlive-collection-fontsrecommended \
  texlive-subfigure \
  texlive-pdftex-def \
  texlive-epstopdf-bin \
  ghostscript \
  python36 \
  && yum clean all

# copy context files
COPY docker/builddocImage/entrypoint.py /context/entrypoint.py

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/builddoc" \
  org.label-schema.description="Build latex documentation for MBSim-Env." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/builddocImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /mbsim-env /mbsim-report /mbsim-state && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-report /mbsim-state

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]

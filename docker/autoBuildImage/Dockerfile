# use the build image as base
FROM mbsimenv/build

# install software
RUN yum install -y \
  python-requests \
  texlive-latex-bin-bin \
  texlive-bibtex-bin \
  texlive-collection-fontsrecommended \
  texlive-subfigure \
  texlive-pdftex-def \
  && yum clean all

# ccache
ENV CCACHE_DIR=/mbsim-ccache

# copy build repo
COPY docker/autoBuildImage/entrypoint.py /mbsim-build/build/docker/autoBuildImage/entrypoint.py
COPY buildScripts /mbsim-build/build/buildScripts
COPY buildSystem/scripts /mbsim-build/build/buildSystem/scripts

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/mbsim-build/build/docker/autoBuildImage/entrypoint.py"]

#mfmf set user to avoid to build as root
#mfmf secure this container since untrusted code is executed.

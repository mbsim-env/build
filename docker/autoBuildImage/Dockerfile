# use the build image as base
FROM mbsimenv/mbsim-env-build

# install software
RUN yum install -y \
  python-requests \
  texlive-latex-bin-bin \
  texlive-bibtex-bin \
  texlive-collection-fontsrecommended \
  texlive-subfigure \
  texlive-pdftex-def \
  && yum clean all

# configuration
ARG BUILDBRANCH=master

# checkout the build repo
#mfmf do not use this code but the below for testing
#RUN mkdir /mbsim-build
#WORKDIR /mbsim-build
#RUN git clone https://github.com/mbsim-env/build.git
#WORKDIR /mbsim-build/build
#RUN git checkout $BUILDBRANCH
COPY docker /mbsim-build/build/docker
COPY buildScripts /mbsim-build/build/buildScripts
COPY buildSystem /mbsim-build/build/buildSystem

# ccache
ENV CCACHE_DIR=/mbsim-ccache

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/mbsim-build/build/docker/autoBuildImage/entrypoint.py"]

#mfmf set user to avoid to build as root
#mfmf secure this container since untrusted code is executed.

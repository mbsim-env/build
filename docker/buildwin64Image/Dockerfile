FROM centos:centos7 AS centosBaseImage

RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  git \
  ccache \
  patch \
  make \
  mingw64-gcc \
  mingw64-gcc-c++ \
  mingw64-gcc-gfortran \
  wine \
  python36-requests \
  libtool automake autoconf \
  python3-pip \
  python36-numpy \
  mingw64-boost \
  doxygen \
  tigervnc-server \
  xalan-c \
  which \
  dos2unix \
  file \
  java-1.8.0-openjdk-devel \
  graphviz \
  swig3 \
  && yum clean all
RUN pip3 install h5py

# install install mingw64-qt5-qtsvg to add its dependencies and then
# remove mingw64-qt5-qtbase mingw64-qt5-qmake which is rebuild/reinstalled later
RUN rpm -i --nodeps http://download-ib01.fedoraproject.org/pub/fedora/linux/releases/29/Everything/x86_64/os/Packages/m/mingw64-postgresql-10.3-2.fc29.noarch.rpm \
  && yum --setopt=skip_missing_names_on_install=False -y install mingw64-qt5-qtsvg \
  && rpm -e --nodeps mingw64-qt5-qtbase mingw64-qt5-qmake \
  && yum clean all
# fix mingw
COPY docker/buildwin64Image/mingw64.patch /context/mingw64.patch
RUN patch -d / -p0 < /context/mingw64.patch


##################################################################################


FROM centosBaseImage AS thirdpartyBuildImage

ARG JOBS=4

RUN yum --setopt=skip_missing_names_on_install=False -y install \
  wget \
  cmake3 \
  gcc-c++ \
  pcre-devel \
  unzip \
  mercurial \
  flex \
  bison \
  rpm-build

RUN mkdir /3rdparty

# rebuild mingw64-qt5-qtbase mingw64-qt5-qmake which is buggy in EPEL repo

# EPEL mingw64-qt5-qtbase is build with GLES (ANGLE) which does not work with coin. Hence this package must be rebuild
# using the SRPM. In the spec file mingw-qt5-qtbase.spec "-opengl desktop" is set to disable ANGLE.

WORKDIR /3rdparty
RUN yumdownloader --source mingw-qt5-qtbase
RUN rpm -ivh ./mingw-qt5-qtbase*.src.rpm
WORKDIR /root/rpmbuild/SPECS
RUN rpm -i --nodeps http://download-ib01.fedoraproject.org/pub/fedora/linux/releases/29/Everything/x86_64/os/Packages/m/mingw32-postgresql-10.3-2.fc29.noarch.rpm
RUN yum-builddep -y mingw-qt5-qtbase
COPY docker/buildwin64Image/qt5base.patch /context/qt5base.patch
RUN patch -d /root/rpmbuild -p0 < /context/qt5base.patch
RUN rpmbuild -ba mingw-qt5-qtbase.spec
RUN rpm -i /root/rpmbuild/RPMS/noarch/mingw64-qt5-qtbase-5.6.0-3.el7.noarch.rpm /root/rpmbuild/RPMS/x86_64/mingw64-qt5-qmake-5.6.0-3.el7.x86_64.rpm

# 3rd party

COPY docker/buildwin64Image/toolchain-mingw64.cmake /context/toolchain-mingw64.cmake

# lapack
ARG LAPACKVERSION=3.4.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - http://www.netlib.org/lapack/lapack-$LAPACKVERSION.tgz | tar -xz
RUN mkdir /3rdparty/lapack-build
WORKDIR /3rdparty/lapack-build
RUN cmake3 ../lapack-$LAPACKVERSION -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local
RUN make -j $JOBS
RUN make install

# hdf5
ARG HDF5VERSION=1_8_12
WORKDIR /3rdparty
RUN git clone --depth 1 -b hdf5-$HDF5VERSION https://bitbucket.hdfgroup.org/scm/hdffv/hdf5.git
WORKDIR /3rdparty/hdf5
RUN git checkout -b test
COPY docker/buildwin64Image/hdf5.patch /context/hdf5.patch
RUN git apply /context/hdf5.patch
RUN mkdir /3rdparty/hdf5-build
WORKDIR /3rdparty/hdf5-build
RUN cmake3 ../hdf5 -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DMSVC=TRUE -DHDF5_BUILD_CPP_LIB=ON -DBUILD_SHARED_LIBS=1
RUN make -j $JOBS
RUN make install
RUN ln -s /3rdparty/local/lib/hdf5.lib /3rdparty/local/lib/libhdf5.lib && \
    ln -s /3rdparty/local/lib/hdf5_cpp.lib /3rdparty/local/lib/libhdf5_cpp.lib

# qwt
ARG QWTVERSION=6.1.3
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://sourceforge.net/projects/qwt/files/qwt/$QWTVERSION/qwt-$QWTVERSION.tar.bz2 | tar -xj
RUN mkdir /3rdparty/qwt-build
WORKDIR /3rdparty/qwt-build
RUN sed -ire "s|^ *QWT_INSTALL_PREFIX *=.*$|QWT_INSTALL_PREFIX = /3rdparty/local|" /3rdparty/qwt-$QWTVERSION/qwtconfig.pri && \
  sed -ire "s|^ *QWT_CONFIG *+= *QwtDesigner *$|#|" /3rdparty/qwt-$QWTVERSION/qwtconfig.pri && \
  sed -ire "s|^ *CONFIG *+= *debug_and_release *$|CONFIG += release|" /3rdparty/qwt-$QWTVERSION/qwtbuild.pri
RUN sed -ire "s|^ *CONFIG *+= *debug_and_release *$|CONFIG += release|" /3rdparty/qwt-$QWTVERSION/qwtbuild.pri
RUN mingw64-qmake-qt5 ../qwt-$QWTVERSION
# the first make fails but the second not???
RUN make -j $JOBS || make -j $JOBS || make -j 1
RUN make install

# wine
RUN yum remove -y wine wine-courier-fonts wine-marlett-fonts wine-core wine-twain wine-capi wine-filesystem wine-small-fonts wine-system-fonts wine-common wine-alsa wine-cms wine-ms-sans-serif-fonts wine-symbol-fonts wine-fonts wine-desktop wine-pulseaudio wine-wingdings-fonts wine-fixedsys-fonts wine-systemd wine-ldap wine-openal wine-tahoma-fonts
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://dl.winehq.org/wine/source/3.0/wine-3.0.5.tar.xz | tar -xJ
RUN mkdir /3rdparty/wine-build
WORKDIR /3rdparty/wine-build
RUN yum install -y libX11-devel
RUN yum install -y freetype-devel
# zlib-devel libxcb-devel libxslt-devel libgcrypt-devel libxml2-devel gnutls-devel libpng-devel libjpeg-turbo-devel libtiff-devel gstreamer-devel dbus-devel fontconfig-devel
RUN ../wine-3.0.5/configure --enable-win64 --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install
RUN ln -s /3rdparty/local/bin/wine64 /3rdparty/local/bin/wine
ENV PATH=$PATH:/3rdparty/local/bin

# python
ARG PYTHONVERSION=3.4.4
WORKDIR /3rdparty
RUN wget https://www.python.org/ftp/python/$PYTHONVERSION/python-$PYTHONVERSION.amd64.msi
RUN wine msiexec -i python-$PYTHONVERSION.amd64.msi -q n TARGETDIR="$(winepath -w /3rdparty/local/python-win64)" && wineserver -w
# fix libfile name
RUN mv /3rdparty/local/python-win64/libs/python34.lib /3rdparty/local/python-win64/libs/libpython34.lib

# numpy
ARG NUMPYVERSION=1.15.0
WORKDIR /3rdparty
RUN wget https://files.pythonhosted.org/packages/11/9f/f7550ba7d6ea7d1da16ac2069157b42d225b02b47e4c30ccc1c5b6be3b8f/numpy-$NUMPYVERSION-cp34-none-win_amd64.whl
RUN mkdir /3rdparty/numpy-build
WORKDIR /3rdparty/numpy-build
RUN unzip ../numpy-$NUMPYVERSION-cp34-none-win_amd64.whl
RUN cp -a numpy /3rdparty/local/python-win64/Lib/site-packages/.

# mpmath/sympy
ARG MPMATHVERSION=1.1.0
ARG SYMPYVERSION=1.4
WORKDIR /3rdparty
RUN wget https://files.pythonhosted.org/packages/ca/63/3384ebb3b51af9610086b23ea976e6d27d6d97bf140a76a365bd77a3eb32/mpmath-$MPMATHVERSION.tar.gz \
  && wget https://github.com/sympy/sympy/releases/download/sympy-$SYMPYVERSION/sympy-$SYMPYVERSION.tar.gz
RUN mkdir /3rdparty/mpmath-build /3rdparty/mpmath-local /3rdparty/sympy-build /3rdparty/sympy-local
WORKDIR /3rdparty/mpmath-build
RUN tar -xzf ../mpmath-$MPMATHVERSION.tar.gz
WORKDIR /3rdparty/sympy-build
RUN tar -xzf ../sympy-$SYMPYVERSION.tar.gz
WORKDIR /3rdparty/mpmath-build/mpmath-$MPMATHVERSION
RUN wine /3rdparty/local/python-win64/python.exe setup.py build && \
    wine /3rdparty/local/python-win64/python.exe setup.py install && wineserver -w
WORKDIR /3rdparty/sympy-build/sympy-$SYMPYVERSION
RUN mkdir -p /3rdparty/sympy-inst/Lib/site-packages
RUN wine /3rdparty/local/python-win64/python.exe setup.py build && wineserver -w
RUN PYTHONPATH="$(winepath -w /3rdparty/sympy-inst/Lib/site-packages)" wine /3rdparty/local/python-win64/python.exe \
    setup.py install --prefix="$(winepath -w /3rdparty/sympy-inst)" && \
    wineserver -w
RUN unzip -d /3rdparty/local/python-win64/Lib/site-packages dist/sympy-$SYMPYVERSION-py3.4.egg

# octave
ARG OCTAVEVERSION=3.8.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://ftp.gnu.org/gnu/octave/octave-$OCTAVEVERSION.tar.bz2 | tar -xj
RUN mkdir /3rdparty/octave-build
WORKDIR /3rdparty/octave-build
COPY docker/buildwin64Image/octave.patch /context/octave.patch
RUN patch -d /3rdparty/octave-$OCTAVEVERSION -p0 < /context/octave.patch
RUN ../octave-$OCTAVEVERSION/configure --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local --disable-java --disable-gui --without-opengl --with-blas="-L/3rdparty/local/lib -lblas" --with-lapack="-L/3rdparty/local/lib -llapack" --disable-readline
RUN make -j $JOBS
RUN make install
# fix octave 3.8.2: it is not initializing when runnig without a DISPLAY
RUN sed -i -re "s/\<__have_fltk__ *\( *\) *&& *have_window_system *\( *\)/have_window_system () \&\& __have_fltk__ ()/" \
  /3rdparty/local/lib/octave/3.8.2/oct/x86_64-w64-mingw32/PKG_ADD

# xerces-c
ARG XERCESCVERSION=3.1.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://archive.apache.org/dist/xerces/c/3/sources/xerces-c-$XERCESCVERSION.tar.bz2 | tar -xj
RUN mkdir /3rdparty/xercesc-build
COPY docker/buildwin64Image/xercesc.patch /context/xercesc.patch
RUN patch -d /3rdparty/xerces-c-$XERCESCVERSION -p0 < /context/xercesc.patch
WORKDIR /3rdparty/xercesc-build
RUN ../xerces-c-$XERCESCVERSION/configure --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install

# coin
ARG COINBRANCH=3d7321d07d57
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/coin -r $COINBRANCH
COPY docker/buildwin64Image/coin.patch /context/coin.patch
WORKDIR /3rdparty/coin
RUN hg import --no-commit /context/coin.patch
RUN mkdir /3rdparty/coin-build
WORKDIR /3rdparty/coin-build
RUN cmake3 -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2 -fpermissive" -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake ../coin
RUN make -j $JOBS
RUN make install

# soqt
ARG SOQTBRANCH=945ec22f6219
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/soqt -r $SOQTBRANCH
RUN mkdir /3rdparty/soqt-build
WORKDIR /3rdparty/soqt-build
RUN cmake3 -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2 -fpermissive" -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DQt5_DIR=/usr/x86_64-w64-mingw32/sys-root/mingw/lib/cmake/Qt5 ../soqt
RUN make -j $JOBS
RUN make install

# libarchive
ARG LIBARCHIVEVERION=3.1.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://libarchive.org/downloads/libarchive-$LIBARCHIVEVERION.tar.gz | tar -xz
RUN mkdir /3rdparty/libarchive-build
WORKDIR /3rdparty/libarchive-build
RUN ../libarchive-$LIBARCHIVEVERION/configure  --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local --without-xml2 --without-expat --without-openssl --without-nettle --without-lzo2 --without-lzma --without-libiconv-prefix --without-iconv --without-lzmadec --without-bz2lib
RUN make -j $JOBS
RUN make install


##################################################################################


FROM centosBaseImage

COPY --from=thirdpartyBuildImage /3rdparty/local /3rdparty/local
COPY --from=thirdpartyBuildImage /root/rpmbuild/RPMS/noarch/mingw64-qt5-qtbase-5.6.0-3.el7.noarch.rpm /3rdparty/mingw64-qt5-qtbase-5.6.0-3.el7.noarch.rpm
COPY --from=thirdpartyBuildImage /root/rpmbuild/RPMS/x86_64/mingw64-qt5-qmake-5.6.0-3.el7.x86_64.rpm /3rdparty/mingw64-qt5-qmake-5.6.0-3.el7.x86_64.rpm

RUN rpm -i /3rdparty/mingw64-qt5-qtbase-5.6.0-3.el7.noarch.rpm \
  /3rdparty/mingw64-qt5-qmake-5.6.0-3.el7.x86_64.rpm

# fix swig
COPY docker/buildwin64Image/swig.patch /context/swig.patch
RUN patch -d /usr/share/swig/3.0.12 -p0 < /context/swig.patch

# ccache
# enable swig interface to mbsim
# compile flags
ENV CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    PATH=/usr/lib64/ccache:$PATH \
    WINEPATH="/usr/x86_64-w64-mingw32/sys-root/mingw/bin;/3rdparty/local/bin;/3rdparty/local/lib;/3rdparty/local/python-win64;/3rdparty/local/python-win64/Lib/site-packages/numpy/core;/usr/lib64/wine/fakedlls" \
    MOC=/usr/x86_64-w64-mingw32/bin/qt5/moc \
    UIC=/usr/x86_64-w64-mingw32/bin/qt5/uic \
    RCC=/usr/x86_64-w64-mingw32/bin/qt5/rcc \
    CXXFLAGS="-g -O2 -gdwarf-2 -DNDEBUG" \
    CFLAGS="-g -O2 -gdwarf-2 -DNDEBUG" \
    FFLAGS="-g -O2 -gdwarf-2 -DNDEBUG" \
    PKG_CONFIG_PATH=/3rdparty/local/lib/pkgconfig \
    PLATFORM=Windows \
    CXX=x86_64-w64-mingw32-g++

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/buildwin64" \
  org.label-schema.description="Automatic build (win64) for the MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/buildwin64Image" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state

# configure wine
COPY docker/buildwin64Image/wine.inf /context/wine.inf
RUN P=$(winepath -w /3rdparty/local/python-win64 | sed -re 's+\\+\\\\+g'); \
    sed -re "s+%_PYTHONHOME_%+$P+" /context/wine.inf >> /usr/share/wine/wine.inf

# copy
COPY buildScripts /mbsim-build/build/buildScripts
COPY docker/buildImage/buildSystemState.py /context/buildSystemState.py
COPY docker/buildImage/distribute.py /context/distribute.py
COPY docker/buildwin64Image/entrypoint.py /context/entrypoint.py
COPY docker/buildwin64Image/jni_md.h /context/java_jni/jni_md.h

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# init conf
RUN wine cmd echo && wineserver -w

# config ccache
RUN ccache -M 10G

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]

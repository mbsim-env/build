# Dashboard

Current Daily Build Status of the MBSim-Environment

| Build Type | Variant | Failed |
|------------|---------|--------|
| linux64-dailydebug | build | [![image](https://www.mbsim-env.de/service/builds/current/linux64-dailydebug/nrFailed.svg) / ![image](https://www.mbsim-env.de/service/builds/current/linux64-dailydebug/nrAll.svg)](https://www.mbsim-env.de/builds/run/current/linux64-dailydebug/) |
| linux64-dailydebug | examples | [![image](https://www.mbsim-env.de/service/runexamples/current/linux64-dailydebug/nrFailed.svg) / ![image](https://www.mbsim-env.de/service/runexamples/current/linux64-dailydebug/nrAll.svg)](https://www.mbsim-env.de/runexamples/run/current/linux64-dailydebug/) |
| linux64-dailydebug | coverage | [![image](https://www.mbsim-env.de/service/runexamples/current/linux64-dailydebug/coverageRate.svg)](https://www.mbsim-env.de/runexamples/run/current/linux64-dailydebug/#coverage) |
| linux64-dailydebug | examples-valgrind | [![image](https://www.mbsim-env.de/service/runexamples/current/linux64-dailydebug-valgrind/nrFailed.svg) / ![image](https://www.mbsim-env.de/service/runexamples/current/linux64-dailydebug-valgrind/nrAll.svg)](https://www.mbsim-env.de/runexamples/run/current/linux64-dailydebug-valgrind/) |
| linux64-dailydebug | coverage-valgrind | [![image](https://www.mbsim-env.de/service/runexamples/current/linux64-dailydebug-valgrind/coverageRate.svg)](https://www.mbsim-env.de/runexamples/run/current/linux64-dailydebug-valgrind/#coverage) |
| linux64-dailyrelease | build | [![image](https://www.mbsim-env.de/service/builds/current/linux64-dailyrelease/nrFailed.svg) / ![image](https://www.mbsim-env.de/service/builds/current/linux64-dailyrelease/nrAll.svg)](https://www.mbsim-env.de/builds/run/current/linux64-dailyrelease/) |
| linux64-dailyrelease | examples | [![image](https://www.mbsim-env.de/service/runexamples/current/linux64-dailyrelease/nrFailed.svg) / ![image](https://www.mbsim-env.de/service/runexamples/current/linux64-dailyrelease/nrAll.svg)](https://www.mbsim-env.de/runexamples/run/current/linux64-dailyrelease/) |
| win64-dailyrelease | build | [![image](https://www.mbsim-env.de/service/builds/current/win64-dailyrelease/nrFailed.svg) / ![image](https://www.mbsim-env.de/service/builds/current/win64-dailyrelease/nrAll.svg)](https://www.mbsim-env.de/builds/run/current/win64-dailyrelease/) |
| win64-dailyrelease | examples | [![image](https://www.mbsim-env.de/service/runexamples/current/win64-dailyrelease/nrFailed.svg) / ![image](https://www.mbsim-env.de/service/runexamples/current/win64-dailyrelease/nrAll.svg)](https://www.mbsim-env.de/runexamples/run/current/win64-dailyrelease/) |
| - | manuals | [![image](https://www.mbsim-env.de/service/manuals/nrFailed.svg) / ![image](https://www.mbsim-env.de/service/manuals/nrAll.svg)](https://www.mbsim-env.de/service/home/#manuals) |



# Repository Content

This repository holds data (mainly scripts) to build and run the tools of the MBSim-Environement.
It contains


## docker

A set of [Docker](https://www.docker.com/) files which are used to build Docker images of the
MBSim-Environement. These can be used to run or build the MBSim-Environement easily.
Dependent of your use case you should use one of the following options.

### Building and Running the Linux MBSim-Env Tools as a Developer

Building MBSim-Env from scratch is QUITE complicated since it has many dependencies to other tools. And not all of these
tools are available via the package manager of your preferred Linux distribution. Different versions of these
dependent tools can also cause a lot of trouble.
That's why we provide Docker images to build and run MBSim-Env easily in the typical edit-compile-run cycle.

To prepare this, the following steps needs to be done once:

1. **Install Docker**. Please look at [Docker](https://www.docker.com/) or your Linux distribution how to do this.
Allow Docker for the user of your choice, e.g. by giving this user access to the Docker socket.
2. **Clone this Git repository to your preferred directory (`<mypath>`)** which should have enough 
space to hold the MBSim-Env source code the build directories as well as all your MBSim-Env models and data.
3. Configure your shell to **add `<mypath>/build/docker/buildScripts` to your `PATH`**.
This is not really required but recommended to allow starting programs without typing the full path all the time.
4. **Call `build.sh`** in the above configured shell. This will clone all MBSim-Env repositories, if not already done manually,
to `<mypath>/fmatvec`, `<mypath>/hdf5serie`, ... Then it will download a large Docker image of MBSim-Env.
After that it will completely build MBSim-Env. So, take a coffee, this takes some time.
The current progress of building MBSim-Env can be checked via your browser.
The corresponding URL will be printed at the beginning.
Note that running `build.sh` without any parameters will build everything and also run ALL examples.
See `build.sh -h` for available options to change this default behavior.

You are done. Now start the GUI of MBSim by running `mbsimgui` in the above configured shell.
All other MBSim-Env commands like `mbsimxml`, `openmbv` or `h5plotserie` are also available.

Make adaptions to the source code and rerun `build.sh` (with proper options to speed up the build) or run `make` in the corresponding
build directory (`fmatvec-docker`, `hdf5serie-docker`, ...) to rebuild your changed code parts.

Run `runexamples.sh` in the directory `mbsim/examples` to run examples.
See `runexamples.sh -h` for available options.

Run `mbsimenv-bash.sh` to start an interactive bash inside of the Docker container.
See `mbsimenv-bash.sh -h` for available options.

Note that you do not need to have any development tools installed on your host computer (no make, not gcc, ... is required) since
everything comes along with the Docker image automatically and consistently.

### Building and Running the Windows MBSim-Env Tools as a Developer

You can also build (cross-compile) all MBSim-Env tools for Windows using a Docker image. You can than run the generated Windows
executables using Wine on Linux or run these natively on a Windows PC.

To build and run MBSim-Env for Windows just follow the instructions from the previous section but replace in 3. 
`<mypath>/build/docker/buildScripts` with `<mypath>/build/docker/buildwin64Scripts`.
The build directories are named `fmatvec-dockerwin64`, `hdf5serie-dockerwin64`, ...

It is recommended NOT to use the same base directory `<mypath>` for the Linux and Windows Docker build.
This works in principle but causes problems due to different versions of the autotools build tools.



## codeStyle

Contains the coding style conventions used in the MBSim-Environement.


## misc

Contains some miscellaneous files and scripts (e.g. valgrind suppressions)


## django

Django 3 project of the mbsim server

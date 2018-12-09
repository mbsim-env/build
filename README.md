# Dashboard

Current Daily Build Status of the MBSim-Environment

| Build Type | Variant | Failed |
|------------|---------|--------|
| linux64-dailydebug | build | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailydebug-build.nrFailed.svg) / ![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailydebug-build.nrAll.svg)](https://www.mbsim-env.de/mbsim/linux64-dailydebug/report/result_current/) |
| linux64-dailydebug | examples | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailydebug-examples.nrFailed.svg) / ![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailydebug-examples.nrAll.svg)](https://www.mbsim-env.de/mbsim/linux64-dailydebug/report/result_current/runexamples_report/result_current/) |
| linux64-dailydebug | coverage | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailydebug-coverage.svg)](https://www.mbsim-env.de/mbsim/linux64-dailydebug/report/result_current/runexamples_report/result_current/coverage/) |
| linux64-dailydebug | examples-valgrind | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailydebug-valgrind-examples.nrFailed.svg) / ![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailydebug-valgrind-examples.nrAll.svg)](https://www.mbsim-env.de/mbsim/linux64-dailydebug/report/runexamples_valgrind_report/result_current/) |
| linux64-dailydebug | coverage-valgrind | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailydebug-valgrind-coverage.svg)](https://www.mbsim-env.de/mbsim/linux64-dailydebug/report/runexamples_valgrind_report/result_current/coverage/) |
| linux64-dailyrelease | build | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailyrelease-build.nrFailed.svg) / ![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailyrelease-build.nrAll.svg)](https://www.mbsim-env.de/mbsim/linux64-dailyrelease/report/result_current/) |
| linux64-dailyrelease | examples | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailyrelease-examples.nrFailed.svg) / ![image](https://www.mbsim-env.de/mbsim/buildsystemstate/linux64-dailyrelease-examples.nrAll.svg)](https://www.mbsim-env.de/mbsim/linux64-dailyrelease/report/result_current/runexamples_report/result_current/) |
| win64-dailyrelease | build | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/win64-dailyrelease-build.nrFailed.svg) / ![image](https://www.mbsim-env.de/mbsim/buildsystemstate/win64-dailyrelease-build.nrAll.svg)](https://www.mbsim-env.de/mbsim/win64-dailyrelease/report/result_current/) |
| win64-dailyrelease | examples | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/win64-dailyrelease-examples.nrFailed.svg) / ![image](https://www.mbsim-env.de/mbsim/buildsystemstate/win64-dailyrelease-examples.nrAll.svg)](https://www.mbsim-env.de/mbsim/win64-dailyrelease/report/result_current/runexamples_report/result_current/) |
| - | manuals | [![image](https://www.mbsim-env.de/mbsim/buildsystemstate/build-manuals.nrFailed.svg) / ![image](https://www.mbsim-env.de/mbsim/buildsystemstate/build-manuals.nrAll.svg)](https://www.mbsim-env.de/mbsim/doc_manualsbuild.log) |



# Repository Content

This repository holds data (mainly scripts) to build and run the tools of the MBSim-Environement.
It contains


## buildScripts

A set of scripts used to simplify the build of the MBSim-Environement.


## docker

A set of [Docker](https://www.docker.com/) files which are used to build Docker images of the
MBSim-Environement. These can be used to run or build the MBSim-Environement easily.
Dependent of your use case you should use one of the following options.

### Running MBSim-Env Tools as a User

The Docker image for running the MBSim-Env is till now not available.

### Building and Running the Linux MBSim-Env Tools as a Developer

Building MBSim-Env from scratch is quite complicated since it has many dependencies to other tools. And not all these
tools are available via your preferred Linux package manager or minor differences on these lead to problems dependent
on your preferred Linux distribution.
That's why we provide Docker images to build and run MBSim-Env easily in the typical edit-compile-run cycle.

To prepare this the following needs to be done once.

1. Install Docker. Please look on [Docker](https://www.docker.com/) or your Linux distribution how to do this.
Allow Docker for the user of your choice, e.g. by giving this user access to the Docker socket.
2. Clone this Git repository to your preferred directory (`<mypath>`) which should have enough 
space to hold the MBSim-Env source code the build directories as well as all your MBSim-Env models and data.
3. Configure your shell to add `<mypath>/build/docker/buildScripts` to your `PATH`.
This is not really required but recommended.
4. Call `build.sh` in the above configured shell. This will clone all MBSim-Env repositories, if not already done manually,
to `<mypath>/fmatvec`, `<mypath>/hdf5serie`, ... Then it will download a large Docker image of MBSim-Env. After that it will completely build MBSim-Env, so this all may take some time.
For the current progress of building MBSim-Env see the output of the script or view `file://<mypath>/build_report/result_current/index.html`
via your browser.
Note that running `build.sh` without any parameters will build everything and also run ALL examples. See `build.sh -h` for available
options to change this default behaviour.

You are done. Now start the GUI of MBSim by running `mbsimgui` in the above configured shell.
All other MBSim-Env commands like `mbsimxml`, `openmbv` or `h5plotserie` are also available.

Make adaptions to the source code and rerun `build.sh` (with proper options to speed up the build) or run `make` in the corresponding
build directory (`fmatvec-build`, `hdf5serie-build`, ...) to rebuild your changed code parts.

Note that you do not need to have any development tools installed on your host computer (no make, not gcc, ... is required) since
everything comes along with the Docker image automatically and consistently.

### Building and Running the Windows MBSim-Env Tools as a Developer

You can also build (cross-compile) all MBSim-Env tools for Windows using a Docker image. You can than run the generated Windows
executables using Wine on Linux or run these natively on a Windows PC.

To build and run MBSim-Env for Windows just follow the instructions from the previous section but replace in 3. 
`<mypath>/build/docker/buildScripts` with `<mypath>/build/docker/buildwin64Scripts`.
The build output report will be available at `file://<mypath>/buildwin64_report/result_current/index.html` and the build directories
are `fmatvec-build`, `hdf5serie-build`, ...
Note that you can use the same base directory (`<mypath>`) for the Linux and Windows build. This will use the same git clones of the source for both platforms.



## codeStyle

Contains the coding style conventions used in the MBSim-Environement.


## misc

Contains some miscellaneous files not useful for most people.

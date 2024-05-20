@echo off
echo mfmfa
cd
echo mfmfb
dir c:\msys64\usr\bin\bash.exe
echo mfmfc
echo "%*"
echo mfmfd
c:\msys64\usr\bin\bash.exe -l -c "ls -l /ucrt64/bin/python3*"
echo mfmfe
c:\msys64\usr\bin\bash.exe -l -c "ls -l /context/entrypoint.py"
echo mfmff
c:\msys64\usr\bin\bash.exe -l -c "%*"
echo mfmfg

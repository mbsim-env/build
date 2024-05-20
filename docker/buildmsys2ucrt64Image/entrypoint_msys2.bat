@echo off
echo mfmfa
dir c:\msys64\usr\bin\bash.exe
echo "%*"
c:\msys64\usr\bin\bash.exe -l -c "ls -l /ucrt64/bin/python3*"
c:\msys64\usr\bin\bash.exe -l -c "ls -l /context/entrypoint.py"
echo mfmfa
c:\msys64\usr\bin\bash.exe -l -c "%*"
echo mfmfb

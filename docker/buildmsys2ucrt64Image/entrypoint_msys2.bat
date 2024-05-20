REM @echo off
echo mfmfa
cd
echo mfmfb
dir c:\msys64\usr\bin\bash.exe
echo mfmfc1
echo "%0"
echo mfmfc2
echo "%1"
echo mfmfc3
echo "%2"
echo mfmfc4
echo "%*"
echo mfmfd
c:\msys64\usr\bin\bash.exe -l -c "ls -l /ucrt64/bin/python3*"
echo mfmfe
c:\msys64\usr\bin\bash.exe -l -c "ls -l /context/entrypoint.py"
echo mfmff
c:\msys64\usr\bin\bash.exe -l -c "%*"
echo mfmfg
c:\msys64\usr\bin\bash.exe -l -c "/ucrt64/bin/python3 /context/entrypoint.py"
echo mfmfh

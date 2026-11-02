@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
cl /nologo /utf-8 /W4 /I tmp\acceptance-031\source\iso532-ffi\include "%~dp0c-client.c" /Fo:tmp\acceptance-031\contract-target\release\c-client.obj /Fe:tmp\acceptance-031\contract-target\release\c-client.exe tmp\acceptance-031\contract-target\release\iso532_ffi.dll.lib
if errorlevel 1 exit /b 1
tmp\acceptance-031\contract-target\release\c-client.exe > "%~dp0c-results.jsonl"

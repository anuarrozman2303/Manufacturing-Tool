@echo off
setlocal enabledelayedexpansion

set basedir=%CD%
set "folder_to_monitor=C:\change\to\folder"
set "printer_name=postek_g600"

echo %basedir%

:Start
rem Prompt for the filename
set /p filename="Enter the filename to print (with extension): "

rem Check if the file exists
if not exist "%filename%" (
    echo File not found: %filename%
    pause
    exit /b
)

echo %basedir%
echo Printing %filename%
"%basedir%\IrfanViewPortable\IrfanViewPortable.exe" "%CD%\%filename%" /print="%printer_name%"
echo Done!

rem Prompt to print another file
set /p choice="Do you want to print another file? (Y/N): "
if /i "%choice%"=="Y" goto Start
if /i "%choice%"=="y" goto Start

echo Exiting...
pause
exit /b
	

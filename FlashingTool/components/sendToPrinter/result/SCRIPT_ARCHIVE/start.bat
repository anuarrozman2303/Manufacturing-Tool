@echo off
setlocal enabledelayedexpansion

set basedir=%CD%
set "folder_to_monitor=z:\"
set "printer_name=Postek G6000"

echo %basedir%

"%basedir%\IrfanViewPortable\IrfanViewPortable.exe" "%CD%\test-print.png" /print
REM "%basedir%\IrfanViewPortable\IrfanViewPortable.exe" "%CD%\test-print.png" /print="%printer_name%"
REM "%basedir%\IrfanViewPortable\IrfanViewPortable.exe" "%CD%\test-print.png" /print="%printer_name%" /ini="%basedir%\IrfanViewPortable\preset"
REM start "" "mspaint.exe" /pt "%CD\test-print.png"

REM :Start
REM rem Prompt for the filename
REM set /p filename="Enter the filename to print (with extension): "
REM 
REM rem Check if the file exists
REM if not exist "%filename%" (
REM     echo File not found: %filename%
REM     pause
REM     exit /b
REM )
REM 
REM echo %basedir%
REM echo Printing %filename%
REM "%basedir%\IrfanViewPortable\IrfanViewPortable.exe" "%CD%\%filename%" /print="%printer_name%"
REM echo Done!
REM 
REM rem Prompt to print another file
REM set /p choice="Do you want to print another file? (Y/N): "
REM if /i "%choice%"=="Y" goto Start
REM if /i "%choice%"=="y" goto Start

echo Exiting...
pause
exit /b
	

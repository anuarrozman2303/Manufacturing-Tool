@echo off
setlocal enabledelayedexpansion

:Start
rem List all PNG files in the current directory
echo Listing all PNG files...
set count=0
for %%f in (*.png) do (
    set /a count+=1
    set "file!count!=%%f"
    echo !count!. %%f
)

rem Prompt user to select a file
set /p choice="Enter the number of the file you want to print: "

rem Validate the choice
if "!file%choice%!"=="" (
    echo Invalid choice.
    goto :end
)

rem Print the selected file
echo Printing "!file%choice%!..."
start "" "mspaint.exe" /pt "!file%choice%!%"

rem Prompt to print another file
set /p choice="Do you want to print another file? (Y/N): "
if /i "%choice%"=="Y" goto Start
if /i "%choice%"=="y" goto Start

:end
pause
exit /b


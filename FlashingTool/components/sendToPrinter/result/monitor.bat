@echo off
setlocal enabledelayedexpansion

::set "folder_to_monitor=Z:"
set folder_to_monitor=%~d0
set "printer_name=POSTEK G6000"

:loop
@REM Monitor for new .png files
for %%f in ("%folder_to_monitor%\*.png") do (
    echo %%f
    if not exist "%%f.printed" (
        echo New file detected: %%~nxf
        @REM echo Printing %%~nxf...
        @REM Below will echo file full path
        echo Full Path: %%f 
        @REM Below will echo file name with extension
        echo File Name with Extension: %%~nxf
        
        @REM Move the file to the archive folder
        if exist "%folder_to_monitor%\printed\%%~nxf" (
            @REM echo "File %%~nxf exist. Skipping" >> printer_log.txt
            echo "File %%~nxf exist in printed folder, Skipping!"
        ) else (
            @REM echo "File %%~nxf doesn't exist. Printing" >> printer_log.txt
            echo "File %%~nxf doesn't exist in printed folder, Printing..."

            @REM "E:\Program Files (x86)\postek\IrfanView\i_view64.exe" "%%f" /print="!printer_name!" 
            "E:\postek\IrfanView\i_view64.exe" "%%f" /print="!printer_name!"

            @REM Introduce a small delay to ensure IrfanView is done with the file
            timeout /t 5 /nobreak >nul

            copy /y "%%f" "%folder_to_monitor%\printed\"
        )

        @REM if errorlevel 1 (
        @REM     echo ERROR: Failed to move file %%~nxf
        @REM ) else (
        @REM     echo File %%~nxf moved to printed folder
        @REM )
    )
)

@REM exit
@REM Sleep 10 seconds
timeout /t 10 /nobreak >nul

goto loop

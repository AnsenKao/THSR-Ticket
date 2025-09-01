@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM 設定預設值
set DEFAULT_INPUT=4
set WAIT_BEFORE_INPUT=10
set WAIT_BEFORE_RESTART=60
set INSTANCE_NAME=auto_%RANDOM%
set USE_UV=true

REM 顯示使用說明
if "%1"=="-h" goto :show_usage
if "%1"=="--help" goto :show_usage

REM 解析命令列參數
:parse_args
if "%1"=="" goto :start_main
if "%1"=="-i" (
    set DEFAULT_INPUT=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="-w" (
    set WAIT_BEFORE_INPUT=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="-r" (
    set WAIT_BEFORE_RESTART=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="-n" (
    set INSTANCE_NAME=%2
    shift
    shift
    goto :parse_args
)
shift
goto :parse_args

:show_usage
echo Usage: %0 [Options]
echo Options:
echo   -i NUMBER    Specify input number (default: %DEFAULT_INPUT%)
echo   -w SECONDS   Wait time before input (default: %WAIT_BEFORE_INPUT% seconds)
echo   -r SECONDS   Wait time before restart (default: %WAIT_BEFORE_RESTART% seconds)
echo   -n NAME      Instance name (for multi-instance execution)
echo   -h           Show this help
echo.
echo Examples:
echo   %0              # Use default settings
echo   %0 -i 2         # Input number 2
echo   %0 -i 3 -w 10 -n instance1   # Input 3, wait 10 seconds, instance name instance1
goto :eof

:start_main
REM 創建實例專用的臨時目錄
set TEMP_DIR=%TEMP%\thsr_ticket_%INSTANCE_NAME%
set PID_FILE=%TEMP_DIR%\main.pid
set INPUT_FILE=%TEMP_DIR%\input.txt

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo === THSR-Ticket Auto Run Script (Instance: %INSTANCE_NAME%) ===
echo Input Number: %DEFAULT_INPUT%
echo Wait Before Input: %WAIT_BEFORE_INPUT% seconds
echo Wait Before Restart: %WAIT_BEFORE_RESTART% seconds
echo Temp Directory: %TEMP_DIR%
echo Press Ctrl+C to stop script
echo.

REM 設定清理函數
set CLEANUP_DONE=false

REM 主循環
set CYCLE_COUNT=0
:main_loop
set /a CYCLE_COUNT+=1
echo === Start THSR-Ticket (Instance: %INSTANCE_NAME%, Cycle: %CYCLE_COUNT%) ===
echo Time: %date% %time%

REM Create input file
(
echo %DEFAULT_INPUT%
echo.
echo 23
echo A123456789
echo.
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
echo %DEFAULT_INPUT%
) > "%INPUT_FILE%"

REM Wait before start
echo Waiting %WAIT_BEFORE_INPUT% seconds before start...
timeout /t %WAIT_BEFORE_INPUT% /nobreak >nul

REM Run main program
echo Starting THSR-Ticket...
start /b "" uv run python thsr_ticket\main.py < "%INPUT_FILE%"

REM Wait for program execution
echo Waiting %WAIT_BEFORE_RESTART% seconds before restart...
timeout /t %WAIT_BEFORE_RESTART% /nobreak >nul

REM Stop all related processes
echo Stopping current instance processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im uv.exe >nul 2>&1

echo === Preparing to restart (Instance: %INSTANCE_NAME%) ===
echo.

REM Short pause before restart
timeout /t 2 /nobreak >nul

goto :main_loop

:cleanup
if "%CLEANUP_DONE%"=="true" goto :eof
set CLEANUP_DONE=true
echo.
echo === Cleaning up instance %INSTANCE_NAME% processes... ===
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im uv.exe >nul 2>&1
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
echo Stopped instance %INSTANCE_NAME% related processes
goto :eof

@echo off
chcp 65001 >nul 2>&1

set OUT=dist\app
set DEST=%OUT%\metaminsweeper

echo [Clean] Removing old builds...
if exist "%OUT%\metaminsweeper" rmdir /s /q "%OUT%\metaminsweeper"
if exist "%OUT%\plugin_manager" rmdir /s /q "%OUT%\plugin_manager"

echo.
echo [1/3] metaminsweeper.exe
pyinstaller --noconfirm --name metaminsweeper --windowed --distpath %OUT% ^
    --icon src/media/cat.ico ^
    --clean ^
    --paths src ^
    --add-data "src/media;media" ^
    src\main.py

echo.
echo [2/3] plugin_manager.exe
pyinstaller --noconfirm --name plugin_manager --windowed --icon src/media/cat.ico --add-data "src/plugins;plugins" --add-data "src/shared_types;shared_types" --hidden-import sqlite3 --hidden-import code --hidden-import xmlrpc --hidden-import xmlrpc.server --hidden-import xmlrpc.client --hidden-import http.server --hidden-import socketserver --hidden-import email --hidden-import email.utils --hidden-import requests --hidden-import Crypto.Cipher.AES --hidden-import Crypto.Random --distpath %OUT% src\plugin_manager\_run.py

echo.
echo [3/3] Copy resources to metaminsweeper\
copy /y "%OUT%\plugin_manager\plugin_manager.exe" "%DEST%\"
xcopy /e /y /i "%OUT%\plugin_manager\_internal" "%DEST%\_internal" >nul
xcopy /e /y /i "src\plugin_sdk" "%DEST%\plugin_sdk" >nul
xcopy /e /y /i "src\plugin_manager" "%DEST%\plugin_manager" >nul
xcopy /e /y /i "src\shared_types" "%DEST%\shared_types" >nul
if exist "%DEST%\plugin_manager\_run.py" del /f /q "%DEST%\plugin_manager\_run.py"
mkdir "%DEST%\user_plugins" >nul 2>&1

echo [4/4] Copy debugpy from venv to _internal\
set SP=.venv\Lib\site-packages
xcopy /e /y /i "%SP%\debugpy" "%DEST%\_internal\debugpy" >nul
xcopy /e /y /i "%SP%\msgspec" "%DEST%\_internal\msgspec" >nul 2>nul
xcopy /e /y /i "%SP%\setuptools" "%DEST%\_internal\setuptools" >nul 2>nul

echo [5/5] Copy plugin-dev-tutorial.md
copy /y "plugin-dev-tutorial.md" "%DEST%\" >nul

echo.
echo Done! Both in: %OUT%\
pause

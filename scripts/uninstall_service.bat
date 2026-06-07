@echo off
echo Uninstalling Saki Core Service...
cd /d "E:\Priv Bot"
call venv\Scripts\activate
python saki_core/service.py stop
python saki_core/service.py remove
echo.
echo Saki Core Service uninstalled.
pause
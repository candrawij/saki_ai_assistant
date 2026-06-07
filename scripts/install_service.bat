@echo off
echo Installing Saki Core Service...
cd /d "E:\Priv Bot"
call venv\Scripts\activate
python saki_core/service.py install
python saki_core/service.py start
echo.
echo Saki Core Service installed and started!
echo Check Services Manager (services.msc) for "Saki Core Service"
pause
@echo off
echo Installing Saki Auto-Start Task...
cd /d "E:\Priv Bot"

schtasks /create /tn "SakiCore" /tr "E:\Priv Bot\scripts\start_saki_hidden.vbs" /sc onstart /rl highest /f

echo.
echo Saki Auto-Start installed!
echo Saki akan berjalan otomatis saat PC menyala.
pause
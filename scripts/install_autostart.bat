@echo off
echo Installing Saki Auto-Start...
cd /d "E:\Priv Bot"
schtasks /create /tn "SakiCore" /tr "E:\Priv Bot\scripts\start_saki_hidden.vbs" /sc onstart /rl highest /f
echo Done. Saki will start automatically on boot.
pause
@echo off
echo Uninstalling Saki Auto-Start...
schtasks /delete /tn "SakiCore" /f
echo Done.
pause
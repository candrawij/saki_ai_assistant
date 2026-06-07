Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d E:\Priv Bot && venv\Scripts\python.exe run.py > logs\autostart.log 2>&1", 0, False
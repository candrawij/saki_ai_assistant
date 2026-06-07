Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\Priv Bot"
ReturnCode = WshShell.Run("E:\Priv Bot\venv\Scripts\python.exe run.py", 0, False)
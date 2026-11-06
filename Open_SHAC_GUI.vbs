Set shell = CreateObject("WScript.Shell")
folder = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
command = "cmd /c cd /d """ & folder & """ && .venv\Scripts\python.exe gui_pyqt/app.py"
shell.Run command, 0, False

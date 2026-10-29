Option Explicit
Dim fs, shell, root, processEnv
Set fs = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fs.GetParentFolderName(WScript.ScriptFullName)
Set processEnv = shell.Environment("PROCESS")
processEnv("PATH") = root & "\runtime\Library\bin;" & root & "\runtime\Scripts;" & root & "\runtime;" & processEnv("PATH")
processEnv("PYTHONNOUSERSITE") = "1"
shell.Run Chr(34) & root & "\start-windows.cmd" & Chr(34), 0, False

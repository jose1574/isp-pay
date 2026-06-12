Set fso = CreateObject("Scripting.FileSystemObject")
scriptFolder = fso.GetParentFolderName(WScript.ScriptFullName)
runBatPath = fso.BuildPath(scriptFolder, "run.bat")
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & runBatPath & Chr(34), 0
Set WshShell = Nothing
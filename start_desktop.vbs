Set WshShell = CreateObject("WScript.Shell")
projectDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = projectDir

exePath = projectDir & "\dist\WaveMash\WaveMash.exe"
If CreateObject("Scripting.FileSystemObject").FileExists(exePath) Then
    WshShell.Run """" & exePath & """", 1, False
Else
    WshShell.Run "pythonw -m desktop_app", 1, False
End If

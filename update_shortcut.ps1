$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\junno\OneDrive\Desktop\WaveMash.lnk")
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = """C:\Users\junno\OneDrive\Desktop\WaveMash\start_desktop.vbs"""
$Shortcut.WorkingDirectory = "C:\Users\junno\OneDrive\Desktop\WaveMash"
$Shortcut.IconLocation = "C:\Users\junno\OneDrive\Desktop\WaveMash\icon_large.ico"
$Shortcut.Save()

$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\junno\OneDrive\Desktop\WaveMash.lnk")
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/c `"`"C:\Users\junno\OneDrive\Desktop\WAVMASH\start_wavemash.bat`"`""
$Shortcut.WorkingDirectory = "C:\Users\junno\OneDrive\Desktop\WAVMASH"
$Shortcut.IconLocation = "C:\Users\junno\OneDrive\Desktop\WAVMASH\wavemash.ico"
$Shortcut.Save()


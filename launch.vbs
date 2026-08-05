' Optional silent launcher. Prefer Desktop/Start Menu Sekikit.lnk after install_shortcuts.ps1.
' Order: packaged onedir exe → onefile exe → pythonw run.py → launch.bat (first-time setup)

Option Explicit
Dim sh, fso, root, onedir, onefile, pythonw, runpy

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root

onedir = root & "\dist\Sekikit\Sekikit.exe"
onefile = root & "\dist\Sekikit.exe"
pythonw = root & "\.venv\Scripts\pythonw.exe"
runpy = root & "\run.py"

If fso.FileExists(onedir) Then
  sh.Run """" & onedir & """", 1, False
  WScript.Quit 0
End If

If fso.FileExists(onefile) Then
  sh.Run """" & onefile & """", 1, False
  WScript.Quit 0
End If

If fso.FileExists(pythonw) And fso.FileExists(runpy) Then
  sh.Run """" & pythonw & """ """ & runpy & """", 0, False
  WScript.Quit 0
End If

' First-time setup (may show a brief console)
sh.Run """" & root & "\launch.bat""", 1, False

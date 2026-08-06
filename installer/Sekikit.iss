; Sekikit Windows installer (Inno Setup 6+)
; Best practices for small offline freeware:
;   - Single Setup.exe, clear wizard, uninstall registration
;   - App under {autopf} or per-user Programs; data under %LOCALAPPDATA%
;   - Never require network at install time
;   - Optional desktop shortcut (default off)
;   - Close running app before upgrade
; Sign Setup.exe later when you have a code-signing cert.
;
; Build: scripts\build_installer.ps1  (runs PyInstaller first)
;
; Compile-time only (ISPP) — never use [Code] InitializeSetup for this:
; that runs on end-user PCs and will fail when dist\ is absent there.

#ifnexist "..\dist\Sekikit\Sekikit.exe"
  #error "Missing dist\Sekikit\Sekikit.exe — run scripts\build_exe.ps1 (or build_installer.ps1) first."
#endif

#define MyAppName "Sekikit"
#ifndef MyAppVersion
  #define MyAppVersion "0.15.0-beta.1"
#endif
; Windows VERSIONINFO must be numeric (a.b.c.d) — separate from display/beta label
#ifndef MyAppVersionInfo
  #define MyAppVersionInfo "0.15.0.1"
#endif
#define MyAppPublisher "Sekiboi"
#define MyAppURL "https://github.com/Sekiboi/sekikit"
#define MyAppExeName "Sekikit.exe"
; Product id for Sekikit (separate from any prior JustPages install)
#define MyAppId "{{A1C8E2F4-9D6B-4A3C-B7E1-5F8D2C0A9E6B}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
InfoBeforeFile=..\installer\WELCOME.txt
OutputDir=..\dist\installer
OutputBaseFilename=Sekikit-{#MyAppVersion}-Setup
SetupIconFile=..\assets\sekikit.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Prefer non-admin when possible; allow elevation if user picks Program Files
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
; Show uninstall in Apps & features
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} installer (beta)
VersionInfoProductName={#MyAppName}
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
; Silent: Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Entire onedir PyInstaller tree (must exist at compile time: dist\Sekikit\*)
Source: "..\dist\Sekikit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Extra docs (not inside PyInstaller tree)
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\PRIVACY.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\LIMITS.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\REPORTING.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Offline PDF page toolkit — free forever"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Offline PDF page toolkit"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Leave user data (%LOCALAPPDATA%\Sekikit) so prefs/logs survive reinstall.
; Optional: Type: filesandordirs; Name: "{localappdata}\Sekikit"

; NOTE: Do NOT put developer path checks in [Code]/InitializeSetup — that runs on
; end-user machines. Ensure dist\Sekikit exists before compiling (build_installer.ps1).

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
; Entire onedir PyInstaller tree (must exist: dist\Sekikit\*)
Source: "..\dist\Sekikit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Offline PDF page toolkit — free forever"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Offline PDF page toolkit"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Leave user data (%LOCALAPPDATA%\Sekikit) so prefs/logs survive reinstall.
; Optional: Type: filesandordirs; Name: "{localappdata}\Sekikit"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not DirExists(ExpandConstant('{#SourcePath}\..\dist\Sekikit')) then
  begin
    MsgBox('Build dist\Sekikit first (scripts\build_exe.ps1), then re-run the installer build.',
      mbError, MB_OK);
    Result := False;
  end;
end;

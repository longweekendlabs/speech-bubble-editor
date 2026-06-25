; installer.iss — Inno Setup script for Speech Bubble Editor v4 (Windows x64)
; Download Inno Setup 6: https://jrsoftware.org/isdl.php

#define AppName      "Speech Bubble Editor"
; AppVersion can be overridden from command line: ISCC /DAppVersion=4.0.4 installer.iss
#ifndef AppVersion
  #define AppVersion "4.0.4"
#endif
#define AppPublisher "Long Weekend Labs"
#define AppExeName   "SpeechBubbleEditor.exe"

[Setup]
AppId={{A4F1C3E2-8B2D-4F9A-BC3E-1D2A3F4E5B6C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://longweekendlabs.com
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=SpeechBubbleEditor-{#AppVersion}-win64-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=icons\icon.ico
DisableProgramGroupPage=yes
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; \
    Flags: nowait postinstall skipifsilent

; installer_arm64.iss — Inno Setup script for Speech Bubble Editor v3.1 (Windows ARM64)
; Download Inno Setup 6: https://jrsoftware.org/isdl.php

#define AppName      "Speech Bubble Editor"
; AppVersion can be overridden from command line: ISCC /DAppVersion=3.1.0 installer_arm64.iss
#ifndef AppVersion
  #define AppVersion "3.1.0"
#endif
#define AppPublisher "Long Weekend Labs"
#define AppExeName   "SpeechBubbleEditor.exe"

[Setup]
AppId={{B5G2D4F3-9C3E-5G0B-CD4F-2E3B4G5F6C7D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://longweekendlabs.com
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=SpeechBubbleEditor-{#AppVersion}-winarm64-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=arm64
ArchitecturesInstallIn64BitMode=arm64
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

; VRChat Avatar Tagger — branded Windows installer
; Compiled by Inno Setup in GitHub Actions, with assets built by Pillow.
#define MyAppName "VRChat Avatar Tagger"
#define MyAppVersion "1.5.0"
#define MyAppExeName "VRChat Avatar Tagger.exe"

[Setup]
AppId=VRChatAvatarTagger.Y2KBeatzzDot
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Ksyusha (Ксюша)
AppPublisherURL=https://guns.lol/life999
AppSupportURL=https://github.com/y2kbeatzz-dot/vrchat-avatar-tagger/issues
AppUpdatesURL=https://github.com/y2kbeatzz-dot/vrchat-avatar-tagger/releases/latest
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
WizardStyle=modern
WizardImageFile=..\assets\generated\installer-wizard.bmp
WizardSmallImageFile=..\assets\generated\installer-wizard-small.bmp
WizardImageBackColor=$171122
WizardSmallImageBackColor=$171122
SetupIconFile=..\assets\generated\app-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
SetupLogging=yes
OutputDir=..\dist\installer
OutputBaseFilename=VRChat-Avatar-Tagger-Setup-Windows
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion=1.5.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\VRChat Avatar Tagger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch VRChat Avatar Tagger"; Flags: nowait postinstall skipifsilent

; Скрипт установщика для программы "Менеджер контактов организаций"

#define MyAppName "Менеджер контактов организаций"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "ОАО ""Компания МогНат"""
#define MyAppExeName "ManagerContacts.exe"
#define MyAppURL "https://github.com/Londimain/Organization-Contacts-Manager"

[Setup]
AppId={{B2C3D4E5-F6A7-8901-2345-6789ABCDEF01}
AppName={#MyAppName}
VersionInfoVersion={#MyAppVersion}.0
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
CloseApplications=force
RestartApplications=yes

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

OutputDir=installer_output
OutputBaseFilename=ManagerContacts_Setup_v{#MyAppVersion}
SetupIconFile=ico\manager.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=admin

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Даем права на запись в папку программы (для локальной базы данных и логов)
Name: "{app}"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
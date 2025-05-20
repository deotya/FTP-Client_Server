#define MyAppName "FTP Server"
#define MyAppVersion "1.0"
#define MyAppPublisher "YourCompany"
#define MyAppURL "https://company.com"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{B2C3D4E5-F6G7-H8I9-J0K1-L2M3N4O5P6Q7}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\FTP Server
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.\installer
OutputBaseFilename=FTP_Server_Setup
Compression=lzma
SolidCompression=yes
; Am eliminat referințele la fișierele care nu există
; SetupIconFile=ftp_server\resources\server_icon.ico
; WizardImageFile=ftp_server\resources\wizard_image.bmp
; WizardSmallImageFile=ftp_server\resources\wizard_small.bmp

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; FTP Server (director complet cu toate componentele)
Source: "dist\FTP_Server\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FTP Server"; Filename: "{app}\FTP_Server.exe"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\FTP Server"; Filename: "{app}\FTP_Server.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FTP_Server.exe"; Description: "{cm:LaunchProgram,FTP Server}"; Flags: nowait postinstall skipifsilent 
#define MyAppName "FTP Client"
#define MyAppVersion "1.0"
#define MyAppPublisher "YourCompany"
#define MyAppURL "https://company.com"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{A1B2C3D4-E5F6-G7H8-I9J0-K1L2M3N4O5P6}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\FTP Client
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.\installer
OutputBaseFilename=FTP_Client_Setup
Compression=lzma
SolidCompression=yes
; Am eliminat referințele la fișierele care nu există
; SetupIconFile=ftp_client\ui\resources\client_icon.ico
; WizardImageFile=ftp_client\ui\resources\wizard_image.bmp
; WizardSmallImageFile=ftp_client\ui\resources\wizard_small.bmp

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; FTP Client (director complet cu toate componentele)
Source: "dist\FTP_Client\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Copiem și conținutul ftp_server în directorul FTP Server
Source: "ftp_server\*"; DestDir: "{app}\FTP Server"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FTP Client"; Filename: "{app}\FTP_Client.exe"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\FTP Client"; Filename: "{app}\FTP_Client.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FTP_Client.exe"; Description: "{cm:LaunchProgram,FTP Client}"; Flags: nowait postinstall skipifsilent 
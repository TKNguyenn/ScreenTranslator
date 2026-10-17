#ifndef AppVersion
  #define AppVersion "0.4.1.9"
#endif
#ifndef InstallId
  #define InstallId "AIScreenTranslator-96F65CB7-531C-4202-B340-B90251E5B2AC"
#endif
#ifndef InstallDir
  #define InstallDir "{localappdata}\Programs\AIScreenTranslator"
#endif
#ifndef LegacyDataDir
  #define LegacyDataDir "{localappdata}\AIScreenTranslator"
#endif
#ifndef SetupName
  #define SetupName "AI-Screen-Translator-" + AppVersion + "-Setup"
#endif
#ifndef ShortcutName
  #define ShortcutName "AI Screen Translator"
#endif
#ifndef LauncherPath
  #define LauncherPath "..\build\Uninstall.exe"
#endif

[Setup]
AppId={#InstallId}
AppName=AI Screen Translator
AppVersion={#AppVersion}
DefaultDirName={#InstallDir}
DisableDirPage=no
DefaultGroupName=AI Screen Translator
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\release
OutputBaseFilename={#SetupName}
SetupIconFile=..\app\assets\app_icon.ico
UninstallDisplayIcon={app}\ScreenTranslator.exe
UninstallDisplayName=AI Screen Translator
AppMutex=Local\AIScreenTranslator_Running
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
Uninstallable=yes
UninstallLogMode=append
VersionInfoVersion={#AppVersion}

[Files]
Source: "..\dist\ScreenTranslator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#LauncherPath}"; DestDir: "{app}"; DestName: "Uninstall.exe"; Flags: ignoreversion
Source: "..\build\Update.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\Windows_Release.md"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion
; Copy old settings only on migration; never replace existing local files or delete originals during setup.
Source: "{#LegacyDataDir}\config.json"; DestDir: "{app}"; Flags: external onlyifdoesntexist skipifsourcedoesntexist; Check: MigrateLegacyData
Source: "{#LegacyDataDir}\providers.json"; DestDir: "{app}"; Flags: external onlyifdoesntexist skipifsourcedoesntexist; Check: MigrateLegacyData
Source: "{#LegacyDataDir}\prompts.json"; DestDir: "{app}"; Flags: external onlyifdoesntexist skipifsourcedoesntexist; Check: MigrateLegacyData
Source: "{#LegacyDataDir}\.env"; DestDir: "{app}"; Flags: external onlyifdoesntexist skipifsourcedoesntexist; Check: MigrateLegacyData
Source: "{#LegacyDataDir}\data\*"; DestDir: "{app}\data"; Flags: external onlyifdoesntexist skipifsourcedoesntexist recursesubdirs createallsubdirs; Check: MigrateLegacyData

[Icons]
Name: "{userprograms}\{#ShortcutName}\{#ShortcutName}"; Filename: "{app}\ScreenTranslator.exe"; WorkingDir: "{app}"
Name: "{userprograms}\{#ShortcutName}\Uninstall AI Screen Translator"; Filename: "{uninstallexe}"

[InstallDelete]
Type: files; Name: "{app}\Uninstall.bat"

[UninstallDelete]
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\providers.json"
Type: files; Name: "{app}\prompts.json"
Type: files; Name: "{app}\.env"
Type: files; Name: "{app}\self-check.json"
Type: filesandordirs; Name: "{app}\data"
Type: files; Name: "{#LegacyDataDir}\config.json"
Type: files; Name: "{#LegacyDataDir}\providers.json"
Type: files; Name: "{#LegacyDataDir}\prompts.json"
Type: files; Name: "{#LegacyDataDir}\.env"
Type: files; Name: "{#LegacyDataDir}\self-check.json"
Type: filesandordirs; Name: "{#LegacyDataDir}\data"
Type: dirifempty; Name: "{#LegacyDataDir}"
Type: dirifempty; Name: "{app}"
Type: files; Name: "{userdesktop}\{#ShortcutName}.lnk"

[Code]
var
  DesktopShortcutCheck: TNewCheckBox;
  KeepCatalogs: Boolean;
  CatalogBackupDir: String;
  ShouldMigrateLegacy: Boolean;

function MigrateLegacyData(): Boolean;
begin
  Result := ShouldMigrateLegacy;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  // Qt platform plugins cannot reliably load from long Windows paths.
  if Length(ExpandConstant('{app}')) > 180 then
    Result := 'Please choose a shorter installation path (up to 180 characters).';
  if Pos(Lowercase(AddBackslash(ExpandConstant('{#LegacyDataDir}'))),
      Lowercase(AddBackslash(ExpandConstant('{app}')))) = 1 then
    if CompareText(ExpandConstant('{app}'), ExpandConstant('{#LegacyDataDir}')) <> 0 then
      Result := 'Please choose a folder outside the old AIScreenTranslator data folder.';
  // Retained catalogs mean this is a reinstall, not an import of stale settings.
  ShouldMigrateLegacy :=
    not FileExists(ExpandConstant('{app}\config.json')) and
    not FileExists(ExpandConstant('{app}\providers.json')) and
    not FileExists(ExpandConstant('{app}\prompts.json')) and
    (CompareText(ExpandConstant('{app}'), ExpandConstant('{#LegacyDataDir}')) <> 0);
end;

procedure InitializeWizard();
begin
  DesktopShortcutCheck := TNewCheckBox.Create(WizardForm);
  DesktopShortcutCheck.Parent := WizardForm.FinishedPage;
  DesktopShortcutCheck.SetBounds(WizardForm.RunList.Left, WizardForm.RunList.Top,
    WizardForm.RunList.Width, ScaleY(24));
  DesktopShortcutCheck.Caption := 'Create a desktop shortcut';
  DesktopShortcutCheck.Checked := ExpandConstant('{param:UPDATE|0}') <> '1';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssDone) and DesktopShortcutCheck.Checked then
    try
      CreateShellLink(ExpandConstant('{userdesktop}\{#ShortcutName}.lnk'),
        'AI Screen Translator', ExpandConstant('{app}\ScreenTranslator.exe'), '',
        ExpandConstant('{app}'), ExpandConstant('{app}\ScreenTranslator.exe'), 0, SW_SHOWNORMAL);
    except
      Log('Desktop shortcut could not be created: ' + GetExceptionMessage);
      if not WizardSilent then
        MsgBox('The app was installed, but the desktop shortcut could not be created.' + #13#10 +
          'You can open the app from the Start Menu.', mbInformation, MB_OK);
    end;
end;

function InitializeUninstall(): Boolean;
var
  Form: TSetupForm;
  Heading, Details: TNewStaticText;
  KeepChoice, AllChoice: TNewRadioButton;
  ContinueButton, CancelButton: TNewButton;
  DataMode: String;
begin
  DataMode := Lowercase(ExpandConstant('{param:DATA|keep}'));
  KeepCatalogs := DataMode = 'keep';
  Result := (DataMode = 'keep') or (DataMode = 'all');
  if not Result then begin
    Log('Invalid /DATA mode; expected keep or all. No files removed.');
    Exit;
  end;
  if UninstallSilent then Exit;
  Form := CreateCustomForm(ScaleX(540), ScaleY(290), True, True);
  try
    Form.Caption := 'AI Screen Translator - Uninstall';
    Form.Position := poScreenCenter;
    Heading := TNewStaticText.Create(Form);
    Heading.Parent := Form;
    Heading.SetBounds(ScaleX(20), ScaleY(20), ScaleX(500), ScaleY(30));
    Heading.Caption := 'Choose what to remove';
    Heading.Font.Style := [fsBold];
    KeepChoice := TNewRadioButton.Create(Form);
    KeepChoice.Parent := Form;
    KeepChoice.SetBounds(ScaleX(20), ScaleY(62), ScaleX(500), ScaleY(26));
    KeepChoice.Caption := 'Uninstall app; keep only providers.json and prompts.json';
    KeepChoice.Checked := KeepCatalogs;
    AllChoice := TNewRadioButton.Create(Form);
    AllChoice.Parent := Form;
    AllChoice.SetBounds(ScaleX(20), ScaleY(100), ScaleX(500), ScaleY(26));
    AllChoice.Caption := 'Remove everything, including saved providers and prompts';
    AllChoice.Checked := not KeepCatalogs;
    Details := TNewStaticText.Create(Form);
    Details.Parent := Form;
    Details.SetBounds(ScaleX(20), ScaleY(146), ScaleX(500), ScaleY(76));
    Details.AutoSize := False;
    Details.WordWrap := True;
    Details.Caption := 'Both options remove the app, shortcuts, settings, cache and logs.' + #13#10 +
      'Kept files remain in your installation folder: ' + ExpandConstant('{app}');
    ContinueButton := TNewButton.Create(Form);
    ContinueButton.Parent := Form;
    ContinueButton.SetBounds(ScaleX(316), ScaleY(240), ScaleX(96), ScaleY(30));
    ContinueButton.Caption := 'Uninstall';
    ContinueButton.Default := True;
    ContinueButton.ModalResult := mrOk;
    CancelButton := TNewButton.Create(Form);
    CancelButton.Parent := Form;
    CancelButton.SetBounds(ScaleX(424), ScaleY(240), ScaleX(96), ScaleY(30));
    CancelButton.Caption := 'Cancel';
    CancelButton.Cancel := True;
    CancelButton.ModalResult := mrCancel;
    Result := Form.ShowModal = mrOk;
    KeepCatalogs := KeepChoice.Checked;
  finally
    Form.Free;
  end;
end;

procedure BackupCatalog(const Name: String);
var
  Source: String;
begin
  Source := ExpandConstant('{app}\') + Name;
  if FileExists(Source) and not FileCopy(Source, CatalogBackupDir + '\' + Name, True) then
    RaiseException('Cannot preserve ' + Name + '. No app files have been removed.');
end;

procedure RestoreCatalog(const Name: String);
var
  Source: String;
begin
  Source := CatalogBackupDir + '\' + Name;
  if FileExists(Source) and not FileCopy(Source, ExpandConstant('{app}\') + Name, True) then
    RaiseException('Cannot restore ' + Name);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usUninstall) and KeepCatalogs then begin
    // Older installs logged unconditional data deletion; preserve outside that folder.
    CatalogBackupDir := ExpandConstant('{#LegacyDataDir}') + '.keep-' + ExtractFileName(ExpandConstant('{tmp}'));
    if not CreateDir(CatalogBackupDir) then
      RaiseException('Cannot create the provider/prompt recovery folder. Uninstall cancelled.');
    try
      BackupCatalog('providers.json');
      BackupCatalog('prompts.json');
    except
      DelTree(CatalogBackupDir, True, True, True);
      RaiseException(GetExceptionMessage);
    end;
  end;
  if (CurUninstallStep = usPostUninstall) and KeepCatalogs then begin
    try
      if not ForceDirectories(ExpandConstant('{app}')) then
        RaiseException('Cannot recreate the data folder');
      RestoreCatalog('providers.json');
      RestoreCatalog('prompts.json');
      if not DelTree(CatalogBackupDir, True, True, True) then
        RaiseException('Cannot remove the recovery folder');
      RemoveDir(ExpandConstant('{app}'));
    except
      Log('Catalog recovery required: ' + CatalogBackupDir + ': ' + GetExceptionMessage);
      SuppressibleMsgBox('Your preserved files are in: ' + CatalogBackupDir + #13#10 +
        'Copy providers.json and prompts.json back to ' + ExpandConstant('{app}'),
        mbError, MB_OK, IDOK);
    end;
  end;
end;

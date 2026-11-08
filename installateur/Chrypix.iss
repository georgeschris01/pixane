; Chrypix — © 2026 Georges Christophe (chrypox).
; Installateur de Chrypix (Inno Setup 7, gratuit : https://jrsoftware.org/isdl.php), même présentation que TwinPanel.
; Compilé par construire-installateur.bat, qui prépare d'abord les fichiers dans publication\Chrypix et donne la version.
; Une nouvelle version = un nouveau Chrypix-Setup-x.y.z.exe : lancé sur un PC où Chrypix est déjà installé, il le met
; à jour (même AppId ci-dessous, à NE JAMAIS changer). Les réglages (registre, %LOCALAPPDATA%\Chrypix) ne sont pas touchés.
; Pages : langue, accueil, dossier, vérification du PC (carte graphique, place libre, moteur IA ComfyUI), installation.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{89EBA9CC-CDC6-468F-A638-3F71B48EE9A3}
AppName=Chrypix
AppVersion={#AppVersion}
AppVerName=Chrypix {#AppVersion}
AppPublisher=chrypox
AppCopyright=© 2026 Georges Christophe (chrypox)
ShowLanguageDialog=yes
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Installation de Chrypix
DefaultDirName={autopf}\Chrypix
DefaultGroupName=Chrypix
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
DisableDirPage=no
OutputDir=..\publication\installateur
OutputBaseFilename=Chrypix-Setup-{#AppVersion}
SetupIconFile=..\chrypix\ressources\chrypix.ico
UninstallDisplayIcon={app}\chrypix.ico
UninstallDisplayName=Chrypix
WizardStyle=modern
; Présentation : bande bleu nuit à gauche des pages d'accueil et de fin (logo, nom, petite capture), bandeau bleu nuit
; en haut des autres pages (voir [Code]). Images fabriquées par images\fabrique_images.py, une par réglage d'affichage
; (100 % à 250 %) ; Setup prend la mieux adaptée. Capture anglaise chargée dans [Code].
DisableWelcomePage=no
WizardImageFile=images\accueil-fr-202x386.png,images\accueil-fr-269x515.png,images\accueil-fr-336x643.png,images\accueil-fr-403x772.png,images\accueil-fr-430x824.png,images\accueil-fr-534x1022.png
WizardSmallImageFile=images\logo-58.png,images\logo-77.png,images\logo-97.png,images\logo-116.png,images\logo-124.png,images\logo-143.png,images\logo-159.png
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; Par défaut pour l'utilisateur seulement (sans droits administrateur) : la langue et le dossier de ComfyUI sont des
; réglages de l'utilisateur. L'installateur propose aussi « pour tous les utilisateurs » (Program Files).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UsedUserAreasWarning=no
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
french.PagePCTitre=Vérification du PC
french.PagePCDescription=Chrypix vérifie ce dont son moteur d'intelligence artificielle a besoin.
french.CarteOk=Carte graphique : %1 (%2 Go de mémoire) — convient.
french.CartePetite=Carte graphique : %1 (%2 Go de mémoire) — il faut au moins 8 Go : les actions IA risquent d'être très lentes ou de ne pas fonctionner.
french.CarteAucune=Aucune carte graphique NVIDIA trouvée : Chrypix s'installera, mais les actions IA (Effacer, Remplir, Agrandir, Upscale) ne fonctionneront pas.
french.Place=Place libre sur %1 : %2 Go.
french.ComfyTrouve=Moteur IA (ComfyUI) trouvé : %1
french.ComfyAbsent=Moteur IA (ComfyUI) non trouvé sur ce PC.
french.ComfyAide=S'il est installé ailleurs, indique son dossier. Sans lui, Chrypix sert à ouvrir, retoucher (calques, texte) et enregistrer les photos, mais pas aux actions IA.
french.Parcourir=Parcourir…
french.ChoisirDossier=Choisis le dossier de ComfyUI (celui qui contient main.py, ou le dossier de ComfyUI portable ou de ComfyUI Desktop) :
french.DossierInvalide=Ce dossier ne contient pas ComfyUI (main.py et son Python sont introuvables).
french.CreerIcone=Créer une icône sur le Bureau
french.Associer=Ouvrir les projets Chrypix (.chr) avec Chrypix
french.TypeProjet=Projet Chrypix
english.PagePCTitre=Checking the PC
english.PagePCDescription=Chrypix checks what its artificial intelligence engine needs.
english.CarteOk=Graphics card: %1 (%2 GB of memory) — suitable.
english.CartePetite=Graphics card: %1 (%2 GB of memory) — at least 8 GB is needed: AI actions may be very slow or may not work.
english.CarteAucune=No NVIDIA graphics card found: Chrypix will install, but the AI actions (Erase, Fill, Expand, Upscale) will not work.
english.Place=Free space on %1: %2 GB.
english.ComfyTrouve=AI engine (ComfyUI) found: %1
english.ComfyAbsent=AI engine (ComfyUI) not found on this PC.
english.ComfyAide=If it is installed elsewhere, select its folder. Without it, Chrypix can open, edit (layers, text) and save photos, but not run the AI actions.
english.Parcourir=Browse…
english.ChoisirDossier=Select the ComfyUI folder (the one containing main.py, or the ComfyUI portable or ComfyUI Desktop folder):
english.DossierInvalide=This folder does not contain ComfyUI (main.py and its Python were not found).
english.CreerIcone=Create a desktop icon
english.Associer=Open Chrypix projects (.chr) with Chrypix
english.TypeProjet=Chrypix project

[Tasks]
Name: "desktopicon"; Description: "{cm:CreerIcone}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associer"; Description: "{cm:Associer}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Mise à jour : l'ancienne version est retirée avant de copier la nouvelle (aucun fichier abandonné ne reste).
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\chrypix"

[Files]
; Seulement le programme, Python et ses bibliothèques : aucun réglage, photo, modèle ni journal.
Source: "..\publication\Chrypix\*"; DestDir: "{app}"; Excludes: "*.log,*.chr,*.ora,*.safetensors,*.ckpt"; Flags: ignoreversion recursesubdirs createallsubdirs
; Images de l'accueil en anglais : seulement pour l'installateur, jamais copiées sur le PC.
Source: "images\accueil-en-*.png"; Flags: dontcopy

[Registry]
; Langue choisie dans l'installateur = langue de Chrypix (modifiable ensuite dans Affichage > Langue).
Root: HKCU; Subkey: "Software\Chrypix\Chrypix"; ValueType: string; ValueName: "langue"; ValueData: "fr"; Languages: french
Root: HKCU; Subkey: "Software\Chrypix\Chrypix"; ValueType: string; ValueName: "langue"; ValueData: "en"; Languages: english
; Fichiers .chr ouverts par Chrypix (seulement si la case est cochée).
Root: HKA; Subkey: "Software\Classes\.chr"; ValueType: string; ValueName: ""; ValueData: "Chrypix.Projet"; Flags: uninsdeletevalue; Tasks: associer
Root: HKA; Subkey: "Software\Classes\Chrypix.Projet"; ValueType: string; ValueName: ""; ValueData: "{cm:TypeProjet}"; Flags: uninsdeletekey; Tasks: associer
Root: HKA; Subkey: "Software\Classes\Chrypix.Projet\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\chrypix.ico"; Tasks: associer
Root: HKA; Subkey: "Software\Classes\Chrypix.Projet\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\python\pythonw.exe"" -m chrypix ""%1"""; Tasks: associer

[Icons]
Name: "{autoprograms}\Chrypix"; Filename: "{app}\python\pythonw.exe"; Parameters: "-m chrypix"; WorkingDir: "{app}"; IconFilename: "{app}\chrypix.ico"; AppUserModelID: "chrypox.Chrypix"
Name: "{autodesktop}\Chrypix"; Filename: "{app}\python\pythonw.exe"; Parameters: "-m chrypix"; WorkingDir: "{app}"; IconFilename: "{app}\chrypix.ico"; AppUserModelID: "chrypox.Chrypix"; Tasks: desktopicon

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: "-m chrypix"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,Chrypix}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallDelete]
; Fichiers créés par Python en fonctionnant (__pycache__) dans le dossier du programme.
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\chrypix"

[Code]
const
  { Couleurs au format Inno Setup ($BBGGRR). }
  BannerColor = $33241D;      { bleu nuit du logo, RGB 29, 36, 51 }
  BannerLineColor = $3D8AFF;  { orange du logo, RGB 255, 138, 61 }
  BannerTextColor = $EBD7C8;  { bleu très clair, RGB 200, 215, 235 }

var
  PagePC: TWizardPage;
  TexteCarte, TextePlace, TexteComfy, TexteAide: TNewStaticText;
  BoutonParcourir: TNewButton;
  ComfyChoisi: String;          { dossier indiqué à la main (écrit dans les réglages de Chrypix) }
  CarteLue: Boolean;
  CarteNom: String;
  CarteMo: Integer;

{ ---------------------------------------------------------------- présentation (comme TwinPanel) }
procedure StyleBanner(Panel: TPanel; Bevel: TBevel; Logo: TBitmapImage; Title, Description: TNewStaticText);
var
  Name: TNewStaticText;
  Line: TPanel;
  Margin, TextLeft, LineHeight: Integer;
begin
  Margin := ScaleX(16);
  LineHeight := ScaleY(3);
  Panel.ParentBackground := False;
  Panel.Color := BannerColor;
  Bevel.Visible := False;

  Line := TPanel.Create(Panel);
  Line.Parent := Panel;
  Line.BevelOuter := bvNone;
  Line.ParentBackground := False;
  Line.Color := BannerLineColor;
  Line.Height := LineHeight;
  Line.Align := alBottom;

  Logo.BackColor := BannerColor;
  Logo.Left := Margin;
  Logo.Top := (Panel.Height - LineHeight - Logo.Height) div 2;

  Name := TNewStaticText.Create(Panel);
  Name.Parent := Panel;
  Name.Caption := 'Chrypix';
  Name.AutoSize := True;
  Name.Font.Style := [fsBold];
  Name.Font.Size := 13;
  Name.Font.Color := BannerLineColor;
  Name.Color := BannerColor;
  Name.Left := Panel.Width - Name.Width - Margin - ScaleX(4);
  Name.Top := (Panel.Height - LineHeight - Name.Height) div 2;
  Name.Anchors := [akTop, akRight];

  TextLeft := Logo.Left + Logo.Width + ScaleX(14);
  Title.Left := TextLeft;
  Title.Width := Name.Left - TextLeft - Margin;
  Title.Color := BannerColor;
  Title.Font.Color := clWhite;
  Description.Left := TextLeft;
  Description.Width := Name.Left - TextLeft - Margin;
  Description.Color := BannerColor;
  Description.Font.Color := BannerTextColor;
end;

procedure LoadEnglishWelcomeImage;
var
  Sizes: TArrayOfString;
  I, Width: Integer;
  FileName: String;
begin
  Sizes := ['202x386', '269x515', '336x643', '403x772', '430x824', '534x1022'];
  FileName := Sizes[GetArrayLength(Sizes) - 1];
  for I := 0 to GetArrayLength(Sizes) - 1 do
  begin
    Width := StrToInt(Copy(Sizes[I], 1, Pos('x', Sizes[I]) - 1));
    if Width >= WizardForm.WizardBitmapImage.Width then
    begin
      FileName := Sizes[I];
      Break;
    end;
  end;
  FileName := 'accueil-en-' + FileName + '.png';
  ExtractTemporaryFile(FileName);
  WizardForm.WizardBitmapImage.PngImage.LoadFromFile(ExpandConstant('{tmp}\' + FileName));
  WizardForm.WizardBitmapImage2.PngImage.LoadFromFile(ExpandConstant('{tmp}\' + FileName));
end;

{ ---------------------------------------------------------------- recherche de ComfyUI
  Même logique que chrypix\moteur.py : dossier de main.py, puis le Python qui le fait tourner. }
function DossierMain(D: String): String;
begin
  Result := '';
  D := RemoveBackslashUnlessRoot(D);
  if D = '' then Exit;
  if FileExists(D + '\main.py') then Result := D
  else if FileExists(D + '\ComfyUI\main.py') then Result := D + '\ComfyUI'
  else if FileExists(D + '\ComfyUI\ComfyUI\main.py') then Result := D + '\ComfyUI\ComfyUI';
end;

function PythonTrouve(D: String): Boolean;
var
  Parent: String;
begin
  Parent := ExtractFileDir(D);
  Result := FileExists(D + '\.venv\Scripts\python.exe') or FileExists(Parent + '\python_embeded\python.exe')
    or FileExists(Parent + '\.venv\Scripts\python.exe') or FileExists(ExtractFileDir(Parent) + '\.venv\Scripts\python.exe');
end;

function ComfyValide(D: String): String;
begin
  Result := DossierMain(D);
  if (Result <> '') and not PythonTrouve(Result) then Result := '';
end;

{ Dossier de base de ComfyUI Desktop, lu dans %APPDATA%\ComfyUI\config.json ("basePath": "D:\\ComfyUI"). }
function BaseDesktop: String;
var
  Json: AnsiString;
  S: String;
  P: Integer;
begin
  Result := '';
  if not LoadStringFromFile(ExpandConstant('{userappdata}\ComfyUI\config.json'), Json) then Exit;
  S := String(Json);
  P := Pos('"basePath"', S);
  if P = 0 then Exit;
  S := Copy(S, P + 10, Length(S));
  P := Pos('"', S);
  if P = 0 then Exit;
  S := Copy(S, P + 1, Length(S));
  P := Pos('"', S);
  if P = 0 then Exit;
  S := Copy(S, 1, P - 1);
  StringChangeEx(S, '\\', '\', True);
  Result := S;
end;

function TrouverComfy: String;
var
  D: String;
begin
  Result := '';
  if ComfyChoisi <> '' then Result := ComfyValide(ComfyChoisi);
  if (Result = '') and RegQueryStringValue(HKCU, 'Software\Chrypix\Chrypix', 'comfyui_dir', D) then
    Result := ComfyValide(D);
  if Result = '' then Result := ComfyValide(BaseDesktop);
  if Result = '' then Result := ComfyValide(ExpandConstant('{localappdata}\Chrypix\moteur\ComfyUI_windows_portable'));
end;

{ ---------------------------------------------------------------- carte graphique (nvidia-smi, fourni avec le pilote) }
procedure LireCarte;
var
  Fichier, Ligne: String;
  Lignes: TArrayOfString;
  Code, P: Integer;
begin
  CarteLue := True;
  CarteNom := '';
  CarteMo := 0;
  Fichier := ExpandConstant('{tmp}\carte.txt');
  if not Exec(ExpandConstant('{cmd}'), '/C nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits > "'
      + Fichier + '"', '', SW_HIDE, ewWaitUntilTerminated, Code) then Exit;
  if (Code <> 0) or not LoadStringsFromFile(Fichier, Lignes) or (GetArrayLength(Lignes) = 0) then Exit;
  Ligne := Lignes[0];
  P := Pos(',', Ligne);
  if P = 0 then Exit;
  CarteNom := Trim(Copy(Ligne, 1, P - 1));
  CarteMo := StrToIntDef(Trim(Copy(Ligne, P + 1, Length(Ligne))), 0);
end;

{ ---------------------------------------------------------------- page « Vérification du PC » }
procedure MettreAJourPagePC;
var
  Libre, Total: Int64;
  Lecteur, Comfy: String;
  Go: Integer;
begin
  if not CarteLue then LireCarte;
  Go := (CarteMo + 512) div 1024;
  if CarteNom = '' then TexteCarte.Caption := CustomMessage('CarteAucune')
  else if CarteMo < 7900 then TexteCarte.Caption := FmtMessage(CustomMessage('CartePetite'), [CarteNom, IntToStr(Go)])
  else TexteCarte.Caption := FmtMessage(CustomMessage('CarteOk'), [CarteNom, IntToStr(Go)]);

  Lecteur := AddBackslash(ExtractFileDrive(WizardDirValue));
  if GetSpaceOnDisk64(Lecteur, Libre, Total) then
    TextePlace.Caption := FmtMessage(CustomMessage('Place'), [Lecteur, IntToStr(Libre div (1024 * 1024 * 1024))])
  else
    TextePlace.Caption := '';

  Comfy := TrouverComfy;
  if Comfy <> '' then
  begin
    TexteComfy.Caption := FmtMessage(CustomMessage('ComfyTrouve'), [Comfy]);
    TexteAide.Caption := '';
  end
  else
  begin
    TexteComfy.Caption := CustomMessage('ComfyAbsent');
    TexteAide.Caption := CustomMessage('ComfyAide');
  end;
  TextePlace.Top := TexteCarte.Top + TexteCarte.Height + ScaleY(12);
  TexteComfy.Top := TextePlace.Top + TextePlace.Height + ScaleY(18);
  TexteAide.Top := TexteComfy.Top + TexteComfy.Height + ScaleY(8);
  BoutonParcourir.Top := TexteAide.Top + TexteAide.Height + ScaleY(10);
end;

procedure ParcourirClic(Sender: TObject);
var
  D: String;
begin
  D := ComfyChoisi;
  if not BrowseForFolder(CustomMessage('ChoisirDossier'), D, False) then Exit;
  if ComfyValide(D) = '' then
  begin
    MsgBox(CustomMessage('DossierInvalide'), mbError, MB_OK);
    Exit;
  end;
  ComfyChoisi := ComfyValide(D);
  MettreAJourPagePC;
end;

function Texte(Page: TWizardPage; Top: Integer): TNewStaticText;
begin
  Result := TNewStaticText.Create(Page);
  Result.Parent := Page.Surface;
  Result.Top := Top;
  Result.Left := 0;
  Result.Width := Page.SurfaceWidth;
  Result.AutoSize := False;
  Result.WordWrap := True;
  Result.Height := ScaleY(34);
end;

procedure CreerPagePC;
begin
  PagePC := CreateCustomPage(wpSelectDir, CustomMessage('PagePCTitre'), CustomMessage('PagePCDescription'));
  TexteCarte := Texte(PagePC, 0);
  TexteCarte.Height := ScaleY(48);
  TextePlace := Texte(PagePC, 0);
  TextePlace.Height := ScaleY(18);
  TexteComfy := Texte(PagePC, 0);
  TexteComfy.Font.Style := [fsBold];
  TexteComfy.Height := ScaleY(48);
  TexteAide := Texte(PagePC, 0);
  TexteAide.Height := ScaleY(48);
  BoutonParcourir := TNewButton.Create(PagePC);
  BoutonParcourir.Parent := PagePC.Surface;
  BoutonParcourir.Caption := CustomMessage('Parcourir');
  BoutonParcourir.Left := 0;
  BoutonParcourir.Width := ScaleX(110);
  BoutonParcourir.Height := ScaleY(26);
  BoutonParcourir.OnClick := @ParcourirClic;
end;

{ ---------------------------------------------------------------- étapes }
procedure InitializeWizard;
begin
  StyleBanner(WizardForm.MainPanel, WizardForm.Bevel1, WizardForm.WizardSmallBitmapImage,
    WizardForm.PageNameLabel, WizardForm.PageDescriptionLabel);
  if ActiveLanguage = 'english' then
    LoadEnglishWelcomeImage;
  CreerPagePC;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = PagePC.ID then
    MettreAJourPagePC;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  { dossier de ComfyUI indiqué à la main : retenu dans les réglages de Chrypix }
  if (CurStep = ssPostInstall) and (ComfyChoisi <> '') then
    RegWriteStringValue(HKCU, 'Software\Chrypix\Chrypix', 'comfyui_dir', ComfyChoisi);
end;

procedure InitializeUninstallProgressForm;
begin
  StyleBanner(UninstallProgressForm.MainPanel, UninstallProgressForm.Bevel1, UninstallProgressForm.WizardSmallBitmapImage,
    UninstallProgressForm.PageNameLabel, UninstallProgressForm.PageDescriptionLabel);
end;

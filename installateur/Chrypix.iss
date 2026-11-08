; Chrypix — © 2026 Georges Christophe (chrypox).
; Installateur de Chrypix (Inno Setup 7, gratuit : https://jrsoftware.org/isdl.php), même présentation que TwinPanel.
; Compilé par construire-installateur.bat, qui prépare d'abord les fichiers dans publication\Chrypix et donne la version.
; Une nouvelle version = un nouveau Chrypix-Setup-x.y.z.exe : lancé sur un PC où Chrypix est déjà installé, il le met
; à jour (même AppId ci-dessous, à NE JAMAIS changer). Les réglages (registre, %LOCALAPPDATA%\Chrypix) ne sont pas touchés.
; Pages : langue, accueil, dossier, vérification du PC (carte graphique, place libre, moteur IA ComfyUI), moteur IA
; (seulement si ComfyUI est absent : liste des téléchargements, licence FLUX.1 [dev] à accepter), installation.
; Le téléchargement du moteur se fait après, par Chrypix (chrypix\installation_moteur.py, reprise possible).
; Désinstallation : propose de supprimer aussi le moteur IA installé par Chrypix et les réglages (non par défaut).

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
french.PageMoteurTitre=Moteur IA
french.PageMoteurDescription=Le moteur IA n'est pas sur ce PC : Chrypix peut le télécharger et l'installer.
french.MoteurIntro=Les actions IA (Effacer, Remplir, Agrandir, Upscale) utilisent ComfyUI, caché derrière les boutons de Chrypix. Tout vient des sites officiels (GitHub, Hugging Face) ; le téléchargement se fait après l'installation, dans une fenêtre qui montre l'avancement. On peut l'arrêter : il reprendra plus tard (menu IA > Installer le moteur IA).
french.MoteurCase=Télécharger et installer le moteur IA après l'installation de Chrypix
french.MoteurDossier=Dossier du moteur IA :
french.MoteurListe=ComfyUI portable 0.44 (le moteur) — 1,9 Go — GitHub — GPL-3.0%nExtensions Inpaint nodes, Crop and Stitch, Ultimate SD Upscale, GGUF — moins de 5 Mo — GitHub — GPL-3.0, Apache-2.0%nFlux Fill, version GGUF Q8 (effacer, remplir, agrandir) — 11,9 Go — Hugging Face — FLUX.1 [dev] non commerciale%nEncodeurs de texte T5 et CLIP — 5,0 Go — Hugging Face — Apache-2.0%nDécodeur d'image (VAE) — 0,3 Go — Hugging Face — Apache-2.0%nLaMa (effacer) — 0,2 Go — GitHub — Apache-2.0%nRealESRGAN x4 (upscale) — 64 Mo — GitHub — BSD-3-Clause%n7-Zip (pour décompresser) — 0,6 Mo — GitHub — LGPL-2.1%nTotal : 19,4 Go à télécharger, environ 28 Go sur le disque.
french.MoteurSchnell=Ajouter Flux Schnell pour « Upscale net » (11,8 Go de plus, facultatif ; l'upscale simple marche sans)
french.MoteurLicence=Flux Fill est sous licence FLUX.1 [dev] non commerciale : usage personnel permis, pas d'usage commercial.
french.MoteurLien=Lire la licence FLUX.1 [dev]
french.MoteurAccepte=J'accepte la licence FLUX.1 [dev] (usage non commercial)
french.MoteurPasAccepte=Pour installer le moteur IA, il faut accepter la licence FLUX.1 [dev]. Sinon, décoche « Télécharger et installer le moteur IA » : Chrypix s'installera sans lui.
french.MoteurPlace=Pas assez de place sur %1 : il faut environ %2 Go, il reste %3 Go. Choisis un autre dossier.
french.MoteurLancer=Télécharger et installer le moteur IA maintenant
french.DesinstMoteur=Supprimer aussi le moteur IA installé par Chrypix (ComfyUI, ses extensions et les modèles d'IA, environ 20 à 32 Go) ?%n%n%1%n%nNon : il reste sur le PC et resservira si tu réinstalles Chrypix.
french.DesinstReglages=Supprimer aussi les réglages de Chrypix (langue, thème, dernier dossier, style de texte, dossier du moteur) et ses journaux ?%n%nNon : ils resserviront si tu réinstalles Chrypix.
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
english.PageMoteurTitre=AI engine
english.PageMoteurDescription=The AI engine is not on this PC: Chrypix can download and install it.
english.MoteurIntro=The AI actions (Erase, Fill, Expand, Upscale) use ComfyUI, hidden behind Chrypix's buttons. Everything comes from the official sites (GitHub, Hugging Face); the download runs after the installation, in a window showing its progress. It can be stopped and resumed later (AI menu > Install the AI engine).
english.MoteurCase=Download and install the AI engine after installing Chrypix
english.MoteurDossier=AI engine folder:
english.MoteurListe=ComfyUI portable 0.44 (the engine) — 1.9 GB — GitHub — GPL-3.0%nExtensions Inpaint nodes, Crop and Stitch, Ultimate SD Upscale, GGUF — under 5 MB — GitHub — GPL-3.0, Apache-2.0%nFlux Fill, GGUF Q8 version (erase, fill, expand) — 11.9 GB — Hugging Face — FLUX.1 [dev] non-commercial%nT5 and CLIP text encoders — 5.0 GB — Hugging Face — Apache-2.0%nImage decoder (VAE) — 0.3 GB — Hugging Face — Apache-2.0%nLaMa (erase) — 0.2 GB — GitHub — Apache-2.0%nRealESRGAN x4 (upscale) — 64 MB — GitHub — BSD-3-Clause%n7-Zip (to unpack) — 0.6 MB — GitHub — LGPL-2.1%nTotal: 19.4 GB to download, about 28 GB on disk.
english.MoteurSchnell=Add Flux Schnell for "Sharp upscale" (11.8 GB more, optional; the simple upscale works without it)
english.MoteurLicence=Flux Fill is under the FLUX.1 [dev] non-commercial licence: personal use allowed, no commercial use.
english.MoteurLien=Read the FLUX.1 [dev] licence
english.MoteurAccepte=I accept the FLUX.1 [dev] licence (non-commercial use)
english.MoteurPasAccepte=To install the AI engine, you must accept the FLUX.1 [dev] licence. Otherwise, untick "Download and install the AI engine": Chrypix will install without it.
english.MoteurPlace=Not enough space on %1: about %2 GB is needed, %3 GB is left. Choose another folder.
english.MoteurLancer=Download and install the AI engine now
english.DesinstMoteur=Also delete the AI engine installed by Chrypix (ComfyUI, its extensions and the AI models, about 20 to 32 GB)?%n%n%1%n%nNo: it stays on the PC and will be reused if you reinstall Chrypix.
english.DesinstReglages=Also delete Chrypix's settings (language, theme, last folder, text style, engine folder) and its logs?%n%nNo: they will be reused if you reinstall Chrypix.

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
; Moteur IA absent et licence acceptée : le téléchargeur démarre (Chrypix sera lancé ensuite par l'utilisateur).
Filename: "{app}\python\pythonw.exe"; Parameters: "{code:ParamsMoteur}"; WorkingDir: "{app}"; Description: "{cm:MoteurLancer}"; Check: InstallerMoteur; Flags: nowait postinstall skipifsilent runasoriginaluser
Filename: "{app}\python\pythonw.exe"; Parameters: "-m chrypix"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,Chrypix}"; Check: not InstallerMoteur; Flags: nowait postinstall skipifsilent runasoriginaluser

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
  PageMoteur: TWizardPage;
  CaseMoteur, CaseSchnell, CaseLicence: TNewCheckBox;
  EditMoteur: TNewEdit;
  MoteurAbsent: Boolean;        { ComfyUI introuvable au moment de la page Moteur IA }
  SupprimerMoteur, SupprimerReglages: Boolean;
  DossierMoteurU: String;

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

{ ---------------------------------------------------------------- page « Moteur IA » (ComfyUI absent) }
procedure MoteurCaseClic(Sender: TObject);
begin
  EditMoteur.Enabled := CaseMoteur.Checked;
  CaseSchnell.Enabled := CaseMoteur.Checked;
  CaseLicence.Enabled := CaseMoteur.Checked;
end;

procedure MoteurParcourirClic(Sender: TObject);
var
  D: String;
begin
  D := EditMoteur.Text;
  if BrowseForFolder(CustomMessage('MoteurDossier'), D, True) then
    EditMoteur.Text := D;
end;

procedure LicenceClic(Sender: TObject);
var
  Code: Integer;
begin
  ShellExec('open', 'https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md', '', '', SW_SHOWNORMAL,
    ewNoWait, Code);
end;

procedure CreerPageMoteur;
var
  Intro, Etiquette, Licence, Lien: TNewStaticText;
  Liste: TNewMemo;
  Bouton: TNewButton;
  Y: Integer;
begin
  PageMoteur := CreateCustomPage(PagePC.ID, CustomMessage('PageMoteurTitre'), CustomMessage('PageMoteurDescription'));
  Intro := Texte(PageMoteur, 0);
  Intro.Caption := CustomMessage('MoteurIntro');
  Intro.Height := ScaleY(56);

  CaseMoteur := TNewCheckBox.Create(PageMoteur);
  CaseMoteur.Parent := PageMoteur.Surface;
  CaseMoteur.Top := Intro.Top + Intro.Height + ScaleY(4);
  CaseMoteur.Width := PageMoteur.SurfaceWidth;
  CaseMoteur.Height := ScaleY(18);
  CaseMoteur.Caption := CustomMessage('MoteurCase');
  CaseMoteur.Font.Style := [fsBold];
  CaseMoteur.Checked := True;
  CaseMoteur.OnClick := @MoteurCaseClic;

  Y := CaseMoteur.Top + CaseMoteur.Height + ScaleY(6);
  Etiquette := Texte(PageMoteur, Y + ScaleY(3));
  Etiquette.Caption := CustomMessage('MoteurDossier');
  Etiquette.AutoSize := True;
  Etiquette.WordWrap := False;
  EditMoteur := TNewEdit.Create(PageMoteur);
  EditMoteur.Parent := PageMoteur.Surface;
  EditMoteur.Top := Y;
  EditMoteur.Left := Etiquette.Width + ScaleX(8);
  EditMoteur.Width := PageMoteur.SurfaceWidth - EditMoteur.Left - ScaleX(100);
  EditMoteur.Text := ExpandConstant('{localappdata}\Chrypix\moteur');
  Bouton := TNewButton.Create(PageMoteur);
  Bouton.Parent := PageMoteur.Surface;
  Bouton.Caption := CustomMessage('Parcourir');
  Bouton.Top := Y - ScaleY(1);
  Bouton.Left := PageMoteur.SurfaceWidth - ScaleX(92);
  Bouton.Width := ScaleX(92);
  Bouton.Height := ScaleY(23);
  Bouton.OnClick := @MoteurParcourirClic;

  Liste := TNewMemo.Create(PageMoteur);
  Liste.Parent := PageMoteur.Surface;
  Liste.Top := Y + ScaleY(28);
  Liste.Width := PageMoteur.SurfaceWidth;
  Liste.Height := ScaleY(74);
  Liste.ReadOnly := True;
  Liste.ScrollBars := ssVertical;
  Liste.WordWrap := False;
  Liste.Text := CustomMessage('MoteurListe');

  CaseSchnell := TNewCheckBox.Create(PageMoteur);
  CaseSchnell.Parent := PageMoteur.Surface;
  CaseSchnell.Top := Liste.Top + Liste.Height + ScaleY(6);
  CaseSchnell.Width := PageMoteur.SurfaceWidth;
  CaseSchnell.Height := ScaleY(18);
  CaseSchnell.Caption := CustomMessage('MoteurSchnell');

  Licence := Texte(PageMoteur, CaseSchnell.Top + CaseSchnell.Height + ScaleY(6));
  Licence.Caption := CustomMessage('MoteurLicence');
  Licence.Height := ScaleY(30);
  Lien := TNewStaticText.Create(PageMoteur);
  Lien.Parent := PageMoteur.Surface;
  Lien.Top := Licence.Top + Licence.Height;
  Lien.Caption := CustomMessage('MoteurLien');
  Lien.Font.Color := clBlue;
  Lien.Font.Style := [fsUnderline];
  Lien.Cursor := crHand;
  Lien.OnClick := @LicenceClic;

  CaseLicence := TNewCheckBox.Create(PageMoteur);
  CaseLicence.Parent := PageMoteur.Surface;
  CaseLicence.Top := Lien.Top + Lien.Height + ScaleY(6);
  CaseLicence.Width := PageMoteur.SurfaceWidth;
  CaseLicence.Height := ScaleY(18);
  CaseLicence.Caption := CustomMessage('MoteurAccepte');
  CaseLicence.Checked := False;
end;

function InstallerMoteur: Boolean;
begin
  Result := MoteurAbsent and CaseMoteur.Checked and CaseLicence.Checked;
end;

function ParamsMoteur(Param: String): String;
begin
  Result := '-m chrypix.installation_moteur --dossier "' + RemoveBackslashUnlessRoot(EditMoteur.Text) +
    '" --accepte --demarrer';
  if CaseSchnell.Checked then Result := Result + ' --schnell';
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = PageMoteur.ID then
  begin
    MoteurAbsent := TrouverComfy = '';
    Result := not MoteurAbsent;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Libre, Total: Int64;
  Lecteur: String;
  Besoin: Integer;
begin
  Result := True;
  if (CurPageID <> PageMoteur.ID) or not CaseMoteur.Checked then Exit;
  if not CaseLicence.Checked then
  begin
    MsgBox(CustomMessage('MoteurPasAccepte'), mbInformation, MB_OK);
    Result := False;
    Exit;
  end;
  Besoin := 29;
  if CaseSchnell.Checked then Besoin := 41;
  Lecteur := AddBackslash(ExtractFileDrive(EditMoteur.Text));
  if GetSpaceOnDisk64(Lecteur, Libre, Total) and (Libre div (1024 * 1024 * 1024) < Besoin) then
  begin
    MsgBox(FmtMessage(CustomMessage('MoteurPlace'), [Lecteur, IntToStr(Besoin),
      IntToStr(Libre div (1024 * 1024 * 1024))]), mbError, MB_OK);
    Result := False;
  end;
end;

{ ---------------------------------------------------------------- étapes }
procedure InitializeWizard;
begin
  StyleBanner(WizardForm.MainPanel, WizardForm.Bevel1, WizardForm.WizardSmallBitmapImage,
    WizardForm.PageNameLabel, WizardForm.PageDescriptionLabel);
  if ActiveLanguage = 'english' then
    LoadEnglishWelcomeImage;
  CreerPagePC;
  CreerPageMoteur;
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

{ ---------------------------------------------------------------- désinstallation
  Propose (réponse « Non » par défaut) de supprimer le moteur IA, seulement s'il a été installé par Chrypix
  (marque chrypix-moteur.json dans son dossier : un ComfyUI installé autrement n'est jamais touché),
  puis les réglages (registre) et les fichiers de travail (%LOCALAPPDATA%\Chrypix, thème dans %TEMP%). }
function DossierMoteurChrypix: String;
var
  D: String;
begin
  Result := '';
  if RegQueryStringValue(HKCU, 'Software\Chrypix\Chrypix', 'moteur_dossier', D) and
     FileExists(AddBackslash(D) + 'chrypix-moteur.json') then
    Result := RemoveBackslashUnlessRoot(D)
  else if FileExists(ExpandConstant('{localappdata}\Chrypix\moteur\chrypix-moteur.json')) then
    Result := ExpandConstant('{localappdata}\Chrypix\moteur');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Travail: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    DossierMoteurU := DossierMoteurChrypix;
    if not UninstallSilent then
    begin
      if DossierMoteurU <> '' then
        SupprimerMoteur := MsgBox(FmtMessage(CustomMessage('DesinstMoteur'), [DossierMoteurU]), mbConfirmation,
          MB_YESNO or MB_DEFBUTTON2) = IDYES;
      SupprimerReglages := MsgBox(CustomMessage('DesinstReglages'), mbConfirmation,
        MB_YESNO or MB_DEFBUTTON2) = IDYES;
    end;
  end;
  if CurUninstallStep = usPostUninstall then
  begin
    if SupprimerMoteur then
    begin
      DelTree(DossierMoteurU + '\ComfyUI_windows_portable', True, True, True);
      DelTree(DossierMoteurU + '\telechargements', True, True, True);
      DeleteFile(DossierMoteurU + '\chrypix-moteur.json');
      RemoveDir(DossierMoteurU);
    end;
    if SupprimerReglages then
    begin
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Chrypix');
      Travail := ExpandConstant('{localappdata}\Chrypix');
      DeleteFile(Travail + '\config.json');
      DeleteFile(Travail + '\moteur.log');
      DeleteFile(Travail + '\installation_moteur.log');
      DelTree(ExpandConstant('{%TEMP}\chrypix_theme'), True, True, True);
      RemoveDir(Travail);        { seulement s'il est vide : un moteur gardé y reste }
    end;
  end;
end;

procedure InitializeUninstallProgressForm;
begin
  StyleBanner(UninstallProgressForm.MainPanel, UninstallProgressForm.Bevel1, UninstallProgressForm.WizardSmallBitmapImage,
    UninstallProgressForm.PageNameLabel, UninstallProgressForm.PageDescriptionLabel);
end;

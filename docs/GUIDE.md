# Guide d'utilisation de Pixane

Pixane est un éditeur photo pour Windows qui retouche les images avec une IA qui tourne **sur votre PC**
(pas d'abonnement, pas d'envoi de photos sur Internet).
Ce guide explique chaque outil et chaque réglage : **à quoi il sert** et **comment s'en servir**. Il est complété
à chaque nouvelle fonction.

**Pour qui ?** Pixane est pensé pour celles et ceux qui débutent en retouche photo, ou qui en ont peu l'expérience : les outils vont à l'essentiel, l'IA se charge du travail difficile et l'aide explique chaque réglage pas à pas. Pour un travail professionnel poussé, des logiciels comme Photoshop restent la référence ; Pixane, lui, veut rendre la retouche accessible à tous.

## Avant de commencer : une IA 100 % sur votre PC

- **Aucune IA en ligne.** Toutes les actions IA de Pixane (Effacer, Remplir, Agrandir, Upscale, sélection d'objet,
  arrière-plan, réduction du bruit, netteté, restauration…) tournent **sur votre ordinateur**, avec des modèles
  installés sur votre disque. **Aucune photo n'est envoyée sur Internet** ; pas de compte, pas d'abonnement, pas de
  limite d'utilisation. Internet sert seulement à télécharger le moteur IA une fois (et ses mises à jour, si vous
  les acceptez). Ensuite, Pixane marche même sans connexion.
- **La vitesse dépend de votre PC, surtout de la carte graphique** : c'est elle qui fait les calculs de l'IA. **Plus
  elle est puissante et plus elle a de mémoire, plus les traitements vont vite.** Une carte récente avec 12, 16 ou
  24 Go de mémoire va nettement plus vite que celle du PC d'essai ; une carte plus modeste, plus lentement. La
  mémoire vive (RAM) compte aussi : quand la carte graphique manque de mémoire, une partie du modèle passe par la RAM,
  ce qui ralentit.
- **Durées mesurées** sur le PC d'essai (NVIDIA RTX 3060 Ti 8 Go, 32 Go de mémoire vive) :

| Action | Durée |
|---|---|
| Démarrage du moteur IA (à l'ouverture de Pixane) | environ 20 secondes |
| Sélection d'objet, sélection rapide | environ 1 seconde |
| Supprimer l'arrière-plan, sélectionner le sujet, outil Supprimer (J), Réduire le bruit | quelques secondes |
| Netteté (IA) | 15 à 20 secondes |
| Remplir, Agrandir l'image | environ 1 minute par proposition |
| Effacer | environ 2 minutes |
| Upscale net | 20 à 30 secondes par morceau de 1024 px |
| Restaurer une vieille photo | environ 2 minutes par proposition |

La première utilisation d'un modèle après le démarrage est un peu plus longue (il se charge en mémoire).

### Configuration

| | Minimum | Conseillé |
|---|---|---|
| **Système** | Windows 10 ou 11, 64 bits | Windows 11, 64 bits |
| **Carte graphique** | NVIDIA, **8 Go** de mémoire (par exemple RTX 3060 Ti, 3070, 4060) | NVIDIA RTX, **12 Go ou plus** (par exemple RTX 3060 12 Go, 4070, 4080, 4090) |
| **Mémoire vive** | 16 Go (les actions Flux sont alors lentes) | **32 Go** |
| **Disque** | 35 Go libres pour le moteur IA | 60 Go libres (avec Flux Schnell et Flux Kontext), sur un SSD |
| **Processeur** | 4 cœurs récent | 6 cœurs ou plus |

Pixane a été testé sur une **RTX 3060 Ti (8 Go) avec 32 Go de mémoire vive**. Le minimum est une estimation : il
n'a pas été essayé sur d'autres PC. **Sans carte NVIDIA** (carte AMD ou Intel, PC portable sans carte graphique),
Pixane s'ouvre et retouche normalement (calques, texte, réglages, filtres, export…), mais les actions IA ne
marchent pas.

---

## 1. La fenêtre

| Zone | Rôle |
|---|---|
| **Barre du haut** | Ouvrir, Enregistrer, Annuler / Rétablir, réglages de l'outil choisi (taille, Nouvelle / Ajouter / Retirer…), zoom |
| **Outils (à gauche)** | Main, Déplacer, outils de sélection, outils de retouche, Recadrer, Texte. Un petit triangle sur un bouton = plusieurs outils : **clic droit** (ou clic maintenu) pour choisir |
| **Panneau « Texte » (à gauche)** | Réglages du texte, visible avec l'outil Texte (voir chapitre 7) |
| **Onglets (au-dessus de la photo)** | Un onglet par photo ouverte (dès qu'il y en a deux) ; un point « • » marque une photo modifiée |
| **Règles** | En haut et à gauche de la photo, en pixels (Affichage > Règles, Ctrl+R) |
| **Photo (au centre)** | La photo ; la zone sélectionnée apparaît en rouge transparent |
| **Panneau « Intelligence artificielle » (à droite)** | Effacer, Remplir, Agrandir l'image, Upscale |
| **Panneau « Calques » (à droite, en dessous)** | Les calques de l'image (voir chapitre 6) ; onglet **Historique** à côté |
| **Barre d'état (en bas)** | État du moteur IA (point de couleur), taille de la photo |

**Couleurs** : Pixane prend la couleur d'accent choisie dans Windows (Paramètres > Personnalisation > Couleurs)
et suit le mode clair / sombre de Windows. Menu **Affichage > Thème** : *Comme Windows*, *Clair* ou *Sombre*.
Le bouton soleil / lune de la barre du haut bascule aussi entre clair et sombre.

**Langue** : Pixane existe en **français** et en **anglais**. Par défaut, il prend la langue de Windows
(français si Windows est en français, anglais sinon). Menu **Affichage > Langue** : *Comme Windows*, *Français*
ou *English* ; Pixane propose alors de redémarrer pour appliquer la langue (le moteur IA redémarre aussi,
environ 20 secondes). Les boutons standard (Oui / Non / Annuler, menu clic droit) suivent la même langue.
Les noms de calques déjà créés gardent leur langue d'origine. Guide en anglais : `docs\GUIDE_en.md`.

**Moteur IA** : au démarrage, Pixane lance l'IA (ComfyUI) en arrière-plan, sans fenêtre. Comptez environ
20 secondes. Le point en bas à gauche passe au vert quand le moteur est prêt ; les actions IA sont grisées avant.

---

## 2. Ouvrir et enregistrer

- **Fichier > Ouvrir** (Ctrl+O) : JPG, PNG, TIFF, WebP, BMP, et les fichiers à calques **.pixane**, **.ora** et
  **.psd** (Photoshop).
  La photo est redressée selon son orientation d'appareil.
- **Enregistrer** (Ctrl+S), **Enregistrer sous** (Ctrl+Maj+S) :
  - **.pixane** (projet Pixane) : le format de Pixane. Garde **tout** : calques (noms, ordre, visibilité, opacité,
    verrou), **textes modifiables** et **styles de calque modifiables**. Proposé d'office quand l'image a plusieurs calques ou un texte.
  - **.ora** (OpenRaster) : pour **partager avec Krita ou GIMP** (format ouvert). Garde les calques, mais les
    textes y deviennent des images.
  - Bon à savoir : un .pixane est construit comme un .ora ; renommé en .ora, il s'ouvre aussi dans Krita ou GIMP.
  - **.psd** (Photoshop) : pour **travailler avec Photoshop**. Garde les calques (noms, ordre, visibilité,
    opacité, verrou) ; les textes y deviennent des images. Une photo ouverte depuis un PSD est proposée en PSD.
  - **PSD ouverts dans Pixane** : RVB ou niveaux de gris, 8 ou 16 bits, avec les calques, les **groupes**, les
    **masques de calque**, les **modes de fusion** et les **styles** (ombre portée et interne, lueurs, contour,
    biseau, incrustations couleur et dégradé), qui restent modifiables. Pixane ne reproduit pas les calques de
    réglage de Photoshop, les masques d'écrêtage, ni les groupes en mode « traverser » (ouverts en mode Normal) :
    un message le signale à l'ouverture, car l'aspect peut alors différer. Un PSD en CMJN s'ouvre aplati (un seul
    calque). Les grands documents .psb ne sont pas pris en charge.
  - **PSD enregistrés par Pixane** : calques, groupes, masques et modes de fusion sont gardés ; les styles sont mis
    dans les pixels ; un calque de réglage devient un calque d'image (le résultat du réglage).
  - **JPG** (qualité 95), **PNG**, **TIFF**, **WebP** : l'image **à plat** (ce que vous voyez, calques fusionnés).
    Un message le rappelle si l'image a plusieurs calques.
  Les informations de l'appareil (EXIF) et le profil de couleur sont conservés.
- **Annuler** (Ctrl+Z) / **Rétablir** (Ctrl+Y ou Ctrl+Maj+Z) : chaque retouche et chaque sélection peut être annulée
  (30 étapes).
- **Panneau Historique** (onglet à côté de « Calques ») : la liste des étapes. Un clic sur une étape revient à ce
  moment-là ; un clic sur une étape plus bas refait les suivantes. Une nouvelle retouche efface les étapes « en avance ».
- **Fichier > Fichiers récents** : les 10 dernières images ouvertes ou enregistrées (*Effacer la liste* pour la vider).
- **Plusieurs photos à la fois** : *Ouvrir* accepte plusieurs fichiers d'un coup (Ctrl+clic ou Maj+clic dans la
  fenêtre), et on peut en glisser plusieurs sur Pixane. Chaque photo a son **onglet** et son propre **Annuler**
  (Ctrl+Z ne touche que la photo affichée). Changer de photo : clic sur l'onglet, **Ctrl+Tab** / **Ctrl+Maj+Tab**.
  **Fichier > Fermer la photo** (Ctrl+W, ou la croix de l'onglet) demande d'enregistrer si besoin. Rouvrir une photo
  déjà ouverte revient simplement à son onglet.
- **Enregistrement automatique** : toutes les 3 minutes, chaque photo modifiée est copiée (calques, textes, styles,
  masques compris) dans `%LOCALAPPDATA%\Pixane\recuperation`, sans ralentir le travail. Si Pixane se ferme mal
  (plantage, coupure de courant), il propose au démarrage suivant de **rouvrir ces copies** ; elles s'ouvrent
  « à enregistrer », avec le nom du fichier d'origine. Les copies sont effacées quand la photo est enregistrée ou
  fermée, et quand Pixane se ferme normalement.
- **En cas d'erreur** : si une commande échoue, Pixane l'affiche et la note dans
  `%LOCALAPPDATA%\Pixane\erreurs.log` (utile pour signaler le problème).
- **Fichier > Exporter sous…** (Ctrl+Alt+Maj+W) : une copie **pour un envoi normal** (imprimeur, ami, clé USB) :
  pleine taille, pleine qualité, résolution, profil de couleur et informations de l'appareil photo gardés. JPEG, PNG
  (avec la transparence), TIFF ou WebP. La photo ouverte ne change pas (elle reste à enregistrer si elle a été
  modifiée) ; Pixane ne propose jamais d'écraser la photo d'origine et retient le dernier format choisi.
- **Fichier > Exporter pour le web…** (Ctrl+Alt+Maj+S) : une copie légère pour Internet, sans toucher à la photo.
  - **Format** : JPEG (photos), **WebP** (plus léger à qualité égale, garde la transparence), PNG (sans perte).
  - **Réduire : plus grand côté** (par exemple 2048 px) ; jamais agrandie.
  - **Qualité** (30 à 100 ; 80 environ suffit pour le web).
  - Le **poids du fichier** s'affiche en direct.
  - Les informations de l'appareil (EXIF : modèle, date, parfois le lieu) sont **enlevées** par défaut (case pour
    les garder). Nom proposé : `<photo>_web.jpg`.
- **Fichier > Traitement par lot…** : le même travail sur **tout un dossier** de photos.
  - **Photos à traiter** (dossier d'origine, jamais modifié) et **Résultats dans** (un autre dossier).
  - Au choix : **Réduire** (plus grand côté), **Réglage automatique** (luminosité, contraste, température, comme
    le bouton Auto), **Upscale IA ×2** (RealESRGAN), **Supprimer l'arrière-plan** (résultats en PNG transparent),
    **Format** (garder, JPEG, WebP, PNG) et qualité, **Ajouter au nom** (ex. `_web`).
  - Une barre montre l'avancement ; **Arrêter** termine la photo en cours puis s'arrête. Une photo qui pose
    problème est signalée à la fin, les autres sont faites.
  - Sécurité : si les résultats iraient dans le même dossier sous le même nom, Pixane refuse (les originaux
    seraient remplacés).
- **Fichier > Nouvelle image…** (Ctrl+N) : une image vide, comme dans Photoshop.
  - **Formats tout prêts** (à gauche) : **pochettes** (CD, vinyle 33 et 45 tours, 3000 × 3000 px pour Spotify,
    Deezer, Apple Music), **livres** (poche, roman, Amazon KDP, livre numérique), **réseaux sociaux** (Instagram,
    Story, Facebook, YouTube, X), **impression** (A3, A4, A5, photos, affiches, carte de visite, flyer), **écran**
    (HD, Full HD, 4K). **Enregistrer ce format…** garde vos propres formats dans **Mes formats** (taille, unité, résolution, fond perdu, zone de sécurité, mode et fond) ; le dernier format
    utilisé est proposé la fois suivante.
  - **Largeur, hauteur et unité** : pixels, pouces, centimètres, millimètres, points ou picas (1 pouce = 2,54 cm
    = 72 points = 6 picas). Changer d'unité ne change pas l'image.
  - **Orientation** : Portrait ou Paysage échange largeur et hauteur.
  - **Résolution** (ppp, points par pouce) : **300** pour l'impression, **72** pour l'écran. Elle est **gardée dans
    le fichier** (.pixane, PSD, JPEG, PNG, TIFF) : un imprimeur verra la bonne taille.
  - **Mode** : couleurs RVB ou **niveaux de gris** (voir *Image > Mode*). Pixane travaille en **8 bits par couche**
    (16,7 millions de couleurs, comme le JPEG, le PNG et le web) ; le 16 et le 32 bits sont prévus plus tard.
  - **Fond** : blanc, transparent, noir ou une couleur au choix.
  - **Fond perdu** (impression) : bande ajoutée tout autour, coupée par l'imprimeur (en général 3 mm) : le fond doit
    aller jusqu'au bord de l'image. **Zone de sécurité** : marge à l'intérieur du format fini où ne mettre rien
    d'important (texte, visage). Des **repères** sont posés tout seuls sur ces deux lignes.
  - En bas : la taille en pixels, la taille imprimée et la mémoire utilisée.
- **Fichier > Exporter pour l'impression (CMJN)…** : pour un imprimeur qui demande du CMJN (les quatre encres).
  Pixane travaille en RVB et convertit au moment d'exporter, comme le conseillent les imprimeurs.
  - **Format** : TIFF (le plus sûr), PDF ou JPEG.
  - **Profil CMJN** : ceux installés dans Windows, rien à télécharger. Demandez celui de votre imprimeur ; en Europe,
    c'est souvent **Coated FOGRA39** (papier couché).
  - **Intention de rendu** : *Perceptive* pour les photos, *Colorimétrie relative* pour les logos et les aplats.
    **Compensation du point noir** : cochée, les ombres gardent leurs détails.
  - La **résolution** est notée dans le fichier ; la photo n'est pas modifiée (nom proposé : `<photo>_cmjn.tif`).
  - Avant d'exporter : **Affichage > Aperçu de l'impression (CMJN)** (Ctrl+Alt+Y) montre à l'écran les couleurs
    telles qu'elles sortiront (les bleus et les verts très vifs ternissent souvent). Le recliquer revient à l'écran
    normal ; l'image n'est jamais modifiée.
- **Fichier > Nouvelle image depuis le presse-papiers** (Ctrl+Alt+V) : ouvre l'image copiée (capture d'écran, autre
  logiciel…). **Ctrl+V** sans photo ouverte fait la même chose.

---

## 3. Se déplacer dans la photo

| Action | Comment |
|---|---|
| Zoomer | Molette (autour du curseur), Ctrl++ / Ctrl+-, boutons loupe |
| Ajuster à la fenêtre | Ctrl+0 |
| Taille réelle (100 %) | Ctrl+1 |
| Déplacer la vue | Outil **Main** (H), ou maintenir **Espace** et glisser, ou glisser avec le **bouton du milieu** |
| Déplacer **un calque** | Outil **Déplacer** (V) : seul le calque choisi bouge (la Main, elle, ne déplace que la vue) |

### Règles, repères et grille (menu Affichage)
- **Règles** (Ctrl+R) : graduées en pixels de l'image, le 0 au coin haut-gauche de la photo ; un trait suit la
  souris.
- **Repères** : glissez depuis une règle vers la photo pour poser une ligne bleue (horizontale depuis la règle du
  haut, verticale depuis celle de gauche). Avec l'outil **Déplacer** (V), attrapez un repère pour le bouger (le
  curseur devient une double flèche au-dessus) ; tiré hors de la photo, il disparaît. *Nouveau repère…* le pose à une position exacte, *Effacer les repères* les enlève tous,
  Ctrl+; les cache ou les montre. Ils sont gardés dans le fichier .pixane.
- **Grille** (Ctrl+') : lignes régulières sur la photo ; *Taille de la grille…* règle l'écart (100 px par défaut).
- **Magnétisme** (Ctrl+Maj+;, coché par défaut) : la sélection rectangle, le dégradé et les formes s'accrochent aux
  repères, aux bords de la photo et à la grille (si elle est affichée), à moins de 8 pixels d'écran.

---

## 4. Sélectionner (dire à l'IA où travailler)

La zone sélectionnée apparaît en **rouge transparent**. Il n'est pas nécessaire d'« entourer » un objet :
on peut simplement **peindre dessus**.

Les outils de sélection sont rangés sous **deux boutons** de la barre de gauche (petit triangle) : les outils
« à la main » et les outils « automatiques ». **Clic droit** sur le bouton, ou clic maintenu, pour choisir ; ou
directement leur touche.

| Outil | Touche | Usage |
|---|---|---|
| **Rectangle** | M | Sélection rectangulaire |
| **Lasso** | L | Tracer un contour à main levée, bouton appuyé ; la forme est fermée automatiquement |
| **Pinceau de sélection** | B | Peindre la zone. Idéal pour un objet, un texte, un fil… |
| **Gomme de sélection** | E | Retirer de la sélection en peignant |
| **Sélection d'objet** (IA) | O | Tirer un cadre autour d'un objet, ou cliquer dessus : l'IA le détoure |
| **Sélection rapide** (IA) | Q | Peindre grossièrement sur l'objet : l'IA trouve ses contours |
| **Baguette magique** | W | Un clic sur une couleur : toute la zone de couleur proche (sans IA) |

- **Rectangle et lasso**, comme dans Photoshop : une nouvelle sélection **remplace** l'ancienne. Maintenir **Maj** en
  commençant le tracé **ajoute** à la sélection, **Alt** **retire**. Un simple clic sans tracer **désélectionne**.
  Les pastilles **Nouvelle / Ajouter / Retirer** de la barre du haut choisissent le mode sans touche.
- **Pinceau de sélection** : il ajoute toujours à la sélection ; pastille **Retirer** ou **Alt** maintenu : il retire
  (comme la gomme de sélection).
- **Taille du pinceau** : curseur « Taille » de la barre du haut, ou touches `[` et `]`.
- Menu **Sélection** : *Tout sélectionner* (Ctrl+A), *Désélectionner* (Ctrl+D), *Inverser* (Ctrl+Maj+I).
- **Flèches du clavier** (avec un outil de sélection : rectangle, lasso, pinceau de sélection, baguette, sélection
  rapide ou d'objet) : la sélection bouge de **1 pixel** (Maj : **10 pixels**). Seul le contour bouge, pas l'image ;
  un seul Ctrl+Z annule tous les appuis.
- **Sélection > Modifier la sélection** : *Agrandir…* ou *Réduire…* d'un nombre de pixels, *Adoucir les bords…*
  (bord progressif, utile pour les réglages de l'image).
- **Sélection > Sélectionner le sujet (IA)** (Ctrl+Alt+S) : l'IA trouve le sujet principal (personne, animal,
  objet) et le sélectionne. Voir chapitre 5, « Sujet et arrière-plan ».

### Sélection d'objet et sélection rapide (IA)
Elles utilisent le modèle **SAM 3.1** de Meta (1,6 Go, installé avec le moteur IA). L'IA comprend l'**objet entier**
(une personne, une voiture, un meuble…), même quand ses couleurs varient, et suit ses vrais contours. Environ une
seconde par demande (quelques secondes la première fois).
- **Sélection d'objet (O)** : tirer un **cadre** autour de l'objet, ou **cliquer** dessus. Comme le rectangle : la
  nouvelle sélection remplace l'ancienne ; **Maj** ajoute, **Alt** retire (ou les pastilles Nouvelle / Ajouter /
  Retirer).
- **Sélection rapide (Q)** : **peindre** grossièrement sur l'objet (dessus, ou en
  suivant son contour). Comme dans Photoshop, chaque trait trouve **son** objet, qui s'**ajoute** à la sélection : un
  trait sur un titre puis un trait autour d'une personne donnent le titre + la personne entière. Des points verts
  montrent ce que l'IA doit garder. **Alt + peindre** sur une partie à enlever (points rouges) : l'IA corrige les
  objets déjà trouvés. Une sélection vidée (Ctrl+D) ou changée par un autre outil fait repartir de zéro ; **Échap**
  aussi.
- Ctrl+Z annule chaque étape. Le résultat se règle ensuite avec *Modifier la sélection* (agrandir, adoucir…).

### Baguette magique (W)
Un clic sur une couleur sélectionne la zone de couleur proche. Sans IA, instantané.
- **Régler en glissant** : après le clic, **garder le bouton appuyé et glisser à droite** (plus large) **ou à gauche**
  (plus étroit) : la sélection suit en direct. La tolérance trouvée reste pour le clic suivant.
- **Tolérance** (0 à 255, 32 par défaut) : écart de couleur accepté. Les couleurs sont comparées comme l'œil les
  voit, et la couleur de départ est prise sur 3 × 3 pixels : le bruit d'une photo gêne moins.
- **Contiguë** (coché) : seulement la zone touchée ; décoché : toutes les couleurs proches de l'image.
- **Bords doux** (coché) : bord progressif, sans escalier.
- **Boucher les trous** : ajoute ce qui est entièrement entouré (oiseaux dans un ciel, reflets sur un objet…).
- **Image visible** ou **Calque choisi** : sur quoi les couleurs sont comparées.
- Maj ajoute, Alt retire, comme le rectangle.

### Améliorer le contour (Ctrl+Alt+R, menu Sélection)
Pour une sélection grossière autour de **cheveux, poils, feuillage ou bords flous** (par exemple après *Sélectionner
le sujet* ou un lasso rapide) : Pixane recalcule le bord d'après les couleurs de la photo.
- **Rayon** : largeur de la bande recalculée autour du bord. Augmentez-le jusqu'à ce que les mèches apparaissent ;
  hors de cette bande, rien ne change.
- **Lissage** : adoucit un bord irrégulier. **Contraste du bord** : bord plus net. **Décaler le bord** : négatif le
  rentre (enlève un liseré de l'ancien fond), positif le sort.
- **Voir** : le sujet **sur noir**, **sur blanc**, le masque en **noir et blanc**, ou la sélection en rouge.
  Choisissez un fond qui contraste avec l'ancien fond pour bien juger les bords.
- **Résultat** : une **nouvelle sélection**, ou le **masque du calque choisi** (le fond est alors caché sans être
  effacé, voir *Masques de calque*).
Une seule étape dans Annuler. Le calcul prend une à trois secondes sur une grande photo.

### Couper, copier, coller, supprimer (menu Édition)
Ils agissent sur le **calque choisi** dans le panneau Calques :
- **Copier** (Ctrl+C) : copie ce qui est sélectionné (tout le calque s'il n'y a pas de sélection). La copie garde sa
  transparence ; on peut aussi la coller dans un autre logiciel.
- **Couper** (Ctrl+X) : copie, puis efface la zone sélectionnée (elle devient transparente).
- **Coller** (Ctrl+V) : met l'image copiée dans un **nouveau calque**, à **la même place** si elle vient de Pixane,
  au centre si elle vient d'ailleurs (capture d'écran, autre logiciel…). Bougez-la ensuite avec l'outil Déplacer (V).
  Pour l'agrandir ou la réduire : **Ctrl+T** (voir *Transformer le calque*).
  - **Image plus grande que la photo** : elle arrive **réduite pour tenir entière**, avec le cadre *Transformer*
    déjà ouvert. Ajustez sa taille et sa place, puis **Entrée**. Rien n'est jamais coupé : ce qui dépasse de la
    feuille est gardé dans le calque (voir *Pixels hors de la feuille*).
- **Supprimer la sélection** (Suppr) : efface la zone sélectionnée du calque (transparente).

Un calque **verrouillé** est protégé ; un **texte** coupé ou supprimé devient une image. Ctrl+Z annule tout.

Les autres outils : **Déplacer** (V) bouge le contenu du **calque choisi** (un texte déplacé reste modifiable ; ce qui
sort de la feuille est gardé, on peut le faire revenir ; refusé sur un calque verrouillé).
- Un **cadre à poignées** entoure ce qu'il y a sur le calque (ou seulement la partie sélectionnée, s'il y a une
  sélection) : **glisser au milieu** déplace ; **un coin** change la taille en gardant les proportions (Maj : libre) ;
  **un milieu de côté**, seulement la largeur ou la hauteur ; **juste à l'extérieur d'un coin** (curseur en croix),
  on tourne. Dès qu'une poignée est touchée, c'est le mode *Transformer* (comme Ctrl+T) : **Entrée** pour garder,
  **Échap** pour annuler.
- La case **Afficher le cadre de transformation** (en haut) le cache s'il gêne. Pas de cadre sur un calque vide,
  verrouillé, caché ou de texte (un texte change de taille avec l'outil Texte).

La **Gomme de calque** (G) efface **pour de vrai** les
pixels du calque choisi (voir chapitre 6) ; elle est rangée avec le pinceau de couleur et le tampon.

**Conseil (texte, cursive, objet fin)** : couvrez bien chaque lettre, bords compris, avec un pinceau un peu plus large
que le trait ; n'oubliez pas l'ombre ou le contour s'il y en a. Pixane élargit déjà un peu la zone (environ 16 px)
pour attraper les bords flous.

---

## 5. Les actions IA

Chaque action propose **plusieurs résultats** : on choisit le meilleur, comme dans Photoshop.
Le résultat gardé arrive sur un **nouveau calque** (« Effacer 1 », « Remplir 2 »…) : la photo d'origine n'est
jamais abîmée. L'IA travaille toujours sur l'image **telle qu'on la voit** (tous les calques visibles ensemble).

### Fenêtre de choix du résultat
- Cliquez sur une vignette pour la voir en grand.
- **Maintenir pour voir l'original** : tant que le bouton est enfoncé, la photo d'avant s'affiche.
- **Autres propositions** : relance l'IA pour de nouvelles versions (elles s'ajoutent aux précédentes).
- **Garder ce résultat** : applique la version choisie (annulable par Ctrl+Z). La sélection (pinceau, lasso,
  rectangle) disparaît alors ; Ctrl+Z la fait revenir avec la photo d'avant.

### Pendant le calcul
Une fenêtre affiche l'étape en cours, une **barre de progression**, le temps écoulé et le **temps restant estimé**.
**Annuler** arrête le calcul.

### Effacer (Maj+E)
Enlève ce qui est peint en rouge et reconstruit le fond.
- Deux méthodes combinées : **LaMa** (rapide, efface proprement) puis une finition par **Flux Fill** (plus réaliste).
- Résultats proposés : 2 versions Flux + la version « LaMa seul ».
- Marche aussi sur une sélection fine (lettres prises à la baguette magique) : tout pixel touché par la sélection est
  effacé, même sur un bord adouci.
- Durée indicative : environ 2 minutes (carte graphique 8 Go).

### Remplir (Maj+R)
Redessine la zone peinte en rouge.
- **Sans texte** (recommandé) : l'IA invente ce qui va bien avec le reste de la photo. Elle part du fond nettoyé
  par LaMa : même près d'un titre, elle ne réinvente pas de lettres.
- **Avec un texte** (champ « Texte facultatif », en anglais de préférence) : décrit ce qu'on veut voir à la place.
- 3 propositions, environ 1 minute chacune.

### Agrandir l'image (Maj+A)
Étend la photo au-delà de ses bords : l'IA invente la suite du décor.

Deux cadres apparaissent sur la photo :

| Cadre | Aspect | Rôle |
|---|---|---|
| **Cadre d'agrandissement** | pointillés blancs, **poignées carrées** couleur d'accent | Tirez-le **vers l'extérieur** : la zone ajoutée s'affiche en damier gris |
| **Cadre « bord abîmé »** | pointillés **rouges**, **poignées rondes** rouges | Tirez-le **vers l'intérieur** : la bande hachurée rouge est un bord abîmé (liseré, trait, flou, coin déchiré…) qui sera **jeté puis redessiné** par l'IA |

- Quand les deux cadres sont l'un sur l'autre (au départ), le **sens du geste** décide : vers l'extérieur = agrandir,
  vers l'intérieur = bord abîmé.
- **Maj** en tirant : le côté opposé bouge pareil (agrandir à gauche et à droite en même temps, par exemple).
- **Détection automatique** : à l'ouverture, Pixane repère les liserés clairs ou foncés (1 à 8 px) que beaucoup
  d'images ont sur leurs bords, et place déjà le cadre rouge dessus. Vous pouvez l'ajuster ou le remettre à 0.
- **Barre en haut de la photo** :
  - ligne **Agrandir** : ce qui est ajouté de chaque côté, en % de la photo (0 à 200 %) ;
  - ligne **Bord abîmé** : la bande à refaire de chaque côté, en pixels ;
  - **taille finale** de l'image ;
  - **Lancer** (ou Entrée) / **Annuler** (ou Échap).
  Les cases et les cadres se suivent : modifier l'un met l'autre à jour.
- **Taille finale** = photo d'origine + agrandissement. Le bord abîmé ne réduit pas l'image : il est remplacé.
- Le raccord entre la photo et l'ajout est fait par Pixane : la photo d'origine est gardée **au pixel près**, avec un
  fondu progressif et un accord des couleurs, pour qu'aucune ligne ne soit visible.
- 3 propositions, environ 1 minute chacune.
- **Pleine définition** (case dans la barre, cochée par défaut) : l'IA invente l'ajout sur une image réduite à
  environ 1 million de pixels, puis l'ajout est agrandi à la taille de la photo ; sur une grande photo, il serait
  donc plus flou que le reste. Avec la case cochée, une fois la proposition choisie, l'ajout est **redessiné à la
  vraie taille**, par morceaux de 1024 px, en gardant sa forme : il devient aussi net et détaillé que la photo, et
  reçoit le **même grain**. Plus long : environ 30 s à 1 min par morceau (la fenêtre d'attente montre « Morceau 2
  sur 6 » et le temps restant). **Annuler** pendant ce travail garde la proposition telle quelle. Sans effet sur une
  petite photo (déjà travaillée à sa vraie taille).
- **Conseils** pour un ajout réaliste : agrandir par petites étapes (20 à 30 % à la fois) plutôt que 100 % d'un
  coup ; comparer les propositions (« Autres propositions ») ; marquer en bord abîmé un liseré ou un cadre.
- **Calques** : tous les calques sont décalés sur la nouvelle toile ; un calque « Agrandir 1 » contient l'ajout
  et le bord refait (seulement les pixels nouveaux).
- Si la photo contient du texte, l'IA invente parfois des lettres sans sens dans l'ajout : utilisez
  « Autres propositions ».

### Upscale (Maj+U)
Augmente la définition (nombre de pixels) de la photo.

| Réglage | Valeurs | Effet |
|---|---|---|
| **Net** | par défaut | RealESRGAN agrandit, puis **Flux redessine les détails** morceau par morceau. Plus lent (environ 20 à 30 s par morceau de 1024 px) mais net |
| **Rapide** | | RealESRGAN seul : quelques secondes, mais peut donner un aspect lissé (« plastique ») |
| **Facteur** | ×1,5 à ×4 (×2 par défaut) | Combien de fois plus grand |
| **Force** (mode Net) | 0,10 à 0,60 (0,35 par défaut) | Liberté laissée à Flux : bas = fidèle à l'original, haut = plus de détails inventés |

La fenêtre indique la taille finale avant de lancer ; pendant le calcul, la progression compte les morceaux.

**Calques** : tous les calques sont agrandis (lissage simple) et le résultat de l'IA arrive, complet, sur un
calque « Upscale 1 » au-dessus.

### Sujet et arrière-plan
Modèle **BiRefNet** (MIT, 444 Mo, installé avec le moteur IA ; s'il manque, menu **IA > Installer le moteur IA…**
l'ajoute). Quelques secondes.
- **Supprimer l'arrière-plan** (Maj+B, panneau IA ou menu IA) : le fond du **calque choisi** devient transparent,
  le sujet reste. Enregistrez en PNG, PSD ou .pixane pour garder la transparence. Ctrl+Z annule.
- **Sélectionner le sujet** (Ctrl+Alt+S, menu Sélection) : sélectionne le sujet sans rien effacer, par exemple
  pour le régler (Ctrl+U), ou *Inverser* (Ctrl+Maj+I) pour travailler le fond.

### Réduire le bruit, Netteté, Restaurer une vieille photo (menu IA)
Ces trois actions travaillent sur l'image visible ; s'il y a une **sélection**, le résultat ne change que
l'intérieur. Comme les autres actions IA, le résultat va dans un **nouveau calque** (Ctrl+Z annule).
- **Réduire le bruit (IA)** : enlève le grain (photo de nuit, téléphone) et les défauts de compression JPEG en
  gardant les détails. Modèle **SCUNet** (Apache-2.0, 72 Mo). Quelques secondes.
- **Netteté (IA)** : rend un flou léger plus net (contours, textes, détails) : la photo est agrandie ×4 par
  RealESRGAN puis ramenée à sa taille. Elle lisse aussi le grain : sur une photo très texturée, le filtre
  *Netteté* (menu Filtres) peut être préférable. 15 à 20 secondes.
- **Restaurer une vieille photo…** : l'IA **redessine** toute la photo en enlevant rayures, taches, poussières,
  plis et grain, et en rendant le contraste et les visages plus nets. La photo garde **exactement sa taille et ses
  proportions**.
  - **Restaurer** garde les **couleurs d'origine** : une photo noir et blanc ou sépia le reste, une photo en couleur
    garde ses couleurs. L'IA ne fournit que la lumière et les détails ; Pixane remet ensuite la teinte de
    l'original.
  - **Restaurer et coloriser** met en plus des couleurs naturelles à une photo en noir et blanc ou sépia.
  - Le résultat arrive dans un calque **« Restaurée »** (ou **« Restaurée et colorisée »**), et *Enregistrer sous*
    comme *Exporter pour le web* proposent un nom qui le dit : `photo_restauree.jpg`, `photo_restauree_colorisee.jpg`
    (sans accents, pour que le nom passe partout : sites web, autres logiciels, pièces jointes).
   Deux propositions, environ **2 minutes chacune** ;
  *Autres propositions* en redemande. L'IA peut changer de petits détails (traits d'un visage, lettres) :
  comparez bien avec l'original (œil du calque). Modèle **Flux Kontext dev** (11,9 Go, licence FLUX.1 [dev], usage
  **non commercial**), facultatif : case *Flux Kontext* dans **IA > Installer le moteur IA…**.

---

## 6. Les calques

Une image peut avoir plusieurs **calques**, empilés comme des feuilles transparentes : celui du haut passe
devant. Une photo ouverte a un seul calque, « Arrière-plan ».

### Pixels hors de la feuille

Comme dans Photoshop, un calque peut être **plus grand que la feuille** : une image collée en taille réelle, un
élément poussé au bord avec Déplacer ou agrandi avec Ctrl+T. Ce qui dépasse **ne se voit pas, mais n'est jamais
coupé** : on peut le ramener, le réduire, le réafficher.
- **Déplacer**, **Transformer (Ctrl+T)**, le cadre à poignées, **Taille de la zone de travail**, **Taille de
  l'image**, les **rotations** et **miroirs** travaillent sur le calque entier. Le cadre à poignées montre aussi
  ce qui dépasse.
- Le **pinceau**, la **gomme**, les **filtres** et l'IA ne changent que ce qui est dans la feuille ; la partie
  dehors reste telle quelle.
- **Image > Tout faire apparaître** : la feuille s'agrandit juste assez pour montrer tout ce qui dépasse
  (Ctrl+Z pour revenir).
- Enregistré en **.pixane**, **PSD** et **ORA** (Photoshop, Krita et GIMP le relisent). JPEG, PNG… n'enregistrent
  que la feuille. **Recadrer** et **Aplatir** suppriment ce qui dépasse.

### Le panneau Calques
| Élément | Rôle |
|---|---|
| **Liste** | Le calque du haut est en haut. Cliquez sur un calque pour le choisir (il est surligné) |
| **Œil** | Afficher / masquer le calque (pratique pour comparer avant / après une retouche IA) |
| **Vignette** | Aperçu du calque ; le damier gris montre les parties transparentes |
| **Nom** | Double-clic sur le nom pour renommer ; double-clic ailleurs sur la ligne : style du calque |
| **Opacité** | Transparence du calque choisi, de 0 % (invisible) à 100 % ; affichée sous le nom quand < 100 % |
| **Cadenas** (à droite du nom) | Verrouille le calque pour le protéger : il ne peut plus être gommé, supprimé ni fusionné, et son opacité est bloquée ; Aplatir est désactivé tant qu'un calque est verrouillé. Les actions IA sont refusées avec un message : Effacer et Remplir si le calque choisi est verrouillé, Agrandir et Upscale si un calque quelconque est verrouillé (ils changent la taille de tous les calques). On peut toujours le masquer, le renommer et le monter / descendre. Le cadenas ouvert est discret, le cadenas fermé bien visible. Le verrou est gardé dans les fichiers .pixane et .ora |
| **Glisser un calque** | Changer sa place dans la pile à la souris : prenez la ligne (sur le nom) et glissez-la vers le haut ou le bas ; un **trait orange** montre où il ira. Lâché juste sous un calque d'un groupe ouvert, il entre dans le groupe ; un groupe bouge avec ses calques. Une seule étape dans Annuler |
| **Mode de fusion** (liste en haut du panneau) | Comment le calque se mélange à ce qui est dessous (voir plus bas) |
| **Vignette du masque** (à droite de la vignette) | Le masque du calque, s'il en a un. Clic : on peint le masque (cadre orange) ; clic sur la vignette du calque : on repeint les pixels. Maj+clic : désactiver / réactiver le masque (barré en rouge) |
| **Ctrl+clic** sur un calque | L'ajoute aux calques choisis (ou l'en retire) : on peut en choisir plusieurs, ils sont surlignés en bleu |
| **Maj+clic** sur un calque | Choisit tous les calques entre le calque actif et celui-ci |
| **Clic droit** | Menu du calque : renommer, dupliquer, supprimer, fusionner, aplatir, grouper, style, masque, afficher / masquer, verrouiller, nouveau calque. Avec plusieurs calques choisis : **Fusionner les calques choisis**, les supprimer, les afficher ou les masquer |

### Les boutons (de gauche à droite)
| Bouton | Action |
|---|---|
| **Nouveau calque** | Ajoute un calque vide au-dessus du calque choisi (Ctrl+Maj+N) |
| **Nouveau groupe** | Crée un dossier de calques (Ctrl+G met le calque choisi dans un groupe) |
| **Masque** | Ajoute un masque au calque choisi (d'après la sélection s'il y en a une) |
| **Réglage** | Menu : nouveau calque de réglage (Niveaux, Courbes, Balance, Noir et blanc, Vibrance, Réglages de l'image) |
| **Dupliquer** | Copie le calque choisi (Ctrl+J) ; un groupe est copié avec ses calques |
| **fx** | Style du calque (voir plus bas) |
| **Monter / Descendre** | Change la place du calque dans la pile ; entre dans un groupe ouvert, en sort au bord ; un groupe bouge avec ses calques |
| **Fusionner** (Ctrl+E) | Plusieurs calques choisis : les réunit en un seul (à la place du plus haut, avec son nom). Un seul : le réunit avec celui du dessous (opacité, masque et mode appliqués). Refusé pour un calque verrouillé, un groupe ou un calque de réglage |
| **Aplatir** | Réunit tous les calques visibles en un seul « Arrière-plan » |
| **Supprimer** | Supprime le calque choisi, ou tous les calques choisis (un groupe : avec ses calques) |

### Modes de fusion
Les mêmes que Photoshop, rangés par familles : **Normal** ; **Obscurcir**, **Produit**, **Densité couleur +** (ce qui
assombrit) ; **Éclaircir**, **Superposition**, **Densité couleur −**, **Densité linéaire − (Ajout)** (ce qui éclaircit) ;
**Incrustation**, **Lumière tamisée**, **Lumière crue** (contraste) ; **Différence**, **Exclusion** ; **Teinte**,
**Saturation**, **Couleur**, **Luminosité**. Exemples : *Produit* pour une ombre ou une texture sombre, *Superposition*
pour une lueur, *Incrustation* pour une texture de papier, *Couleur* pour teinter. Gardés dans les fichiers .pixane,
.ora et .psd.

### Masques de calque
Un masque **cache une partie du calque sans l'effacer** : noir = caché, blanc = visible, gris = à moitié. On peut
toujours revenir en arrière en repeignant en blanc.
- **Calque > Masque de calque** : *Ajouter : tout visible*, *Ajouter : montrer la sélection*, *Ajouter : cacher la
  sélection* ; *Peindre le masque / les pixels* (Ctrl+\) ; *Désactiver le masque* ; *Inverser le masque* ; *Masque
  vers sélection* ; *Appliquer le masque* (mis dans les pixels) ; *Supprimer le masque*.
- **Peindre le masque** : choisissez-le (clic sur sa vignette), puis le **pinceau de couleur** (en noir, il cache ;
  en blanc, il montre ; en gris, à moitié), la **gomme de calque** (cache), le **dégradé** (fondu progressif, par
  exemple pour fondre deux photos) ou le pot de peinture. Les réglages et filtres s'appliquent aussi au masque.
- Exemple : *Supprimer l'arrière-plan* puis un masque plutôt qu'une gomme : un bout de sujet coupé par erreur se
  récupère en peignant en blanc.
- Les masques suivent le calque (Ctrl+T, recadrer, taille de l'image, Upscale) et sont gardés en .pixane, .ora et .psd.

### Groupes
Un **groupe** range plusieurs calques dans un dossier : on peut les masquer, les déplacer, les dupliquer ou les
supprimer d'un coup, et donner au groupe une opacité, un mode de fusion et un masque qui valent pour tout son contenu.
- **Ctrl+G** : met le calque choisi dans un nouveau groupe ; **Ctrl+Maj+G** : défait le groupe (les calques restent).
- La flèche à gauche du groupe le **replie** ou le **déplie**. Les calques d'un groupe sont décalés vers la droite.
- Monter / Descendre fait entrer un calque dans un groupe ouvert, ou l'en fait sortir.

### Calques de réglage
Un **calque de réglage** applique un réglage (Niveaux, Courbes, Balance des couleurs, Noir et blanc, Vibrance,
Réglages de l'image) à **tout ce qui est dessous**, sans toucher aux pixels : on peut le modifier (double-clic
dessus, ou **Calque > Modifier le réglage…**), le masquer (œil), baisser son opacité ou le supprimer à tout moment.
- **Calque > Nouveau calque de réglage**, ou le bouton **Réglage** du panneau. S'il y a une sélection, elle devient
  le masque du calque de réglage (le réglage ne s'applique que là).
- Dans un groupe, il ne règle que les calques du groupe placés dessous.
- Gardé tel quel en .pixane ; en .ora et .psd, il devient un calque d'image (le résultat).

### Style du calque : ombres, contour, lueur, relief… (Ctrl+Alt+F)
Des **effets ajoutés au calque**, toujours modifiables : les pixels du calque ne sont pas touchés. Pour l'ouvrir :
**double-clic** sur un calque (ailleurs que sur son nom), bouton **fx** du panneau, ou menu **Calque > Style du
calque…**. La photo montre le résultat en direct ; **OK** garde le style (une seule étape dans Annuler),
**Annuler** remet tout comme avant.

| Effet | Ce qu'il fait |
|---|---|
| **Ombre portée** | Ombre décalée sous le calque. Case **Ombre réaliste** : nette près de l'objet, de plus en plus floue en s'éloignant, comme une vraie ombre |
| **Ombre interne** | Ombre à l'intérieur des bords (effet creusé) |
| **Lueur externe / interne** | Halo de couleur autour du calque, ou depuis ses bords (ou son centre) vers l'intérieur |
| **Contour** | Trait autour du calque : à l'extérieur, au centre ou à l'intérieur, épaisseur au choix |
| **Biseau et relief** | Donne du volume : biseau interne, externe ou estampage ; vers le haut ou le bas ; hauteur de la lumière |
| **Incrustation couleur** | Recouvre le calque d'une couleur (modes Normal, Produit, Écran, Incrustation) |
| **Incrustation dégradé** | Recouvre le calque d'un dégradé linéaire ou radial, angle et échelle au choix |
| **Ombre au sol** | Pour un objet détouré : ombre couchée sur le sol, en perspective, nette au pied et floue au bout. **Tirez le point rond sur la photo** pour choisir sa direction et sa longueur |

- **Styles tout prêts** (en haut) : Ombre douce, Ombre réaliste, Ombre au sol, Autocollant, Contour noir, Contour
  seul, Néon, Or, Chrome, Relief, Gravé, Feu, Bonbon, Verre. Les vignettes sont calculées **sur votre calque**. Un
  clic l'essaie, puis chaque effet reste réglable.
- **Plusieurs fois le même effet** (deux contours, trois ombres…) : bouton ⧉. Le premier de la liste passe devant.
  ▲ / ▼ changent l'ordre, ✕ supprime, la case à cocher éteint un effet sans le perdre.
- **Remplissage** : opacité du contenu seul, les effets restent. À 0 % : il ne reste que le contour ou l'ombre
  (texte en contour, verre…).
- **Lumière commune** (cochée par défaut) : tous les calques ont la même lumière ; changer son angle sur un calque
  le change partout.
- **Enregistrer ce style…** : il rejoint les styles tout prêts (clic droit dessus pour le supprimer).
- Les effets **suivent le calque** : Ctrl+T, Taille de l'image et Upscale les agrandissent ou les réduisent avec lui.
  Ils suivent aussi un texte modifié ou un calque déplacé.
- Menu **Calque** : **Copier le style** / **Coller le style** (sur un autre calque), **Enlever le style**, **Mettre
  le style dans les pixels** (pour gommer ou peindre le calque avec ses effets).
- Enregistrement : en **.pixane**, les styles restent modifiables. En **.psd** et **.ora**, ils sont mis dans les pixels
  (visibles dans Photoshop, Krita, GIMP, mais plus modifiables). Les styles d'un PSD ouvert sont repris et restent modifiables (voir chapitre 2).
- Fusionner ou aplatir met aussi les effets dans les pixels.

### Gomme de calque (G)
Efface les pixels du **calque choisi** avec le pinceau rond (taille : curseur « Taille » ou `[` `]`).
Exemple : une retouche IA réussie sauf sur un bord → choisissez son calque et gommez ce bord ; la photo
d'origine réapparaît dessous. Les zones effacées d'un calque seul apparaissent en damier.
À ne pas confondre avec la **Gomme de sélection** (E), qui ne touche qu'au rouge de la sélection.
Sur un calque verrouillé, la gomme ne fait rien et un message en bas de la fenêtre l'indique.

Toutes les actions sur les calques s'annulent avec Ctrl+Z (changer de calque choisi ne compte pas).

---

## 7. Le texte

Outil **Texte** (touche **T**, icône « T » dans la barre d'outils). Le panneau **Texte** s'ouvre à gauche.

### Écrire, déplacer, tourner
- **Cliquer sur la photo** : un nouveau texte « Texte » apparaît à cet endroit, sur **son propre calque**.
  Tapez directement : le mot proposé est remplacé. La case du panneau accepte plusieurs lignes (Entrée).
- **Cliquer sur un texte existant** : il est choisi et ses réglages s'affichent ; on peut le modifier à tout
  moment, même après avoir enregistré en **.pixane** et rouvert.
- Le texte s'applique **au fur et à mesure** : rien à valider.
- **Glisser le texte** : le déplacer (aussi avec l'outil Déplacer, V). Un cadre en pointillés entoure le texte choisi.
- **Poignée ronde** au-dessus du cadre : tourner le texte (**Maj** : par pas de 15°), ou case *Rotation*.
- Le nom du calque suit la première ligne du texte (tant qu'on ne l'a pas renommé à la main).
- Sans texte choisi, les réglages du panneau servent pour le **prochain** texte ; Pixane retient aussi le
  dernier style utilisé (police, couleur, effets…). La taille du nouveau texte est calculée d'après la photo.

### Réglages du panneau
| Réglage | Effet |
|---|---|
| **Police** | Toutes les polices installées dans Windows. La liste montre chaque police **avec le début de votre texte** (ou de la partie sélectionnée dans la case), sinon « Aa Bb Cc 123 ». En passant la souris sur une police, **le texte de la photo la prend tout de suite** pour voir le résultat ; liste fermée sans choisir : il revient comme avant |
| **Taille** | Hauteur des lettres, en pixels de la photo |
| **Couleur** (pastille) | Couleur des lettres, avec la transparence (canal alpha) |
| **G / I / S / B** | Gras, italique, souligné, barré |
| **Alignement** | À gauche, centré, à droite (pour plusieurs lignes) |
| **Lettres** | Espace ajouté entre les lettres, en % de la taille (négatif = lettres serrées) |
| **Lignes** | Écart entre les lignes, × la taille des lettres |
| **Rotation** | Angle en degrés |
| **Courbe** | Texte en arc : positif = en voûte, négatif = en creux, 360° = cercle complet |
| **Contour** | Trait autour des lettres : couleur et épaisseur |
| **Ombre portée** | Couleur, distance, direction (0° = vers la droite, 90° = vers le bas) et flou |
| **Fond** | Rectangle coloré derrière le texte : couleur, marge et arrondi des coins |

Les tailles des effets (épaisseur, distance, flou, marge, arrondi) sont en **% de la taille des lettres** :
ils restent proportionnés quand on change la taille du texte.
**Transparence** du texte entier : curseur **Opacité** du panneau Calques.

### Bon à savoir
- Toutes les modifications s'annulent avec Ctrl+Z ; une saisie de plusieurs lettres s'annule d'un seul coup.
- **Agrandir** et **Upscale** gardent les textes modifiables : ils sont décalés ou redessinés nets à la nouvelle taille.
- La **Gomme de calque** sur un texte le transforme en image (un message le signale ; Ctrl+Z pour revenir).
  **Fusionner** ou **Aplatir** aussi.
- Un texte sur un calque **verrouillé** ne peut être ni déplacé ni modifié.
- Pour garder les textes modifiables, enregistrez en **.pixane** (dans un .ora, ils deviennent des images).

---

## 8. Recadrer, peindre, retoucher

Les outils de retouche à la main, comme dans Photoshop. Tout s'annule par **Ctrl+Z** ; un calque **verrouillé**
est protégé. Les outils d'un même bouton (petit triangle) se choisissent par **clic droit** sur le bouton.

### Recadrer (C)
1. Tirez un cadre sur la photo : la partie gardée reste claire, le reste est assombri, une grille des tiers aide à
   placer le sujet. La taille du résultat s'affiche sous le cadre.
2. Ajustez-le : les **poignées** (coins et milieux des côtés) changent sa taille, glisser **dans** le cadre le
   déplace. Le cadre ne sort jamais de la photo (pour l'agrandir, voir *Agrandir l'image*).
3. **Proportions** (barre du haut) : *Libre*, *Comme la photo*, 1:1, 4:3, 3:2, 16:9, et les mêmes en hauteur.
4. **Entrée**, double-clic dans le cadre ou bouton **Recadrer** : c'est fait. **Échap** ou **Annuler** : le cadre
   disparaît sans rien changer. Ce qui est hors du cadre est supprimé, même ce qui dépassait déjà de la feuille
   (comme dans Photoshop).

Tous les calques sont recadrés ensemble ; les textes restent modifiables. Menu **Sélection > Recadrer à la
sélection** : garde le plus petit rectangle qui contient la sélection.

### Pinceau de couleur (P)
Peint sur le **calque choisi** dans le panneau Calques (astuce : un calque vide au-dessus de la photo permet de
corriger sans toucher à la photo).
- **Couleur** : pastille de la barre du haut. **Alt+clic** sur la photo prend la couleur à cet endroit (pipette).
- **Taille** (ou `[` et `]`), **Opacité** (100 % couvre tout, moins laisse voir dessous) et **Dureté** (100 % bord
  net, 0 % bord très doux).
- Repasser au même endroit pendant un même coup ne fonce pas la couleur ; un nouveau coup, si.

### Tampon (S)
Recopie une partie de la photo sur une autre : pour effacer un petit défaut à la main, dupliquer une texture…
1. **Alt+clic** sur l'endroit à copier (une croix le marque).
2. Peignez là où il doit être recopié : la croix suit, à la même distance.
3. Les coups suivants gardent ce même décalage (comme l'option « Aligné » de Photoshop). Un nouvel Alt+clic choisit
   un autre endroit.

Le tampon copie la photo **telle qu'on la voit** (tous les calques visibles) et peint sur le calque choisi. Taille,
opacité et dureté comme le pinceau.

### Supprimer (J, IA)
Peignez sur un petit défaut (fil électrique, tache, bouton, poussière) : **au lâcher**, il disparaît (LaMa). Le
résultat va dans un calque « Suppressions », réutilisé pour les coups suivants. Pour un gros objet, préférez
*Effacer* (Maj+E), qui propose plusieurs résultats.

### Pinceau correcteur (R)
Comme le tampon, mais la copie **prend la lumière et la couleur d'autour** : idéal pour une ride, une tache sur la
peau, une rayure sur un ciel dégradé.
1. **Alt+clic** sur une zone saine.
2. Peignez sur le défaut : pendant le geste, la copie brute s'affiche ; **au lâcher**, elle est raccordée aux
   alentours.

### Dégradé (D)
Glissez du début à la fin du dégradé (**Maj** : horizontal, vertical ou à 45°). Barre du haut : **Linéaire** ou
**Radial**, couleur de départ (la couleur du pinceau) **vers** couleur d'arrivée, ou **transparent** (fondu vers
rien). Dans la sélection s'il y en a une. Sur un **masque**, il fait un fondu progressif (par exemple pour mélanger
deux photos).

### Pot de peinture (K)
**À quoi il sert** : remplir d'un seul clic une zone de couleur unie, sans la peindre à la main. Par exemple :
changer la couleur d'un fond uni ou d'un bandeau, remplir l'intérieur d'une lettre ou d'une forme, colorer une zone
d'un dessin au trait, ou remplir une sélection.

**Comment** : choisissez la couleur (pastille de la barre du haut, ou **Alt+clic** sur la photo pour la prendre),
puis cliquez dans la zone : elle se remplit jusqu'à ce que la couleur change, en suivant l'image visible.
- **Tolérance** (barre du haut) : à 0, seule la couleur exacte est remplie ; plus haut, le remplissage déborde sur
  des teintes voisines (utile pour un fond légèrement dégradé ou une photo JPEG).
- S'il y a une **sélection**, il reste dedans. Il peint sur le calque choisi (astuce : un calque vide au-dessus
  permet de revenir en arrière facilement).

### Formes (U)
Glissez pour dessiner un **rectangle**, un **rectangle arrondi**, une **ellipse**, une **ligne** ou une **flèche**
(**Maj** : carré, cercle, ligne droite). Chaque forme va dans un **nouveau calque**, dans la couleur du pinceau.
**Remplie** (case) ou seulement le contour ; la **taille** règle l'épaisseur du trait.

Un **texte** retouché au pinceau ou au tampon devient une image (un message le rappelle ; Ctrl+Z pour revenir).
Les groupes et calques de réglage n'ont pas de pixels : un message invite à choisir un calque d'image ou un masque.

---

## 9. Réglages de l'image

Menu **Image > Réglages de l'image…** (Ctrl+U) : corriger la lumière, les couleurs et la netteté.

| Réglage | De … à | Effet |
|---|---|---|
| **Luminosité** | -100 à +100 | Éclaircit ou assombrit, en gardant le noir et le blanc |
| **Contraste** | -100 à +100 | Écarte ou rapproche les clairs et les sombres |
| **Saturation** | -100 à +100 | Couleurs plus vives ou plus ternes ; -100 = noir et blanc |
| **Teinte** | -180° à +180° | Fait tourner toutes les couleurs (le rouge devient orange, vert…) |
| **Température** | -100 à +100 | Plus chaud (orangé) ou plus froid (bleuté) |
| **Netteté** | 0 à 200 % | Renforce les détails |

- Le réglage s'applique au **calque choisi** dans le panneau Calques ; s'il y a une **sélection**, seulement à
  l'intérieur (avec ses bords doux). La fenêtre le rappelle en haut.
- **Aperçu sur la photo** : on voit le résultat en direct en bougeant les curseurs (sur une grande photo, il
  arrive après une fraction de seconde). Décochez pour comparer avec l'original.
- **Réinitialiser** remet tout à zéro, **Appliquer** garde le résultat, **Annuler** (ou Échap) laisse la photo
  comme avant. Après Appliquer, Ctrl+Z annule le réglage.
- **Auto** : propose d'office une luminosité, un contraste et une température (d'après la photo, ou la sélection) ;
  les curseurs restent ajustables ensuite.
- Un calque **verrouillé** est protégé ; un **texte** réglé devient une image.

### Niveaux, Courbes, Balance, Noir et blanc, Vibrance (menu Image > Réglages)
Comme dans Photoshop, avec aperçu en direct et histogramme. Ils changent les pixels du **calque choisi** (dans la
sélection s'il y en a une). Pour pouvoir y revenir plus tard, utilisez plutôt un **calque de réglage** (chapitre 6).

| Réglage | Raccourci | Ce qu'il fait |
|---|---|---|
| **Niveaux** | Ctrl+L | Point noir, gris (gamma) et blanc d'entrée, noir et blanc de sortie ; par canal (RVB, rouge, vert, bleu). **Auto** cale le noir et le blanc sur la photo |
| **Courbes** | Ctrl+M | Courbe de tons : clic pour ajouter un point, glisser pour le bouger, clic droit pour l'enlever ; par canal. Une courbe en S donne du contraste |
| **Balance des couleurs** | Ctrl+B | Pousse les **Ombres**, **Tons moyens** ou **Hautes lumières** vers Cyan–Rouge, Magenta–Vert, Jaune–Bleu ; *Préserver la luminosité* |
| **Noir et blanc** | Ctrl+Alt+Maj+B | Passe en noir et blanc en choisissant la clarté de chaque couleur (rouges, jaunes, verts, cyans, bleus, magentas) ; **Virage** : teinte le gris (sépia…) |
| **Vibrance** | — | Ravive surtout les couleurs ternes en ménageant celles déjà vives (la peau) ; **Saturation** : toutes les couleurs autant |

### Filtres (menu Filtres)
**Flou gaussien**, **Flou de mouvement** (angle, distance), **Réduction du bruit** (force, garder les détails, bruit
de couleur), **Netteté** (quantité, rayon, seuil : le masque flou de Photoshop), **Vignette** (assombrir ou
éclaircir les bords : force, taille du centre, douceur, rond). Même fonctionnement que les réglages : aperçu en
direct, calque choisi, dans la sélection s'il y en a une, une étape dans Annuler. Ils marchent aussi sur un masque.

---

## 10. Menu Image : taille, rotation, transformer

- **Mode** : **Couleurs RVB** ou **Niveaux de gris**. En niveaux de gris, l'image est montrée et enregistrée en gris
  (JPEG, PNG, TIFF en vrai gris) ; les calques gardent leurs couleurs, pour revenir en RVB sans rien perdre.
- **Taille de la zone de travail…** (Ctrl+Alt+C) : agrandit la feuille **sans étirer l'image** (par exemple pour
  ajouter un fond perdu ou une bande pour un titre), ou la rogne.
  - Nouvelle **largeur** et **hauteur** en pixels, pouces, cm, mm, points, picas ou **pourcentage** ; **Relative**
    : on tape ce qu'on ajoute (ex. +200 px).
  - **Ancrage** : où reste l'image (au centre, en haut à gauche…) ; les flèches montrent où la feuille s'agrandit.
  - **Couleur ajoutée** sur le calque du bas : blanc, transparent, noir ou une couleur au choix.
  - Les textes restent modifiables, les repères suivent ; Ctrl+Z annule. Ce qui dépassait de la feuille
    réapparaît s'il entre dans la nouvelle feuille.
- **Tout faire apparaître** : la feuille s'agrandit pour montrer tous les pixels qui dépassent des calques.
- **Taille de l'image…** (Ctrl+Alt+I) : en pixels ou en %, proportions gardées (case à décocher), boutons rapides
  (par exemple 1920 px pour l'écran et Internet). Sans IA : pour agrandir avec plus de détails, préférez Upscale.
- **Pivoter** de 90° à droite, à gauche ou de 180°, **Retourner** horizontalement ou verticalement : toute l'image,
  tous les calques, sans perte. Les textes retournés deviennent des images ; pivotés, ils restent modifiables.
- **Pivoter selon un angle…** : toute l'image tourne de l'angle tapé, **au degré près** (ou au dixième),
  de -359,9° à +359,9° (positif : sens des aiguilles d'une montre). La feuille s'agrandit pour tout garder, les coins
  sont transparents.
- **Redresser…** : tourner d'un petit angle (-45° à +45°) avec une grille pour aligner l'horizon ou un mur.
  *Recadrer pour enlever les coins vides* (coché par défaut) ; décoché, l'image s'agrandit et les coins sont
  transparents.
- **Édition > Transformer le calque** (Ctrl+T) : un cadre entoure le **calque choisi**. Pour agrandir, réduire ou
  tourner **un seul élément** du calque, **sélectionnez-le d'abord** (rectangle, lasso, baguette…) : le cadre
  n'entoure que lui, le reste du calque ne bouge pas, sa place d'origine devient transparente.
  - **coin** : taille, proportions gardées (Maj : libre) ; **bord** : largeur ou hauteur seule ;
  - **dedans** : déplacer ; **dehors** (le curseur devient une flèche ronde) : tourner, **degré par degré**
    (Maj : par 15°) ;
  - la barre du haut montre **Largeur**, **Hauteur** (en %) et **Angle** (en degrés) dans des cases où l'on peut
    **taper la valeur exacte** (flèches : 1° ; Maj+flèches : 10°) ; **Entrée**, double-clic ou **Valider** pour garder,
    **Échap** ou **Annuler** pour revenir. Changer d'outil valide aussi.
  Un texte transformé devient une image (pour garder un texte modifiable, utilisez l'outil Texte).

Tout s'annule par Ctrl+Z.

---

## 11. Raccourcis

| Touche | Action |
|---|---|
| H, V, M, L, B, E, G, T | Main, Déplacer, Rectangle, Lasso, Pinceau, Gomme de sélection, Gomme de calque, Texte |
| C, P, S | Recadrer, Pinceau de couleur, Tampon |
| J, R, D, K, U | Supprimer (IA), Pinceau correcteur, Dégradé, Pot de peinture, Formes |
| Alt+clic | (Pinceau de couleur, Pot de peinture) prendre une couleur ; (Tampon, Pinceau correcteur) endroit à copier |
| `[` / `]` | Pinceau plus petit / plus grand |
| Espace (maintenu) | Déplacer la vue |
| Maj / Alt (en commençant un rectangle ou un lasso) | Ajouter / Retirer |
| Alt (maintenu, pinceau de sélection) | Retirer le temps d'un geste |
| Maj+E, Maj+R, Maj+A, Maj+U | Effacer, Remplir, Agrandir, Upscale |
| Ctrl+Z, Ctrl+Y | Annuler, Rétablir |
| Ctrl+A, Ctrl+D, Ctrl+Maj+I | Tout sélectionner, Désélectionner, Inverser |
| Ctrl+X, Ctrl+C, Ctrl+V, Suppr | Couper, Copier, Coller (nouveau calque), Supprimer la sélection |
| Ctrl+U | Réglages de l'image |
| Ctrl+L, Ctrl+M, Ctrl+B, Ctrl+Alt+Maj+B | Niveaux, Courbes, Balance des couleurs, Noir et blanc |
| Ctrl+G, Ctrl+Maj+G | Grouper, Dégrouper |
| Ctrl+\ | Peindre le masque / les pixels du calque |
| Ctrl+Alt+R | Améliorer le contour |
| Ctrl+R, Ctrl+', Ctrl+;, Ctrl+Maj+; | Règles, Grille, Repères, Magnétisme |
| Ctrl+W, Ctrl+Tab, Ctrl+Maj+Tab | Fermer la photo, Photo suivante, Photo précédente |
| Ctrl+Alt+Maj+S, Ctrl+Alt+Maj+W | Exporter pour le web, Exporter sous |
| Flèches (Maj : x10) | Bouger la sélection (outils de sélection) |
| Ctrl+N, Ctrl+Alt+V | Nouvelle image, Nouvelle image depuis le presse-papiers |
| Ctrl+Alt+I, Ctrl+Alt+C | Taille de l'image, Taille de la zone de travail |
| Ctrl+Alt+Y | Aperçu de l'impression (CMJN) |
| Ctrl+T | Transformer le calque (Entrée valider, Échap annuler) |
| Ctrl+Alt+F | Style du calque |
| Ctrl+Maj+N, Ctrl+J | Nouveau calque, Dupliquer le calque |
| Ctrl+Alt+S, Maj+B | Sélectionner le sujet, Supprimer l'arrière-plan (IA) |
| O, Q, W | Sélection d'objet (IA), Sélection rapide (IA), Baguette magique |
| Glisser après un clic de baguette | Régler la tolérance en direct |
| Clic droit sur un outil à petit triangle | Choisir un autre outil du groupe |
| Ctrl+0, Ctrl+1 | Ajuster, 100 % |
| Entrée / Échap | (Agrandir) Lancer / Annuler ; (Recadrer) Valider / Annuler |
| Maj (en tournant un texte) | Rotation par pas de 15° |
| F1 | Guide, ouvert sur les raccourcis (menu Aide > Guide de Pixane : tout le guide, avec une recherche) |

---

## 12. Matériel et licences

**Installation** : lancer `Pixane-Setup-<version>-64bits.exe`.
1. Langue de l'installation (ce sera aussi la langue de Pixane, modifiable ensuite dans Affichage > Langue).
2. Pour moi seulement (par défaut, sans droits administrateur) ou pour tous les utilisateurs.
3. Dossier d'installation.
4. **Vérification du PC** : carte graphique NVIDIA et sa mémoire (8 Go conseillés), place libre, moteur IA
   (ComfyUI) trouvé ou non. Si ComfyUI est installé ailleurs, bouton **Parcourir…** pour indiquer son dossier.
   Sans ComfyUI, Pixane ouvre, retouche (calques, texte) et enregistre, mais les actions IA ne marchent pas.
5. **Moteur IA** (seulement si ComfyUI n'est pas trouvé) : liste de ce qui sera téléchargé, avec taille, site et
   licence (21,5 Go à télécharger, environ 31 Go sur le disque) ; dossier du moteur (par défaut
   `%LOCALAPPDATA%\Pixane\moteur`) ; case facultative **Flux Schnell** pour « Upscale net » (11,8 Go de plus) ;
   case **J'accepte la licence FLUX.1 [dev]** (usage non commercial) obligatoire pour installer le moteur.
   On peut aussi décocher : Pixane s'installe sans moteur.
6. Options : icône sur le Bureau ; ouvrir les fichiers .pixane avec Pixane.
7. À la fin, la fenêtre **Installer le moteur IA** télécharge et installe tout (ComfyUI portable, ses extensions,
   les modèles). Elle montre l'avancement, la vitesse et le temps restant. **Arrêter** est possible à tout moment :
   le téléchargement reprendra plus tard là où il s'était arrêté (même après une coupure). Chaque fichier est
   vérifié (empreinte SHA-256).

La même fenêtre s'ouvre par le menu **IA > Installer le moteur IA…** (par exemple pour ajouter Flux Schnell plus
tard, ou **Flux Kontext** — 11,9 Go, facultatif — pour *Restaurer une vieille photo*), et Pixane la propose au démarrage s'il ne trouve pas de moteur. Si un ComfyUI installé autrement est déjà
là, Pixane l'utilise et n'installe rien.

**Mises à jour du moteur IA** : les versions de ComfyUI, des extensions et des modèles sont choisies et essayées
avec chaque version de Pixane ; rien ne change tout seul. Quand une nouvelle version de Pixane demande d'autres
versions, Pixane le propose une fois au démarrage (liste et taille à télécharger), et la fenêtre **Installer le
moteur IA** montre l'état de chaque élément (*à jour*, *nouvelle version*) avec le bouton **Mettre à jour**.
Seul ce qui a changé est téléchargé. ComfyUI est remplacé en gardant ses modèles, ses extensions et ses réglages ;
un ancien modèle remplacé est effacé. Le moteur est arrêté pendant la mise à jour et relancé après. Un ComfyUI
installé autrement (par exemple ComfyUI Desktop) se met à jour de son côté : Pixane n'y touche pas.

**Aide > Rechercher une mise à jour…** (ou au démarrage, si *Vérifier les mises à jour au démarrage* est coché) : quand une nouvelle version existe, une fenêtre montre **ce qui change** (nouveautés, corrections) dans toutes les versions que vous n'avez pas encore ; **Télécharger** ouvre la page de téléchargement. Une nouvelle version s'installe par-dessus l'ancienne (réglages gardés). Désinstaller : Paramètres de Windows >
Applications. Le désinstalleur pose deux questions (réponse « Non » par défaut) :
- supprimer aussi le **moteur IA installé par Pixane** (ComfyUI, extensions, modèles) ? Un ComfyUI installé
  autrement, par exemple ComfyUI Desktop, n'est jamais touché ;
- supprimer aussi les **réglages** (langue, thème, dernier dossier, style de texte, dossier du moteur) et les
  journaux ?

**Licences et matériel d'essai** :
- Pixane : Licence Pixane 1.1, © 2026 Georges Christophe (chrypox) : gratuit, modifiable et partageable,
  nom de l'auteur obligatoire, aucune vente (ni de Pixane ni d'une version modifiée) ; fichier `LICENSE`.
  Éléments tiers : `docs\LICENCES_TIERS.md`.
- Testé sur une carte graphique NVIDIA de 8 Go (RTX 3060 Ti). Les durées indiquées viennent de ce PC.
- Modèles utilisés : Flux.1 Fill dev (**usage non commercial** ; version GGUF Q8 si installé par Pixane, même
  qualité), Flux.1 Kontext dev (**usage non commercial**, facultatif), Flux.1 Schnell (Apache-2.0), LaMa
  (Apache-2.0), RealESRGAN x4plus (BSD-3), SCUNet (Apache-2.0), BiRefNet (MIT), SAM 3.1 (SAM License de Meta).
- Moteur : ComfyUI (GPL-3.0) et ses extensions Inpaint nodes, Inpaint Crop and Stitch, Ultimate SD Upscale
  (GPL-3.0), ComfyUI-GGUF (Apache-2.0).

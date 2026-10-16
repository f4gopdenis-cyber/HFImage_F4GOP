# Guide technique — HFImage F4GOP

## Réglage des Kenwood TS-890 / TS-990

Côté poste :
1. Mode **USB-DATA** (touche DATA, « USB-D ») : avec le PTT CAT `TX1;` (DATA SEND),
   l'audio USB n'est émis qu'en mode DATA.
2. Source audio de DATA SEND = **USB Audio** (réglage par défaut en DATA 1/2/3).
   TS-990 : appui long sur DATA pour l'écran des sources audio.
3. Niveau d'entrée USB : menu **7-05** (TS-990, défaut 50). Ajustez pour que l'ALC ne bouge pas.
4. **DATA VOX sur OFF** si vous utilisez le PTT CAT (sinon les sons de Windows émettent).

Côté Windows / HFImage (onglet Réglages) :
- Sortie : « Haut-parleurs (USB Audio CODEC) [MME] » ; entrée : « Microphone (USB Audio CODEC) [MME] ».
- Le volume Windows de ces deux périphériques ne doit pas être coupé.
- PTT : **CAT** sur le port COM virtuel du poste, 115200 bauds (menu 7-01 / 7-02), commande `TX1;`.
  Le port doit être libre : fermez ARCP / logger / WSJT-X, ou utilisez l'**autre** port COM
  virtuel (les TS-890/990 en créent deux : Standard et Enhanced).
  Autres méthodes : RTS, DTR (interface externe) ou VOX.
- **Vérifier le poste** : lit le modèle et le mode par CAT, et prévient si le poste n'est pas en DATA.
  Le même contrôle est fait automatiquement avant chaque émission en CAT.
- **Tester la sortie (1 kHz)** puis **Tester le PTT**.

### Robustesse audio (nouveau en 0.4)
- Lecture en mode « callback » : l'écriture bloquante de PortAudio ne joue **rien** en
  DirectSound sans signaler d'erreur ; c'était une cause de « listé mais muet ».
- 0,6 s de silence en tête : les cartes son perdent 0,3 à 0,5 s au démarrage d'un flux.
- Contrôle que le son a vraiment été joué ; sinon essai automatique du même codec par
  les autres interfaces Windows (MME → WASAPI → DirectSound), et réglage mis à jour.
- Une trame par rafale : chaque trame a son préambule et se resynchronise seule après
  une micro-coupure de carte son ou un évanouissement (≈ 4 % de durée en plus).

### Diagnostic
- **Ouvrir le journal** (Réglages) : `Documents\HFImage\journal.txt`, avec la liste des
  cartes son et ports COM vus par le programme et le détail de chaque erreur.
- Test des sorties, sans PTT (**DATA VOX sur OFF**, sinon le poste émet 1,5 s par interface) :
  `HFImage_F4GOP.exe --audiotest test_audio.txt "USB Audio CODEC"`
- Autotest + inventaire audio/COM : `HFImage_F4GOP.exe --selftest rapport.txt`
  (ajouter `ftp://id:motdepasse@serveur/dossier http://lien/public/` pour tester le serveur hybride).

## Mode hybride

L'image est déposée par **FTP** sur votre hébergement web ; la radio n'émet qu'une
annonce (indicatif, taille, CRC32, lien public), 3 fois en rafales indépendantes :
**~11 s en DATAC3**. Les stations qui la reçoivent téléchargent l'image, vérifient taille
et CRC32, et l'affichent. **Le mot de passe ne passe jamais par radio** ; il est stocké
chiffré (DPAPI Windows) dans les réglages.

Réglages → Mode hybride : serveur FTP, port, identifiant, mot de passe, dossier (créé si
besoin), FTPS éventuel, **lien public** (l'adresse web de ce dossier, ex.
`http://monsite.free.fr/hfimage/`), taille de l'image hybride (640 px / 60 ko par défaut).
**Tester le serveur** dépose un petit fichier, le relit par le lien public et l'efface.

Émission : cocher « Mode hybride », puis Émettre (dépôt FTP puis annonce radio).
« Répéter l'annonce » réémet l'annonce sans redéposer l'image.
Réception : automatique (case à décocher dans Réglages). Seuls les liens http/https sont
suivis, avec une taille maximale de 8 Mo ; une image qui ne correspond pas au CRC est refusée.

Mesures : image 512×512 de 56 ko reçue en ~15 s au total (annonce 11 s + téléchargement) ;
annonce décodée jusqu'à −2 dB (canal calme) et 0 dB (fading CCIR moderate).

## Émission normale

- Durée max : le programme fait tenir l'image dans cette durée (taille/qualité/largeur auto).
- Émettre = image + 10 % de redondance + identification ; « Compléter » = symboles nouveaux.

| Mode | Débit utile | 2 min donnent | Seuil approx. |
|---|---|---|---|
| DATAC1X | ~1 420 bit/s | 800×600 net, ~16 ko | +9 dB (fading moyen : +12 dB) |
| DATAC1 | ~880 bit/s | ~11 ko | +3 dB |
| DATAC3 | ~255 bit/s | ~3 ko | −2 dB |
| DATAC4 | ~58 bit/s | ~0,7 ko | −6 dB |

## Protocole (v2)

| Trame | Contenu |
|---|---|
| DATA | type/version, ID, taille u24, CRC32, SBN+ESI, symbole fontaine |
| HDR | identification de fin : indicatif, format, taille, CRC32 |
| HYB | annonce hybride : ID, indicatif, taille u32, CRC32, format, lien (≤ 255 car.) |
| PDATA | comme DATA, pour l'aperçu rapide |
| NACK (BSR) / ACK | DATAC0 : ID image, indicatif, nombre de symboles demandés (BSR) ou report en dB (ACK) |
| QRV | DATAC0 : présence, indicatif + locator |

Une trame par rafale dans tous les modes. Code fontaine GF(256) systématique.

## Fichiers source (dossier `src/`)

| Fichier | Rôle |
|---|---|
| `app.py` | Interface Tkinter, autotests (`--selftest`, `--audiotest`) |
| `panel.py` | Panneau d'état |
| `qsl.py` | Cartes QSL |
| `updater.py` | Mise à jour automatique depuis les Releases GitHub |
| `theme.py` | Apparence : thèmes de couleurs et police |
| `presence.py` | Présence des stations par Internet (MQTT) et Rx Ok par Internet |
| `stationmap.py`, `carte.bin` | Carte des stations (fond Natural Earth) |
| `build_map.py` | Fabrique `carte.bin` à partir des fichiers Natural Earth |
| `imgfmt.py` | Formats JPEG / SVG / GIF animé / original : chargement, compression SVG, rendu (resvg), réduction des GIF |
| `wavtext.py` | Texte waterfall, begin.wav / end.wav |
| `i18n.py` | Traductions (FR, EN, DE, ES, IT) |
| `audio.py` | Lecture callback avec contrôle et repli, rééchantillonnage, PTT CAT/RTS/DTR, lecture du mode Kenwood |
| `hybrid.py` | Dépôt FTP/FTPS, téléchargement vérifié, mot de passe DPAPI |
| `engine.py` | Compression, émission normale et hybride, réception multi-modes |
| `protocol.py` | Trames DATA / HDR / HYB / NACK / ACK |
| `fountain.py` | Code fontaine GF(256) |
| `modem.py` | Wrapper ctypes de libcodec2 |
| `../codec2_patch/hfi_modes.c` | Mode DATAC1X ajouté à codec2 (voir `codec2_patch/README.md`) |
| `waterfall.py` | Waterfall |
| `channel.py`, `loopback.py` | Canal simulé et banc d'essai |
| `HFImage.spec` | Recette PyInstaller |

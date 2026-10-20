# <img src="docs/images/icone.png" width="64" align="center"> HFImage F4GOP

**Transmission d'images numériques en HF, façon EasyPal — sans SSTV.**
Programme Windows de F4GOP (Denis, IN98QR) pour envoyer et recevoir des photos par radio, avec un modem numérique moderne (codec2 OFDM), une correction d'erreurs par code fontaine et un mode hybride par Internet.

![Fenêtre principale](docs/images/fenetre_principale.png)

## Téléchargement

👉 **[Dernière version : HFImage_F4GOP.exe](https://github.com/f4gopdenis-cyber/HFImage_F4GOP/releases/latest)**

- Un seul fichier, rien à installer (Windows 8.1 / 10 / 11, 64 bits).
- **Windows 7 ou 8 (64 bits)** : prenez **HFImage_F4GOP_Win7.exe** dans la même page (rubrique « Assets »). Même programme, compilé avec Python 3.8 ; il se met à jour avec sa propre version Windows 7. Seule différence : les images SVG ne s'affichent pas (elles sont quand même reçues et enregistrées). Windows 7 doit avoir le Service Pack 1 et la mise à jour KB2533623 (présente si Windows Update a été fait).
- Au premier lancement, Windows SmartScreen peut afficher un avertissement : cliquez sur « Informations complémentaires », puis « Exécuter quand même ».
- Ensuite, le programme se met à jour tout seul : un bandeau apparaît quand une nouvelle version est publiée, un clic suffit.

## Ce que fait le programme

### Images
- Envoi de **photos nettes en 800×600 en environ 2 minutes** grâce au mode rapide **DATAC1X** (1 420 bit/s utiles, 2,2 kHz de large). Pour les conditions difficiles : DATAC1, DATAC3, DATAC4.
- **Mode Auto** : DATAC1X, DATAC1 ou DATAC3 choisi d'après les reports des stations ; **robustesse** réglable contre le QSB.
- **Coupe-QRM** à la réception : porteuses, CW, RTTY et BLU voisines effacées avant la démodulation.
- **Analyseur de réception** : relit un enregistrement et donne un diagnostic (niveau, QRM, QSB, SNR, décalage, mode conseillé).
- **Envoi de fichiers** quelconques (texte, PDF, ZIP, ADIF…), par radio ou en hybride.
- L'image reçue est **identique bit à bit** à l'image envoyée, ou rien : pas d'image « abîmée ».
- Formats AVIF (le plus compact), WebP, JPG, ou le fichier **original** tel quel ; SVG vectoriel en quelques centaines d'octets.
- **Aperçu rapide** : une petite image arrive en ~20 s, puis l'image complète la remplace.
- **BSR / FIX** : une station à qui il manque des morceaux le demande, l'émetteur ne renvoie que ce qui manque.
- **Mode hybride** : l'image passe par votre hébergement web (FTP), seul le lien passe par radio (~11 s). Fonctionne aussi pour les **GIF animés**.
- **Hybride éclair** (par défaut) : l'annonce radio part en **DATAC13** (200 Hz), qui passe dans le bruit et le QRM jusqu'à **−7 dB** ; le lien passe par Internet.
- **Mode EasyPal** : échange d'images avec les stations **EasyPal** et **QSSTV** dans leur mode image (HamDRM, JPEG 2000, Reed-Solomon, BSR / FIX). Les images EasyPal sont reçues automatiquement, en même temps que les modes DATAC.
- **Hybride EasyPal** : en mode EasyPal, le mode hybride est celui d'EasyPal et de QSSTV (image déposée dans `HybridFiles1`, annonce en HamDRM). Les images hybrides des stations EasyPal sont téléchargées automatiquement. Comme dans EasyPal, l'accès FTP part dans l'annonce : utilisez un compte FTP dédié.

### Comme dans EasyPal
- Disposition familière : panneau d'état, grille de boutons, waterfall, onglets RX / TX.
- **Stations en ligne** : dès l'ouverture du programme, on voit toutes les stations qui ont HFImage ouvert, avec leur fréquence (présence par Internet).
- **Rx Ok** : la liste des stations qui ont reçu l'image, avec leur **report en dB**, visible par tout le monde.
- **Carte des stations** : votre station et celles qui ont reçu l'image, placées d'après leur locator.
- **Galerie** des dernières images reçues et envoyées, comme EZPix.
- **Site web / Digi-Sites** : images reçues mises en ligne par FTP comme EasyPal (image1.jpg, image2.jpg…, TX1.jpg…), avec une page prête à l'emploi.
- **Texte dans le waterfall** (begin.wav / end.wav), envoi de texte, texte inclus avec l'image.
- **Bulles de texte** façon bande dessinée sur l'image (parole, pensée, cri, cartouche), placées à la souris.
- **Carte QSL** : photo de fond, indicatif, locator, report rempli automatiquement, police et couleurs au choix.

### Trafic
- **Attendre fréquence libre** : si une autre station émet, HFImage attend la fin de son émission et part tout seul (signal reçu par radio, ou station en ligne en émission sur votre fréquence).
- **Changer de fréquence d'un clic** (comme WSJT-X) : clic sur la fréquence affichée → 3,733 / 7,058 / 14,233 / 21,340 / 28,680 MHz, liste modifiable ; ou clic droit sur une station → sa fréquence.
- **Traduction automatique** des messages reçus dans la langue du programme (l'original reste affiché).
- **Plusieurs fréquences à la fois** : un HFImage par fréquence, chacun avec ses réglages (Réglages → Ouvrir une autre instance, ou `HFImage_F4GOP.exe --profil 20m`), par exemple avec un SDR multi-bandes.
- **Écouteurs (SWL)** bienvenus : avec un identifiant d'écouteur (PA0041SWL, F-12345…), HFImage reçoit tout et envoie les reports par Internet, sans jamais émettre.

### Station
- **Plus de 300 postes** reconnus (Icom, Yaesu, Kenwood, Elecraft, Xiegu, Flex…), réglés comme dans WSJT-X : Kenwood en direct, **Hamlib**, **OmniRig**, **FLRig**.
- PTT par CAT, DTR, RTS (y compris sur une interface à côté du poste, sur un autre port COM) ou VOX. Fréquence du poste affichée et notée.
- **Kenwood TS-890 / TS-990** : codec audio USB, PTT par CAT (audio arrière / data).
- **Passage automatique en DATA** en gardant la bande latérale (LSB-DATA / USB-DATA) ; **installation de Hamlib** proposée d'un clic si votre poste en a besoin.
- **Assistant de démarrage** au premier lancement : indicatif, carte son, poste.
- 5 langues (français, English, Deutsch, Español, Italiano).
- Couleurs (dont un thème **Nuit**), police et zones de la fenêtre réglables.

| | |
|---|---|
| ![Carte des stations](docs/images/carte_stations.png) | ![Carte QSL](docs/images/carte_qsl.png) |
| Carte des stations | Carte QSL personnalisable |
| ![Thèmes](docs/images/themes.png) | ![Netteté](docs/images/nettete_datac1x.png) |
| Thèmes de couleurs | DATAC1 60 s (avant) / DATAC1X 1 min 30 / DATAC1X 2 min |
| ![Poste radio](docs/images/poste_radio.png) | ![Stations et Rx Ok](docs/images/stations_rxok.png) |
| Réglages du poste (comme WSJT-X) | Stations en ligne et Rx Ok |
| ![Galerie](docs/images/galerie.png) | |
| Galerie des dernières images | |

## Démarrage rapide (Kenwood TS-890 / TS-990)

1. Poste en **USB-DATA**, source audio de DATA SEND = **USB Audio**, **DATA VOX sur OFF**.
2. Lancez `HFImage_F4GOP.exe` : l'**assistant de démarrage** guide les trois réglages essentiels. Pour le détail, ouvrez **Réglages** :
   - indicatif et locator ;
   - sortie « Haut-parleurs (USB Audio CODEC) [MME] », entrée « Microphone (USB Audio CODEC) [MME] » ;
   - **Poste radio…** : poste « Kenwood TS-890S » ou « TS-990S », port COM virtuel du poste, 115200 bauds, PTT **CAT**, source audio **Arrière / Data** (DATA SEND, poste en USB-DATA), ou **Avant / Micro** si votre poste est réglé pour émettre l'audio USB sans le mode DATA ;
   - autres postes : choisissez-les dans la liste (Hamlib, OmniRig ou FLRig), puis **Tester le CAT**.
3. **Vérifier le poste**, **Tester la sortie (1 kHz)**, puis **Tester le PTT**.
4. Onglet **TX** → *Ouvrir une image…* → **Émettre**. Réglez le niveau pour que l'ALC ne bouge pas.

📘 **[Mode d'emploi (PDF)](docs/HFImage_mode_emploi.pdf)** — aussi dans le programme : Infos → Mode d'emploi.

Détails (réglages du poste, mode hybride, protocole, débits) : **[docs/TECHNIQUE.md](docs/TECHNIQUE.md)**.

## Important

- Les modes **DATAC** (dont DATAC1X) et l'hybride HFImage demandent HFImage des deux côtés, de préférence à jour. Pour échanger avec **EasyPal** ou **QSSTV**, choisissez le **mode EasyPal**.
- La liste des stations en ligne passe par un serveur MQTT public (`broker.hivemq.com`). Elle ne partage que l'indicatif, le locator, la fréquence et l'état émission / réception. On peut la désactiver dans les Réglages.
- Diagnostic : `HFImage_F4GOP.exe --selftest rapport.txt` (modems, carte, accès Internet, cartes son, ports COM).

## Lancer depuis les sources (Windows)

Python 3.12 (64 bits), puis dans le dossier `src` :

```
pip install -r ..\requirements.txt
python app.py
```

`libcodec2.dll` (fournie dans `src/`) contient le mode DATAC1X. Pour la recompiler : [codec2_patch/README.md](codec2_patch/README.md).

Fabriquer l'exécutable :

```
cd src
pyinstaller --noconfirm HFImage.spec
```

## Organisation du dépôt

| Dossier | Contenu |
|---|---|
| `src/` | Programme Python, `libcodec2.dll`, données de la carte (`carte.bin`), recette PyInstaller |
| `codec2_patch/` | Mode DATAC1X ajouté à codec2 (source et instructions de compilation) |
| `exemples/` | Enregistrement d'une émission DATAC1, carte QSL en SVG, GIF animé |
| `docs/` | Guide technique et captures d'écran |
| `CHANGELOG.md` | Historique des versions |
| `THIRD_PARTY.md` | Composants utilisés et leurs licences |

## Auteur, dédicace et intelligence artificielle

Programme **dédié à Erik Sundstrup VK4AES (SK)**, créateur d'EasyPal, en hommage à son travail.

HFImage a été conçu par Denis F4GOP, qui en a choisi chaque fonction, l'a testé sur l'air avec sa station et l'a fait évoluer avec les retours des utilisateurs. Le code a été écrit en grande partie avec l'aide de l'**intelligence artificielle Claude** (Anthropic).

## Licence

HFImage F4GOP — © 2026 Denis F4GOP.

Logiciel **libre et gratuit**, sous licence **GNU GPL v3** (texte officiel : [LICENSE](LICENSE)), avec les conditions complémentaires et les informations en français de [LICENCE.txt](LICENCE.txt) : attribution, nom du programme, aucune garantie, données personnelles. Vous pouvez l'utiliser, le copier, le partager et le modifier. Une version modifiée que vous distribuez doit rester sous la même licence, avec ses sources, garder la mention de l'auteur et porter un autre nom que « HFImage F4GOP ».

HFImage intègre le modem HamDRM de QSSTV (Johan Maes ON4QZ, GPL v3) et utilise codec2 (David Rowe VK5DGR, LGPL-2.1) : voir [THIRD_PARTY.md](THIRD_PARTY.md).

## Contact

F4GOP — Denis — f4gop.denis@gmail.com

73 !

---

*English: HFImage F4GOP is a free Windows program for sending digital images over HF radio, EasyPal-style but based on codec2 OFDM data modes (including a faster custom mode, DATAC1X) with fountain-code error correction, BSR/FIX repair, a hybrid mode (image via FTP, link over the air, robust DATAC13 "flash" announcement down to −7 dB), EasyPal / QSSTV compatibility (HamDRM), an online station list and Rx Ok reports over MQTT, a station map, QSL card maker, automatic translation of received messages, "wait for clear frequency", one-click frequency change by CAT, and SWL support. The interface is available in English (Settings → Language); English manual: Infos → Manual in English.*

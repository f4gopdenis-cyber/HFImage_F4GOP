# Composants utilisés

HFImage F4GOP lui-même est sous licence **GNU GPL v3** (fichier [LICENSE](LICENSE)).

HFImage F4GOP s'appuie sur les composants libres suivants. Leurs licences s'appliquent à ces composants, y compris quand ils sont inclus dans `HFImage_F4GOP.exe`.

| Composant | Rôle | Licence |
|---|---|---|
| [codec2](https://github.com/drowe67/codec2) (David Rowe et contributeurs) | Modems OFDM DATAC0/1/3/4, codes LDPC | LGPL-2.1 |
| Mode DATAC1X (`codec2_patch/hfi_modes.c`) | Ajout à codec2, compilé dans `libcodec2.dll` | LGPL-2.1 (comme codec2) |
| Modem HamDRM, mode EasyPal (`hamdrm/`, compilé dans `hamdrm.dll`) : [QSSTV](https://github.com/ON4QZ/QSSTV) (Johan Maes ON4QZ), Dream (Volker Fischer), RXAMADRM (Ties Bos PA0MBO) | Mode image d'EasyPal / QSSTV : OFDM, MOT, Reed-Solomon, BSR / FIX | GPL-3.0 (code source dans `hamdrm/`) |
| Brouillage des annonces hybrides EasyPal (`src/easypal_hybrid.py`), d'après `hybridcrypt.cpp` de [QSSTV](https://github.com/ON4QZ/QSSTV) (Johan Maes ON4QZ) | Hybride compatible EasyPal / QSSTV | GPL-3.0 |
| [Natural Earth](https://www.naturalearthdata.com/) | Fond de la carte des stations (`carte.bin`) | Domaine public |
| [Twemoji](https://github.com/jdecked/twemoji) (© Twitter, Inc. et contributeurs) | 30 émoticônes des bulles de texte (`src/emoji/`, images 72×72 non modifiées ; les animations des « émoticônes animées » sont calculées par HFImage à partir de ces images) | [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| [Python](https://www.python.org/) | Langage, Tkinter | PSF License |
| [NumPy](https://numpy.org/) | Calcul | BSD-3-Clause |
| [Pillow](https://python-pillow.org/) (avec libavif, libwebp, libjpeg) | Images AVIF / WebP / JPEG / GIF | MIT-CMU (HPND) et licences des bibliothèques |
| [python-sounddevice](https://github.com/spatialaudio/python-sounddevice) / [PortAudio](http://www.portaudio.com/) | Son | MIT |
| [pySerial](https://github.com/pyserial/pyserial) | CAT / PTT | BSD-3-Clause |
| [certifi](https://github.com/certifi/python-certifi) | Liste des certificats racine (Mozilla) pour les connexions HTTPS, en plus de ceux de Windows | MPL-2.0 |
| [Hamlib](https://github.com/Hamlib/Hamlib) | Commande de plus de 300 postes (`rigctld`). **Pas inclus dans l'exe** : téléchargé à la demande depuis les Releases officielles de Hamlib, sans modification. La liste des modèles (`src/riglist.py`) en est tirée | LGPL-2.1 (bibliothèque), GPL-2.0 (rigctld) |
| [comtypes](https://github.com/enthought/comtypes) | Liaison avec OmniRig | MIT |
| [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) / [tkdnd](https://github.com/petasis/tkdnd) | Glisser-déposer de fichiers sur la fenêtre | MIT / BSD |
| [Eclipse Paho MQTT](https://github.com/eclipse-paho/paho.mqtt.python) | Présence des stations par Internet | EPL-2.0 / EDL-1.0 |
| [resvg](https://github.com/linebender/resvg) / resvg_py | Affichage des images SVG | Apache-2.0 / MIT |
| [PyInstaller](https://pyinstaller.org/) | Fabrication de l'exécutable | GPL-2.0 avec exception pour les programmes produits |

## codec2 (LGPL-2.1)

`src/libcodec2.dll` est une version de codec2 compilée pour Windows (MinGW, x86-64), à partir du commit `310777b1c6f1af0bc7c72f5b32f80f6fd9136962` de https://github.com/drowe67/codec2, avec une seule modification : l'ajout du fichier `hfi_modes.c` (mode DATAC1X). Le source de cette modification et la façon de recompiler la bibliothèque sont dans [`codec2_patch/`](codec2_patch/README.md). Le texte complet de la licence LGPL-2.1 se trouve dans le dépôt codec2 (fichier `COPYING`).

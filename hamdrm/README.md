# hamdrm.dll — mode EasyPal (HamDRM) de HFImage

Ce dossier contient le code source du modem **HamDRM** utilisé par le mode
« EasyPal » de HFImage : c'est le mode image d'**EasyPal** et de **QSSTV**
(OFDM 2,3 / 2,5 kHz, modes A / B / E, QAM 4 / 16 / 64, segments MOT,
Reed-Solomon RS1 à RS4, BSR / FIX).

Il est compilé en une seule bibliothèque `hamdrm.dll` (sans Qt ni FFTW, sans
autre dépendance que Windows), copiée dans `src/` et utilisée par `src/hamdrm.py`.

## Recompiler `hamdrm.dll` (sous Linux, avec MinGW)

```
sudo apt install g++-mingw-w64-x86-64-posix
./build_standalone.sh windows ../src      # -> src/hamdrm.dll
./build_standalone.sh linux ../src        # -> src/libhamdrm.so (essais sous Linux)
```

## Organisation

- `tx/`, `rx/`, `support/` : modem d'origine (QSSTV, Dream, RXAMADRM), avec
  quelques corrections (voir les commentaires « HFImage ») ;
- `api/` : interface C++ (`hamdrm::Transmitter`, `hamdrm::Receiver`) ;
- `capi/` : interface C exportée par la DLL (`hamdrm_c.h`) ;
- `shim/` : remplace les quelques classes Qt et fonctions FFTW utilisées, pour
  une DLL sans dépendance. Le signal émis est identique, échantillon par
  échantillon, à celui de la version compilée avec Qt et FFTW ;
- `stubs/` : remplace les liens avec l'interface de QSSTV.

## Corrections apportées au code d'origine

- Reed-Solomon : taille du fichier décodé fausse quand le remplissage dépassait
  127 octets (octet lu comme signé) ; remplissage mal calculé quand l'en-tête
  imposait un bloc supplémentaire.
- Qt 6 : lecture du nom de fichier dans l'en-tête MOT (pointeur invalide).
- Compteur de segments reçus mis à jour après chaque recomptage.
- Fuites de mémoire de l'émetteur.
- Erreurs mémoire trouvées avec AddressSanitizer (pouvaient fermer le programme
  sous Windows) : indicatif reçu écrit un caractère trop loin
  (`localDrmCallsign`), lecture après la fin de la table FAC
  (`CellMappingTable.cpp`), index -12 dans le décodeur FAC (« + 12 » oublié,
  `msdhardfac.cpp`), dépassement d'entier (`Parameter.cpp`), variable non
  initialisée (`sourcedecoder.cpp`). Le signal émis reste identique.

## Licence et auteurs

GNU GPL version 3 (fichier `LICENSE`). Modem issu de **QSSTV** (Johan Maes
ON4QZ), de **Dream** (Volker Fischer, TU Darmstadt) et de **RXAMADRM** (Ties
Bos PA0MBO). Adaptation pour HFImage : Denis F4GOP, 2026.

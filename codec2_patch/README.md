# Mode DATAC1X pour codec2

HFImage ajoute à codec2 un mode de données plus rapide, **DATAC1X**, construit sur DATAC1 :

- 35 porteuses au lieu de 27 : 2,19 kHz de large (≈ 420-2580 Hz), comme EasyPal ;
- code LDPC long DVB-S2 de rendement 0,6 (`H_16200_9720`) au lieu de 0,5 ;
- paquets de 6,4 s : le code long traverse les évanouissements.

Résultat : **1 420 bit/s utiles, 1,6 × DATAC1**. Sur canal simulé, 100 % des trames passent dès 9 dB de SNR avec un fading faible (CCIR « good ») et dès 12 dB avec un fading moyen, soit environ 3 dB de plus que DATAC1.

Le mode est ouvert par `hfi_open("datac1x")`, qui utilise `FREEDV_MODE_DATA_CUSTOM` de l'API FreeDV ; les autres modes de codec2 ne changent pas.

## Recompiler `libcodec2.dll` (sous Linux, avec MinGW)

```
git clone https://github.com/drowe67/codec2.git
cd codec2
git checkout 310777b1c6f1af0bc7c72f5b32f80f6fd9136962
cp /chemin/vers/codec2_patch/hfi_modes.c src/
git apply /chemin/vers/codec2_patch/CMakeLists.patch      # ajoute hfi_modes.c à CODEC2_SRCS
mkdir build_win && cd build_win
cmake .. -DCMAKE_SYSTEM_NAME=Windows \
         -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
         -DCMAKE_SHARED_LINKER_FLAGS="-static-libgcc -static"
make codec2
# résultat : src/libcodec2.dll  ->  à copier dans HFImage_F4GOP/src/
```

Pour essayer sous Linux, la même chose sans les options MinGW donne `src/libcodec2.so`, trouvée automatiquement par `modem.py` (variable `CODEC2_LIB` pour un autre chemin).

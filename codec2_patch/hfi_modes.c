/* HFImage F4GOP : mode de données supplémentaire (FREEDV_MODE_DATA_CUSTOM).
 *
 * "datac1x" (rapide) : structure de DATAC1 (QPSK, pilotes, rafales), mais
 *   - 35 porteuses au lieu de 27 : 2,19 kHz de large (~420-2580 Hz), comme EasyPal ;
 *   - code LDPC long DVB-S2 de rendement 0,6 (H_16200_9720) au lieu de 0,5 ;
 *   - paquets de 6,4 s : le code long traverse les évanouissements.
 *   ~1,6 fois le débit utile de DATAC1 ; demande ~3 dB de SNR en plus.
 */
#include <string.h>
#include "freedv_api.h"
#include "ofdm_internal.h"
#include "filter.h"
#include "codec2_ofdm.h"

static struct OFDM_CONFIG hfi_cfg;

int hfi_config(const char *name, struct OFDM_CONFIG *cfg) {
  if (strcmp(name, "datac1x") == 0) {
    /* 35 porteuses (2,19 kHz), 58 x 4 x 35 x 2 = 16240 = 16200 + 40 */
    ofdm_init_mode("datac1", cfg);
    cfg->nc = 35;
    cfg->np = 58;
    cfg->nuwbits = 40;
    cfg->bad_uw_errors = 10;
    cfg->codename = "H_16200_9720";
    uint8_t uw[40] = {1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1,
                      0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1};
    memset(cfg->tx_uw, 0, sizeof(cfg->tx_uw));
    memcpy(cfg->tx_uw, uw, sizeof(uw));
    cfg->amp_scale = 125E3;
    cfg->tx_bpf_proto = filtP1100S1300;
    cfg->tx_bpf_proto_n = 100;
    strcpy(cfg->mode, "datac1x");
    return 0;
  }
  return -1;
}

struct freedv *hfi_open(const char *name) {
  if (hfi_config(name, &hfi_cfg) != 0) return NULL;
  struct freedv_advanced adv;
  memset(&adv, 0, sizeof(adv));
  adv.config = &hfi_cfg;
  return freedv_open_advanced(FREEDV_MODE_DATA_CUSTOM, &adv);
}

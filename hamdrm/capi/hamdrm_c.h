/* HFImage F4GOP - C interface of the HamDRM modem (hamdrm.dll / libhamdrm.so)
 *
 * HamDRM is the digital picture mode of EasyPal and QSSTV (OFDM, 2.3/2.5 kHz,
 * MOT file transfer, Reed-Solomon, BSR/FIX). Audio is mono, signed 16 bit,
 * 48000 Hz, both for transmission and reception.
 *
 * All functions are thread safe (one internal lock). Buffers returned through
 * pointer arguments are allocated by the library and must be released with
 * hamdrm_free().
 *
 * Copyright (C) 2026 Denis F4GOP - GPL v3 or later. The modem is derived
 * from QSSTV (Johan Maes ON4QZ), Dream (Volker Fischer) and RXAMADRM (Ties
 * Bos PA0MBO).
 */
#ifndef HAMDRM_C_H
#define HAMDRM_C_H

#include <stdint.h>

#ifdef _WIN32
#define HAMDRM_API __declspec(dllexport)
#else
#define HAMDRM_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define HAMDRM_SAMPLE_RATE 48000

/* Transmission parameters
 *   mode        0 = A, 1 = B, 2 = E
 *   bandwidth   0 = 2.3 kHz, 1 = 2.5 kHz
 *   qam         0 = QAM4, 1 = QAM16, 2 = QAM64
 *   protection  0 = high, 1 = normal
 *   interleaver 0 = long, 1 = short
 *   rs          0 = none, 1..4 = Reed-Solomon RS1..RS4
 */
typedef struct {
  int mode, bandwidth, qam, protection, interleaver, rs;
  char callsign[16];
} hamdrm_params;

typedef struct {
  int time_sync, frame_sync, fac_valid, msc_valid;
  float snr;              /* dB, averaged */
  float freq_offset;      /* Hz, tuning error */
  int mode;               /* 0=A 1=B 2=E, -1 unknown */
  int bandwidth;          /* 0=2.3 1=2.5 */
  int qam;                /* 4, 16, 64 */
  int protection;         /* 0=high 1=normal */
  int interleaver;        /* 0=long 1=short */
  int seg_received, seg_total, seg_current;
  char callsign[16];
  char filename[96];
} hamdrm_status;

HAMDRM_API const char *hamdrm_version(void);
HAMDRM_API void hamdrm_free(void *p);

/* ---- transmission ------------------------------------------------------ */
/* Encodes a file ('name' without extension, 'ext' e.g. "jp2"). Returns the
 * number of samples (>0) and *audio, or <= 0 on error. The file is kept to
 * answer a BSR later. */
HAMDRM_API int hamdrm_tx_file(const uint8_t *data, int len, const char *name, const char *ext,
                              const hamdrm_params *p, int16_t **audio);

/* Number of segments a received BSR asks for if it refers to our last file,
 * -1 otherwise. */
HAMDRM_API int hamdrm_bsr_check(const uint8_t *bsr, int len);

/* Encodes the answer ("FIX") to a BSR: only the missing segments of the last
 * file. Returns the number of samples, <= 0 if the BSR is not for our file. */
HAMDRM_API int hamdrm_tx_fix(const uint8_t *bsr, int len, int16_t **audio);

/* Encodes a BSR (request for missing segments) built from the last
 * incomplete reception. Returns the number of samples, 0 if nothing to ask. */
HAMDRM_API int hamdrm_tx_bsr(const hamdrm_params *p, int16_t **audio);

/* Exact duration in seconds needed to send 'len' bytes. */
HAMDRM_API double hamdrm_estimate(int len, const hamdrm_params *p);

/* ---- reception --------------------------------------------------------- */
HAMDRM_API void hamdrm_rx_reset(void);
HAMDRM_API void hamdrm_rx_process(const int16_t *samples, int count);
HAMDRM_API void hamdrm_rx_status(hamdrm_status *st);

/* Next completely received file, if any: returns its length (> 0), the data,
 * its name and the sender's callsign; 0 when the queue is empty. */
HAMDRM_API int hamdrm_rx_get_file(uint8_t **data, char *name, int name_cap, char *callsign, int call_cap,
                                  unsigned int *mode_code, float *snr);

/* Next BSR received from another station (to answer with hamdrm_tx_fix). */
HAMDRM_API int hamdrm_rx_get_bsr(uint8_t **data);

/* Mode code as text, e.g. "B/2.5/Hi/16/Long". */
HAMDRM_API void hamdrm_mode_string(unsigned int mode_code, char *out, int cap);

#ifdef __cplusplus
}
#endif
#endif

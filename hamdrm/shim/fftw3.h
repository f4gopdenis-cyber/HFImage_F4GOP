/* HFImage F4GOP - minimal replacement for the part of the FFTW 3 API used by
 * the HamDRM modem (complex DFT of any size, real <-> half-complex), so that
 * hamdrm.dll has no external dependency.
 * Copyright (C) 2026 Denis F4GOP - GPL v3 or later */
#ifndef HAMDRM_MINI_FFTW3_H
#define HAMDRM_MINI_FFTW3_H
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef double fftw_complex[2];
typedef float fftwf_complex[2];
typedef struct minifft_plan_s *fftw_plan;
typedef struct minifft_plan_s *fftwf_plan;
typedef enum { FFTW_R2HC = 0, FFTW_HC2R = 1 } fftw_r2r_kind;

#define FFTW_FORWARD (-1)
#define FFTW_BACKWARD (+1)
#define FFTW_MEASURE (0U)
#define FFTW_ESTIMATE (1U << 6)

void *fftw_malloc(size_t n);
void fftw_free(void *p);
fftw_plan fftw_plan_dft_1d(int n, fftw_complex *in, fftw_complex *out, int sign, unsigned flags);
fftw_plan fftw_plan_r2r_1d(int n, double *in, double *out, fftw_r2r_kind kind, unsigned flags);
void fftw_execute(const fftw_plan p);
void fftw_destroy_plan(fftw_plan p);

fftwf_plan fftwf_plan_dft_1d(int n, fftwf_complex *in, fftwf_complex *out, int sign, unsigned flags);
void fftwf_execute(const fftwf_plan p);
void fftwf_destroy_plan(fftwf_plan p);

#ifdef __cplusplus
}
#endif
#endif

// HFImage F4GOP - minimal FFTW replacement (see fftw3.h)
// Mixed-radix Cooley-Tukey (decimation in time), direct DFT for prime factors.
// Unnormalised, same conventions as FFTW.
// Copyright (C) 2026 Denis F4GOP - GPL v3 or later
#include "fftw3.h"

#include <cmath>
#include <complex>
#include <cstdlib>
#include <vector>

typedef std::complex<double> cplx;

struct minifft_plan_s {
  int n;
  int sign;
  int kind;            // 0 complex double, 1 complex float, 2 r2hc, 3 hc2r
  void *in;
  void *out;
  std::vector<cplx> tw;   // exp(sign*2*pi*i*k/n), k = 0..n-1
  std::vector<int> factors;
  std::vector<cplx> a, b;
};

static void transform(const minifft_plan_s *p, const cplx *in, int stride, int n, cplx *out, int level)
{
  if (n == 1) {
    out[0] = in[0];
    return;
  }
  const int f = p->factors[size_t(level)];
  const int m = n / f;
  const int twStep = p->n / n;    // W_n = W_N^(N/n)
  for (int r = 0; r < f; ++r) transform(p, in + r * stride, stride * f, m, out + r * m, level + 1);
  std::vector<cplx> tmp(static_cast<size_t>(f));
  for (int k = 0; k < m; ++k) {
    for (int r = 0; r < f; ++r) tmp[size_t(r)] = out[r * m + k] * p->tw[size_t((r * k * twStep) % p->n)];
    for (int q = 0; q < f; ++q) {
      cplx s = 0;
      for (int r = 0; r < f; ++r) s += tmp[size_t(r)] * p->tw[size_t((r * q * m * twStep) % p->n)];
      out[q * m + k] = s;
    }
  }
}

static minifft_plan_s *makePlan(int n, int sign, int kind, void *in, void *out)
{
  auto *p = new minifft_plan_s;
  p->n = n;
  p->sign = sign;
  p->kind = kind;
  p->in = in;
  p->out = out;
  p->tw.resize(size_t(n));
  for (int k = 0; k < n; ++k) {
    const double ang = sign * 2.0 * M_PI * k / n;
    p->tw[size_t(k)] = cplx(std::cos(ang), std::sin(ang));
  }
  int rest = n;
  for (int f : {4, 2, 3, 5}) {
    while (rest % f == 0) {
      p->factors.push_back(f);
      rest /= f;
    }
  }
  for (int f = 7; rest > 1; f += 2) {
    while (rest % f == 0) {
      p->factors.push_back(f);
      rest /= f;
    }
  }
  p->a.resize(size_t(n));
  p->b.resize(size_t(n));
  return p;
}

static void run(minifft_plan_s *p)
{
  const int n = p->n;
  switch (p->kind) {
  case 0: {
    const double *src = static_cast<const double *>(p->in);
    for (int i = 0; i < n; ++i) p->a[size_t(i)] = cplx(src[2 * i], src[2 * i + 1]);
    transform(p, p->a.data(), 1, n, p->b.data(), 0);
    double *dst = static_cast<double *>(p->out);
    for (int i = 0; i < n; ++i) {
      dst[2 * i] = p->b[size_t(i)].real();
      dst[2 * i + 1] = p->b[size_t(i)].imag();
    }
    break;
  }
  case 1: {
    const float *src = static_cast<const float *>(p->in);
    for (int i = 0; i < n; ++i) p->a[size_t(i)] = cplx(src[2 * i], src[2 * i + 1]);
    transform(p, p->a.data(), 1, n, p->b.data(), 0);
    float *dst = static_cast<float *>(p->out);
    for (int i = 0; i < n; ++i) {
      dst[2 * i] = float(p->b[size_t(i)].real());
      dst[2 * i + 1] = float(p->b[size_t(i)].imag());
    }
    break;
  }
  case 2: {   // real -> half complex: r0 r1 .. r(n/2) i((n+1)/2-1) .. i1
    const double *src = static_cast<const double *>(p->in);
    for (int i = 0; i < n; ++i) p->a[size_t(i)] = cplx(src[i], 0.0);
    transform(p, p->a.data(), 1, n, p->b.data(), 0);
    double *dst = static_cast<double *>(p->out);
    for (int k = 0; k <= n / 2; ++k) dst[k] = p->b[size_t(k)].real();
    for (int k = 1; k < (n + 1) / 2; ++k) dst[n - k] = p->b[size_t(k)].imag();
    break;
  }
  case 3: {   // half complex -> real (unnormalised inverse)
    const double *src = static_cast<const double *>(p->in);
    p->a[0] = cplx(src[0], 0.0);
    for (int k = 1; k < (n + 1) / 2; ++k) {
      p->a[size_t(k)] = cplx(src[k], src[n - k]);
      p->a[size_t(n - k)] = std::conj(p->a[size_t(k)]);
    }
    if (n % 2 == 0) p->a[size_t(n / 2)] = cplx(src[n / 2], 0.0);
    transform(p, p->a.data(), 1, n, p->b.data(), 0);
    double *dst = static_cast<double *>(p->out);
    for (int i = 0; i < n; ++i) dst[i] = p->b[size_t(i)].real();
    break;
  }
  }
}

extern "C" {

void *fftw_malloc(size_t n) { return std::malloc(n); }
void fftw_free(void *p) { std::free(p); }

fftw_plan fftw_plan_dft_1d(int n, fftw_complex *in, fftw_complex *out, int sign, unsigned)
{
  return makePlan(n, sign, 0, in, out);
}

fftw_plan fftw_plan_r2r_1d(int n, double *in, double *out, fftw_r2r_kind kind, unsigned)
{
  // R2HC is a forward transform, HC2R a backward one
  return kind == FFTW_R2HC ? makePlan(n, FFTW_FORWARD, 2, in, out) : makePlan(n, FFTW_BACKWARD, 3, in, out);
}

void fftw_execute(const fftw_plan p) { run(p); }
void fftw_destroy_plan(fftw_plan p) { delete p; }

fftwf_plan fftwf_plan_dft_1d(int n, fftwf_complex *in, fftwf_complex *out, int sign, unsigned)
{
  return makePlan(n, sign, 1, in, out);
}
void fftwf_execute(const fftwf_plan p) { run(p); }
void fftwf_destroy_plan(fftwf_plan p) { delete p; }

}

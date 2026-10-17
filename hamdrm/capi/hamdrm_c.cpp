// HFImage F4GOP - C interface of the HamDRM modem
// Copyright (C) 2026 Denis F4GOP - GPL v3 or later
#include "hamdrm_c.h"
#include "hamdrm.h"

#include <cstdlib>
#include <cstring>
#include <deque>
#include <mutex>

namespace {

std::mutex g_lock;
hamdrm::Transmitter *g_tx = nullptr;
hamdrm::Receiver *g_rx = nullptr;
bool g_haveTxFile = false;

std::deque<hamdrm::ReceivedFile> g_files;
std::deque<QByteArray> g_bsrs;

void ensure()
{
  if (!g_tx) g_tx = new hamdrm::Transmitter;
  if (!g_rx) {
    g_rx = new hamdrm::Receiver;
    g_rx->onFileReceived = [](const hamdrm::ReceivedFile &f) {
      if (g_files.size() < 32) g_files.push_back(f);
    };
    g_rx->onBsrReceived = [](const QByteArray &b) {
      if (g_bsrs.size() < 32) g_bsrs.push_back(b);
    };
  }
}

hamdrm::TxParams toParams(const hamdrm_params *p)
{
  hamdrm::TxParams t;
  if (!p) return t;
  t.mode = hamdrm::RobustnessMode(p->mode < 0 || p->mode > 2 ? 1 : p->mode);
  t.bandwidth = hamdrm::Bandwidth(p->bandwidth ? 1 : 0);
  t.qam = hamdrm::Qam(p->qam < 0 || p->qam > 2 ? 1 : p->qam);
  t.protection = hamdrm::Protection(p->protection ? 1 : 0);
  t.interleaver = hamdrm::Interleaver(p->interleaver ? 1 : 0);
  t.reedSolomon = hamdrm::ReedSolomon(p->rs < 0 || p->rs > 4 ? 0 : p->rs);
  char call[16];
  std::memcpy(call, p->callsign, sizeof call);
  call[15] = 0;
  t.callsign = QString(call);
  return t;
}

int giveAudio(const QVector<qint16> &a, int16_t **audio)
{
  if (!audio || a.isEmpty()) return 0;
  *audio = static_cast<int16_t *>(std::malloc(sizeof(int16_t) * size_t(a.size())));
  if (!*audio) return 0;
  std::memcpy(*audio, a.constData(), sizeof(int16_t) * size_t(a.size()));
  return a.size();
}

void copyStr(char *dst, int cap, const QString &s)
{
  if (!dst || cap <= 0) return;
  const std::string t = s.toLatin1().toStdString();   // copy: toLatin1() is a temporary
  const size_t n = std::min(size_t(cap - 1), t.size());
  std::memcpy(dst, t.data(), n);
  dst[n] = 0;
}

} // namespace

extern "C" {

const char *hamdrm_version(void) { return "HFImage HamDRM 1.0 (EasyPal / QSSTV compatible)"; }

void hamdrm_free(void *p) { std::free(p); }

int hamdrm_tx_file(const uint8_t *data, int len, const char *name, const char *ext, const hamdrm_params *p,
                   int16_t **audio)
{
  if (!data || len <= 0 || !name || !ext) return -1;
  std::lock_guard<std::mutex> l(g_lock);
  ensure();
  if (!g_tx->prepare(QByteArray(reinterpret_cast<const char *>(data), len), QString(name), QString(ext),
                     toParams(p)))
    return -1;
  g_haveTxFile = true;
  return giveAudio(g_tx->generate(), audio);
}

int hamdrm_bsr_check(const uint8_t *bsr, int len)
{
  if (!bsr || len <= 0) return -1;
  std::lock_guard<std::mutex> l(g_lock);
  ensure();
  if (!g_haveTxFile) return -1;
  const QByteArray b(reinterpret_cast<const char *>(bsr), len);
  if (!g_tx->prepareFix(b)) return -1;
  // count the requested segments (same rules as the transmitter)
  QString str = QString(b);
  str.remove('\r');
  const QStringList sl = str.split('\n', Qt::SkipEmptyParts);
  int count = 1, last = sl.at(3).toInt();
  bool inSeries = false;
  for (int i = 4; i < sl.count(); ++i) {
    const int v = sl.at(i).toInt();
    if (v == -99) break;
    if (v < 0) { inSeries = true; continue; }
    count += inSeries ? (v - last) : 1;
    inSeries = false;
    last = v;
  }
  return count;
}

int hamdrm_tx_fix(const uint8_t *bsr, int len, int16_t **audio)
{
  if (!bsr || len <= 0) return -1;
  std::lock_guard<std::mutex> l(g_lock);
  ensure();
  if (!g_haveTxFile || !g_tx->prepareFix(QByteArray(reinterpret_cast<const char *>(bsr), len))) return -1;
  return giveAudio(g_tx->generate(), audio);
}

int hamdrm_tx_bsr(const hamdrm_params *p, int16_t **audio)
{
  std::lock_guard<std::mutex> l(g_lock);
  ensure();
  const QByteArray bsr = g_rx->buildBsr();
  if (bsr.isEmpty()) return 0;
  hamdrm::Transmitter t;   // keep our own last file in g_tx
  if (!t.prepareBsr(bsr, toParams(p))) return -1;
  return giveAudio(t.generate(), audio);
}

double hamdrm_estimate(int len, const hamdrm_params *p)
{
  std::lock_guard<std::mutex> l(g_lock);
  ensure();
  return hamdrm::estimateDuration(len, toParams(p));
}

void hamdrm_rx_reset(void)
{
  std::lock_guard<std::mutex> l(g_lock);
  ensure();
  g_rx->reset();
}

void hamdrm_rx_process(const int16_t *samples, int count)
{
  if (!samples || count <= 0) return;
  std::lock_guard<std::mutex> l(g_lock);
  ensure();
  g_rx->process(reinterpret_cast<const qint16 *>(samples), count);
}

void hamdrm_rx_status(hamdrm_status *st)
{
  if (!st) return;
  std::lock_guard<std::mutex> l(g_lock);
  ensure();
  const hamdrm::RxStatus s = g_rx->status();
  std::memset(st, 0, sizeof *st);
  st->time_sync = s.timeSync;
  st->frame_sync = s.frameSync;
  st->fac_valid = s.facValid;
  st->msc_valid = s.mscValid;
  st->snr = s.snr;
  st->freq_offset = s.freqOffset;
  st->mode = s.robustnessMode;
  st->bandwidth = s.bandwidth;
  st->qam = s.qam;
  st->protection = s.protection;
  st->interleaver = s.interleaver;
  st->seg_received = s.segmentsReceived;
  st->seg_total = s.segmentsTotal;
  st->seg_current = s.currentSegment;
  copyStr(st->callsign, sizeof st->callsign, s.callsign);
  copyStr(st->filename, sizeof st->filename, s.fileName);
}

int hamdrm_rx_get_file(uint8_t **data, char *name, int name_cap, char *callsign, int call_cap,
                       unsigned int *mode_code, float *snr)
{
  std::lock_guard<std::mutex> l(g_lock);
  if (g_files.empty() || !data) return 0;
  const hamdrm::ReceivedFile f = g_files.front();
  g_files.pop_front();
  const int n = f.data.size();
  *data = static_cast<uint8_t *>(std::malloc(size_t(std::max(1, n))));
  if (!*data) return 0;
  std::memcpy(*data, f.data.constData(), size_t(n));
  copyStr(name, name_cap, f.fileName);
  copyStr(callsign, call_cap, f.callsign);
  if (mode_code) *mode_code = f.modeCode;
  if (snr) *snr = f.snr;
  return n;
}

int hamdrm_rx_get_bsr(uint8_t **data)
{
  std::lock_guard<std::mutex> l(g_lock);
  if (g_bsrs.empty() || !data) return 0;
  const QByteArray b = g_bsrs.front();
  g_bsrs.pop_front();
  *data = static_cast<uint8_t *>(std::malloc(size_t(std::max(1, b.size()))));
  if (!*data) return 0;
  std::memcpy(*data, b.constData(), size_t(b.size()));
  return b.size();
}

void hamdrm_mode_string(unsigned int mode_code, char *out, int cap)
{
  copyStr(out, cap, hamdrm::modeCodeToString(mode_code));
}

}

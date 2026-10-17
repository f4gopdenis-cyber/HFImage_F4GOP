// HFImage F4GOP - HamDRM modem public API implementation
// Copyright (C) 2026 Denis F4GOP
//
// Wraps the HamDRM code derived from QSSTV (ON4QZ), Dream (V. Fischer) and
// RXAMADRM (PA0MBO).
//
// This program is free software: you can redistribute it and/or modify it
// under the terms of the GNU General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option)
// any later version.

#include "hamdrm.h"

#include "appglobal.h"
#include "drm.h"
#include "drmdefs.h"
#include "demodulator.h"
#include "sourcedecoder.h"
#include "drmproto.h"
#include "drmtransmitter.h"
#include "drmparams.h"
#include "reedsolomoncoder.h"
#include "downsamplefilter.h"
#include "filters.h"
#include "hamdrm_rxhooks.h"
#include "hamdrm_txhooks.h"

#include <QStringList>
#include <cstring>
#include <cmath>
#include <algorithm>

// ---------------------------------------------------------------------------
// Globals expected by the original code
// ---------------------------------------------------------------------------
bool hamdrmVerbose = false;
QString myCallsign;
QString rxDRMImagesPath = QStringLiteral(".");

namespace {
// Transmitter sink: active output buffer while generate() runs
QVector<qint16> *g_txSink = nullptr;
// Receiver currently attached to the hooks
hamdrm::Receiver *g_activeReceiver = nullptr;
std::function<void(const hamdrm::ReceivedFile &)> *g_rxFileCb = nullptr;
std::function<void(const QByteArray &)> *g_rxBsrCb = nullptr;
QString g_rxCurrentFileName;
}

void hamdrmTxWrite(const short *stereoFrames, int frameCount)
{
  if (!g_txSink) return;
  const int base = g_txSink->size();
  g_txSink->resize(base + frameCount);
  qint16 *out = g_txSink->data() + base;
  for (int i = 0; i < frameCount; ++i) out[i] = stereoFrames[2 * i]; // left = signal
}

void hamdrmRxFileName(const QString &name)
{
  g_rxCurrentFileName = name;
}

void hamdrmRxFile(const QString &name, const QByteArray &data,
                  const QString &callsign, unsigned int modeCode, float snr)
{
  if (g_rxFileCb && *g_rxFileCb) {
    hamdrm::ReceivedFile f;
    f.fileName = name;
    f.data = data;
    f.callsign = callsign.trimmed();
    f.modeCode = modeCode;
    f.snr = snr;
    (*g_rxFileCb)(f);
  }
}

void hamdrmRxBsr(const QByteArray &bsr)
{
  if (g_rxBsrCb && *g_rxBsrCb) (*g_rxBsrCb)(bsr);
}

namespace hamdrm {

void setVerbose(bool on) { hamdrmVerbose = on; }

QString describe(const TxParams &p)
{
  static const char *modes[] = {"A", "B", "E"};
  static const char *qams[] = {"QAM4", "QAM16", "QAM64"};
  return QStringLiteral("%1 / %2 kHz / %3 / %4 / %5%6")
      .arg(modes[int(p.mode)])
      .arg(p.bandwidth == Bandwidth::BW_2_3kHz ? "2.3" : "2.5")
      .arg(qams[int(p.qam)])
      .arg(p.protection == Protection::High ? "High" : "Normal")
      .arg(p.interleaver == Interleaver::Long ? "Long" : "Short")
      .arg(p.reedSolomon == ReedSolomon::None ? QString()
                                              : QStringLiteral(" / RS%1").arg(int(p.reedSolomon)));
}

double estimateDuration(int fileBytes, const TxParams &p)
{
  Transmitter t;
  // content does not matter, only the size (and the name length a little)
  if (!t.prepare(QByteArray(std::max(1, fileBytes), 'x'), "image", "jp2", p)) return 0.0;
  return t.estimatedDuration();
}

unsigned int modeCode(const TxParams &p)
{
  return int(p.mode) * 10000 + int(p.bandwidth) * 1000 + int(p.protection) * 100 +
         int(p.qam) * 10 + int(p.interleaver);
}

QString modeCodeToString(unsigned int mode)
{
  QString tmp;
  switch (mode / 10000) {
  case 0: tmp += "A"; break;
  case 1: tmp += "B"; break;
  case 2: tmp += "E"; break;
  default: tmp += "-"; break;
  }
  tmp += "/";
  mode -= (mode / 10000) * 10000;
  switch (mode / 1000) {
  case 0: tmp += "2.3"; break;
  case 1: tmp += "2.5"; break;
  default: tmp += "---"; break;
  }
  tmp += "/";
  mode -= (mode / 1000) * 1000;
  switch (mode / 100) {
  case 0: tmp += "Hi"; break;
  case 1: tmp += "Lo"; break;
  default: tmp += "--"; break;
  }
  tmp += "/";
  mode -= (mode / 100) * 100;
  switch (mode / 10) {
  case 0: tmp += "4"; break;
  case 1: tmp += "16"; break;
  case 2: tmp += "64"; break;
  default: tmp += "--"; break;
  }
  tmp += "/";
  tmp += (mode & 1) ? "Short" : "Long";
  return tmp;
}

static drmTxParams toDrmParams(const TxParams &p)
{
  drmTxParams d;
  d.robMode = int(p.mode);
  d.qam = int(p.qam);
  d.bandwith = int(p.bandwidth);
  d.interleaver = int(p.interleaver);
  d.protection = int(p.protection);
  d.callsign = p.callsign.left(9).toUpper();
  d.reedSolomon = int(p.reedSolomon);
  return d;
}

// ---------------------------------------------------------------------------
// Transmitter
// ---------------------------------------------------------------------------
struct Transmitter::Impl {
  drmTransmitter tx;
  bool prepared = false;
  // last file session, used to answer a BSR
  QByteArray originalData;   // file data before Reed-Solomon coding
  QByteArray encodedData;    // data actually put in the MOT object
  QString name;
  QString extension;
  TxParams params;
  unsigned int transportId = 0;
  bool haveSession = false;
  int segments = 0;
};

Transmitter::Transmitter() : d(new Impl) {}
Transmitter::~Transmitter() { delete d; }

bool Transmitter::prepare(const QByteArray &fileData, const QString &name,
                          const QString &extension, const TxParams &params)
{
  if (fileData.isEmpty() || name.isEmpty()) return false;
  fixBlockList.clear();
  myCallsign = params.callsign.left(9).toUpper();

  d->originalData = fileData;
  d->encodedData = fileData;
  d->name = name;
  d->extension = extension;
  d->params = params;

  QString format = extension;
  const eRSType rsType = eRSType(int(params.reedSolomon));
  if (rsType != RSTNONE) {
    reedSolomonCoder rsc;
    rsc.encode(d->encodedData, extension, rsType);
    format = rsTypeStr[rsType];
  }
  d->tx.init(&d->encodedData, name, format, toDrmParams(params));
  d->transportId = txTransportID;
  d->segments = numTxFrames;
  d->haveSession = true;
  d->prepared = true;
  return true;
}

bool Transmitter::prepareFix(const QByteArray &bsrData)
{
  if (!d->haveSession) return false;
  // BSR format (QSSTV/EasyPal):
  //  transportID \n H_OK \n segmentSize \n firstMissing \n ... -1 (range) ... \n -99
  QString str = QString::fromLatin1(bsrData);
  str.remove('\r');
  const QStringList sl = str.split('\n', Qt::SkipEmptyParts);
  if (sl.count() < 4 || sl.at(1) != "H_OK") return false;
  const unsigned int trId = sl.at(0).toUInt();
  if (trId != d->transportId) return false;

  fixBlockList.clear();
  int lastBlock = sl.at(3).toInt();
  fixBlockList.append(lastBlock++);
  bool inSeries = false;
  for (int i = 4; i < sl.count(); ++i) {
    const int block = sl.at(i).toInt();
    if (block == -99) break;
    if (block < 0) {
      inSeries = true;
    } else {
      if (inSeries) {
        inSeries = false;
        for (int j = lastBlock; j < block; ++j) fixBlockList.append(j);
      }
      fixBlockList.append(block);
      lastBlock = block + 1;
    }
  }

  QString format = d->extension;
  const eRSType rsType = eRSType(int(d->params.reedSolomon));
  if (rsType != RSTNONE) format = rsTypeStr[rsType];
  myCallsign = d->params.callsign.left(9).toUpper();
  d->tx.init(&d->encodedData, d->name, format, toDrmParams(d->params));
  d->segments = numTxFrames;
  d->prepared = true;
  return true;
}

bool Transmitter::prepareBsr(const QByteArray &bsrData, const TxParams &params)
{
  if (bsrData.isEmpty()) return false;
  fixBlockList.clear();
  myCallsign = params.callsign.left(9).toUpper();
  // a BSR is sent as a small "bsr.bin" file; keep our own copy alive
  static QByteArray bsrCopy;
  bsrCopy = bsrData;
  d->tx.init(&bsrCopy, "bsr", "bin", toDrmParams(params));
  d->segments = numTxFrames;
  d->prepared = true;
  return true;
}

QVector<qint16> Transmitter::generate()
{
  QVector<qint16> out;
  if (!d->prepared) return out;
  out.reserve(int(estimatedDuration() * kSampleRate) + kSampleRate);
  g_txSink = &out;
  d->tx.start(true);   // runs until all segments (plus run-out) are sent
  g_txSink = nullptr;
  d->prepared = false;
  fixBlockList.clear();
  return out;
}

double Transmitter::estimatedDuration() const
{
  // every 400 ms frame carries one MOT segment; the encoder adds a few
  // extra frames at the end to flush the interleaver
  return (d->segments + 4) * 0.4;
}

int Transmitter::segmentCount() const { return d->segments; }

// ---------------------------------------------------------------------------
// Receiver
// ---------------------------------------------------------------------------
struct Receiver::Impl {
  Impl() : downsampler(DOWNSAMPLESIZE, true), iqFilter(RXSTRIPE) {}
  downsampleFilter downsampler;
  drmHilbertFilter iqFilter;
  QVector<short> pending;          // 48 kHz samples waiting for a full block
  float resampSignal[2 * DRMBUFSIZE];
  double block12k[RXSTRIPE];
  bool initialised = false;
};

static bool g_rxObjectsCreated = false;

Receiver::Receiver() : d(new Impl)
{
  if (!g_rxObjectsCreated) {
    srcDecoder = new sourceDecoder;
    demodulatorPtr = new demodulator;
    g_rxObjectsCreated = true;
  }
  g_activeReceiver = this;
  g_rxFileCb = &onFileReceived;
  g_rxBsrCb = &onBsrReceived;
  reset();
}

Receiver::~Receiver()
{
  if (g_activeReceiver == this) {
    g_activeReceiver = nullptr;
    g_rxFileCb = nullptr;
    g_rxBsrCb = nullptr;
  }
  delete d;
}

void Receiver::reset()
{
  g_activeReceiver = this;
  g_rxFileCb = &onFileReceived;
  g_rxBsrCb = &onBsrReceived;
  g_rxCurrentFileName.clear();
  d->pending.clear();
  d->downsampler.init();
  d->iqFilter.init();
  std::memset(d->resampSignal, 0, sizeof(d->resampSignal));

  avgSNR = 0;
  avgSNRAvailable = false;
  demodulatorPtr->init();
  initGetmode(DRMBUFSIZE / 4);
  samplerate_offset_estimation = 0.0;
  runstate = RUN_STATE_POWER_ON;
  channel_decoding();
  runstate = RUN_STATE_INIT;
  channel_decoding();
  runstate = RUN_STATE_NORMAL;
  srcDecoder->init();
  d->initialised = true;
}

void Receiver::process(const qint16 *samples, int count)
{
  // the modem state is process-wide: make sure the callbacks are ours
  g_activeReceiver = this;
  g_rxFileCb = &onFileReceived;
  g_rxBsrCb = &onBsrReceived;
  d->pending.append(QVector<short>(samples, samples + count));
  int offset = 0;
  while (d->pending.size() - offset >= DOWNSAMPLESIZE) {
    d->downsampler.downSample4(d->pending.data() + offset);
    offset += DOWNSAMPLESIZE;
    std::memcpy(d->block12k, d->downsampler.filteredDataPtr(), sizeof(d->block12k));

    // same sequence as QSSTV drmRx::run()
    float temp = WMERFAC;
    if (temp < 0) temp = 0;
    if (avgSNRAvailable) avgSNR = (1 - 0.05f) * avgSNR + 0.05f * temp;
    if (input_samples_buffer_request == 0) demodulatorPtr->demodulate(d->resampSignal, 0);
    d->iqFilter.process(d->block12k, d->resampSignal, RXSTRIPE);
    demodulatorPtr->demodulate(d->resampSignal, RXSTRIPE);
  }
  if (offset) d->pending.remove(0, offset);
}

RxStatus Receiver::status() const
{
  RxStatus s;
  s.timeSync = demodulatorPtr->isTimeSync();
  s.frameSync = demodulatorPtr->isFrameSync();
  s.facValid = (fac_valid == 1);
  s.mscValid = (msc_valid == VALID);
  s.snr = avgSNRAvailable ? avgSNR : 0.0f;
  // HamDRM signals are centred 350 Hz above the nominal position (as shown
  // by QSSTV / EasyPal), report the tuning error relative to that
  s.freqOffset = freqOffset - 350.0f;
  if (s.facValid) {
    s.robustnessMode = robustness_mode;
    s.bandwidth = spectrum_occupancy_new;
    s.qam = (msc_mode_new == 3) ? 4 : (msc_mode_new == 0 ? 64 : 16);
    s.protection = (multiplex_description.PL_PartB == 1) ? 1 : 0;
    s.interleaver = interleaver_depth_new;
    s.currentSegment = currentSegmentNumber;
  }
  if (callsignValid) s.callsign = drmCallsign.trimmed();
  s.fileName = g_rxCurrentFileName;
  s.segmentsReceived = rxSegments;
  s.segmentsTotal = bodyTotalSegments;
  return s;
}

QByteArray Receiver::buildBsr(QString *fileName) const
{
  QList<bsrBlock> *list = srcDecoder->getBSR();
  for (int i = list->count() - 1; i >= 0; --i) {
    transportBlock *tb = list->at(i).tbPtr;
    if (srcDecoder->storeBSR(tb, true)) {
      if (fileName) *fileName = tb->fileName;
      return tb->baBSR;
    }
  }
  return QByteArray();
}

} // namespace hamdrm

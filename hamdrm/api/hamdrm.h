// HFImage F4GOP - HamDRM modem public API
// Copyright (C) 2026 Denis F4GOP
//
// The modem itself is derived from QSSTV (Johan Maes ON4QZ), Dream (Volker
// Fischer) and RXAMADRM (Ties Bos PA0MBO). It is on-air compatible with
// EasyPal and QSSTV DRM transmissions.
//
// This program is free software: you can redistribute it and/or modify it
// under the terms of the GNU General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option)
// any later version.

#ifndef HAMDRM_API_H
#define HAMDRM_API_H

#include <QByteArray>
#include <QString>
#include <QVector>
#include <QList>
#include <functional>

namespace hamdrm {

// Audio sample rate used for both transmission and reception (Hz, mono).
constexpr int kSampleRate = 48000;

enum class RobustnessMode { A = 0, B = 1, E = 2 };
enum class Bandwidth { BW_2_3kHz = 0, BW_2_5kHz = 1 };
enum class Qam { QAM4 = 0, QAM16 = 1, QAM64 = 2 };
enum class Interleaver { Long = 0, Short = 1 };
enum class Protection { High = 0, Normal = 1 };
// Reed-Solomon coding of the file (EasyPal/QSSTV .rs1 ... .rs4), none = raw
enum class ReedSolomon { None = 0, RS1 = 1, RS2 = 2, RS3 = 3, RS4 = 4 };

struct TxParams {
  RobustnessMode mode = RobustnessMode::B;
  Bandwidth bandwidth = Bandwidth::BW_2_5kHz;
  Qam qam = Qam::QAM16;
  Interleaver interleaver = Interleaver::Long;
  Protection protection = Protection::High;
  ReedSolomon reedSolomon = ReedSolomon::None;
  QString callsign;            // max 9 characters, sent in the service label
};

// Human readable short description, e.g. "B / 2.5k / QAM16 / High / Long"
QString describe(const TxParams &p);

// Exact on-air duration (seconds) needed to send 'fileBytes' with these
// parameters. Uses the modem: call it from the thread that runs the modem.
double estimateDuration(int fileBytes, const TxParams &p);

// Compact mode code used by QSSTV/EasyPal (e.g. 11100 for B 2.5k ...)
unsigned int modeCode(const TxParams &p);
QString modeCodeToString(unsigned int code);

class Transmitter {
public:
  Transmitter();
  ~Transmitter();

  // Prepare the transmission of one file. 'name' is the file name without
  // extension and 'extension' the format ("jpg", "jp2", "png", ...).
  bool prepare(const QByteArray &fileData, const QString &name,
               const QString &extension, const TxParams &params);

  // Prepare a Bad Segment Request answer ("fix"): retransmits only the
  // segments listed in the BSR received from the other station.
  // Returns false if the BSR does not match the last prepared file.
  bool prepareFix(const QByteArray &bsrData);

  // Prepare a Bad Segment Request to send to the transmitting station.
  bool prepareBsr(const QByteArray &bsrData, const TxParams &params);

  // Generate the complete audio of the prepared transmission
  // (mono, signed 16 bit, kSampleRate).
  QVector<qint16> generate();

  // Estimated duration of the prepared transmission in seconds.
  double estimatedDuration() const;

  // Number of segments the prepared file was split into.
  int segmentCount() const;

private:
  struct Impl;
  Impl *d;
};

struct RxStatus {
  bool timeSync = false;       // OFDM symbol timing found
  bool frameSync = false;      // OFDM frame synchronised
  bool facValid = false;       // FAC (mode information) decoded
  bool mscValid = false;       // last data block CRC ok
  float snr = 0.0f;            // dB, averaged
  float freqOffset = 0.0f;     // Hz, tuning error (0 = perfectly tuned)
  int robustnessMode = -1;     // 0=A, 1=B, 2=E (-1 unknown)
  int bandwidth = -1;          // 0=2.3k, 1=2.5k
  int qam = -1;                // 4/16/64
  int protection = -1;         // 0=High, 1=Normal
  int interleaver = -1;        // 0=Long, 1=Short
  int currentSegment = -1;     // last segment number decoded
  QString callsign;            // transmitting station, when decoded
  QString fileName;            // file being received
  int segmentsReceived = 0;
  int segmentsTotal = 0;
};

struct ReceivedFile {
  QString fileName;            // as sent by the other station (with extension)
  QByteArray data;             // file content (after Reed-Solomon decoding)
  QString callsign;
  unsigned int modeCode = 0;
  float snr = 0.0f;
};

class Receiver {
public:
  Receiver();
  ~Receiver();

  void reset();

  // Feed received audio (mono, signed 16 bit, kSampleRate). Any length.
  void process(const qint16 *samples, int count);

  RxStatus status() const;

  // Called when a complete file has been decoded.
  std::function<void(const ReceivedFile &)> onFileReceived;
  // Called when a Bad Segment Request from another station was received.
  std::function<void(const QByteArray &bsr)> onBsrReceived;

  // Build a BSR for the last incomplete file (empty if nothing to request).
  QByteArray buildBsr(QString *fileName = nullptr) const;

private:
  struct Impl;
  Impl *d;
};

// Only one Transmitter and one Receiver may be active at a time (the
// underlying modem code uses process-wide state).

void setVerbose(bool on);

} // namespace hamdrm

#endif

// HFImage F4GOP - glue layer replacing the QSSTV application globals
// used by the HamDRM modem code (derived from QSSTV, GPL v3).
#ifndef HAMDRM_GLUE_H
#define HAMDRM_GLUE_H

#include <QString>
#include <QByteArray>
#include <QList>
#include <QDebug>
#include "appdefs.h"

enum hamdrmLogCategory {
  LOGALL = 1, LOGDRMDEMOD, LOGDRMMOT, LOGDRMSRC, LOGDRMTX, LOGDRMTXMOT,
  LOGFFT, LOGPERFORM, LOGSOUND
};

extern bool hamdrmVerbose;
inline void addToLog(const QString &msg, int cat)
{
  if (hamdrmVerbose && cat != LOGPERFORM) qDebug().noquote() << "[hamdrm]" << msg;
}

// Station callsign used in the transmitted service label
extern QString myCallsign;

#endif

// Receive path: directory prefix used by the original code when building
// file names. Files are delivered in memory, this is only a name prefix.
extern QString rxDRMImagesPath;
inline QDebug errorOut() { return qWarning(); }

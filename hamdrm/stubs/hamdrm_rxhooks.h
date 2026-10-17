// HFImage F4GOP - hooks called by the receiver source decoder.
// Implemented in api/hamdrm.cpp
#ifndef HAMDRM_RXHOOKS_H
#define HAMDRM_RXHOOKS_H
#include <QString>
#include <QByteArray>

void hamdrmRxFileName(const QString &name);
void hamdrmRxFile(const QString &name, const QByteArray &data,
                  const QString &callsign, unsigned int modeCode, float snr);
void hamdrmRxBsr(const QByteArray &bsr);

#endif

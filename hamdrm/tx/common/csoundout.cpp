// HFImage F4GOP - transmitter audio sink.
// Replaces the QSSTV synthesizer output: the DRM transmitter produces stereo
// frames (left = real signal), we keep the left channel as mono samples.
#include "csoundout.h"
#include "appglobal.h"
#include "hamdrm_txhooks.h"

CSoundOut::CSoundOut()
{
}

CSoundOut::~CSoundOut()
{
}

bool CSoundOut::Write(CVector< _SAMPLE >& psData)
{
  hamdrmTxWrite(&psData[0],psData.Size()/2);
  return false;
}

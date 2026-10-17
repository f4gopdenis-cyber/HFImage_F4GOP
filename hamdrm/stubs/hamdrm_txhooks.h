// HFImage F4GOP - hook called by the transmitter sound output.
// Implemented in api/hamdrm.cpp
#ifndef HAMDRM_TXHOOKS_H
#define HAMDRM_TXHOOKS_H
// interleaved stereo int16 frames
void hamdrmTxWrite(const short *stereoFrames, int frameCount);
#endif

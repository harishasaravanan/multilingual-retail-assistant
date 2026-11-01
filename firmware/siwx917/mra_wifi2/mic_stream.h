#ifndef MIC_STREAM_H
#define MIC_STREAM_H
#include <stdint.h>
#define MIC_BLK 2048 /* mono samples per block (128 ms at 16 kHz) */
int mic_stream_init(void);
int mic_ring_pop(int16_t *out);
void led_set(int r, int g, int b);
extern volatile int mic_state;        /* 0 idle, 1 capturing, 2 finished */
extern volatile int mic_speech;       /* 1 if speech was found in this press */
extern volatile unsigned mic_stat[6]; /* blocks, speech_block, thr, floor, dropped, last_err */
#endif

#include "mic_stream.h"
#include "cmsis_os2.h"
#include "rsi_ccp_user_config.h"
#include "sl_si91x_mic.h"
#include "sl_driver_gpio.h"
#include "sl_si91x_driver_gpio.h"
#include "RTE_Device_917.h"
#include <string.h>

#define MIC_N_CHANNELS 2
#define REC_CH         1
#define REC_GAIN       5
#define RING_BLOCKS    12
#define MAX_BLOCKS     31
#define VAD_MIN        ((uint32_t)(60 * REC_GAIN) * (uint32_t)(60 * REC_GAIN))
#define LED_ON_LEVEL   1

volatile int mic_state;
volatile int mic_speech;
volatile unsigned mic_stat[6];

static int16_t bufA[MIC_BLK * MIC_N_CHANNELS];
static int16_t bufB[MIC_BLK * MIC_N_CHANNELS];
static int16_t ring[RING_BLOCKS][MIC_BLK];
static int16_t cur_m[MIC_BLK], p1[MIC_BLK], p2[MIC_BLK];
static volatile unsigned r_head, r_tail;
static osMutexId_t r_mtx;
static int32_t hp_x1, hp_y1;
static int leds_ready = 0;
static int ptt_ready = 0;

static void gpio_out(sl_gpio_port_t port, uint8_t pin)
{
  sl_si91x_gpio_pin_config_t c = { { port, pin }, GPIO_OUTPUT };
  sl_gpio_set_configuration(c);
}
static void led_pin(sl_gpio_port_t port, uint8_t pin, int on)
{
  sl_gpio_t g;
  g.port = port;
  g.pin  = pin;
  if (on == LED_ON_LEVEL) sl_gpio_driver_set_pin(&g);
  else sl_gpio_driver_clear_pin(&g);
}
void led_set(int r, int g, int b)
{
  if (!leds_ready) {
    sl_si91x_gpio_driver_enable_clock((sl_si91x_gpio_select_clock_t)M4CLK_GPIO);
    sl_si91x_gpio_driver_enable_clock((sl_si91x_gpio_select_clock_t)ULPCLK_GPIO);
    gpio_out((sl_gpio_port_t)RTE_LED0_LEDR_PORT, RTE_LED0_LEDR_PIN);
    gpio_out((sl_gpio_port_t)RTE_LED0_LEDG_PORT, RTE_LED0_LEDG_PIN);
    gpio_out((sl_gpio_port_t)RTE_LED0_LEDB_PORT, RTE_LED0_LEDB_PIN);
    leds_ready = 1;
  }
  led_pin((sl_gpio_port_t)RTE_LED0_LEDR_PORT, RTE_LED0_LEDR_PIN, r);
  led_pin((sl_gpio_port_t)RTE_LED0_LEDG_PORT, RTE_LED0_LEDG_PIN, g);
  led_pin((sl_gpio_port_t)RTE_LED0_LEDB_PORT, RTE_LED0_LEDB_PIN, b);
}
static int ptt_down(void)
{
  if (!ptt_ready) {
    sl_si91x_gpio_driver_set_uulp_npss_pin_mux(RTE_BUTTON0_PIN, NPSS_GPIO_PIN_MUX_MODE0);
    sl_si91x_gpio_driver_select_uulp_npss_receiver(RTE_BUTTON0_PIN, GPIO_RECEIVER_EN);
    sl_si91x_gpio_pin_config_t c = { { (sl_gpio_port_t)RTE_BUTTON0_PORT, RTE_BUTTON0_PIN }, GPIO_INPUT };
    sl_gpio_set_configuration(c);
    ptt_ready = 1;
  }
  return sl_si91x_gpio_driver_get_uulp_npss_pin(RTE_BUTTON0_PIN) ? 0 : 1; /* active low */
}

static void ring_push(const int16_t *b)
{
  osMutexAcquire(r_mtx, osWaitForever);
  if (r_head - r_tail >= RING_BLOCKS) {
    r_tail++;
    mic_stat[4]++;
  }
  memcpy(ring[r_head % RING_BLOCKS], b, sizeof(ring[0]));
  r_head++;
  osMutexRelease(r_mtx);
}
int mic_ring_pop(int16_t *out)
{
  int ok = 0;
  osMutexAcquire(r_mtx, osWaitForever);
  if (r_head != r_tail) {
    memcpy(out, ring[r_tail % RING_BLOCKS], sizeof(ring[0]));
    r_tail++;
    ok = 1;
  }
  osMutexRelease(r_mtx);
  return ok;
}

static uint32_t to_mono(const int16_t *s, int16_t *m)
{
  uint64_t acc = 0;
  for (int i = 0; i < MIC_BLK; i++) {
    int32_t x = s[i * MIC_N_CHANNELS + REC_CH];
    int32_t y = x - hp_x1 + ((hp_y1 * 245) >> 8); /* high-pass, about 110 Hz */
    hp_x1 = x;
    hp_y1 = y;
    y *= REC_GAIN;
    if (y > 32767) y = 32767;
    if (y < -32768) y = -32768;
    m[i] = (int16_t)y;
    acc += (uint64_t)((int64_t)y * y);
  }
  return (uint32_t)(acc / MIC_BLK);
}

static void capture_thread(void *arg)
{
  (void)arg;
  for (;;) {
    while (mic_state != 0 || !ptt_down()) osDelay(10);
    osMutexAcquire(r_mtx, osWaitForever);
    r_head = 0;
    r_tail = 0;
    osMutexRelease(r_mtx);
    memset((void *)mic_stat, 0, sizeof(mic_stat));
    mic_speech = 0;
    hp_x1 = 0;
    hp_y1 = 0;
    mic_state = 1;
    int16_t *cur = bufA, *nxt = bufB;
    uint32_t floor_min = 0xFFFFFFFFu, hot = 0, nblk = 0;
    int speech = 0;
    if (sl_si91x_mic_get_n_samples(cur, MIC_BLK) != SL_STATUS_OK) {
      mic_stat[5] = 1;
      mic_state   = 2;
      continue;
    }
    for (;;) {
      while (!sl_si91x_mic_sample_buffer_ready()) osDelay(1);
      sl_si91x_mic_stop();
      nblk++;
      int last = !ptt_down() || nblk >= MAX_BLOCKS;
      if (!last) {
        sl_status_t st = sl_si91x_mic_get_n_samples(nxt, MIC_BLK);
        if (st != SL_STATUS_OK) {
          mic_stat[5] = (unsigned)st;
          last        = 1;
        }
      }
      uint32_t e = to_mono(cur, cur_m);
      if (speech) {
        ring_push(cur_m);
      } else {
        if (e < floor_min) floor_min = e;
        uint32_t fl  = floor_min < 4 * VAD_MIN ? floor_min : 4 * VAD_MIN;
        uint32_t thr = fl * 3;
        if (thr < VAD_MIN) thr = VAD_MIN;
        mic_stat[2] = thr;
        mic_stat[3] = floor_min;
        hot         = (e > thr) ? hot + 1 : 0;
        if (hot >= 2) {
          speech      = 1;
          mic_speech  = 1;
          mic_stat[1] = nblk;
          if (nblk > 2) ring_push(p2);
          ring_push(p1);
          ring_push(cur_m);
        } else {
          memcpy(p2, p1, sizeof(p2));
          memcpy(p1, cur_m, sizeof(p1));
        }
      }
      mic_stat[0] = nblk;
      int16_t *t  = cur;
      cur         = nxt;
      nxt         = t;
      if (last) break;
    }
    mic_state = 2;
  }
}

int mic_stream_init(void)
{
  led_set(0, 0, 1);
  (void)ptt_down();
  r_mtx = osMutexNew(NULL);
  if (r_mtx == NULL) return -2;
  sl_status_t st = sl_si91x_mic_init(32000, MIC_N_CHANNELS);
  if (st != SL_STATUS_OK) {
    mic_stat[5] = (unsigned)st;
    return -1;
  }
  static const osThreadAttr_t ta = { .name = "mic", .stack_size = 4096, .priority = osPriorityNormal };
  if (osThreadNew(capture_thread, NULL, &ta) == NULL) return -3;
  return 0;
}

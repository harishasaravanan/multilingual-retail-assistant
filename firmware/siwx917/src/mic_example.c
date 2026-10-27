/*******************************************************************************
 * @file  mic_example.c
 * @brief
 *******************************************************************************
 * # License
 * <b>Copyright 2024 Silicon Laboratories Inc. www.silabs.com</b>
 *******************************************************************************
 *
 * The licensor of this software is Silicon Laboratories Inc. Your use of this
 * software is governed by the terms of Silicon Labs Master Software License
 * Agreement (MSLA) available at
 * www.silabs.com/about-us/legal/master-software-license-agreement. This
 * software is distributed to you in Source Code format and is governed by the
 * sections of the MSLA applicable to Source Code.
 *
 ******************************************************************************/
/**============================================================================
 * @section Description
 * This file contains example code to demonstrate the mic functionality
 ============================================================================**/

// Include Files
#include "mic_example.h"
#include "rsi_ccp_user_config.h"
#include "rsi_debug.h"

#include "sl_si91x_mic.h"

/*******************************************************************************
 *******************************   DEFINES   ***********************************
 ******************************************************************************/
#define MIC_N_CHANNELS         2   // Number of Mic channels
#define MIC_SAMPLE_BUFFER_SIZE 512 // Mic buffer size to collect mic samples
#define REC_RATE    16000
#define REC_SECONDS 4
#define REC_CH      1   // 0 or 1: which mic channel to record
#define REC_BLOCK   2048 // frames per transfer; try 2048 later
#define REC_GAIN    5   // digital gain, saturating
static int32_t hp_x1, hp_y1;
#define VAD_FRAME     320     // 20 ms at 16 kHz
#define VAD_MIN_MS    ((uint32_t)(60 * REC_GAIN) * (uint32_t)(60 * REC_GAIN)) // floor scales with gain
#define VAD_PAD_START 5       // frames kept before speech (100 ms)
#define VAD_PAD_END   10      // frames kept after speech (200 ms)
static int16_t rec[REC_RATE * REC_SECONDS];

/*******************************************************************************
 ***************************  LOCAL VARIABLES   ********************************
 ******************************************************************************/
static int16_t bufA[REC_BLOCK * MIC_N_CHANNELS];
static int16_t bufB[REC_BLOCK * MIC_N_CHANNELS];
static uint16_t sampling_frequency = 32000;

/*******************************************************************************
 *********************   LOCAL FUNCTION PROTOTYPES   ***************************
 ******************************************************************************/

/*******************************************************************************
 **************************   GLOBAL FUNCTIONS   *******************************
 ******************************************************************************/

/***************************************************************************/ /**
* Initialize mic example.
******************************************************************************/
void mic_init(void)
{
  sl_status_t status;
  // Initialize the microphone module
  status = sl_si91x_mic_init(sampling_frequency, MIC_N_CHANNELS);
  if (status != SL_STATUS_OK) {
    // Print error message if mic initialization fails
    DEBUGOUT("Microphone initialization failed");
    return;
  } else {
    DEBUGOUT("Microphone initialized successfully.\r\n");
  }
}

/***************************************************************************/ /**
* Mic ticking function.
******************************************************************************/
static uint32_t frame_ms(const int16_t *q)
{
  uint64_t a = 0;
  for (int i = 0; i < VAD_FRAME; i++) a += (int32_t)q[i] * q[i];
  return (uint32_t)(a / VAD_FRAME);
}

#include "sl_driver_gpio.h"
#include "sl_si91x_driver_gpio.h"
#include "RTE_Device_917.h"
#define LED_ON_LEVEL 1 /* flip to 0 if the LED colours look inverted */
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
static void led_set(int r, int g, int b)
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

void mic_process_action(void)
{
  static int done = 0;
  if (done) return;
  uint32_t n = 0;
  int16_t *cur = bufA, *nxt = bufB;
  static int tested = 0;
  if (!tested) {
    tested = 1;
    DEBUGOUT("LEDTEST: R only, G only, B only, off\r\n");
    led_set(1, 0, 0); for (volatile uint32_t i = 0; i < 40000000u; i++) {}
    led_set(0, 1, 0); for (volatile uint32_t i = 0; i < 40000000u; i++) {}
    led_set(0, 0, 1); for (volatile uint32_t i = 0; i < 40000000u; i++) {}
    led_set(0, 0, 0); for (volatile uint32_t i = 0; i < 40000000u; i++) {}
    DEBUGOUT("LEDTEST done\r\n");
  }
  led_set(0, 0, 1); /* idle: blue */
  DEBUGOUT("WAIT\r\n");
  while (ptt_down()) {}
  while (!ptt_down()) {}
  led_set(0, 1, 0); /* listening: green */
  DEBUGOUT("REC\r\n");
  if (sl_si91x_mic_get_n_samples(cur, REC_BLOCK) != SL_STATUS_OK) {
    DEBUGOUT("ERR first 0\r\n");
    done = 1;
    return;
  }
  while (n + REC_BLOCK <= REC_RATE * REC_SECONDS) {
    while (!sl_si91x_mic_sample_buffer_ready()) {}
    sl_si91x_mic_stop();
    int last_blk = !ptt_down();
    if (!last_blk && n + 2 * REC_BLOCK <= REC_RATE * REC_SECONDS) {
      sl_status_t st = sl_si91x_mic_get_n_samples(nxt, REC_BLOCK);
      if (st != SL_STATUS_OK) {
        DEBUGOUT("ERR next 0x%x\r\n", (unsigned)st);
        break;
      }
    }
    for (int i = 0; i < REC_BLOCK; i++) {
      int32_t x = cur[i * MIC_N_CHANNELS + REC_CH];
      int32_t y = x - hp_x1 + ((hp_y1 * 245) >> 8); /* high-pass, about 110 Hz */
      hp_x1 = x;
      hp_y1 = y;
      y *= REC_GAIN;
      if (y > 32767) y = 32767;
      if (y < -32768) y = -32768;
      rec[n + i] = (int16_t)y;
    }
    n += REC_BLOCK;
    int16_t *t = cur; cur = nxt; nxt = t;
    if (last_blk) break;
  }
  led_set(1, 1, 0); /* processing: yellow */
  uint32_t nf = n / VAD_FRAME, f, ss = 0, se = 0, last = 0;
  int found = 0;
  uint32_t fl = 0xFFFFFFFFu; /* noise floor = quietest 100 ms of the clip */
  for (f = 0; f + 5 <= nf; f++) {
    uint64_t a5 = 0;
    for (uint32_t k = 0; k < 5; k++) a5 += frame_ms(rec + (f + k) * VAD_FRAME);
    if ((uint32_t)(a5 / 5) < fl) fl = (uint32_t)(a5 / 5);
  }
  uint32_t thr = fl * 3;
  if (thr < VAD_MIN_MS) thr = VAD_MIN_MS;
  for (f = 0; f + 2 < nf; f++) {
    if (frame_ms(rec + f * VAD_FRAME) > thr && frame_ms(rec + (f + 1) * VAD_FRAME) > thr
        && frame_ms(rec + (f + 2) * VAD_FRAME) > thr) {
      ss = f;
      found = 1;
      break;
    }
  }
  if (found) {
    for (f = nf - 1; f >= 2; f--) {
      if (frame_ms(rec + f * VAD_FRAME) > thr && frame_ms(rec + (f - 1) * VAD_FRAME) > thr
          && frame_ms(rec + (f - 2) * VAD_FRAME) > thr) {
        last = f;
        break;
      }
    }
    if (last < ss + 10) found = 0; /* shorter than 200 ms: a click, not speech */
    se = last + 1 + VAD_PAD_END;
    if (se > nf) se = nf;
    se *= VAD_FRAME;
    ss = (ss > VAD_PAD_START ? ss - VAD_PAD_START : 0) * VAD_FRAME;
  }
  if (!found) {
    DEBUGOUT("SILENCE\r\nEND\r\n");
    return;
  }
  DEBUGOUT("START %u %u\r\n", (unsigned)(se - ss), (unsigned)REC_RATE);
  for (uint32_t i = ss; i < se; i++) {
    DEBUGOUT("%04x", (unsigned)(uint16_t)rec[i]);
    if (((i - ss) & 31) == 31) DEBUGOUT("\r\n");
  }
  DEBUGOUT("\r\nEND\r\n");
}

#include <Arduino.h>
#include <driver/ledc.h>
#include <esp_adc/adc_oneshot.h>
#include <math.h>

// --- Pin Definitions (ESP32-S3) ---
#define PIN_TX_A      4
#define PIN_TX_B      5
#define PIN_RX_ADC    ADC_CHANNEL_0  // GPIO 1 on ESP32-S3
#define PIN_H_STEP    10
#define PIN_H_DIR     11
#define PIN_E_STEP    12
#define PIN_E_DIR     13
#define PIN_MOTOR_EN  14

// --- Carrier & Sampling Config ---
#define CARRIER_FREQ  40000               // 40 kHz carrier
#define SAMPLE_CYCLES 200                 // 200 cycles per reading (5 ms window)
#define SAMPLES_TOTAL (SAMPLE_CYCLES * 4) // 4x oversampling = 160 kHz (0, 90, 180, 270 deg)

adc_oneshot_unit_handle_t adc1_handle;
int h_position_steps = 0;
int e_position_steps = 0;
bool liveStreaming = false;
uint32_t lastLiveTick = 0;

void setupPWM() {
  ledc_timer_config_t timer_conf = {
    .speed_mode       = LEDC_LOW_SPEED_MODE,
    .duty_resolution  = LEDC_TIMER_8_BIT,
    .timer_num        = LEDC_TIMER_0,
    .freq_hz          = CARRIER_FREQ,
    .clk_cfg          = LEDC_AUTO_CLK
  };
  ledc_timer_config(&timer_conf);

  // Channel 0: Normal 40 kHz (0 deg)
  ledc_channel_config_t ch0 = {
    .gpio_num   = PIN_TX_A,
    .speed_mode = LEDC_LOW_SPEED_MODE,
    .channel    = LEDC_CHANNEL_0,
    .timer_sel  = LEDC_TIMER_0,
    .duty       = 128,
    .hpoint     = 0
  };
  ledc_channel_config(&ch0);

  // Channel 1: Inverted 40 kHz (180 deg push-pull)
  ledc_channel_config_t ch1 = {
    .gpio_num   = PIN_TX_B,
    .speed_mode = LEDC_LOW_SPEED_MODE,
    .channel    = LEDC_CHANNEL_1,
    .timer_sel  = LEDC_TIMER_0,
    .duty       = 128,
    .hpoint     = 128
  };
  ledc_channel_config(&ch1);
}

void setupADC() {
  adc_oneshot_unit_init_cfg_t init_config = { .unit_id = ADC_UNIT_1 };
  adc_oneshot_new_unit(&init_config, &adc1_handle);

  adc_oneshot_chan_cfg_t config = {
    .atten = ADC_ATTEN_DB_12,
    .bitwidth = ADC_BITWIDTH_12
  };
  adc_oneshot_config_channel(adc1_handle, PIN_RX_ADC, &config);
}

void setEmitter(bool active) {
  uint32_t duty = active ? 128 : 0;
  ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty);
  ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
  ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1, duty);
  ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1);
}

void moveStepper(int stepPin, int dirPin, int steps, int &posTracker) {
  digitalWrite(PIN_MOTOR_EN, LOW); // Enable motor drivers
  delay(5);
  digitalWrite(dirPin, steps >= 0 ? HIGH : LOW);
  int count = abs(steps);
  for (int i = 0; i < count; i++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(600);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(600);
  }
  posTracker += steps;
  delay(20); // Mechanical settling time
  digitalWrite(PIN_MOTOR_EN, HIGH); // Disable motors to eliminate acoustic/EMI noise
}

// 4x Oversampled Quadrature Demodulation at 160 kHz (6.25 us nominal)
void measureAureole(float &amplitude, float &phaseDeg, float &coherence) {
  int raw[SAMPLES_TOTAL];
  uint32_t next_tick = micros();

  portDISABLE_INTERRUPTS();
  for (int i = 0; i < SAMPLES_TOTAL; i++) {
    while ((int32_t)(micros() - next_tick) < 0);
    next_tick += 6;
    adc_oneshot_read(adc1_handle, PIN_RX_ADC, &raw[i]);
  }
  portENABLE_INTERRUPTS();

  float mean = 0;
  for (int i = 0; i < SAMPLES_TOTAL; i++) mean += raw[i];
  mean /= SAMPLES_TOTAL;

  double sumI = 0, sumQ = 0, totalPower = 0;
  for (int i = 0; i < SAMPLES_TOTAL; i++) {
    float v = raw[i] - mean;
    totalPower += v * v;
    int quad = i & 3;
    if (quad == 0) sumI += v;
    else if (quad == 1) sumQ += v;
    else if (quad == 2) sumI -= v;
    else if (quad == 3) sumQ -= v;
  }

  float I = (2.0f * sumI) / SAMPLES_TOTAL;
  float Q = (2.0f * sumQ) / SAMPLES_TOTAL;
  float signalPower = 0.5f * (I * I + Q * Q);
  float meanTotalPower = totalPower / SAMPLES_TOTAL;

  amplitude = sqrtf(I * I + Q * Q);
  phaseDeg = atan2f(Q, I) * 180.0f / PI;
  coherence = (meanTotalPower > 1e-3f) ? (signalPower / meanTotalPower) : 0.0f;
}

void logState(const char* label) {
  float amp, phase, coh;
  measureAureole(amp, phase, coh);
  Serial.printf("%s,%lu,%d,%d,%.3f,%.2f,%.4f\n",
                label, millis(), h_position_steps, e_position_steps, amp, phase, coh);
}

// Automated A-B-A-B Null Verification Protocol
void runABABProtocol() {
  Serial.println("STATE,TIME_MS,H_STEPS,E_STEPS,AMP,PHASE_DEG,COHERENCE");

  setEmitter(false);
  delay(100);
  for (int i = 0; i < 10; i++) { logState("N0_NOISE"); delay(50); }

  setEmitter(true);
  delay(100);
  for (int i = 0; i < 10; i++) { logState("A1_ACTIVE"); delay(50); }

  moveStepper(PIN_H_STEP, PIN_H_DIR, -400, h_position_steps);
  delay(150);
  for (int i = 0; i < 10; i++) { logState("B1_H_NULL"); delay(50); }

  moveStepper(PIN_H_STEP, PIN_H_DIR, 400, h_position_steps);
  delay(150);
  for (int i = 0; i < 10; i++) { logState("A2_ACTIVE"); delay(50); }

  setEmitter(false);
}

// Hysteresis Loop Sweep (Loading -> Unloading)
void runHysteresisSweep(int maxSteps, int stepSize) {
  Serial.println("SWEEP,TIME_MS,H_STEPS,E_STEPS,AMP,PHASE_DEG,COHERENCE");
  setEmitter(true);
  delay(100);

  for (int s = 0; s <= maxSteps; s += stepSize) {
    logState("H_LOAD");
    if (s < maxSteps) moveStepper(PIN_H_STEP, PIN_H_DIR, stepSize, h_position_steps);
  }
  for (int s = maxSteps; s >= 0; s -= stepSize) {
    logState("H_UNLOAD");
    if (s > 0) moveStepper(PIN_H_STEP, PIN_H_DIR, -stepSize, h_position_steps);
  }
  setEmitter(false);
}

// 2D Serpentine Parameter Sweep (E x H Grid)
void run2DSweep(int hMaxSteps, int hStepSize, int eMaxSteps, int eStepSize) {
  Serial.println("SWEEP2D,TIME_MS,H_STEPS,E_STEPS,AMP,PHASE_DEG,COHERENCE");
  setEmitter(true);
  delay(100);

  int eDirection = 1;
  for (int h = 0; h <= hMaxSteps; h += hStepSize) {
    if (eDirection == 1) {
      for (int e = 0; e <= eMaxSteps; e += eStepSize) {
        logState("GRID_2D");
        if (e < eMaxSteps) moveStepper(PIN_E_STEP, PIN_E_DIR, eStepSize, e_position_steps);
      }
    } else {
      for (int e = eMaxSteps; e >= 0; e -= eStepSize) {
        logState("GRID_2D");
        if (e > 0) moveStepper(PIN_E_STEP, PIN_E_DIR, -eStepSize, e_position_steps);
      }
    }
    eDirection *= -1;
    if (h < hMaxSteps) moveStepper(PIN_H_STEP, PIN_H_DIR, hStepSize, h_position_steps);
  }

  setEmitter(false);
  moveStepper(PIN_E_STEP, PIN_E_DIR, -e_position_steps, e_position_steps);
  moveStepper(PIN_H_STEP, PIN_H_DIR, -h_position_steps, h_position_steps);
}

void setup() {
  Serial.begin(921600);
  pinMode(PIN_H_STEP, OUTPUT);
  pinMode(PIN_H_DIR, OUTPUT);
  pinMode(PIN_E_STEP, OUTPUT);
  pinMode(PIN_E_DIR, OUTPUT);
  pinMode(PIN_MOTOR_EN, OUTPUT);
  digitalWrite(PIN_MOTOR_EN, HIGH);

  setupPWM();
  setupADC();
  setEmitter(false);

  Serial.println("CAD-01 Ready. Commands: [R]un ABAB Null | [H]ysteresis | [M]atrix 2D | [L]ive Scope | [E] Step");
}

void loop() {
  if (Serial.available()) {
    char cmd = toupper(Serial.read());

    if (cmd == 'L') {
      liveStreaming = !liveStreaming;
      setEmitter(liveStreaming);
      if (liveStreaming) {
        Serial.println("LIVE,TIME_MS,H_STEPS,E_STEPS,AMP,PHASE_DEG,COHERENCE");
      } else {
        Serial.println("# Live stream stopped.");
      }
    } else if (cmd == 'R' || cmd == 'H' || cmd == 'M' || cmd == 'E') {
      liveStreaming = false;
      if (cmd == 'R') runABABProtocol();
      else if (cmd == 'H') runHysteresisSweep(1880, 40);
      else if (cmd == 'M') run2DSweep(1800, 120, 200, 10);
      else if (cmd == 'E') {
        moveStepper(PIN_E_STEP, PIN_E_DIR, 10, e_position_steps);
        setEmitter(true); delay(50);
        logState("E_STEP");
        setEmitter(false);
      }
    }
  }

  if (liveStreaming && (millis() - lastLiveTick >= 50)) {
    lastLiveTick = millis();
    logState("LIVE");
  }
}

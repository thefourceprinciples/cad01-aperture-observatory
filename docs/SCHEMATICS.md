# CAD-01 Analog Front-End & Driver Schematics

## 1. Ultrasonic Receiver Front-End (MCP6002 -> ESP32-S3 GPIO 1)
* **Input High-Pass:** `10 nF` coupling cap + `10 kΩ` load resistor ($f_c \approx 1.6\text{ kHz}$).
* **Virtual Ground:** `10 kΩ / 10 kΩ` divider from `3.3V` bypassed with `10 µF` to `GND` (`1.65 V` bias).
* **Stage 1 (Non-Inverting Pre-Amp):** `R1 = 1 kΩ` (with `100 nF` DC-block to `GND`), `R2 = 10 kΩ` (`Gain = 11x`).
* **Stage 2 (40 kHz MFB Bandpass):** `R_in = 1.5 kΩ`, `R_fb = 100 kΩ`, `C = 10 nF` ($f_0 \approx 41\text{ kHz}, Q \approx 4$).

## 2. Optical Upgrade Front-End (BPW34 TIA -> Stage 2 Bandpass)
* **Photodiode:** `BPW34` reverse-biased between `+3.3V` (filtered via `100 Ω` + `10 µF`) and `1.65V` summing node.
* **TIA Feedback:** `R_f = 100 kΩ` in parallel with `C_f = 10 pF` (NPO/C0G).
* **Laser Emitter:** `5 mW 650 nm` module pulsed at `40 kHz` via `2N2222` NPN transistor (`1 kΩ` base resistor from `GPIO 4`).

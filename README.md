# CAD-01 Aperture-Scaffold Observatory (`C = O × E × H × X`)

Benchtop metamaterial & multiplicative wave-gating testbed translating continuous **Spirograph phase dynamics** into a **discrete Kagome aperture scaffold (`O`)**, modulated by a **40 kHz carrier & dynamic phase wheel (`E`)**, a **bistable 2-story Kresling origami hysteresis stage (`H`)**, and a **quadrature-demodulated receiver (`X`)**.

---

## 1. Repository Structure

```text
cad01-aperture-observatory/
├── docs/
│   ├── ARCHITECTURE.md               # Theory: C = O × E × H × X, Halo/Mandorla/Aureole, & Null Tests
│   └── SCHEMATICS.md                 # Front-end schematics for Ultrasonic, Optical, & Vibration carriers
├── firmware/
│   └── CAD01_Controller/
│       └── CAD01_Controller.ino      # ESP32-S3 40 kHz PWM + 160 kHz I/Q demodulator + R/H/M/L modes
├── cad/
│   ├── cad01_enclosure.scad          # Parametric OpenSCAD 3D-printable flanges, carriage, & mounts
│   ├── generate_kagome_gate.py     # Spirograph density-field -> Kagome SVG/DXF + K-Score evaluator
│   ├── generate_kresling_collar.py   # 6-sided 2-story Kresling origami SVG/DXF cut/score generator
│   └── generate_phase_mask.py        # Rotating spirograph phase-wheel SVG/DXF generator
├── telemetry/
│   └── cad01_logger.py               # Serial logger: A-B-A-B Nulls, Hysteresis, 2D Heatmap, & Live Scope
├── tests/
│   └── test_kscore_pipeline.py       # Automated unit tests for CAD & K-Score pipeline
└── requirements.txt                  # Python dependencies
```

---

## 2. Hardware Wiring Pinout (ESP32-S3)

| Subsystem | Component | ESP32-S3 GPIO | Notes |
| :--- | :--- | :--- | :--- |
| **Emitter Drive (`E`)** | L293D / TC4427 `IN1` | **GPIO 4** | 40 kHz PWM (0° phase) |
| **Emitter Drive (`E`)** | L293D / TC4427 `IN2` | **GPIO 5** | 40 kHz PWM (180° push-pull inverted) |
| **Receiver (`X`)** | 40 kHz RX + MCP6002 Filter | **GPIO 1 (ADC1_CH0)** | Biased at **1.65 V** virtual ground |
| **History Stage (`H`)** | Stepper `STEP` / `DIR` | **GPIO 10 / GPIO 11** | Drives Kresling origami T8 lead-screw stage |
| **Phase Mask (`E`)** | Stepper `STEP` / `DIR` | **GPIO 12 / GPIO 13** | Drives rotating spirograph phase disk |
| **Stepper Enable** | Both Stepper Drivers `EN` | **GPIO 14** | Active LOW; disabled during ADC sampling to cut EMI |

---

## 3. Fabrication Checklist

- **3D Printed Parts (`cad/cad01_enclosure.scad`):**
  - `2x` `halo_flange` (PETG/PLA, 40% infill, 4 walls) — fits **75 mm ID / 85 mm OD** acrylic tube
  - `1x` `kresling_carriage` (PETG/PLA, 40% infill)
  - `1x` `motor_mount` (PETG/PLA, 50% infill)
  - `2x` `transducer_cap` (PETG/PLA, 30% infill, lined with 25 mm acoustic wedge foam)
- **Laser-Cut / Scored Parts (`cad/`):**
  - Run `python cad/generate_kagome_gate.py` → Cut `outputs/cad01_kagome_gate.dxf` from **3 mm cast acrylic** (target `K-Score ≥ 0.70`).
  - Run `python cad/generate_phase_mask.py` → Cut `outputs/cad01_phase_mask.dxf` from **2–3 mm opaque acrylic**.
  - Run `python cad/generate_kresling_collar.py` → Score & cut `outputs/cad01_kresling_collar.svg` from **0.3 mm polypropylene (PP)** sheet.

---

## 4. Bench Calibration & Verification Sequence

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Live Alignment & Gain Check (`--mode L`):**
   ```bash
   python telemetry/cad01_logger.py --port COM4 --mode L
   ```
   Verify `AMP` stays between **200 and 1,600 ADC counts** (below the 2,048 clip ceiling) and **Coherence ($\gamma^2$) $\ge 0.85$** when aligned.
3. **Perimeter Flanking Null (`--mode R`):**
   Swap the Kagome gate for a solid 3 mm acrylic blank disk and run the interleaved **A–B–A–B** protocol. Confirm **Extinction Ratio $\ge 15.0\text{ dB}$**.
4. **Origami Hysteresis Sweep (`--mode H`):**
   ```bash
   python telemetry/cad01_logger.py --port COM4 --mode H --mm-per-step 0.01
   ```
5. **2D Multiplicative Gate Heatmap (`--mode M`):**
   ```bash
   python telemetry/cad01_logger.py --port COM4 --mode M
   ```

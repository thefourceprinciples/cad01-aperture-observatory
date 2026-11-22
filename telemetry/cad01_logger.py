import os
import sys
import time
import argparse
from collections import deque
from datetime import datetime
import serial
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


def run_capture(port: str, baud: int, command: str, out_prefix: str) -> pd.DataFrame:
    print(f"[*] Connecting to {port} at {baud} baud...")
    with serial.Serial(port, baud, timeout=1.0) as ser:
        time.sleep(2.0)
        ser.reset_input_buffer()

        print(f"[*] Sending command '{command}' to CAD-01...")
        ser.write(command.encode("utf-8"))

        rows = []
        header = None
        last_rx_time = time.time()

        while True:
            raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
            if raw_line:
                last_rx_time = time.time()
                print(f"  {raw_line}")

                if raw_line.startswith(("STATE,", "SWEEP,", "SWEEP2D,")):
                    header = raw_line.split(",")
                    continue

                if header is not None:
                    parts = raw_line.split(",")
                    if len(parts) == len(header):
                        rows.append(parts)
            else:
                if header is not None and (time.time() - last_rx_time) > 1.5:
                    print("[*] Telemetry stream complete.")
                    break
                if (time.time() - last_rx_time) > 20.0:
                    print("[!] Timeout waiting for ESP32-S3 response.")
                    sys.exit(1)

    if not rows or header is None:
        print("[!] No valid telemetry rows captured.")
        sys.exit(1)

    df = pd.DataFrame(rows, columns=header)
    numeric_cols = ["TIME_MS", "H_STEPS", "E_STEPS", "AMP", "PHASE_DEG", "COHERENCE"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    csv_path = f"{out_prefix}.csv"
    df.to_csv(csv_path, index=False)
    print(f"[*] Saved raw telemetry to {csv_path}")
    return df


def analyze_abab(df: pd.DataFrame, out_prefix: str):
    """Computes Extinction Ratio (dB) and coherence drop for A-B-A-B null tests."""
    summary = df.groupby("STATE", sort=False).agg(
        mean_amp=("AMP", "mean"),
        std_amp=("AMP", "std"),
        mean_coh=("COHERENCE", "mean"),
        mean_phase=("PHASE_DEG", "mean"),
    )
    print("\n=== A-B-A-B NULL TEST SUMMARY ===")
    print(summary.to_string())

    try:
        p_active = 0.5 * (
            summary.loc["A1_ACTIVE", "mean_amp"] ** 2
            + summary.loc["A2_ACTIVE", "mean_amp"] ** 2
        )
        p_null = summary.loc["B1_H_NULL", "mean_amp"] ** 2
        p_noise = summary.loc["N0_NOISE", "mean_amp"] ** 2

        er_null_db = 10.0 * np.log10(max(p_active, 1e-9) / max(p_null, 1e-9))
        snr_db = 10.0 * np.log10(max(p_active, 1e-9) / max(p_noise, 1e-9))
        coh_active = 0.5 * (
            summary.loc["A1_ACTIVE", "mean_coh"] + summary.loc["A2_ACTIVE", "mean_coh"]
        )
        coh_null = summary.loc["B1_H_NULL", "mean_coh"]

        print(f"\n[*] Active SNR vs Noise Floor : {snr_db:.2f} dB")
        print(f"[*] Null Extinction Ratio (ER): {er_null_db:.2f} dB  (Target: >= 15.0 dB)")
        print(f"[*] Coherence (Active -> Null): {coh_active:.3f} -> {coh_null:.3f}")
        verdict = (
            "PASS"
            if (er_null_db >= 15.0 and coh_active >= 0.85 and coh_null <= 0.10)
            else "CHECK ISOLATION"
        )
        print(f"[*] Gate Multiplicative Verdict : {verdict}\n")
    except KeyError:
        print("[!] Missing expected A-B-A-B state labels.")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    x = np.arange(len(df))
    colors = {
        "N0_NOISE": "#7f8c8d",
        "A1_ACTIVE": "#27ae60",
        "B1_H_NULL": "#e74c3c",
        "A2_ACTIVE": "#2980b9",
    }
    bar_colors = [colors.get(s, "#34495e") for s in df["STATE"]]

    ax1.bar(x, df["AMP"], color=bar_colors, width=0.8)
    ax1.set_ylabel("Aureole Amplitude (ADC)")
    ax1.set_title("CAD-01 A-B-A-B Multiplicative Null Verification")
    ax1.grid(True, alpha=0.3)

    ax2.plot(x, df["COHERENCE"], marker="o", color="#8e44ad", linewidth=1.5)
    ax2.axhline(0.85, color="#27ae60", linestyle="--", label="Active Target (0.85)")
    ax2.axhline(0.05, color="#e74c3c", linestyle="--", label="Null Ceiling (0.05)")
    ax2.set_ylabel("40 kHz Coherence (γ²)")
    ax2.set_xlabel("Sample Index")
    ax2.set_ylim(-0.05, 1.05)
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = f"{out_prefix}_abab.png"
    plt.savefig(plot_path, dpi=150)
    print(f"[*] Saved A-B-A-B plot to {plot_path}")
    plt.show()


def analyze_hysteresis(df: pd.DataFrame, out_prefix: str, mm_per_step: float = 0.01):
    """Plots the History (H) loading vs. unloading hysteresis loop."""
    df["STROKE_MM"] = df["H_STEPS"] * mm_per_step
    load_df = df[df["SWEEP"] == "H_LOAD"]
    unload_df = df[df["SWEEP"] == "H_UNLOAD"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ax1.plot(load_df["STROKE_MM"], load_df["AMP"], "o-", color="#e67e22", label="H_LOAD (Compression)")
    ax1.plot(unload_df["STROKE_MM"], unload_df["AMP"], "s--", color="#2980b9", label="H_UNLOAD (Release)")
    ax1.set_ylabel("Aureole Amplitude (ADC)")
    ax1.set_title("CAD-01 History (H) Kresling Origami Hysteresis Loop")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(load_df["STROKE_MM"], load_df["PHASE_DEG"], "o-", color="#e67e22")
    ax2.plot(unload_df["STROKE_MM"], unload_df["PHASE_DEG"], "s--", color="#2980b9")
    ax2.set_ylabel("Carrier Phase Lag (deg)")
    ax2.set_xlabel("Kresling Axial Compression (mm)")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = f"{out_prefix}_hysteresis.png"
    plt.savefig(plot_path, dpi=150)
    print(f"[*] Saved hysteresis plot to {plot_path}")
    plt.show()


def analyze_2d_sweep(
    df: pd.DataFrame,
    out_prefix: str,
    mm_per_step: float = 0.01,
    deg_per_step: float = 1.8,
):
    """Pivots serpentine 2D grid telemetry into E x H coherence and amplitude heatmaps."""
    df["H_MM"] = (df["H_STEPS"] * mm_per_step).round(2)
    df["E_DEG"] = (df["E_STEPS"] * deg_per_step).round(1)

    amp_grid = df.pivot_table(index="H_MM", columns="E_DEG", values="AMP", aggfunc="mean")
    coh_grid = df.pivot_table(index="H_MM", columns="E_DEG", values="COHERENCE", aggfunc="mean")

    peak_idx = df["COHERENCE"].idxmax()
    peak_row = df.loc[peak_idx]
    print("\n=== 2D (E x H) PARAMETER SWEEP PEAK ===")
    print(f"[*] Peak Coherence (γ²) : {peak_row['COHERENCE']:.4f}")
    print(f"[*] Peak Amplitude      : {peak_row['AMP']:.1f} ADC")
    print(f"[*] Optimal H Stroke    : {peak_row['H_MM']:.2f} mm ({int(peak_row['H_STEPS'])} steps)")
    print(f"[*] Optimal E Angle     : {peak_row['E_DEG']:.1f} deg ({int(peak_row['E_STEPS'])} steps)\n")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    im1 = ax1.imshow(
        amp_grid.values,
        origin="lower",
        aspect="auto",
        cmap="inferno",
        extent=[amp_grid.columns.min(), amp_grid.columns.max(), amp_grid.index.min(), amp_grid.index.max()],
    )
    ax1.set_title("Aureole Amplitude (ADC Counts)")
    ax1.set_xlabel("Expression (E): Phase Mask Angle (deg)")
    ax1.set_ylabel("History (H): Kresling Compression (mm)")
    fig.colorbar(im1, ax=ax1, label="Amplitude")

    im2 = ax2.imshow(
        coh_grid.values,
        origin="lower",
        aspect="auto",
        cmap="viridis",
        vmin=0.0,
        vmax=1.0,
        extent=[coh_grid.columns.min(), coh_grid.columns.max(), coh_grid.index.min(), coh_grid.index.max()],
    )
    X_mesh, Y_mesh = np.meshgrid(coh_grid.columns.values, coh_grid.index.values)
    if np.nanmax(coh_grid.values) >= 0.85:
        ax2.contour(X_mesh, Y_mesh, coh_grid.values, levels=[0.85], colors="white", linewidths=1.5, linestyles="--")

    ax2.set_title("40 kHz Coherence γ² (White Dashed = 0.85 Gate)")
    ax2.set_xlabel("Expression (E): Phase Mask Angle (deg)")
    ax2.set_ylabel("History (H): Kresling Compression (mm)")
    fig.colorbar(im2, ax=ax2, label="Coherence (γ²)")

    plt.tight_layout()
    plot_path = f"{out_prefix}_2d_heatmap.png"
    plt.savefig(plot_path, dpi=150)
    print(f"[*] Saved 2D (E x H) heatmap to {plot_path}")
    plt.show()


def run_live_scope(port: str, baud: int, window_size: int = 200):
    """Real-time rolling oscilloscope for bench tuning."""
    print(f"[*] Connecting to {port} at {baud} baud for Live Oscilloscope...")
    ser = serial.Serial(port, baud, timeout=0.05)
    time.sleep(2.0)
    ser.reset_input_buffer()
    ser.write(b"L")
    print("[*] Live stream started. Close the plot window to stop.")

    t_buf = deque(maxlen=window_size)
    amp_buf = deque(maxlen=window_size)
    phase_buf = deque(maxlen=window_size)
    coh_buf = deque(maxlen=window_size)
    t0 = time.time()

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True)
    fig.canvas.manager.set_window_title("CAD-01 Live Aureole Oscilloscope")

    line_amp, = ax1.plot([], [], color="#e67e22", linewidth=1.8)
    ax1.set_ylabel("Amplitude (ADC)")
    ax1.set_ylim(0, 2100)
    ax1.axhline(1800, color="#e74c3c", linestyle=":", label="ADC Clip Warning (1800)")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    line_phase, = ax2.plot([], [], color="#2980b9", linewidth=1.8)
    ax2.set_ylabel("Phase Lag (deg)")
    ax2.set_ylim(-185, 185)
    ax2.grid(True, alpha=0.3)

    line_coh, = ax3.plot([], [], color="#8e44ad", linewidth=2.0)
    ax3.set_ylabel("Coherence (γ²)")
    ax3.set_xlabel("Elapsed Time (s)")
    ax3.set_ylim(-0.05, 1.05)
    ax3.axhline(0.85, color="#27ae60", linestyle="--", label="Active Gate Lock (0.85)")
    ax3.axhline(0.05, color="#e74c3c", linestyle="--", label="Null Ceiling (0.05)")
    ax3.legend(loc="upper left")
    ax3.grid(True, alpha=0.3)

title_text = ax1.set_title("Waiting for CAD-01 stream...")
def update(_frame):
while ser.in_waiting:
raw = ser.readline().decode("utf-8", errors="ignore").strip()
if raw.startswith("LIVE,") and not raw.startswith("LIVE,TIME_MS"):
parts = raw.split(",")
if len(parts) == 7:
try:
t_buf.append(time.time() - t0)
amp_buf.append(float(parts))
phase_buf.append(float(parts))
coh_buf.append(float(parts))
except ValueError:
pass
if len(t_buf) > 1:
xs = list(t_buf)
line_amp.set_data(xs, list(amp_buf))
line_phase.set_data(xs, list(phase_buf))
line_coh.set_data(xs, list(coh_buf))
ax3.set_xlim(max(0, xs[-1] - 10.0), max(10.0, xs[-1] + 0.2))
title_text.set_text(
f"LIVE | AMP: {amp_buf[-1]:.1f} ADC  |  PHASE: {phase_buf[-1]:+.1f}°  |  COHERENCE γ²: {coh_buf[-1]:.3f}"
)
return line_amp, line_phase, line_coh, title_text
def on_close(_event):
try:
ser.write(b"L")
time.sleep(0.1)
ser.close()
except Exception:
pass
fig.canvas.mpl_connect("close_event", on_close)
ani = FuncAnimation(fig, update, interval=50, blit=False, cache_frame_data=False)
plt.tight_layout()
plt.show()
def main():
parser = argparse.ArgumentParser(description="CAD-01 ESP32-S3 Telemetry Logger")
parser.add_argument("--port", required=True, help="Serial port (e.g., COM4 or /dev/ttyACM0)")
parser.add_argument("--baud", type=int, default=921600, help="Baud rate (default: 921600)")
parser.add_argument(
"--mode",
choices=["R", "H", "M", "L"],
required=True,
help="R = A-B-A-B Nulls | H = Hysteresis | M = 2D Heatmap | L = Live Scope",
)
parser.add_argument("--out-dir", default="outputs", help="Output directory")
parser.add_argument("--mm-per-step", type=float, default=0.01, help="Lead-screw mm per step")
parser.add_argument("--deg-per-step", type=float, default=1.8, help="Phase stepper degrees per step")
args = parser.parse_args()
if args.mode == "L":
run_live_scope(args.port, args.baud)
return
os.makedirs(args.out_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_prefix = os.path.join(args.out_dir, f"cad01_{args.mode}_{timestamp}")
df = run_capture(args.port, args.baud, args.mode, out_prefix)
if args.mode == "R":
analyze_abab(df, out_prefix)
elif args.mode == "H":
analyze_hysteresis(df, out_prefix, args.mm_per_step)
elif args.mode == "M":
analyze_2d_sweep(df, out_prefix, args.mm_per_step, args.deg_per_step)
if name == "main":
main()

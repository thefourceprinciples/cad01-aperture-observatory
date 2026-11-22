import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt


def wrap_phase(angle):
    """Wraps phase difference into [-pi, pi]."""
    return (angle + np.pi) % (2 * np.pi) - np.pi


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))


def run_aperture_simulation(dt=0.02, total_time=20.0, seed=42, out_json: str = ""):
    rng = np.random.default_rng(seed)
    steps = int(total_time / dt)
    t_arr = np.linspace(0, total_time, steps)

    # --- Aperture & Hysteresis Parameters ---
    C_open = 0.80        # Threshold to snap OPEN
    C_hold = 0.55        # Lower threshold to STAY open (prevents flicker)
    DeltaPhi_max = 0.35  # Max allowed phase mismatch (rad)
    G_min, G_max = 0.02, 1.0
    p_exp = 2.0          # Nonlinear conductance exponent

    # Gains for continuous aperture functional a(t)
    alpha, beta, delta, eta = 6.0, 2.5, 3.0, 2.5

    # --- 5 Kuramoto Oscillators ---
    N = 5
    omega = np.array([1.95, 1.98, 2.00, 2.02, 2.05])
    theta = rng.uniform(-np.pi, np.pi, size=N)

    is_latched_open = False
    a = 0.0
    events = []
    active_event = None

    history = {
        "time": [], "openness": [], "coherence": [], "R": [],
        "DeltaPhi": [], "G_A": [], "noise": [], "stress": [], "latched": []
    }

    for t in t_arr:
        # Scenario timeline: closed -> phase-locked open -> noise bump -> stress forced close
        K_coupling = 2.8 if 3.5 <= t <= 14.5 else 0.2
        D_noise = 0.35 if (9.0 <= t <= 10.5 or 13.5 <= t <= 16.0) else 0.05
        S_stress = 0.65 if 13.5 <= t <= 16.0 else 0.10

        # Kuramoto Oscillator Update
        dtheta = np.zeros(N)
        for i in range(N):
            dtheta[i] = omega[i] + (K_coupling / N) * np.sum(np.sin(theta - theta[i]))
        theta = theta + dt * dtheta + rng.normal(0, 0.08 * D_noise, size=N)

        z = np.mean(np.exp(1j * theta))
        R = float(np.abs(z))
        Theta = float(np.angle(z))
        DeltaPhi = float(np.abs(wrap_phase(theta[0] - Theta)))

        # Fource Coherence C = O * E * H * X
        O_align = 0.95 if 3.0 <= t <= 16.5 else 0.30
        E_compat = max(0.0, 1.0 - D_noise)
        H_memory = 0.95 if is_latched_open else 0.75
        X_catalyst = R
        C_total = float(np.clip(O_align * E_compat * H_memory * X_catalyst, 0.0, 1.0))

        # Hysteresis Latch Logic (C_open > C_hold)
        if not is_latched_open:
            if C_total >= C_open and DeltaPhi <= DeltaPhi_max and S_stress < 0.5:
                is_latched_open = True
                active_event = {
                    "event_id": f"EVT-{len(events)+1:04d}",
                    "start_time": round(float(t), 2),
                    "opening_threshold": C_open,
                    "holding_threshold": C_hold,
                    "max_phase_mismatch": DeltaPhi_max,
                    "peak_conductance": 0.0,
                    "noise_level": round(float(D_noise), 3),
                    "stress_level": round(float(S_stress), 3),
                }
        else:
            if C_total < C_hold or S_stress >= 0.5 or DeltaPhi > DeltaPhi_max * 1.5:
                is_latched_open = False
                if active_event:
                    active_event["end_time"] = round(float(t), 2)
                    active_event["noise_level"] = round(float(D_noise), 3)
                    active_event["stress_level"] = round(float(S_stress), 3)
                    active_event["result"] = "forced_close" if S_stress >= 0.5 else "safe_close"
                    events.append(active_event)
                    active_event = None

        # Graded Openness a(t) & Nonlinear Conductance G_A(t)
        threshold_ref = C_hold if is_latched_open else C_open
        drive = alpha * (C_total - threshold_ref) - beta * DeltaPhi - delta * D_noise - eta * S_stress
        target_a = sigmoid(drive) if is_latched_open else 0.15 * sigmoid(drive)
        a = float(np.clip(a + 8.0 * dt * (target_a - a), 0.0, 1.0))

        G_A = float(G_min + (a ** p_exp) * (G_max - G_min))
        if active_event and G_A > active_event["peak_conductance"]:
            active_event["peak_conductance"] = round(G_A, 4)

        history["time"].append(t)
        history["openness"].append(a)
        history["coherence"].append(C_total)
        history["R"].append(R)
        history["DeltaPhi"].append(DeltaPhi)
        history["G_A"].append(G_A)
        history["noise"].append(D_noise)
        history["stress"].append(S_stress)
        history["latched"].append(1.0 if is_latched_open else 0.0)

    print("\n=== LOGGED APERTURE EVENTS (Track E Schema) ===")
    print(json.dumps(events, indent=2))

    if out_json:
        os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
        print(f"[*] Saved event log -> {out_json}")

    return history


def plot_simulation(hist):
    fig, axes = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True)
    t = hist["time"]

    axes[0].plot(t, hist["R"], label="Kuramoto Order (R)", color="#8e44ad", linewidth=1.8)
    axes[0].plot(t, hist["coherence"], label="Fource Coherence (C)", color="#2980b9", linewidth=2.0)
    axes[0].axhline(0.80, color="#27ae60", linestyle="--", label="C_open (0.80)")
    axes[0].axhline(0.55, color="#e67e22", linestyle=":", label="C_hold (0.55)")
    axes[0].set_ylabel("Coherence / Order")
    axes[0].set_title("CAD-01 Dynamical Aperture Simulation (Hysteresis & Kuramoto Phase-Lock)")
    axes[0].legend(loc="upper right", ncol=2)
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(t, hist["openness"], label="Aperture Openness a(t)", color="#27ae60", linewidth=2.0)
    axes[1].plot(t, hist["G_A"], label="Conductance G_A(t)", color="#16a085", linestyle="--", linewidth=1.8)
    axes[1].fill_between(t, 0, hist["latched"], color="#27ae60", alpha=0.12, label="Latch State (OPEN)")
    axes[1].set_ylabel("Openness / Conductance")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(t, hist["noise"], label="Decoherence Noise (D_noise)", color="#7f8c8d", linewidth=1.5)
    axes[2].plot(t, hist["stress"], label="Boundary Stress (S_stress)", color="#e74c3c", linewidth=1.8)
    axes[2].plot(t, hist["DeltaPhi"], label="Phase Mismatch (ΔΦ rad)", color="#f39c12", linewidth=1.5)
    axes[2].set_ylabel("Perturbations")
    axes[2].set_xlabel("Simulation Time (s)")
    axes[2].legend(loc="upper right")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CAD-01 Track B Dynamical Aperture Simulator")
    parser.add_argument("--save-events", default="outputs/sim_aperture_events.json", help="Path to save JSON events")
    parser.add_argument("--no-plot", action="store_true", help="Run headless without opening matplotlib window")
    args = parser.parse_args()

    hist = run_aperture_simulation(out_json=args.save_events)
    if not args.no_plot:
        plot_simulation(hist)

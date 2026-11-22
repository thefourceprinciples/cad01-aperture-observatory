import os
import argparse
import numpy as np


def generate_phase_mask(
    out_dir: str,
    disk_od: float = 84.0,
    active_radius: float = 35.0,
    shaft_d: float = 5.0,
    lobes: int = 6,
    slot_width: float = 3.2,
):
    """Exports laser-ready SVG and R12 DXF files for the rotating spirograph phase wheel."""
    os.makedirs(out_dir, exist_ok=True)
    svg_path = os.path.join(out_dir, "cad01_phase_mask.svg")
    dxf_path = os.path.join(out_dir, "cad01_phase_mask.dxf")

    t = np.linspace(0, 2 * np.pi, 1200, endpoint=False)
    r_base = active_radius * 0.52
    r_mod = active_radius * 0.34
    twist = 0.65 * np.sin(lobes * t)

    r_curve = r_base + r_mod * np.cos(lobes * t)
    theta_curve = t + twist

    x_center = r_curve * np.cos(theta_curve)
    y_center = r_curve * np.sin(theta_curve)

    dx = np.gradient(x_center)
    dy = np.gradient(y_center)
    norm = np.hypot(dx, dy) + 1e-12
    nx = -dy / norm
    ny = dx / norm

    half_w = slot_width / 2.0
    x_outer = x_center + half_w * nx
    y_outer = y_center + half_w * ny
    x_inner = x_center - half_w * nx
    y_inner = y_center - half_w * ny

    hub_bolt_r = 7.0
    hub_angles = [0, 120, 240]

    half = disk_od / 2.0 + 2.0
    svg = [
        f'<svg xmlns="http://w3.org" width="{2*half}mm" height="{2*half}mm" '
        f'viewBox="{-half} {-half} {2*half} {2*half}">',
        f'  <circle cx="0" cy="0" r="{disk_od/2.0:.3f}" fill="none" stroke="red" stroke-width="0.2"/>',
        f'  <circle cx="0" cy="0" r="{active_radius:.3f}" fill="none" stroke="blue" stroke-width="0.15" stroke-dasharray="2,2"/>',
        f'  <circle cx="0" cy="0" r="{shaft_d/2.0:.3f}" fill="none" stroke="red" stroke-width="0.2"/>',
    ]

    for deg in hub_angles:
        bx = hub_bolt_r * np.cos(np.radians(deg))
        by = hub_bolt_r * np.sin(np.radians(deg))
        svg.append(f'  <circle cx="{bx:.3f}" cy="{by:.3f}" r="1.55" fill="none" stroke="red" stroke-width="0.2"/>')

    outer_pts = " ".join(f"{x:.3f},{y:.3f}" for x, y in zip(x_outer, y_outer))
    inner_pts = " ".join(f"{x:.3f},{y:.3f}" for x, y in zip(x_inner, y_inner))
    svg.append(f'  <polygon points="{outer_pts}" fill="none" stroke="red" stroke-width="0.2"/>')
    svg.append(f'  <polygon points="{inner_pts}" fill="none" stroke="red" stroke-width="0.2"/>')
    svg.append("</svg>")

    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

    dxf = ["0", "SECTION", "2", "ENTITIES"]

    def add_dxf_circle(cx, cy, r, layer):
        dxf.extend(["0", "CIRCLE", "8", layer, "10", f"{cx:.4f}", "20", f"{cy:.4f}", "30", "0.0", "40", f"{r:.4f}"])

    def add_dxf_polyline(xs, ys, layer):
        dxf.extend(["0", "POLYLINE", "8", layer, "66", "1", "70", "1"])
        for x, y in zip(xs, ys):
            dxf.extend(["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0"])
        dxf.extend(["0", "SEQEND"])

    add_dxf_circle(0.0, 0.0, disk_od / 2.0, "WHEEL_CUT")
    add_dxf_circle(0.0, 0.0, shaft_d / 2.0, "SHAFT_BORE")
    add_dxf_circle(0.0, 0.0, active_radius, "WAVEGUIDE_REF")
    for deg in hub_angles:
        add_dxf_circle(hub_bolt_r * np.cos(np.radians(deg)), hub_bolt_r * np.sin(np.radians(deg)), 1.55, "HUB_BOLTS")

    add_dxf_polyline(x_outer, y_outer, "SPIROGRAPH_SLOT")
    add_dxf_polyline(x_inner, y_inner, "SPIROGRAPH_SLOT")

    dxf.extend(["0", "ENDSEC", "0", "EOF"])
    with open(dxf_path, "w", encoding="utf-8") as f:
        f.write("\n".join(dxf))

    print(f"[*] Exported Rotating Phase Mask SVG -> {svg_path}")
    print(f"[*] Exported Rotating Phase Mask DXF -> {dxf_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Rotating Spirograph Phase Wheel (E)")
    parser.add_argument("--out-dir", default="outputs", help="Output directory")
    parser.add_argument("--disk-od", type=float, default=84.0, help="Outer diameter of phase disk (mm)")
    parser.add_argument("--tube-id", type=float, default=75.0, help="Waveguide inner diameter (mm)")
    parser.add_argument("--lobes", type=int, default=6, help="Number of rotational symmetry lobes (default: 6)")
    args = parser.parse_args()

    generate_phase_mask(
        out_dir=args.out_dir,
        disk_od=args.disk_od,
        active_radius=args.tube_id / 2.0,
        lobes=args.lobes,
    )

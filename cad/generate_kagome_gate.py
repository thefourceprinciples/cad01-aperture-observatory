import os
import argparse
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter
from scipy.spatial import cKDTree


def generate_spirograph_density(
    grid_size: int = 600,
    radius_mm: float = 36.0,
    R: float = 5.0,
    r: float = 3.0,
    d: float = 4.2,
    rotations: int = 6,
    sigma_px: float = 2.2,
):
    """Generates accumulated density field D(x, y) from phase-shifted hypotrochoids."""
    t = np.linspace(0, 2 * np.pi * r, 8000, endpoint=False)
    x0 = (R - r) * np.cos(t) + d * np.cos(((R - r) / r) * t)
    y0 = (R - r) * np.sin(t) - d * np.sin(((R - r) / r) * t)

    scale = (radius_mm * 0.92) / np.max(np.hypot(x0, y0))
    x0 *= scale
    y0 *= scale

    density = np.zeros((grid_size, grid_size), dtype=np.float64)
    extent = radius_mm * 1.1
    bins = np.linspace(-extent, extent, grid_size + 1)

    for k in range(rotations):
        theta = (2 * np.pi * k) / rotations
        phase_shift = (np.pi * k) / rotations
        xt = (R - r) * np.cos(t + phase_shift) + d * np.cos(((R - r) / r) * (t + phase_shift))
        yt = (R - r) * np.sin(t + phase_shift) - d * np.sin(((R - r) / r) * (t + phase_shift))
        xt *= scale
        yt *= scale

        xr = xt * np.cos(theta) - yt * np.sin(theta)
        yr = xt * np.sin(theta) + yt * np.cos(theta)

        hist, _, _ = np.histogram2d(yr, xr, bins=[bins, bins])
        density += hist

    density = gaussian_filter(density, sigma=sigma_px)
    density /= np.max(density) + 1e-12
    coords = 0.5 * (bins[:-1] + bins[1:])
    return density, coords


def extract_lattice_and_kscore(density: np.ndarray, coords: np.ndarray, active_radius: float = 35.0):
    """Extracts persistent nodes/apertures and evaluates K-Score against ideal kagome topology."""
    local_max = (density == maximum_filter(density, size=15)) & (density > 0.35)
    iy, ix = np.where(local_max)
    nodes = np.column_stack([coords[ix], coords[iy]])

    r_nodes = np.hypot(nodes[:, 0], nodes[:, 1])
    nodes = nodes[r_nodes <= active_radius]

    tree = cKDTree(nodes)
    dists, _ = tree.query(nodes, k=min(6, len(nodes)))
    nn_dist = np.median(dists[:, 1])
    edges = list(tree.query_pairs(r=nn_dist * 1.28))

    degrees = np.zeros(len(nodes), dtype=int)
    for u, v in edges:
        degrees[u] += 1
        degrees[v] += 1

    interior = np.hypot(nodes[:, 0], nodes[:, 1]) < (active_radius * 0.8)
    z_score = np.mean(degrees[interior] == 4) if np.any(interior) else 0.0

    if edges:
        edge_lengths = np.array([np.linalg.norm(nodes[u] - nodes[v]) for u, v in edges])
        reg_score = max(0.0, 1.0 - (np.std(edge_lengths) / (np.mean(edge_lengths) + 1e-9)))
    else:
        reg_score = 0.0

    adj = {i: set() for i in range(len(nodes))}
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)

    triangles = set()
    for u in range(len(nodes)):
        for v in adj[u]:
            for w in adj[u].intersection(adj[v]):
                triangles.add(tuple(sorted((u, v, w))))

    expected_tri = max(1.0, (2.0 / 3.0) * len(nodes))
    tri_score = min(1.0, len(triangles) / expected_tri)

    yy, xx = np.meshgrid(coords, coords, indexing="ij")
    mask_inside = np.hypot(xx, yy) <= active_radius
    void_mask = (density < 0.28) & mask_inside
    open_ratio = np.sum(void_mask) / np.sum(mask_inside)
    void_score = max(0.0, 1.0 - abs(open_ratio - 0.45) / 0.45)

    k_score = 0.30 * z_score + 0.25 * reg_score + 0.25 * tri_score + 0.20 * void_score
    metrics = {
        "k_score": round(float(k_score), 4),
        "coordination_z4": round(float(z_score), 4),
        "edge_regularity": round(float(reg_score), 4),
        "triangle_fidelity": round(float(tri_score), 4),
        "open_aperture_ratio": round(float(open_ratio), 4),
        "node_count": int(len(nodes)),
        "edge_count": int(len(edges)),
        "triangle_count": int(len(triangles)),
    }
    return nodes, edges, metrics


def export_gate_svg_and_dxf(
    nodes: np.ndarray,
    edges: list,
    out_dir: str,
    flange_od: float = 88.0,
    tube_id: float = 75.0,
    strut_width: float = 1.6,
):
    """Exports laser-ready SVG and R12 DXF files for the Halo flange + Kagome lattice."""
    os.makedirs(out_dir, exist_ok=True)
    svg_path = os.path.join(out_dir, "cad01_kagome_gate.svg")
    dxf_path = os.path.join(out_dir, "cad01_kagome_gate.dxf")

    half = flange_od / 2.0 + 2.0
    bolt_r = (flange_od + tube_id) / 4.0
    bolt_angles = [0, 90, 180, 270]

    svg_lines = [
        f'<svg xmlns="http://w3.org" width="{2*half}mm" height="{2*half}mm" '
        f'viewBox="{-half} {-half} {2*half} {2*half}">',
        f'  <circle cx="0" cy="0" r="{flange_od/2.0:.3f}" fill="none" stroke="red" stroke-width="0.2"/>',
        f'  <circle cx="0" cy="0" r="{tube_id/2.0:.3f}" fill="none" stroke="blue" stroke-width="0.15" stroke-dasharray="2,2"/>',
    ]
    for deg in bolt_angles:
        bx = bolt_r * np.cos(np.radians(deg))
        by = bolt_r * np.sin(np.radians(deg))
        svg_lines.append(f'  <circle cx="{bx:.3f}" cy="{by:.3f}" r="1.6" fill="none" stroke="red" stroke-width="0.2"/>')

    for u, v in edges:
        x1, y1 = nodes[u]
        x2, y2 = nodes[v]
        svg_lines.append(
            f'  <line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="black" stroke-width="{strut_width}" stroke-linecap="round"/>'
        )
    svg_lines.append("</svg>")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))

    dxf = ["0", "SECTION", "2", "ENTITIES"]

    def add_dxf_circle(cx, cy, r, layer):
        dxf.extend(["0", "CIRCLE", "8", layer, "10", f"{cx:.4f}", "20", f"{cy:.4f}", "30", "0.0", "40", f"{r:.4f}"])

    def add_dxf_line(x1, y1, x2, y2, layer):
        dxf.extend([
            "0", "LINE", "8", layer,
            "10", f"{x1:.4f}", "20", f"{y1:.4f}", "30", "0.0",
            "11", f"{x2:.4f}", "21", f"{y2:.4f}", "31", "0.0",
        ])

    add_dxf_circle(0.0, 0.0, flange_od / 2.0, "HALO_CUT")
    add_dxf_circle(0.0, 0.0, tube_id / 2.0, "WAVEGUIDE_REF")
    for deg in bolt_angles:
        add_dxf_circle(bolt_r * np.cos(np.radians(deg)), bolt_r * np.sin(np.radians(deg)), 1.6, "BOLT_HOLES")

    for u, v in edges:
        add_dxf_line(nodes[u, 0], nodes[u, 1], nodes[v, 0], nodes[v, 1], "KAGOME_STRUTS")

    dxf.extend(["0", "ENDSEC", "0", "EOF"])
    with open(dxf_path, "w", encoding="utf-8") as f:
        f.write("\n".join(dxf))

    print(f"[*] Exported Kagome Gate SVG -> {svg_path}")
    print(f"[*] Exported Kagome Gate DXF -> {dxf_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Spirograph-to-Kagome Gate & K-Score")
    parser.add_argument("--out-dir", default="outputs", help="Output directory")
    parser.add_argument("--tube-id", type=float, default=75.0, help="Waveguide inner diameter (mm)")
    parser.add_argument("--flange-od", type=float, default=88.0, help="Halo outer flange diameter (mm)")
    args = parser.parse_args()

    density, coords = generate_spirograph_density(radius_mm=args.tube_id / 2.0)
    nodes, edges, metrics = extract_lattice_and_kscore(density, coords, active_radius=(args.tube_id / 2.0) - 1.5)

    print("\n=== KAGOME GATE K-SCORE REPORT ===")
    for k, v in metrics.items():
        print(f"  {k:<22}: {v}")
    print()

    export_gate_svg_and_dxf(nodes, edges, args.out_dir, flange_od=args.flange_od, tube_id=args.tube_id)

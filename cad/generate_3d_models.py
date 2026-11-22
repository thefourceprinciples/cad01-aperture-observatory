import os
import sys
import struct
import argparse
import numpy as np

# Ensure local imports work whether run from repo root or inside cad/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_kagome_gate import generate_spirograph_density, extract_lattice_and_kscore


def write_binary_stl(filename: str, triangles: np.ndarray):
    """Writes an (N, 3, 3) array of 3D triangles directly to a binary STL file."""
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    n_tris = len(triangles)
    header = b"CAD-01 Procedural 3D Mesh Generator".ljust(80, b"\0")

    v0 = triangles[:, 0]
    v1 = triangles[:, 1]
    v2 = triangles[:, 2]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, norms, out=np.zeros_like(normals), where=norms > 1e-12)

    with open(filename, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", n_tris))
        for i in range(n_tris):
            f.write(struct.pack("<3f", *normals[i]))
            f.write(struct.pack("<3f", *v0[i]))
            f.write(struct.pack("<3f", *v1[i]))
            f.write(struct.pack("<3f", *v2[i]))
            f.write(struct.pack("<H", 0))

    print(f"[*] Exported {n_tris:,} triangles -> {filename}")


def make_strut_box(p1, p2, width: float, z0: float, z1: float) -> list:
    """Builds a 3D rectangular bar between 2D points p1 and p2 extruded from z0 to z1."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = np.hypot(dx, dy)
    if length < 1e-6:
        return []

    nx = (-dy / length) * (width / 2.0)
    ny = (dx / length) * (width / 2.0)

    c0 = (x1 + nx, y1 + ny)
    c1 = (x1 - nx, y1 - ny)
    c2 = (x2 - nx, y2 - ny)
    c3 = (x2 + nx, y2 + ny)
    pts = [c0, c1, c2, c3]

    tris = []
    # Bottom face (z0) & Top face (z1)
    tris.append([[c0[0], c0[1], z0], [c2[0], c2[1], z0], [c1[0], c1[1], z0]])
    tris.append([[c0[0], c0[1], z0], [c3[0], c3[1], z0], [c2[0], c2[1], z0]])
    tris.append([[c0[0], c0[1], z1], [c1[0], c1[1], z1], [c2[0], c2[1], z1]])
    tris.append([[c0[0], c0[1], z1], [c2[0], c2[1], z1], [c3[0], c3[1], z1]])

    # 4 side walls
    for i in range(4):
        a = pts[i]
        b = pts[(i + 1) % 4]
        tris.append([[a[0], a[1], z0], [b[0], b[1], z0], [b[0], b[1], z1]])
        tris.append([[a[0], a[1], z0], [b[0], b[1], z1], [a[0], a[1], z1]])

    return tris


def make_annulus_ring(r_in: float, r_out: float, z0: float, z1: float, segs: int = 96) -> list:
    """Builds a solid 3D washer/ring between r_in and r_out extruded from z0 to z1."""
    angles = np.linspace(0, 2 * np.pi, segs + 1)
    tris = []

    for i in range(segs):
        a0, a1 = angles[i], angles[i + 1]
        in0 = (r_in * np.cos(a0), r_in * np.sin(a0))
        in1 = (r_in * np.cos(a1), r_in * np.sin(a1))
        out0 = (r_out * np.cos(a0), r_out * np.sin(a0))
        out1 = (r_out * np.cos(a1), r_out * np.sin(a1))

        # Top face (z1)
        tris.append([[in0[0], in0[1], z1], [out0[0], out0[1], z1], [out1[0], out1[1], z1]])
        tris.append([[in0[0], in0[1], z1], [out1[0], out1[1], z1], [in1[0], in1[1], z1]])
        # Bottom face (z0)
        tris.append([[in0[0], in0[1], z0], [out1[0], out1[1], z0], [out0[0], out0[1], z0]])
        tris.append([[in0[0], in0[1], z0], [in1[0], in1[1], z0], [out1[0], out1[1], z0]])
        # Outer wall
        tris.append([[out0[0], out0[1], z0], [out1[0], out1[1], z0], [out1[0], out1[1], z1]])
        tris.append([[out0[0], out0[1], z0], [out1[0], out1[1], z1], [out0[0], out0[1], z1]])
        # Inner wall
        tris.append([[in0[0], in0[1], z0], [in1[0], in1[1], z1], [in1[0], in1[1], z0]])
        tris.append([[in0[0], in0[1], z0], [in0[0], in0[1], z1], [in1[0], in1[1], z1]])

    return tris


def build_3d_kagome_gate(
    out_dir: str = "outputs",
    tube_id: float = 75.0,
    flange_od: float = 88.0,
    thickness: float = 3.0,
    strut_width: float = 2.0,
) -> np.ndarray:
    """Generates a 3D printable binary STL of the Spirograph-to-Kagome Gate + Halo Rim."""
    density, coords = generate_spirograph_density(radius_mm=tube_id / 2.0)
    nodes, edges, metrics = extract_lattice_and_kscore(density, coords, active_radius=(tube_id / 2.0) - 1.0)
    print(f"[*] Building 3D Kagome Mesh (K-Score = {metrics['k_score']})...")

    tris = []
    tris.extend(make_annulus_ring(r_in=(tube_id / 2.0) - 1.5, r_out=flange_od / 2.0, z0=0.0, z1=thickness))
    for u, v in edges:
        tris.extend(make_strut_box(nodes[u], nodes[v], width=strut_width, z0=0.0, z1=thickness))

    tri_arr = np.array(tris, dtype=np.float32)
    stl_path = os.path.join(out_dir, "cad01_kagome_gate_3d.stl")
    write_binary_stl(stl_path, tri_arr)
    return tri_arr


def build_3d_spirograph_wheel(
    out_dir: str = "outputs",
    disk_od: float = 84.0,
    tube_id: float = 75.0,
    thickness: float = 2.4,
    lobes: int = 6,
) -> np.ndarray:
    """Generates a 3D printable binary STL of the Rotating Spirograph Phase Wheel."""
    tris = []
    r_active = tube_id / 2.0

    tris.extend(make_annulus_ring(r_in=r_active - 1.0, r_out=disk_od / 2.0, z0=0.0, z1=thickness))
    tris.extend(make_annulus_ring(r_in=2.55, r_out=10.0, z0=0.0, z1=thickness))

    t = np.linspace(0, 2 * np.pi, 360)
    for k in range(lobes):
        phase = (2 * np.pi * k) / lobes
        r_rib = np.linspace(9.5, r_active - 0.5, len(t))
        theta_rib = phase + 0.85 * np.sin(np.linspace(0, np.pi, len(t)))
        xs = r_rib * np.cos(theta_rib)
        ys = r_rib * np.sin(theta_rib)

        for i in range(len(t) - 1):
            tris.extend(make_strut_box((xs[i], ys[i]), (xs[i + 1], ys[i + 1]), width=2.8, z0=0.0, z1=thickness))

    tri_arr = np.array(tris, dtype=np.float32)
    stl_path = os.path.join(out_dir, "cad01_phase_wheel_3d.stl")
    write_binary_stl(stl_path, tri_arr)
    return tri_arr


def build_3d_kresling_bellows(
    out_dir: str = "outputs",
    radius: float = 35.0,
    compression: float = 0.0,
    sides: int = 6,
) -> np.ndarray:
    """Generates a 3D STL of the 2-Story Counter-Twisting Kresling Origami Bellows (H)."""
    h_story = 30.3 * (1.0 - 0.62 * compression)
    twist = np.radians(38.2 * compression)
    tris = []

    for story in range(2):
        z0 = story * h_story
        z1 = (story + 1) * h_story
        a0 = 0.0 if story == 0 else twist
        a1 = twist if story == 0 else 0.0

        for i in range(sides):
            t0 = (2 * np.pi * i) / sides + a0
            t1 = (2 * np.pi * (i + 1)) / sides + a0
            u0 = (2 * np.pi * i) / sides + a1
            u1 = (2 * np.pi * (i + 1)) / sides + a1

            b0 = [radius * np.cos(t0), radius * np.sin(t0), z0]
            b1 = [radius * np.cos(t1), radius * np.sin(t1), z0]
            top0 = [radius * np.cos(u0), radius * np.sin(u0), z1]
            top1 = [radius * np.cos(u1), radius * np.sin(u1), z1]

            tris.append([b0, b1, top1])
            tris.append([b0, top1, top0])

    tri_arr = np.array(tris, dtype=np.float32)
    stl_path = os.path.join(out_dir, "cad01_kresling_bellows_3d.stl")
    write_binary_stl(stl_path, tri_arr)
    return tri_arr


def preview_3d_meshes(kagome_tris: np.ndarray, wheel_tris: np.ndarray, kresling_tris: np.ndarray):
    """Opens an interactive 3D matplotlib window showing all three generated meshes."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(14, 5))
    models = [
        ("Kagome Gate (O)", kagome_tris, "#58a6ff"),
        ("Spirograph Phase Wheel (E)", wheel_tris, "#f0883e"),
        ("2-Story Kresling Collar (H)", kresling_tris, "#3fb950"),
    ]

    for idx, (title, tris, color) in enumerate(models, start=1):
        ax = fig.add_subplot(1, 3, idx, projection="3d")
        poly = Poly3DCollection(tris, alpha=0.85, facecolor=color, edgecolor="k", linewidths=0.15)
        ax.add_collection3d(poly)

        mins = tris.reshape(-1, 3).min(axis=0)
        maxs = tris.reshape(-1, 3).max(axis=0)
        span = max(maxs - mins) / 2.0
        mid = (maxs + mins) / 2.0
        ax.set_xlim(mid[0] - span, mid[0] + span)
        ax.set_ylim(mid[1] - span, mid[1] + span)
        ax.set_zlim(mid[2] - span, mid[2] + span)
        ax.set_title(title)
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_zlabel("Z (mm)")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CAD-01 Pure-Python 3D STL Mesh Generator")
    parser.add_argument("--out-dir", default="outputs", help="Output directory for .stl files")
    parser.add_argument("--tube-id", type=float, default=75.0, help="Waveguide inner diameter (mm)")
    parser.add_argument("--compression", type=float, default=0.35, help="Kresling compression (0.0 to 1.0)")
    parser.add_argument("--preview", action="store_true", help="Pop up an interactive 3D render window")
    args = parser.parse_args()

    kag_tris = build_3d_kagome_gate(out_dir=args.out_dir, tube_id=args.tube_id)
    whl_tris = build_3d_spirograph_wheel(out_dir=args.out_dir, tube_id=args.tube_id)
    krs_tris = build_3d_kresling_bellows(out_dir=args.out_dir, compression=args.compression)

    if args.preview:
        preview_3d_meshes(kag_tris, whl_tris, krs_tris)

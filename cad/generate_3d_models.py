import os
import struct
import argparse
import numpy as np
from generate_kagome_gate import generate_spirograph_density, extract_lattice_and_kscore


def write_binary_stl(filename: str, triangles: np.ndarray):
    """Writes an (N, 3, 3) array of 3D triangles directly to a binary STL file."""
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    n_tris = len(triangles)
    header = b"CAD-01 Procedural 3D Mesh Generator".ljust(80, b"\0")

    # Compute face normals via cross product
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

    # 4 base corners (counter-clockwise)
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
):
    """Generates a 3D printable binary STL of the Spirograph-to-Kagome Gate + Halo Rim."""
    density, coords = generate_spirograph_density(radius_mm=tube_id / 2.0)
    nodes, edges, metrics = extract_lattice_and_kscore(density, coords, active_radius=(tube_id / 2.0) - 1.0)
    print(f"[*] Building 3D Kagome Mesh (K-Score = {metrics['k_score']})...")

    tris = []
    # 1. Outer Halo clamping ring (from tube_id/2 to flange_od/2)
    tris.extend(make_annulus_ring(r_in=(tube_id / 2.0) - 1.5, r_out=flange_od / 2.0, z0=0.0, z1=thickness))

    # 2. Extrude every Kagome lattice strut into a 3D structural beam
    for u, v in edges:
        tris.extend(make_strut_box(nodes[u], nodes[v], width=strut_width, z0=0.0, z1=thickness))

    stl_path = os.path.join(out_dir, "cad01_kagome_gate_3d.stl")
    write_binary_stl(stl_path, np.array(tris, dtype=np.float32))


def build_3d_spirograph_wheel(
    out_dir: str = "outputs",
    disk_od: float = 84.0,
    tube_id: float = 75.0,
    thickness: float = 2.4,
    lobes: int = 6,
):
    """Generates a 3D printable binary STL of the Rotating Spirograph Phase Wheel."""
    tris = []
    r_active = tube_id / 2.0

    # Outer rim & central motor hub ring (5 mm shaft bore)
    tris.extend(make_annulus_ring(r_in=r_active - 1.0, r_out=disk_od / 2.0, z0=0.0, z1=thickness))
    tris.extend(make_annulus_ring(r_in=2.55, r_out=10.0, z0=0.0, z1=thickness))

    # Spiral hypotrochoid structural ribs connecting hub to outer rim
    t = np.linspace(0, 2 * np.pi, 360)
    for k in range(lobes):
        phase = (2 * np.pi * k) / lobes
        r_rib = np.linspace(9.5, r_active - 0.5, len(t))
        theta_rib = phase + 0.85 * np.sin(np.linspace(0, np.pi, len(t)))
        xs = r_rib * np.cos(theta_rib)
        ys = r_rib * np.sin(theta_rib)

        for i in range(len(t) - 1):
            tris.extend(make_strut_box((xs[i], ys[i]), (xs[i + 1], ys[i + 1]), width=2.8, z0=0.0, z1=thickness))

    stl_path = os.path.join(out_dir, "cad01_phase_wheel_3d.stl")
    write_binary_stl(stl_path, np.array(tris, dtype=np.float32))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CAD-01 Pure-Python 3D STL Mesh Generator")
    parser.add_argument("--out-dir", default="outputs", help="Output directory for .stl files")
    parser.add_argument("--tube-id", type=float, default=75.0, help="Waveguide inner diameter (mm)")
    args = parser.parse_args()

    build_3d_kagome_gate(out_dir=args.out_dir, tube_id=args.tube_id)
    build_3d_spirograph_wheel(out_dir=args.out_dir, tube_id=args.tube_id)

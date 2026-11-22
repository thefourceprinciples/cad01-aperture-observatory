import os
import argparse


def export_kresling_pattern(
    out_dir: str,
    sides: int = 6,
    panel_width: float = 35.0,
    panel_height: float = 33.4,
    flange_height: float = 8.0,
    overlap_tab: float = 10.0,
):
    """Exports a 2-story symmetrical counter-twisting Kresling crease pattern (SVG + DXF)."""
    os.makedirs(out_dir, exist_ok=True)
    svg_path = os.path.join(out_dir, "cad01_kresling_collar.svg")
    dxf_path = os.path.join(out_dir, "cad01_kresling_collar.dxf")

    body_w = sides * panel_width
    total_w = body_w + overlap_tab
    y0 = 0.0
    y1 = flange_height
    y2 = y1 + panel_height
    y3 = y2 + panel_height
    total_h = y3 + flange_height

    cut_lines = [
        (0, y0, total_w, y0),
        (total_w, y0, total_w, total_h),
        (total_w, total_h, 0, total_h),
        (0, total_h, 0, y0),
    ]
    mountain_lines = [
        (0, y1, total_w, y1),
        (0, y2, total_w, y2),
        (0, y3, total_w, y3),
    ]
    valley_lines = []

    for i in range(1, sides + 1):
        x = i * panel_width
        mountain_lines.append((x, y1, x, y3))
        cut_lines.append((x, y0, x, y1))
        cut_lines.append((x, y3, x, total_h))

    for i in range(sides):
        x_left = i * panel_width
        x_right = (i + 1) * panel_width
        valley_lines.append((x_left, y2, x_right, y1))
        valley_lines.append((x_left, y2, x_right, y3))

    margin = 5.0
    svg = [
        f'<svg xmlns="http://w3.org" width="{total_w + 2*margin}mm" height="{total_h + 2*margin}mm" '
        f'viewBox="{-margin} {-margin} {total_w + 2*margin} {total_h + 2*margin}">',
    ]
    for x1, ya, x2, yb in cut_lines:
        svg.append(f'  <line x1="{x1:.2f}" y1="{ya:.2f}" x2="{x2:.2f}" y2="{yb:.2f}" stroke="red" stroke-width="0.25"/>')
    for x1, ya, x2, yb in mountain_lines:
        svg.append(f'  <line x1="{x1:.2f}" y1="{ya:.2f}" x2="{x2:.2f}" y2="{yb:.2f}" stroke="blue" stroke-width="0.2"/>')
    for x1, ya, x2, yb in valley_lines:
        svg.append(
            f'  <line x1="{x1:.2f}" y1="{ya:.2f}" x2="{x2:.2f}" y2="{yb:.2f}" '
            f'stroke="green" stroke-width="0.2" stroke-dasharray="2.5,1.5"/>'
        )
    svg.append("</svg>")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

    dxf = ["0", "SECTION", "2", "ENTITIES"]

    def add_line(x1, ya, x2, yb, layer):
        dxf.extend([
            "0", "LINE", "8", layer,
            "10", f"{x1:.4f}", "20", f"{ya:.4f}", "30", "0.0",
            "11", f"{x2:.4f}", "21", f"{yb:.4f}", "31", "0.0",
        ])

    for seg in cut_lines:
        add_line(*seg, "CUT")
    for seg in mountain_lines:
        add_line(*seg, "MOUNTAIN_SCORE")
    for seg in valley_lines:
        add_line(*seg, "VALLEY_SCORE")

    dxf.extend(["0", "ENDSEC", "0", "EOF"])
    with open(dxf_path, "w", encoding="utf-8") as f:
        f.write("\n".join(dxf))

    print(f"[*] Exported 2-Story Kresling SVG -> {svg_path}")
    print(f"[*] Exported 2-Story Kresling DXF -> {dxf_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export 2-Story Kresling Origami Collar Pattern")
    parser.add_argument("--out-dir", default="outputs", help="Output directory")
    parser.add_argument("--radius", type=float, default=35.0, help="Circumscribed radius in mm (default: 35.0)")
    args = parser.parse_args()

    scale = args.radius / 35.0
    export_kresling_pattern(
        out_dir=args.out_dir,
        panel_width=35.0 * scale,
        panel_height=33.4 * scale,
        flange_height=8.0,
        overlap_tab=10.0,
    )

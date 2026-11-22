import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../cad")))

from generate_kagome_gate import (
    generate_spirograph_density,
    extract_lattice_and_kscore,
    export_gate_svg_and_dxf,
)
from generate_kresling_collar import export_kresling_pattern
from generate_phase_mask import generate_phase_mask


def test_kagome_generation_and_kscore():
    density, coords = generate_spirograph_density(grid_size=300, radius_mm=37.5)
    nodes, edges, metrics = extract_lattice_and_kscore(density, coords, active_radius=36.0)

    assert len(nodes) > 10
    assert len(edges) > 15
    assert 0.0 <= metrics["k_score"] <= 1.0

    with tempfile.TemporaryDirectory() as tmpdir:
        export_gate_svg_and_dxf(nodes, edges, tmpdir)
        assert os.path.exists(os.path.join(tmpdir, "cad01_kagome_gate.svg"))
        assert os.path.exists(os.path.join(tmpdir, "cad01_kagome_gate.dxf"))


def test_kresling_and_phase_mask_exports():
    with tempfile.TemporaryDirectory() as tmpdir:
        export_kresling_pattern(tmpdir)
        generate_phase_mask(tmpdir)
        assert os.path.exists(os.path.join(tmpdir, "cad01_kresling_collar.svg"))
        assert os.path.exists(os.path.join(tmpdir, "cad01_phase_mask.dxf"))

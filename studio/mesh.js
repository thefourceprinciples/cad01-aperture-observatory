window.CAD01_Mesh = (function () {
  function buildSceneData() {
    const mode = document.getElementById('modelSelect').value;
    const lobes = parseInt(document.getElementById('lobesSlider').value);
    const strut = parseFloat(document.getElementById('strutSlider').value);
    const rotDeg = parseInt(document.getElementById('rotSlider').value);
    const compPct = parseInt(document.getElementById('compSlider').value);
    const compFrac = compPct / 100.0;

    document.getElementById('lobesVal').textContent = lobes;
    document.getElementById('strutVal').textContent = strut.toFixed(1);
    document.getElementById('rotVal').textContent = rotDeg + '°';
    document.getElementById('compVal').textContent = compPct + '%';

    const twistDeg = 38.2 * compFrac;
    const totalAngle = (rotDeg + twistDeg) % (360 / lobes);
    const phaseAlign = Math.cos((totalAngle / (360 / lobes)) * 2 * Math.PI) * 0.5 + 0.5;
    const hAlign = Math.exp(-Math.pow((compFrac - 0.65) / 0.28, 2));
    const coherence = Number((0.95 * phaseAlign * hAlign).toFixed(3));
    const status = coherence >= 0.80 ? 'OPEN (LOCKED)' : (coherence >= 0.55 ? 'HOLD / FILTERED' : 'CLOSED');

    document.getElementById('metricsBox').innerHTML =
      'Tube ID: 75.0 mm | Halo OD: 88.0 mm<br/>Coupled Twist Δφ: ' +
      twistDeg.toFixed(1) + '°<br/>Coherence C: ' + coherence.toFixed(2) + ' | ' + status;

    const lines = [];
    const stlTris = [];

    function addBeam(x1, y1, x2, y2, z0, z1, w, color) {
      lines.push({ x1: x1, y1: y1, z1: (z0 + z1) / 2, x2: x2, y2: y2, z2: (z0 + z1) / 2, color: color, w: w });
      const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
      if (len < 0.05) return;
      const nx = (-dy / len) * (w / 2), ny = (dx / len) * (w / 2);
      const c0 = { x: x1 + nx, y: y1 + ny }, c1 = { x: x1 - nx, y: y1 - ny };
      const c2 = { x: x2 - nx, y: y2 - ny }, c3 = { x: x2 + nx, y: y2 + ny };
      stlTris.push([
        { x: c0.x, y: c0.y, z: z1 }, { x: c1.x, y: c1.y, z: z1 }, { x: c2.x, y: c2.y, z: z1 }
      ]);
      stlTris.push([
        { x: c0.x, y: c0.y, z: z1 }, { x: c2.x, y: c2.y, z: z1 }, { x: c3.x, y: c3.y, z: z1 }
      ]);
    }

    function addRing(rIn, rOut, z0, z1, color, segs) {
      for (let i = 0; i < segs; i++) {
        const a0 = (2 * Math.PI * i) / segs, a1 = (2 * Math.PI * (i + 1)) / segs;
        const ox0 = rOut * Math.cos(a0), oy0 = rOut * Math.sin(a0);
        const ox1 = rOut * Math.cos(a1), oy1 = rOut * Math.sin(a1);
        const ix0 = rIn * Math.cos(a0), iy0 = rIn * Math.sin(a0);
        const ix1 = rIn * Math.cos(a1), iy1 = rIn * Math.sin(a1);
        lines.push({ x1: ox0, y1: oy0, z1: z1, x2: ox1, y2: oy1, z2: z1, color: color, w: 1.5 });
        lines.push({ x1: ix0, y1: iy0, z1: z1, x2: ix1, y2: iy1, z2: z1, color: color, w: 1.2 });
        stlTris.push([
          { x: ix0, y: iy0, z: z1 }, { x: ox0, y: oy0, z: z1 }, { x: ox1, y: oy1, z: z1 }
        ]);
        stlTris.push([
          { x: ix0, y: iy0, z: z1 }, { x: ox1, y: oy1, z: z1 }, { x: ix1, y: iy1, z: z1 }
        ]);
      }
    }

    function addKagome(zBase) {
      const tubeR = 37.5, flangeR = 44.0, thick = 3.0;
      addRing(tubeR - 1.5, flangeR, zBase, zBase + thick, '#58a6ff', 64);
      const rings = 3, nodes = [];
      for (let rIdx = 1; rIdx <= rings; rIdx++) {
        const r = (tubeR * 0.88 * rIdx) / rings, count = lobes * rIdx;
        for (let k = 0; k < count; k++) {
          const ang = (2 * Math.PI * k) / count + (rIdx % 2 === 0 ? Math.PI / count : 0);
          nodes.push({ x: r * Math.cos(ang), y: r * Math.sin(ang) });
        }
      }
      const maxEdge = (tubeR / rings) * 1.45;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          if (Math.hypot(nodes[i].x - nodes[j].x, nodes[i].y - nodes[j].y) <= maxEdge) {
            addBeam(nodes[i].x, nodes[i].y, nodes[j].x, nodes[j].y, zBase, zBase + thick, strut, '#58a6ff');
          }
        }
        if (Math.hypot(nodes[i].x, nodes[i].y) > tubeR * 0.72) {
          const ang = Math.atan2(nodes[i].y, nodes[i].x);
          addBeam(nodes[i].x, nodes[i].y, (tubeR - 1) * Math.cos(ang), (tubeR - 1) * Math.sin(ang), zBase, zBase + thick, strut, '#58a6ff');
        }
      }
    }

    function addPhaseMask(zBase, angleDeg) {
      const tubeR = 37.5, diskR = 42.0, thick = 2.4, rot = (angleDeg * Math.PI) / 180;
      addRing(tubeR - 1.0, diskR, zBase, zBase + thick, '#f0883e', 64);
      addRing(2.55, 9.5, zBase, zBase + thick, '#f0883e', 32);
      const segs = 36;
      for (let k = 0; k < lobes; k++) {
        const baseAng = (2 * Math.PI * k) / lobes + rot;
        let prev = null;
        for (let s = 0; s <= segs; s++) {
          const u = s / segs, r = 9.0 + u * (tubeR - 9.5), theta = baseAng + 0.85 * Math.sin(u * Math.PI);
          const cur = { x: r * Math.cos(theta), y: r * Math.sin(theta) };
          if (prev) addBeam(prev.x, prev.y, cur.x, cur.y, zBase, zBase + thick, strut * 1.2, '#f0883e');
          prev = cur;
        }
      }
    }

    function addKresling() {
      const N = 6, R = 35.0, hStory = 30.3 * (1 - 0.62 * compFrac), twist = (38.2 * compFrac * Math.PI) / 180;
      for (let story = 0; story < 2; story++) {
        const z0 = story * hStory, z1 = (story + 1) * hStory;
        const a0 = story === 0 ? 0 : twist, a1 = story === 0 ? twist : 0;
        for (let i = 0; i < N; i++) {
          const t0 = (2 * Math.PI * i) / N + a0, t1 = (2 * Math.PI * (i + 1)) / N + a0;
          const u0 = (2 * Math.PI * i) / N + a1, u1 = (2 * Math.PI * (i + 1)) / N + a1;
          const B0 = { x: R * Math.cos(t0), y: R * Math.sin(t0), z: z0 };
          const B1 = { x: R * Math.cos(t1), y: R * Math.sin(t1), z: z0 };
          const T0 = { x: R * Math.cos(u0), y: R * Math.sin(u0), z: z1 };
          const T1 = { x: R * Math.cos(u1), y: R * Math.sin(u1), z: z1 };
          lines.push({ x1: B0.x, y1: B0.y, z1: B0.z, x2: B1.x, y2: B1.y, z2: B1.z, color: '#3fb950', w: 1.5 });
          lines.push({ x1: T0.x, y1: T0.y, z1: T0.z, x2: T1.x, y2: T1.y, z2: T1.z, color: '#3fb950', w: 1.5 });
          lines.push({ x1: B0.x, y1: B0.y, z1: B0.z, x2: T0.x, y2: T0.y, z2: T0.z, color: '#3fb950', w: 1.2 });
          lines.push({ x1: B0.x, y1: B0.y, z1: B0.z, x2: T1.x, y2: T1.y, z2: T1.z, color: '#2ea043', w: 1.0 });
          stlTris.push([B0, B1, T1], [B0, T1, T0]);
        }
      }
      return 2 * hStory;
    }

    let gateTopZ = 4.0;
    if (mode === 'kagome') addKagome(0);
    else if (mode === 'phase') addPhaseMask(0, rotDeg);
    else if (mode === 'kresling') gateTopZ = addKresling();
    else {
      const hTop = addKresling();
      addKagome(hTop + 1.0);
      addPhaseMask(hTop + 5.5, rotDeg + twistDeg);
      gateTopZ = hTop + 8.0;
    }

    return { lines: lines, stlTris: stlTris, coherence: coherence, gateTopZ: gateTopZ };
  }

  return { buildSceneData: buildSceneData };
})();

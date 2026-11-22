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

    const faces = [];
    const stlTris = [];

    function pushQuad(p0, p1, p2, p3, rgb, alpha, addStl) {
      faces.push({ pts: [p0, p1, p2, p3], rgb: rgb, alpha: alpha });
      if (addStl) {
        stlTris.push({ a: p0, b: p1, c: p2 });
        stlTris.push({ a: p0, b: p2, c: p3 });
      }
    }

    function addBeam(x1, y1, x2, y2, z0, z1, w, rgb) {
      const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
      if (len < 0.05) return;
      const nx = (-dy / len) * (w / 2), ny = (dx / len) * (w / 2);
      const b0 = { x: x1 + nx, y: y1 + ny, z: z0 }, b1 = { x: x1 - nx, y: y1 - ny, z: z0 };
      const b2 = { x: x2 - nx, y: y2 - ny, z: z0 }, b3 = { x: x2 + nx, y: y2 + ny, z: z0 };
      const t0 = { x: x1 + nx, y: y1 + ny, z: z1 }, t1 = { x: x1 - nx, y: y1 - ny, z: z1 };
      const t2 = { x: x2 - nx, y: y2 - ny, z: z1 }, t3 = { x: x2 + nx, y: y2 + ny, z: z1 };

      pushQuad(t0, t1, t2, t3, rgb, 1.0, true);
      pushQuad(b0, b3, b2, b1, rgb, 1.0, true);
      pushQuad(b0, b1, t1, t0, rgb, 1.0, true);
      pushQuad(b2, b3, t3, t2, rgb, 1.0, true);
      pushQuad(b1, b2, t2, t1, rgb, 1.0, true);
      pushQuad(b3, b0, t0, t3, rgb, 1.0, true);
    }

    function addRing(rIn, rOut, z0, z1, rgb, segs) {
      for (let i = 0; i < segs; i++) {
        const a0 = (2 * Math.PI * i) / segs, a1 = (2 * Math.PI * (i + 1)) / segs;
        const ib0 = { x: rIn * Math.cos(a0), y: rIn * Math.sin(a0), z: z0 };
        const ib1 = { x: rIn * Math.cos(a1), y: rIn * Math.sin(a1), z: z0 };
        const ob0 = { x: rOut * Math.cos(a0), y: rOut * Math.sin(a0), z: z0 };
        const ob1 = { x: rOut * Math.cos(a1), y: rOut * Math.sin(a1), z: z0 };
        const it0 = { x: rIn * Math.cos(a0), y: rIn * Math.sin(a0), z: z1 };
        const it1 = { x: rIn * Math.cos(a1), y: rIn * Math.sin(a1), z: z1 };
        const ot0 = { x: rOut * Math.cos(a0), y: rOut * Math.sin(a0), z: z1 };
        const ot1 = { x: rOut * Math.cos(a1), y: rOut * Math.sin(a1), z: z1 };

        pushQuad(it0, ot0, ot1, it1, rgb, 1.0, true);
        pushQuad(ib0, ib1, ob1, ob0, rgb, 1.0, true);
        pushQuad(ob0, ob1, ot1, ot0, rgb, 1.0, true);
        pushQuad(ib1, ib0, it0, it1, rgb, 1.0, true);
      }
    }

    function addKagome(zBase) {
      const rgb = { r: 88, g: 166, b: 255 };
      const tubeR = 37.5, flangeR = 44.0, thick = 3.0;
      addRing(tubeR - 1.5, flangeR, zBase, zBase + thick, rgb, 64);

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
        const nA = nodes.at(i);
        for (let j = i + 1; j < nodes.length; j++) {
          const nB = nodes.at(j);
          if (Math.hypot(nA.x - nB.x, nA.y - nB.y) <= maxEdge) {
            addBeam(nA.x, nA.y, nB.x, nB.y, zBase, zBase + thick, strut, rgb);
          }
        }
        if (Math.hypot(nA.x, nA.y) > tubeR * 0.72) {
          const ang = Math.atan2(nA.y, nA.x);
          addBeam(nA.x, nA.y, (tubeR - 1) * Math.cos(ang), (tubeR - 1) * Math.sin(ang), zBase, zBase + thick, strut, rgb);
        }
      }
    }

    function addPhaseMask(zBase, angleDeg) {
      const rgb = { r: 240, g: 136, b: 62 };
      const tubeR = 37.5, diskR = 42.0, thick = 2.4, rot = (angleDeg * Math.PI) / 180;
      addRing(tubeR - 1.0, diskR, zBase, zBase + thick, rgb, 64);
      addRing(2.55, 9.5, zBase, zBase + thick, rgb, 32);

      const segs = 32;
      for (let k = 0; k < lobes; k++) {
        const baseAng = (2 * Math.PI * k) / lobes + rot;
        let prev = null;
        for (let s = 0; s <= segs; s++) {
          const u = s / segs, r = 9.0 + u * (tubeR - 9.5), theta = baseAng + 0.85 * Math.sin(u * Math.PI);
          const cur = { x: r * Math.cos(theta), y: r * Math.sin(theta) };
          if (prev) addBeam(prev.x, prev.y, cur.x, cur.y, zBase, zBase + thick, strut * 1.2, rgb);
          prev = cur;
        }
      }
    }

    function addKresling() {
      const rgbPanelA = { r: 63, g: 185, b: 80 };
      const rgbPanelB = { r: 46, g: 160, b: 67 };
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

          faces.push({ pts: [B0, B1, T1], rgb: rgbPanelA, alpha: 0.78 });
          faces.push({ pts: [B0, T1, T0], rgb: rgbPanelB, alpha: 0.78 });
          stlTris.push({ a: B0, b: B1, c: T1 });
          stlTris.push({ a: B0, b: T1, c: T0 });
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

    return { faces: faces, stlTris: stlTris, coherence: coherence, gateTopZ: gateTopZ };
  }

  return { buildSceneData: buildSceneData };
})();

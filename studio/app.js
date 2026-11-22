(function () {
  const canvas = document.getElementById('canvas3d');
  const ctx = canvas.getContext('2d');

  let rotZ = 0.55;
  let rotX = 1.05;
  let zoom = 4.2;
  let dragging = false;
  let lastMouse = { x: 0, y: 0 };

  canvas.addEventListener('mousedown', function (e) {
    dragging = true;
    lastMouse = { x: e.clientX, y: e.clientY };
  });
  window.addEventListener('mouseup', function () { dragging = false; });
  window.addEventListener('mousemove', function (e) {
    if (!dragging) return;
    rotZ += (e.clientX - lastMouse.x) * 0.008;
    rotX = Math.max(0.15, Math.min(Math.PI - 0.15, rotX + (e.clientY - lastMouse.y) * 0.008));
    lastMouse = { x: e.clientX, y: e.clientY };
  });
  canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    zoom = Math.max(1.5, Math.min(12.0, zoom * (e.deltaY > 0 ? 0.92 : 1.08)));
  }, { passive: false });

  function project3D(x, y, z, cx, cy) {
    const cz = Math.cos(rotZ), sz = Math.sin(rotZ);
    const cxr = Math.cos(rotX), sxr = Math.sin(rotX);
    const x1 = x * cz - y * sz;
    const y1 = x * sz + y * cz;
    const y2 = y1 * cxr - z * sxr;
    const z2 = y1 * sxr + z * cxr;
    const perspective = 450 / (450 + z2);
    return { x: cx + x1 * zoom * perspective, y: cy - y2 * zoom * perspective };
  }

  document.getElementById('exportBtn').addEventListener('click', function () {
    const data = window.CAD01_Mesh.buildSceneData();
    const stlTris = data.stlTris;
    const buf = new ArrayBuffer(84 + stlTris.length * 50);
    const view = new DataView(buf);
    view.setUint32(80, stlTris.length, true);
    let offset = 84;
    for (let i = 0; i < stlTris.length; i++) {
      view.setFloat32(offset + 8, 1.0, true);
      offset += 12;
      for (let j = 0; j < 3; j++) {
        const v = stlTris[i][j];
        view.setFloat32(offset, v.x, true);
        view.setFloat32(offset + 4, v.y, true);
        view.setFloat32(offset + 8, v.z, true);
        offset += 12;
      }
      view.setUint16(offset, 0, true);
      offset += 2;
    }
    const blob = new Blob([buf], { type: 'application/octet-stream' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'cad01_' + document.getElementById('modelSelect').value + '.stl';
    link.click();
  });

  function render(now) {
    const waveTime = now * 0.001;
    if (canvas.width !== canvas.clientWidth || canvas.height !== canvas.clientHeight) {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    }
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const cx = canvas.width / 2;
    const cy = canvas.height * 0.58;
    const data = window.CAD01_Mesh.buildSceneData();

    ctx.strokeStyle = '#21262d';
    ctx.lineWidth = 1;
    for (let g = -60; g <= 60; g += 20) {
      const p1 = project3D(g, -60, 0, cx, cy), p2 = project3D(g, 60, 0, cx, cy);
      const p3 = project3D(-60, g, 0, cx, cy), p4 = project3D(60, g, 0, cx, cy);
      ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p3.x, p3.y); ctx.lineTo(p4.x, p4.y); ctx.stroke();
    }

    for (let i = 0; i < data.lines.length; i++) {
      const seg = data.lines[i];
      const p1 = project3D(seg.x1, seg.y1, seg.z1, cx, cy);
      const p2 = project3D(seg.x2, seg.y2, seg.z2, cx, cy);
      ctx.strokeStyle = seg.color;
      ctx.lineWidth = seg.w;
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    }

    if (document.getElementById('waveToggle').checked) {
      for (let i = 0; i < 6; i++) {
        const phase = (waveTime * 0.5 + i / 6) % 1.0;
        const z = -35 + phase * 115;
        const past = z > data.gateTopZ;
        const alpha = past ? data.coherence * (1 - (z - data.gateTopZ) / 55) * 0.85 : 0.35;
        if (alpha <= 0.02) continue;

        ctx.strokeStyle = past ? 'rgba(63, 185, 80, ' + alpha + ')' : 'rgba(88, 166, 255, ' + alpha + ')';
        ctx.lineWidth = past ? 2.2 : 1.4;
        ctx.beginPath();
        const rWave = past ? 22 + 12 * data.coherence : 34;
        for (let s = 0; s <= 48; s++) {
          const a = (2 * Math.PI * s) / 48;
          const pt = project3D(rWave * Math.cos(a), rWave * Math.sin(a), z, cx, cy);
          if (s === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        }
        ctx.stroke();
      }
    }
    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);
})();

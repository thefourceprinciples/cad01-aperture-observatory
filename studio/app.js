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

  function transformPoint(p) {
    const cz = Math.cos(rotZ), sz = Math.sin(rotZ);
    const cxr = Math.cos(rotX), sxr = Math.sin(rotX);
    const x1 = p.x * cz - p.y * sz;
    const y1 = p.x * sz + p.y * cz;
    const y2 = y1 * cxr - p.z * sxr;
    const z2 = y1 * sxr + p.z * cxr;
    return { x: x1, y: y2, z: z2 };
  }

  function projectCam(camPt, cx, cy) {
    const perspective = 480 / (480 + camPt.z);
    return { x: cx + camPt.x * zoom * perspective, y: cy - camPt.y * zoom * perspective };
  }

  document.getElementById('exportBtn').addEventListener('click', function () {
    const data = window.CAD01_Mesh.buildSceneData();
    const stlTris = data.stlTris;
    const buf = new ArrayBuffer(84 + stlTris.length * 50);
    const view = new DataView(buf);
    view.setUint32(80, stlTris.length, true);
    let offset = 84;
    for (let i = 0; i < stlTris.length; i++) {
      const tri = stlTris.at(i);
      view.setFloat32(offset + 8, 1.0, true);
      offset += 12;
      const verts = [tri.a, tri.b, tri.c];
      for (let j = 0; j < 3; j++) {
        const v = verts.at(j);
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

  const lightDir = { x: 0.45, y: 0.65, z: -0.61 };

  function render(now) {
    const waveTime = now * 0.001;
    const dpr = window.devicePixelRatio || 1;
    const rectW = canvas.clientWidth;
    const rectH = canvas.clientHeight;

    if (canvas.width !== Math.floor(rectW * dpr) || canvas.height !== Math.floor(rectH * dpr)) {
      canvas.width = Math.floor(rectW * dpr);
      canvas.height = Math.floor(rectH * dpr);
    }

    ctx.save();
    ctx.scale(dpr, dpr);

    const bgGrad = ctx.createRadialGradient(rectW * 0.5, rectH * 0.5, 20, rectW * 0.5, rectH * 0.5, rectW * 0.65);
    bgGrad.addColorStop(0, '#161b22');
    bgGrad.addColorStop(1, '#090c10');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, rectW, rectH);

    const cx = rectW / 2;
    const cy = rectH * 0.58;
    const data = window.CAD01_Mesh.buildSceneData();

    ctx.strokeStyle = 'rgba(48, 54, 61, 0.55)';
    ctx.lineWidth = 1;
    for (let g = -60; g <= 60; g += 20) {
      const p1 = projectCam(transformPoint({ x: g, y: -60, z: 0 }), cx, cy);
      const p2 = projectCam(transformPoint({ x: g, y: 60, z: 0 }), cx, cy);
      const p3 = projectCam(transformPoint({ x: -60, y: g, z: 0 }), cx, cy);
      const p4 = projectCam(transformPoint({ x: 60, y: g, z: 0 }), cx, cy);
      ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p3.x, p3.y); ctx.lineTo(p4.x, p4.y); ctx.stroke();
    }

    const renderList = [];
    for (let i = 0; i < data.faces.length; i++) {
      const f = data.faces.at(i);
      const camPts = f.pts.map(transformPoint);
      const c0 = camPts.at(0), c1 = camPts.at(1), c2 = camPts.at(2);

      const ux = c1.x - c0.x, uy = c1.y - c0.y, uz = c1.z - c0.z;
      const vx = c2.x - c0.x, vy = c2.y - c0.y, vz = c2.z - c0.z;
      let nx = uy * vz - uz * vy;
      let ny = uz * vx - ux * vz;
      let nz = ux * vy - uy * vx;
      const nLen = Math.hypot(nx, ny, nz) || 1;
      nx /= nLen; ny /= nLen; nz /= nLen;

      if (nz > 0) { nx = -nx; ny = -ny; nz = -nz; }

      const diff = Math.max(0, nx * lightDir.x + ny * lightDir.y + nz * lightDir.z);
      const spec = Math.pow(diff, 14) * 0.45;
      const shade = 0.38 + 0.62 * diff;

      const r = Math.min(255, Math.round(f.rgb.r * shade + 255 * spec));
      const g = Math.min(255, Math.round(f.rgb.g * shade + 255 * spec));
      const b = Math.min(255, Math.round(f.rgb.b * shade + 255 * spec));

      let avgZ = 0;
      for (let k = 0; k < camPts.length; k++) avgZ += camPts.at(k).z;
      avgZ /= camPts.length;

      renderList.push({
        proj: camPts.map(function (cp) { return projectCam(cp, cx, cy); }),
        depth: avgZ,
        fill: 'rgba(' + r + ',' + g + ',' + b + ',' + f.alpha + ')',
        stroke: 'rgba(' + Math.min(255, r + 25) + ',' + Math.min(255, g + 25) + ',' + Math.min(255, b + 25) + ',' + (f.alpha * 0.6) + ')'
      });
    }

    renderList.sort(function (a, b) { return b.depth - a.depth; });

    ctx.lineJoin = 'round';
    ctx.lineWidth = 0.6;
    for (let i = 0; i < renderList.length; i++) {
      const item = renderList.at(i);
      const firstPt = item.proj.at(0);
      ctx.fillStyle = item.fill;
      ctx.strokeStyle = item.stroke;
      ctx.beginPath();
      ctx.moveTo(firstPt.x, firstPt.y);
      for (let k = 1; k < item.proj.length; k++) {
        const pt = item.proj.at(k);
        ctx.lineTo(pt.x, pt.y);
      }
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }

    if (document.getElementById('waveToggle').checked) {
      ctx.save();
      for (let i = 0; i < 6; i++) {
        const phase = (waveTime * 0.5 + i / 6) % 1.0;
        const z = -35 + phase * 115;
        const past = z > data.gateTopZ;
        const alpha = past ? data.coherence * (1 - (z - data.gateTopZ) / 55) * 0.9 : 0.35;
        if (alpha <= 0.02) continue;

        const colorStr = past ? 'rgba(63, 185, 80, ' + alpha + ')' : 'rgba(88, 166, 255, ' + alpha + ')';
        ctx.strokeStyle = colorStr;
        ctx.shadowColor = past ? '#3fb950' : '#58a6ff';
        ctx.shadowBlur = past ? 12 : 6;
        ctx.lineWidth = past ? 2.5 : 1.5;

        ctx.beginPath();
        const rWave = past ? 22 + 12 * data.coherence : 34;
        for (let s = 0; s <= 56; s++) {
          const a = (2 * Math.PI * s) / 56;
          const pt = projectCam(transformPoint({ x: rWave * Math.cos(a), y: rWave * Math.sin(a), z: z }), cx, cy);
          if (s === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        }
        ctx.stroke();
      }
      ctx.restore();
    }

    ctx.restore();
    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);
})();

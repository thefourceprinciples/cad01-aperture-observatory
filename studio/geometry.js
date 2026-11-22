import * as THREE from 'three';

export function createStrutMesh(x1, y1, x2, y2, width, height, material) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  if (len < 0.05) return null;
  const geom = new THREE.BoxGeometry(len, width, height);
  const mesh = new THREE.Mesh(geom, material);
  mesh.position.set((x1 + x2) / 2, (y1 + y2) / 2, height / 2);
  mesh.rotation.z = Math.atan2(dy, dx);
  return mesh;
}

export function createRingMesh(rIn, rOut, height, material) {
  const shape = new THREE.Shape();
  shape.absarc(0, 0, rOut, 0, Math.PI * 2, false);
  const hole = new THREE.Path();
  hole.absarc(0, 0, rIn, 0, Math.PI * 2, true);
  shape.holes.push(hole);
  const geom = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false, curveSegments: 72 });
  return new THREE.Mesh(geom, material);
}

export function buildKagomeGroup(lobes, strutWidth) {
  const group = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0x58a6ff, metalness: 0.25, roughness: 0.4 });
  const tubeR = 37.5, flangeR = 44.0, thick = 3.0;

  group.add(createRingMesh(tubeR - 1.5, flangeR, thick, mat));

  const rings = 3;
  const nodes = [];
  for (let rIdx = 1; rIdx <= rings; rIdx++) {
    const r = (tubeR * 0.88 * rIdx) / rings;
    const count = lobes * rIdx;
    for (let k = 0; k < count; k++) {
      const ang = (2 * Math.PI * k) / count + (rIdx % 2 === 0 ? Math.PI / count : 0);
      nodes.push({ x: r * Math.cos(ang), y: r * Math.sin(ang) });
    }
  }

  const maxEdge = (tubeR / rings) * 1.45;
  for (let i = 0; i < nodes.length; i++) {
    const p1 = nodes[i];
    for (let j = i + 1; j < nodes.length; j++) {
      const p2 = nodes[j];
      if (Math.hypot(p1.x - p2.x, p1.y - p2.y) <= maxEdge) {
        const strut = createStrutMesh(p1.x, p1.y, p2.x, p2.y, strutWidth, thick, mat);
        if (strut) group.add(strut);
      }
    }
    if (Math.hypot(p1.x, p1.y) > tubeR * 0.72) {
      const ang = Math.atan2(p1.y, p1.x);
      const rim = createStrutMesh(
        p1.x, p1.y, (tubeR - 1.0) * Math.cos(ang), (tubeR - 1.0) * Math.sin(ang), strutWidth, thick, mat
      );
      if (rim) group.add(rim);
    }
  }
  return group;
}

export function buildPhaseMaskGroup(lobes, strutWidth) {
  const group = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0xf0883e, metalness: 0.3, roughness: 0.35 });
  const tubeR = 37.5, diskR = 42.0, thick = 2.4;

  group.add(createRingMesh(tubeR - 1.0, diskR, thick, mat));
  group.add(createRingMesh(2.55, 9.5, thick, mat));

  const segs = 48;
  for (let k = 0; k < lobes; k++) {
    const baseAng = (2 * Math.PI * k) / lobes;
    let prev = null;
    for (let s = 0; s <= segs; s++) {
      const u = s / segs;
      const r = 9.0 + u * (tubeR - 9.5);
      const theta = baseAng + 0.85 * Math.sin(u * Math.PI);
      const cur = { x: r * Math.cos(theta), y: r * Math.sin(theta) };
      if (prev) {
        const rib = createStrutMesh(prev.x, prev.y, cur.x, cur.y, strutWidth * 1.2, thick, mat);
        if (rib) group.add(rib);
      }
      prev = cur;
    }
  }
  return group;
}

export function buildKreslingGroup(compressionFrac) {
  const group = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({
    color: 0x3fb950, transparent: true, opacity: 0.82, side: THREE.DoubleSide, roughness: 0.45
  });
  const N = 6, R = 35.0;
  const hStory = 30.3 * (1 - 0.62 * compressionFrac);
  const twist = THREE.MathUtils.degToRad(38.2 * compressionFrac);
  const vertices = [];

  for (let story = 0; story < 2; story++) {
    const z0 = story * hStory;
    const z1 = (story + 1) * hStory;
    const a0 = story === 0 ? 0 : twist;
    const a1 = story === 0 ? twist : 0;

    for (let i = 0; i < N; i++) {
      const t0 = (2 * Math.PI * i) / N + a0;
      const t1 = (2 * Math.PI * (i + 1)) / N + a0;
      const u0 = (2 * Math.PI * i) / N + a1;
      const u1 = (2 * Math.PI * (i + 1)) / N + a1;

      const B0 = [R * Math.cos(t0), R * Math.sin(t0), z0];
      const B1 = [R * Math.cos(t1), R * Math.sin(t1), z0];
      const T0 = [R * Math.cos(u0), R * Math.sin(u0), z1];
      const T1 = [R * Math.cos(u1), R * Math.sin(u1), z1];

      vertices.push(...B0, ...B1, ...T1, ...B0, ...T1, ...T0);
    }
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  geom.computeVertexNormals();
  group.add(new THREE.Mesh(geom, mat));
  return group;
}

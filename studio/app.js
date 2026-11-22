import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLExporter } from 'three/addons/exporters/STLExporter.js';
import { buildKagomeGroup, buildPhaseMaskGroup, buildKreslingGroup } from './geometry.js';

const viewport = document.getElementById('viewport');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d1117);

const camera = new THREE.PerspectiveCamera(45, viewport.clientWidth / viewport.clientHeight, 0.1, 1000);
camera.position.set(0, -135, 95);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(viewport.clientWidth, viewport.clientHeight);
viewport.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0, 28);

scene.add(new THREE.AmbientLight(0xffffff, 0.65));
const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight.position.set(60, -80, 120);
scene.add(dirLight);

const grid = new THREE.GridHelper(160, 16, 0x30363d, 0x21262d);
grid.rotation.x = Math.PI / 2;
scene.add(grid);

let activeGroup = new THREE.Group();
scene.add(activeGroup);

const waveGroup = new THREE.Group();
scene.add(waveGroup);
const waveRings = [];
for (let i = 0; i < 8; i++) {
  const ringGeom = new THREE.RingGeometry(8, 34, 48);
  const ringMat = new THREE.MeshBasicMaterial({
    color: 0x58a6ff, side: THREE.DoubleSide, transparent: true, opacity: 0.35
  });
  const mesh = new THREE.Mesh(ringGeom, ringMat);
  waveGroup.add(mesh);
  waveRings.push({ mesh, phase: i / 8 });
}

let currentCoherence = 0.0;
let gateTopZ = 65.0;

function rebuildModel() {
  scene.remove(activeGroup);
  activeGroup = new THREE.Group();

  const mode = document.getElementById('modelSelect').value;
  const lobes = parseInt(document.getElementById('lobesSlider').value);
  const strut = parseFloat(document.getElementById('strutSlider').value);
  const rotDeg = parseInt(document.getElementById('rotSlider').value);
  const compPct = parseInt(document.getElementById('compSlider').value);
  const compFrac = compPct / 100.0;

  document.getElementById('lobesVal').textContent = lobes;
  document.getElementById('strutVal').textContent = strut.toFixed(1);
  document.getElementById('rotVal').textContent = `${rotDeg}°`;
  document.getElementById('compVal').textContent = `${compPct}%`;

  const twistDeg = 38.2 * compFrac;
  const totalAngle = (rotDeg + twistDeg) % (360 / lobes);
  const phaseAlign = Math.cos((totalAngle / (360 / lobes)) * 2 * Math.PI) * 0.5 + 0.5;
  const hAlign = Math.exp(-Math.pow((compFrac - 0.65) / 0.28, 2));
  currentCoherence = Number((0.95 * phaseAlign * hAlign).toFixed(3));
  const status = currentCoherence >= 0.80 ? 'OPEN (LOCKED)' : (currentCoherence >= 0.55 ? 'HOLD / FILTERED' : 'CLOSED');

  document.getElementById('metricsBox').innerHTML =
    `Tube ID: 75.0 mm | Halo OD: 88.0 mm<br/>Coupled Twist Δφ: ${twistDeg.toFixed(1)}°<br/>Coherence C: ${currentCoherence.toFixed(2)} | ${status}`;

  if (mode === 'kagome') {
    activeGroup.add(buildKagomeGroup(lobes, strut));
    gateTopZ = 3.0;
    controls.target.set(0, 0, 2);
  } else if (mode === 'phase') {
    const pm = buildPhaseMaskGroup(lobes, strut);
    pm.rotation.z = THREE.MathUtils.degToRad(rotDeg);
    activeGroup.add(pm);
    gateTopZ = 2.4;
    controls.target.set(0, 0, 2);
  } else if (mode === 'kresling') {
    activeGroup.add(buildKreslingGroup(compFrac));
    gateTopZ = 2 * 30.3 * (1 - 0.62 * compFrac);
    controls.target.set(0, 0, gateTopZ / 2);
  } else {
    const kres = buildKreslingGroup(compFrac);
    const hTop = 2 * 30.3 * (1 - 0.62 * compFrac);
    gateTopZ = hTop + 8.0;
    controls.target.set(0, 0, gateTopZ / 2);

    const kag = buildKagomeGroup(lobes, strut);
    kag.position.z = hTop + 1.0;

    const pm = buildPhaseMaskGroup(lobes, strut);
    pm.position.z = hTop + 5.5;
    pm.rotation.z = THREE.MathUtils.degToRad(rotDeg + twistDeg);

    activeGroup.add(kres, kag, pm);
  }

  scene.add(activeGroup);
}

['modelSelect', 'lobesSlider', 'strutSlider', 'rotSlider', 'compSlider'].forEach((id) => {
  document.getElementById(id).addEventListener('input', rebuildModel);
});

document.getElementById('exportBtn').addEventListener('click', () => {
  const exporter = new STLExporter();
  const stlData = exporter.parse(activeGroup, { binary: true });
  const blob = new Blob([stlData], { type: 'application/octet-stream' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `cad01_${document.getElementById('modelSelect').value}.stl`;
  link.click();
});

window.addEventListener('resize', () => {
  camera.aspect = viewport.clientWidth / viewport.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(viewport.clientWidth, viewport.clientHeight);
});

rebuildModel();
const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();
  const showWaves = document.getElementById('waveToggle').checked;
  waveGroup.visible = showWaves;

  if (showWaves) {
    waveRings.forEach((w) => {
      w.phase = (w.phase + dt * 0.65) % 1.0;
      const z = -45 + w.phase * 135;
      const pastGate = z > gateTopZ;
      w.mesh.position.z = z;

      if (pastGate) {
        w.mesh.material.color.setHex(0x3fb950);
        w.mesh.material.opacity = currentCoherence * (1.0 - (z - gateTopZ) / 60.0) * 0.65;
        const s = 0.6 + 0.4 * currentCoherence;
        w.mesh.scale.set(s, s, 1);
      } else {
        w.mesh.material.color.setHex(0x58a6ff);
        w.mesh.material.opacity = 0.25 * (1.0 - Math.abs(z + 20) / 40.0);
        w.mesh.scale.set(1, 1, 1);
      }
    });
  }

  controls.update();
  renderer.render(scene, camera);
}
animate();

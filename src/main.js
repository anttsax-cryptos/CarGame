// src/main.js
// Clean, small arcade driving demo for embedding in Streamlit

(() => {
  // Scene setup
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x87ceeb);

  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(window.innerWidth, window.innerHeight);
  document.body.appendChild(renderer.domElement);

  // Lights
  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 0.8);
  scene.add(hemi);
  const dir = new THREE.DirectionalLight(0xffffff, 0.6);
  dir.position.set(5, 10, 2);
  scene.add(dir);

  // Ground
  const groundMat = new THREE.MeshStandardMaterial({ color: 0x2d8b3a });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(500, 500), groundMat);
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);

  // Simple oval track built from lathe geometry
  const outerPoints = [];
  const TRACK_RADIUS_X = 40;
  const TRACK_RADIUS_Z = 24;
  for (let i = 0; i <= 64; i++) {
    const t = (i / 64) * Math.PI * 2;
    const x = Math.cos(t) * TRACK_RADIUS_X;
    const z = Math.sin(t) * TRACK_RADIUS_Z;
    outerPoints.push(new THREE.Vector2(x, z));
  }
  const trackShape = new THREE.Shape(outerPoints);
  const holePoints = [];
  for (let i = 0; i <= 64; i++) {
    const t = (i / 64) * Math.PI * 2;
    const x = Math.cos(t) * (TRACK_RADIUS_X - 12);
    const z = Math.sin(t) * (TRACK_RADIUS_Z - 8);
    holePoints.push(new THREE.Vector2(x, z));
  }
  trackShape.holes.push(new THREE.Path(holePoints));
  const trackGeo = new THREE.ExtrudeGeometry(trackShape, { depth: 0.5, bevelEnabled: false });
  const trackMat = new THREE.MeshStandardMaterial({ color: 0x444444 });
  const track = new THREE.Mesh(trackGeo, trackMat);
  track.rotation.x = -Math.PI / 2;
  track.position.y = 0.01;
  scene.add(track);

  // Finish line marker (for lap counting)
  const finishMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const finish = new THREE.Mesh(new THREE.BoxGeometry(8, 0.1, 0.2), finishMat);
  finish.position.set(TRACK_RADIUS_X - 6, 0.06, 0);
  scene.add(finish);

  // Car factory (returns a Group)
  function createCar(color = 0xff3333) {
    const g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.5, 3), new THREE.MeshStandardMaterial({ color }));
    body.position.y = 0.6;
    g.add(body);

    const roof = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.3, 1.2), new THREE.MeshStandardMaterial({ color: 0xff6666 }));
    roof.position.set(0, 0.95, -0.1);
    g.add(roof);

    const wheelGeo = new THREE.CylinderGeometry(0.28, 0.28, 0.5, 12);
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x111111 });
    function wheel(x, z) {
      const w = new THREE.Mesh(wheelGeo, wheelMat);
      w.rotation.z = Math.PI / 2;
      w.position.set(x, 0.28, z);
      return w;
    }
    g.add(wheel(-0.9, 1));
    g.add(wheel(0.9, 1));
    g.add(wheel(-0.9, -1));
    g.add(wheel(0.9, -1));
    return g;
  }

  // Player car
  const player = createCar(0xff3333);
  scene.add(player);

  // Initial player state
  let playerState = {
    position: new THREE.Vector3(TRACK_RADIUS_X - 6, 0, 0),
    heading: Math.PI, // pointing along negative X
    speed: 0,
    laps: 0,
    lastFinishCross: 0
  };
  player.position.copy(playerState.position);
  player.rotation.y = playerState.heading;

  // Input
  const keys = {};
  window.addEventListener('keydown', (e) => { keys[e.code] = true; if (e.code === 'KeyR') resetPlayer(); });
  window.addEventListener('keyup', (e) => { keys[e.code] = false; });

  // HUD
  const speedEl = document.getElementById('speed');
  const lapsEl = document.getElementById('laps');

  // Physics params
  const PARAMS = {
    MAX_SPEED: 40,
    ACCELERATION: 70,
    BRAKE_DECEL: 140,
    REVERSE_MAX: 12,
    TURN_RATE: 2.2,
    FRICTION: 3
  };

  function resetPlayer() {
    playerState = {
      position: new THREE.Vector3(TRACK_RADIUS_X - 6, 0, 0),
      heading: Math.PI,
      speed: 0,
      laps: 0,
      lastFinishCross: 0
    };
    player.position.copy(playerState.position);
    player.rotation.y = playerState.heading;
    if (lapsEl) lapsEl.textContent = '0';
  }

  // Simple oval path helpers for lap detection and AI
  function angleOnTrack(v) {
    return Math.atan2(v.z / TRACK_RADIUS_Z, v.x / TRACK_RADIUS_X);
  }

  // Keep car on ground
  function clampToGround(v) { v.y = 0; }

  // Main update
  let lastTime = performance.now();
  function update(now) {
    const dt = Math.min(0.05, (now - lastTime) / 1000);
    lastTime = now;

    // Input mapping
    let accel = 0;
    let steer = 0;
    if (keys['KeyW'] || keys['ArrowUp']) accel = 1;
    if (keys['KeyS'] || keys['ArrowDown']) accel = -1;
    if (keys['KeyA'] || keys['ArrowLeft']) steer = 1;
    if (keys['KeyD'] || keys['ArrowRight']) steer = -1;

    // Update speed
    if (accel > 0) playerState.speed += PARAMS.ACCELERATION * accel * dt;
    else if (accel < 0) {
      if (playerState.speed > 0) playerState.speed -= PARAMS.BRAKE_DECEL * Math.abs(accel) * dt;
      else playerState.speed -= PARAMS.ACCELERATION * 0.6 * dt;
    } else {
      // friction
      if (playerState.speed > 0) playerState.speed -= PARAMS.FRICTION * dt;
      else playerState.speed += PARAMS.FRICTION * dt;
    }

    // clamp
    playerState.speed = Math.max(-PARAMS.REVERSE_MAX, Math.min(PARAMS.MAX_SPEED, playerState.speed));
    if (Math.abs(playerState.speed) < 0.01) playerState.speed = 0;

    // steering scales with speed
    const steerEffect = PARAMS.TURN_RATE * (Math.min(Math.abs(playerState.speed) / PARAMS.MAX_SPEED, 1) + 0.15);
    playerState.heading += steer * steerEffect * dt * Math.sign(Math.max(Math.abs(playerState.speed), 0.1));

    // apply movement
    const forward = new THREE.Vector3(Math.cos(playerState.heading), 0, Math.sin(playerState.heading));
    playerState.position.addScaledVector(forward, playerState.speed * dt);
    clampToGround(playerState.position);

    // keep roughly on track by pulling towards track centerline
    const r = Math.sqrt(playerState.position.x * playerState.position.x + playerState.position.z * playerState.position.z);
    const desiredR = Math.sqrt((TRACK_RADIUS_X - 6) * (TRACK_RADIUS_X - 6));
    const pull = THREE.MathUtils.clamp((desiredR - r) * 0.02, -0.5, 0.5);
    if (Math.abs(r - desiredR) > 6) {
      // nudge back
      const dirToCenter = new THREE.Vector3(-playerState.position.x, 0, -playerState.position.z).normalize();
      playerState.position.addScaledVector(dirToCenter, 0.5 * dt * (playerState.speed + 1));
    }

    // update player mesh
    player.position.copy(playerState.position);
    player.rotation.y = -playerState.heading + Math.PI / 2; // orient mesh

    // lap detection: when crossing finish.x threshold from positive z to negative z near finish X
    const FINISH_X = TRACK_RADIUS_X - 6;
    const prevSign = playerState.lastFinishCross;
    const curSign = playerState.position.z > 0 ? 1 : -1;
    if (prevSign === 1 && curSign === -1 && Math.abs(playerState.position.x - FINISH_X) < 6) {
      playerState.laps += 1;
      if (lapsEl) lapsEl.textContent = String(playerState.laps);
    }
    playerState.lastFinishCross = curSign;

    // HUD
    if (speedEl) speedEl.textContent = String(Math.round(Math.max(0, playerState.speed * 3)));

    // camera chase
    const camOffset = new THREE.Vector3(0, 6, -12).applyAxisAngle(new THREE.Vector3(0,1,0), playerState.heading);
    const desiredCam = new THREE.Vector3().copy(playerState.position).add(camOffset);
    camera.position.lerp(desiredCam, 0.14);
    camera.lookAt(new THREE.Vector3().copy(playerState.position).add(new THREE.Vector3(0,1.2,0)));

    renderer.render(scene, camera);
    requestAnimationFrame(update);
  }

  // Handle resize
  function onResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }
  window.addEventListener('resize', onResize);

  // initialize
  camera.position.set(playerState.position.x, 6, playerState.position.z - 12);
  camera.lookAt(playerState.position);
  requestAnimationFrame(update);
})();

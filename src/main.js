// src/main.js
// Simple arcade-style 3D car racing demo using Three.js (no external assets)

(function () {
  // Scene, camera, renderer
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x87ceeb);

  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 6, -10);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.shadowMap.enabled = false;
  document.body.appendChild(renderer.domElement);

  // Lights
  const ambient = new THREE.HemisphereLight(0xffffff, 0x444444, 0.7);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight(0xffffff, 0.8);
  sun.position.set(5, 10, 2);
  scene.add(sun);

  // Ground
  const groundGeo = new THREE.PlaneGeometry(300, 300);
  const groundMat = new THREE.MeshStandardMaterial({ color: 0x2d8b3a });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);

  // Track: use a wide torus to make a circular race track
  const trackRadius = 30;
  const trackThickness = 6;
  const trackGeo = new THREE.TorusGeometry(trackRadius, trackThickness, 36, 200);
  const trackMat = new THREE.MeshStandardMaterial({ color: 0x333333 });
  const track = new THREE.Mesh(trackGeo, trackMat);
  track.rotation.x = Math.PI / 2;
  track.position.y = 0.01; // slightly above ground to avoid z-fighting
  scene.add(track);

  // Road markings: a thin torus slightly above track
  const markGeo = new THREE.TorusGeometry(trackRadius, trackThickness * 0.15, 8, 200);
  const markMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.05 });
  const marks = new THREE.Mesh(markGeo, markMat);
  marks.rotation.x = Math.PI / 2;
  marks.position.y = 0.02;
  scene.add(marks);

  // Simple car (box + wheels)
  const car = new THREE.Group();
  const bodyGeo = new THREE.BoxGeometry(1.8, 0.6, 3);
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0xff3333 });
  const body = new THREE.Mesh(bodyGeo, bodyMat);
  body.position.y = 0.6;
  car.add(body);

  // add a roof
  const roofGeo = new THREE.BoxGeometry(1.2, 0.35, 1.2);
  const roofMat = new THREE.MeshStandardMaterial({ color: 0xff6666 });
  const roof = new THREE.Mesh(roofGeo, roofMat);
  roof.position.set(0, 0.95, -0.1);
  car.add(roof);

  // wheels
  const wheelGeo = new THREE.CylinderGeometry(0.28, 0.28, 0.5, 12);
  const wheelMat = new THREE.MeshStandardMaterial({ color: 0x111111 });
  function makeWheel(x, z) {
    const w = new THREE.Mesh(wheelGeo, wheelMat);
    w.rotation.z = Math.PI / 2;
    w.position.set(x, 0.28, z);
    return w;
  }
  car.add(makeWheel(-0.9, 1)); // front-left
  car.add(makeWheel(0.9, 1)); // front-right
  car.add(makeWheel(-0.9, -1)); // rear-left
  car.add(makeWheel(0.9, -1)); // rear-right

  // initial position: put the car on the inner side of the track start
  const startAngle = Math.PI * 0.25; // 45deg
  const startRadius = trackRadius - trackThickness + 2;
  car.position.set(Math.cos(startAngle) * startRadius, 0, Math.sin(startAngle) * startRadius);
  car.rotation.y = -startAngle + Math.PI / 2; // face along the track
  scene.add(car);

  // HUD elements
  const speedEl = document.getElementById('speed');
  let lapEl = document.getElementById('lap');
  if (!lapEl) {
    const div = document.createElement('div');
    div.id = 'lap';
    div.style.position = 'fixed';
    div.style.left = '10px';
    div.style.top = '30px';
    div.style.color = '#fff';
    div.style.fontFamily = 'monospace';
    div.style.zIndex = '10';
    document.body.appendChild(div);
    lapEl = div;
  }

  // Arcade physics state
  let speed = 0; // forward speed in units/sec
  let heading = car.rotation.y; // angle in world space
  const state = {
    accel: 0,
    steer: 0,
    braking: false
  };

  // Tunable arcade parameters
  const MAX_SPEED = 40; // top speed
  const ACCELERATION = 60; // units / sec^2
  const BRAKE_DECEL = 120;
  const REVERSE_SPEED = 12;
  const TURN_SPEED = 2.3; // radians/sec at full steer
  const FRICTION = 2.8; // natural deceleration
  const DRIFT = 0.96; // lateral damping

  // Input handling
  const keys = {};
  window.addEventListener('keydown', (e) => {
    keys[e.code] = true;
    if (e.code === 'KeyR') resetCar();
  });
  window.addEventListener('keyup', (e) => { keys[e.code] = false; });

  function updateInput() {
    state.accel = 0;
    state.steer = 0;
    state.braking = false;

    if (keys['KeyW'] || keys['ArrowUp']) state.accel = 1;
    if (keys['KeyS'] || keys['ArrowDown']) { state.accel = -1; state.braking = true; }
    if (keys['KeyA'] || keys['ArrowLeft']) state.steer = 1;
    if (keys['KeyD'] || keys['ArrowRight']) state.steer = -1;
  }

  // Lap detection: count when crossing finish line near startAngle
  let lastCrossSign = 0;
  let laps = 0;

  function checkLap(pos) {
    // compute angle around origin
    const ang = Math.atan2(pos.z, pos.x);
    // Normalize to [0, 2PI)
    const nAng = (ang + Math.PI * 2) % (Math.PI * 2);
    const sAng = (startAngle + Math.PI * 2) % (Math.PI * 2);
    // consider crossing line when angle crosses sAng from below
    const diff = nAng - sAng;
    const sign = diff > 0 ? 1 : -1;
    // crossing when sign changes from -1 to 1 and car is near track radius
    const r = Math.sqrt(pos.x * pos.x + pos.z * pos.z);
    const near = Math.abs(r - trackRadius) < (trackThickness + 2);
    if (lastCrossSign === -1 && sign === 1 && near) {
      laps += 1;
    }
    lastCrossSign = sign;
  }

  // Reset function
  function resetCar() {
    speed = 0;
    lap = 0;
    laps = 0;
    car.position.set(Math.cos(startAngle) * startRadius, 0, Math.sin(startAngle) * startRadius);
    car.rotation.y = -startAngle + Math.PI / 2;
  }

  // Simple collision with track bounds: if too far from track centerline, apply heavy drag
  function applyTrackBounds(pos, vel) {
    const r = Math.sqrt(pos.x * pos.x + pos.z * pos.z);
    const outerLimit = trackRadius + trackThickness + 8;
    const innerLimit = trackRadius - trackThickness - 8;
    if (r > outerLimit || r < innerLimit) {
      // slow the car and push it back toward the track
      const dirToCenter = new THREE.Vector3(-pos.x, 0, -pos.z).normalize();
      car.position.x += dirToCenter.x * 0.2;
      car.position.z += dirToCenter.z * 0.2;
      speed *= 0.6; // harsh slow down
    }
  }

  // Game loop
  let last = performance.now();
  function animate(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;

    updateInput();

    // acceleration/braking
    if (state.accel > 0) {
      speed += ACCELERATION * state.accel * dt;
    } else if (state.accel < 0) {
      // braking / reverse
      if (speed > 0) speed -= BRAKE_DECEL * Math.abs(state.accel) * dt;
      else speed -= ACCELERATION * 0.6 * dt; // reverse
    } else {
      // natural friction
      if (speed > 0) speed -= FRICTION * dt;
      else speed += FRICTION * dt;
    }

    // clamp speeds
    if (speed > MAX_SPEED) speed = MAX_SPEED;
    if (speed < -REVERSE_SPEED) speed = -REVERSE_SPEED;
    if (Math.abs(speed) < 0.01) speed = 0;

    // steering is stronger with speed
    const steerEffect = TURN_SPEED * (Math.min(Math.abs(speed) / MAX_SPEED, 1) + 0.2);
    heading += state.steer * steerEffect * dt * Math.sign(Math.max(speed, 0.05));

    // update car orientation
    car.rotation.y = heading;

    // update position along heading
    const forward = new THREE.Vector3(Math.sin(heading), 0, Math.cos(heading));
    car.position.x += forward.x * speed * dt;
    car.position.z += forward.z * speed * dt;

    // small lateral drift (for arcade feel)
    // apply sideways damping so the car aligns to heading slowly
    car.position.x *= 1; // no-op placeholder if we add sideways later

    applyTrackBounds(car.position);

    // lap detection
    checkLap(car.position);

    // update camera: chase camera with smoothing
    const camOffset = new THREE.Vector3(0, 5, -10).applyAxisAngle(new THREE.Vector3(0, 1, 0), heading);
    const desiredCamPos = new THREE.Vector3().copy(car.position).add(camOffset);
    camera.position.lerp(desiredCamPos, 0.12);
    const lookAt = new THREE.Vector3().copy(car.position).add(new THREE.Vector3(0, 1.2, 0));
    camera.lookAt(lookAt);

    // update HUD
    if (speedEl) speedEl.textContent = Math.round(Math.max(0, speed * 3)); // scaled for arcade "km/h" feel
    if (lapEl) lapEl.textContent = `Laps: ${laps}`;

    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  // Resize handling
  window.addEventListener('resize', onWindowResize);
  function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }

  // Start animation
  requestAnimationFrame(animate);
})();

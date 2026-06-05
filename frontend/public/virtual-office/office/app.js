/* app.js — scene assembly, warm lighting, interaction, projected labels, live pipeline.
   Uses window.Models (loaded by models/loader.js) for all 3D assets. */
(function () {
  const T = window.THREE;
  const ROOM_W = 16, ROOM_D = 15, ROOM_H = 6.2;
  let AGENTS, drawScreen, M, C, mat;
  let renderer, scene, camera, controls, raycaster, pointer;
  const clock = new T.Clock();
  const agentObjs = {};
  const pickTargets = [];
  let selected = null, hovered = null;
  const packets = [];
  let motes;

  function bgTexture() {
    const c = document.createElement('canvas'); c.width = 16; c.height = 256;
    const x = c.getContext('2d');
    const grd = x.createLinearGradient(0, 0, 0, 256);
    grd.addColorStop(0, '#ffcf94');
    grd.addColorStop(0.42, '#f4b483');
    grd.addColorStop(0.72, '#e89b86');
    grd.addColorStop(1, '#cf8f93');
    x.fillStyle = grd; x.fillRect(0, 0, 16, 256);
    return new T.CanvasTexture(c);
  }

  function init() {
    // Resolve references now that models are loaded
    AGENTS = window.OfficeAgents.AGENTS;
    drawScreen = window.OfficeAgents.drawScreen;
    M = window.Models;
    C = window.OfficeChars;
    mat = window.ModelMat.mat;
    const container = document.getElementById('scene');
    renderer = new T.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFSoftShadowMap;
    renderer.outputEncoding = T.sRGBEncoding;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.92;
    container.appendChild(renderer.domElement);

    scene = new T.Scene();
    scene.background = bgTexture();
    scene.fog = new T.Fog(0xeeb389, 36, 70);

    const aspect = container.clientWidth / container.clientHeight;
    const d = 8.7;
    camera = new T.OrthographicCamera(-d * aspect, d * aspect, d, -d, -50, 100);
    camera.position.set(18, 16, 18);
    camera.lookAt(0, 1.5, 0);

    controls = new T.OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1.5, 0.5);
    controls.enableDamping = true; controls.dampingFactor = 0.08;
    controls.minPolarAngle = 0.5; controls.maxPolarAngle = Math.PI / 2.35;
    controls.minZoom = 0.55; controls.maxZoom = 2.2;
    controls.enablePan = false;
    controls.update();

    setupLights();
    M.buildRoom(scene, ROOM_W, ROOM_D, ROOM_H);
    buildProps();
    buildStations();
    buildMotes();

    raycaster = new T.Raycaster();
    pointer = new T.Vector2();
    renderer.domElement.addEventListener('pointermove', onMove);
    renderer.domElement.addEventListener('click', onClick);
    window.addEventListener('resize', onResize);

    buildLabels();
    startSimulation();
    animate();
  }

  function setupLights() {
    scene.add(new T.HemisphereLight(0xffe0b5, 0x6a4836, 0.36));
    scene.add(new T.AmbientLight(0xffe0c0, 0.14));
    const sun = new T.DirectionalLight(0xffc06f, 1.85);
    sun.position.set(-9, 13, -7);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    const s = 16;
    sun.shadow.camera.left = -s; sun.shadow.camera.right = s;
    sun.shadow.camera.top = s; sun.shadow.camera.bottom = -s;
    sun.shadow.camera.near = 1; sun.shadow.camera.far = 50;
    sun.shadow.bias = -0.0004;
    sun.shadow.radius = 4;
    scene.add(sun);
    scene.add(sun.target);
    const fill = new T.DirectionalLight(0xa9c2ff, 0.22);
    fill.position.set(10, 8, 12);
    scene.add(fill);
    const bounce = new T.PointLight(0xffc890, 0.55, 30);
    bounce.position.set(0, 3, 4);
    scene.add(bounce);
    const windowGlow = new T.PointLight(0xffd49a, 0.8, 18);
    windowGlow.position.set(-3.5, 3.6, -5.5);
    scene.add(windowGlow);
  }

  function buildProps() {
    const D2 = ROOM_D / 2, W2 = ROOM_W / 2;
    // Room: back wall Z=-7.5 (faces +Z), left wall X=-8 (faces +X)

    // ========== BACK WALL ZONE (Z ≈ -D2, items face +Z into room) ==========

    // Bookshelf — back-right corner, back flush to wall, faces +Z
    const shelf = M.makeBookshelf();
    shelf.position.set(6.8, 0, -D2 + 0.4); scene.add(shelf);

    // Filing cabinets — lined up neatly next to bookshelf, face +Z
    const filing1 = M.makeFilingCabinet(); filing1.position.set(5.4, 0, -D2 + 0.4); scene.add(filing1);
    const filing2 = M.makeFilingCabinet(); filing2.position.set(4.6, 0, -D2 + 0.4); scene.add(filing2);

    // Arcade — back-left corner, face +Z into room
    const arcade = M.makeArcade(); arcade.position.set(-6.2, 0, -D2 + 0.6); scene.add(arcade);

    // Corner plants near back wall
    const plant2 = M.makePlant(); plant2.position.set(-7.0, 0, -D2 + 0.8); plant2.scale.setScalar(0.92); scene.add(plant2);
    const cactus1 = M.makeCactus(); cactus1.position.set(3.6, 0, -D2 + 0.4); scene.add(cactus1);

    // -- Back wall mounted (all face +Z, spaced evenly) --
    // Venetian blinds over window (window at X=-2.2)
    const blinds = M.makeVenetianBlinds(4.0, 1.8); blinds.position.set(-2.2, 4.72, -D2 + 0.28); scene.add(blinds);

    // Wall TV — right side of back wall, away from window
    const tv = M.makeWallTV(); tv.position.set(3.0, 3.8, -D2 + 0.2); scene.add(tv);

    // Whiteboard — far right of back wall
    const wb = M.makeWhiteboard(); wb.position.set(6.0, 3.0, -D2 + 0.2); scene.add(wb);

    // Poster (planet) — between window and TV
    const poster1 = M.makeFramedPoster(0.8, 1.0, '#1a1820', function (x, w, h) {
      x.fillStyle = '#e08040'; x.beginPath(); x.arc(w / 2, h / 2 + 10, 45, 0, 7); x.fill();
      x.strokeStyle = '#c06030'; x.lineWidth = 2;
      x.beginPath(); x.ellipse(w / 2, h / 2 + 10, 62, 14, 0, 0, 7); x.stroke();
    });
    poster1.position.set(0.6, 4.4, -D2 + 0.2); scene.add(poster1);

    // Poster (game controller) — left of window
    const poster3 = M.makeFramedPoster(0.6, 0.5, '#2a4a3a', function (x, w, h) {
      x.fillStyle = '#4ec5d6'; x.fillRect(w / 2 - 30, h / 2 - 10, 60, 20);
      x.fillStyle = '#ffd23f'; x.beginPath(); x.arc(w / 2 - 12, h / 2, 6, 0, 7); x.fill();
      x.fillStyle = '#ff6f61'; x.beginPath(); x.arc(w / 2 + 12, h / 2, 6, 0, 7); x.fill();
    });
    poster3.position.set(-5.0, 4.2, -D2 + 0.2); scene.add(poster3);

    // Security cam — back-right ceiling corner, angled to watch room
    const cam = M.makeSecurityCam(); cam.position.set(7.0, ROOM_H - 0.1, -D2 + 0.5); cam.rotation.y = Math.PI * 0.75; scene.add(cam);

    // Standing lamp — back-right area
    const lamp2 = M.makeStandingLamp(); lamp2.position.set(7.2, 0, -3.0); scene.add(lamp2);

    // ========== LEFT WALL ZONE (X ≈ -W2, items face +X into room) ==========

    // Kitchenette — runs along left wall, doors already face +X
    const kit = M.makeKitchenette(); kit.position.set(-W2 + 0.7, 0, -1.6); scene.add(kit);

    // Fridge — along left wall, rotated so door faces +X
    const fridge = M.makeFridge(); fridge.position.set(-W2 + 0.5, 0, 2.6); fridge.rotation.y = -Math.PI / 2; scene.add(fridge);

    // Microwave — on kitchenette counter, rotated to face +X
    const microwave = M.makeMicrowave(); microwave.position.set(-W2 + 0.7, 1.05, 0.6); microwave.rotation.y = -Math.PI / 2; scene.add(microwave);

    // Upper cabinets — above kitchenette, face +X
    const upperCab = M.makeUpperCabinets(3); upperCab.position.set(-W2 + 0.42, 3.8, -1.6); upperCab.rotation.y = Math.PI / 2; scene.add(upperCab);

    // Water cooler — along left wall, face +X
    const cooler = M.makeWaterCooler(); cooler.position.set(-W2 + 0.5, 0, 4.2); cooler.rotation.y = -Math.PI / 2; scene.add(cooler);

    // -- Left wall mounted (face +X, spaced vertically & along Z) --
    // Wall shelves — spaced apart on left wall
    const shelfW = M.makeWallShelf(); shelfW.position.set(-W2 + 0.22, 2.7, -5.0); shelfW.rotation.y = Math.PI / 2; scene.add(shelfW);
    const shelfW2 = M.makeWallShelf(); shelfW2.position.set(-W2 + 0.22, 3.8, -5.0); shelfW2.rotation.y = Math.PI / 2; scene.add(shelfW2);

    // Neon sign — higher up, separate from shelves
    const neon = M.makeNeonSign(); neon.position.set(-W2 + 0.25, 4.8, -2.8); neon.rotation.y = Math.PI / 2; scene.add(neon);

    // AC unit — high on left wall, above fridge area
    const ac = M.makeACUnit(); ac.position.set(-W2 + 0.25, 5.2, 2.6); ac.rotation.y = Math.PI / 2; scene.add(ac);

    // Poster (typography) — left wall, above chill zone
    const poster2 = M.makeFramedPoster(0.7, 0.9, '#fbf7ef', function (x, w, h) {
      x.fillStyle = '#2a2730'; x.font = 'bold 52px sans-serif'; x.textAlign = 'center';
      x.fillText('&', w / 2, h / 2 + 18);
    });
    poster2.position.set(-W2 + 0.2, 3.4, 5.0); poster2.rotation.y = Math.PI / 2; scene.add(poster2);

    // ========== LOUNGE NOOK (right side, open area) ==========

    // Rug under lounge
    const loungeRug = M.makeRug(2.0, 0xcf8e7a, 0xe9bfa8); loungeRug.position.set(5.2, 0, 1.2); scene.add(loungeRug);

    // Sofa — back against right edge, faces -X (into room)
    const sofa = M.makeSofa(); sofa.position.set(6.4, 0, 1.2); sofa.rotation.y = Math.PI / 2; scene.add(sofa);

    // Coffee table — in front of sofa
    const tbl = new T.Mesh(new T.CylinderGeometry(0.62, 0.62, 0.12, 24), new T.MeshStandardMaterial({ color: 0xb07c46, roughness: 0.6 }));
    tbl.position.set(4.6, 0.45, 1.2); tbl.castShadow = true; scene.add(tbl);
    const tleg = new T.Mesh(new T.CylinderGeometry(0.08, 0.1, 0.45, 12), new T.MeshStandardMaterial({ color: 0x8a5e34 })); tleg.position.set(4.6, 0.2, 1.2); scene.add(tleg);

    // Armchair — across from sofa, faces +X (towards sofa)
    const armchair1 = M.makeArmchair(0xdfa82f); armchair1.position.set(3.2, 0, 1.2); armchair1.rotation.y = -Math.PI / 2; scene.add(armchair1);

    // Cat on sofa
    const cat = M.makeCat(); cat.position.set(6.2, 0.85, 1.6); cat.rotation.y = Math.PI / 2; scene.add(cat);

    // Standing lamp — corner next to sofa
    const lamp1 = M.makeStandingLamp(); lamp1.position.set(7.2, 0, 3.0); scene.add(lamp1);

    // Plant — lounge corner
    const plant1 = M.makePlant(); plant1.position.set(7.0, 0, -0.6); scene.add(plant1);

    // ========== CHILL ZONE (front-left, facing into room) ==========
    const chillRug = M.makeRug(2.0, 0x8fae9e, 0xbfd8c8); chillRug.position.set(-5.4, 0, 5.6); scene.add(chillRug);
    const bb1 = M.makeBeanbag(0xe0764f); bb1.position.set(-6.2, 0, 5.0); scene.add(bb1);
    const bb2 = M.makeBeanbag(0x6f8fd0); bb2.position.set(-4.6, 0, 6.0); scene.add(bb2);
    const cush = M.makeCushion(0xffd23f); cush.position.set(-5.4, 0, 6.4); scene.add(cush);
    const sideT = M.makeSideTable(); sideT.position.set(-4.8, 0, 4.6); scene.add(sideT);
    const cactus2 = M.makeCactus(); cactus2.position.set(-4.8, 0.56, 4.6); scene.add(cactus2);

    // ========== WORK ZONE (around central pod) ==========

    // Printer on stand — right of pod
    const printStand = new T.Mesh(new T.BoxGeometry(0.8, 0.72, 0.6), mat(0xdcd4c4, { rough: 0.5 }));
    printStand.position.set(5.4, 0.36, -2.0); printStand.castShadow = true; scene.add(printStand);
    const printer = M.makePrinter(); printer.position.set(5.4, 0.72, -2.0); scene.add(printer);

    // Pedestals — flanking the pod desks
    const ped1 = M.makePedestal(); ped1.position.set(-3.8, 0, -1.8); scene.add(ped1);
    const ped2 = M.makePedestal(); ped2.position.set(3.8, 0, -1.8); scene.add(ped2);

    // Desk clutter — on pod desk surfaces
    [[-3, -0.5], [0, -0.5], [3, -0.5], [-3, 1.1], [0, 1.1], [3, 1.1]].forEach(([x, z]) => {
      const clutter = M.makeDeskClutter();
      clutter.position.set(x + 0.7, 1.12, z + 0.3); scene.add(clutter);
    });

    // Trash bins — beside pod
    const bin1 = M.makeTrashBin(); bin1.position.set(-4.2, 0, 0.0); scene.add(bin1);
    const bin2 = M.makeTrashBin(); bin2.position.set(4.2, 0, 0.0); scene.add(bin2);

    // Ferns — flanking front of pod area
    const fern1 = M.makeFern(); fern1.position.set(3.4, 0, 4.8); scene.add(fern1);
    const fern2 = M.makeFern(); fern2.position.set(-3.4, 0, 4.8); fern2.scale.setScalar(0.85); scene.add(fern2);

    // Easel — front area, angled to face center
    const easel = M.makeEasel(); easel.position.set(2.4, 0, 4.6); easel.rotation.y = Math.PI; scene.add(easel);

    // ========== GLASS PARTITIONS ==========
    const gp1 = M.makeGlassPanel(4.0, 2.6); gp1.position.set(-5.2, 0, 0.3); gp1.rotation.y = Math.PI / 2; scene.add(gp1);
    const gp2 = M.makeGlassPanel(3.6, 2.6); gp2.position.set(5.2, 0, 0.3); gp2.rotation.y = Math.PI / 2; scene.add(gp2);
    const gp3 = M.makeGlassPanel(5.0, 2.4); gp3.position.set(0, 0, 3.6); scene.add(gp3);

    // ========== CEILING / OVERHEAD ==========
    // Pendant lamps over pod
    [-3, 0, 3].forEach((x) => { const p = M.makePendant(1.1); p.position.set(x, ROOM_H, 0.3); scene.add(p); });

    // String lights — draped across ceiling
    const sl1 = M.makeStringLights(7.4, 9); sl1.position.set(0, 4.7, -2.4); scene.add(sl1); twinkle.push(sl1);
    const sl2 = M.makeStringLights(7.4, 9); sl2.position.set(0, 4.4, 3.0); scene.add(sl2); twinkle.push(sl2);
  }
  const twinkle = [];

  const SEAT_MAP = {
    market: { side: 'N', slot: 0 }, technical: { side: 'N', slot: 1 }, fundamentals: { side: 'N', slot: 2 },
    sentiment: { side: 'S', slot: 0 }, risk: { side: 'S', slot: 1 }, portfolio: { side: 'S', slot: 2 },
  };

  function buildStations() {
    const seats = AGENTS.map((a) => ({
      id: a.id, side: SEAT_MAP[a.id].side, slot: SEAT_MAP[a.id].slot,
      screen: a.screen, accent: parseInt(a.char.accent), chair: a.char.chair,
    }));
    const pod = M.makePod(seats);
    pod.position.set(0, 0, 0.3);
    scene.add(pod);
    pod.updateMatrixWorld(true);

    pod.userData.seats.forEach((si) => {
      const agent = AGENTS.find((a) => a.id === si.id);
      const char = C.makeCharacter(agent.char);
      const world = pod.localToWorld(si.pos.clone());
      char.position.copy(world);
      char.userData.baseY = char.position.y;
      char.rotation.y = si.faceY;
      scene.add(char);

      const hit = new T.Mesh(new T.BoxGeometry(1.2, 2.4, 1.2), new T.MeshBasicMaterial({ visible: false }));
      hit.position.copy(char.position); hit.position.y += 0.8;
      hit.userData.agentId = agent.id;
      scene.add(hit); pickTargets.push(hit);

      agentObjs[agent.id] = {
        agent, char, monitor: si.monitor,
        state: 'idle', paused: false, logIndex: 0, taskIndex: 0,
        logs: [], headWorld: new T.Vector3(),
      };
    });
  }

  function buildMotes() {
    const N = 120;
    const geo = new T.BufferGeometry();
    const pos = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      pos[i * 3] = -8 + Math.random() * 10;
      pos[i * 3 + 1] = 1 + Math.random() * 5;
      pos[i * 3 + 2] = -6 + Math.random() * 10;
    }
    geo.setAttribute('position', new T.BufferAttribute(pos, 3));
    const sprite = new T.CanvasTexture(dotCanvas());
    motes = new T.Points(geo, new T.PointsMaterial({ size: 0.13, map: sprite, transparent: true, opacity: 0.5, depthWrite: false, blending: T.AdditiveBlending, color: 0xffe6b0 }));
    scene.add(motes);
  }
  function dotCanvas() {
    const c = document.createElement('canvas'); c.width = c.height = 32; const x = c.getContext('2d');
    const g = x.createRadialGradient(16, 16, 0, 16, 16, 16);
    g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = g; x.fillRect(0, 0, 32, 32); return c;
  }

  function buildLabels() {
    const layer = document.getElementById('labels');
    AGENTS.forEach((agent) => {
      const el = document.createElement('div');
      el.className = 'tag';
      el.dataset.id = agent.id;
      el.style.setProperty('--c', agent.color);
      el.innerHTML = `<span class="dot"></span><span class="nm">${agent.name}</span><span class="st">idle</span>`;
      el.addEventListener('click', (e) => { e.stopPropagation(); selectAgent(agent.id); });
      el.addEventListener('mouseenter', () => setHover(agent.id));
      el.addEventListener('mouseleave', () => setHover(null));
      layer.appendChild(el);
      agentObjs[agent.id].label = el;
    });
  }

  function updateLabels() {
    const rect = renderer.domElement.getBoundingClientRect();
    AGENTS.forEach((agent) => {
      const o = agentObjs[agent.id];
      o.char.children[0].getWorldPosition(o.headWorld);
      const p = new T.Vector3(o.char.position.x, o.char.position.y + 2.0, o.char.position.z);
      p.project(camera);
      const x = rect.left + (p.x * 0.5 + 0.5) * rect.width;
      const y = rect.top + (-p.y * 0.5 + 0.5) * rect.height;
      const el = o.label;
      el.style.transform = `translate(-50%,-50%) translate(${x}px,${y}px)`;
      el.style.opacity = p.z < 1 ? 1 : 0;
      const st = el.querySelector('.st');
      st.textContent = o.paused ? 'paused' : o.state;
      el.classList.toggle('working', o.state === 'working' && !o.paused);
      el.classList.toggle('thinking', o.state === 'thinking' && !o.paused);
      el.classList.toggle('sel', selected === agent.id);
    });
  }

  function onMove(e) {
    const r = renderer.domElement.getBoundingClientRect();
    pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
    pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(pickTargets, false);
    setHover(hits.length ? hits[0].object.userData.agentId : null);
    renderer.domElement.style.cursor = hits.length ? 'pointer' : 'grab';
  }
  function setHover(id) {
    if (hovered === id) return;
    if (hovered && agentObjs[hovered]) agentObjs[hovered].char.userData.setHighlight(false);
    hovered = id;
    if (hovered && agentObjs[hovered]) agentObjs[hovered].char.userData.setHighlight(true);
  }
  function onClick() {
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(pickTargets, false);
    if (hits.length) selectAgent(hits[0].object.userData.agentId);
  }

  function selectAgent(id) {
    selected = id;
    window.OfficeUI.openPanel(agentObjs[id]);
  }
  function deselect() { selected = null; }

  const EDGES = {
    market: ['technical', 'fundamentals', 'sentiment'],
    technical: ['risk'], fundamentals: ['risk'], sentiment: ['risk'],
    risk: ['portfolio'], portfolio: ['market'],
  };
  let simTimers = [];
  function later(fn, ms) { const id = setTimeout(fn, ms); simTimers.push(id); return id; }

  function setState(id, st) {
    const o = agentObjs[id];
    if (o.paused) { o.state = 'idle'; return; }
    o.state = st;
    if (st === 'working') pushLog(id);
    if (selected === id) window.OfficeUI.refreshPanel(o);
  }

  function pushLog(id) {
    const o = agentObjs[id], a = o.agent;
    const line = a.logs[o.logIndex % a.logs.length]; o.logIndex++;
    const entry = { t: nowClock(), text: line, color: a.color };
    o.logs.unshift(entry); if (o.logs.length > 30) o.logs.pop();
    window.OfficeUI.feed(a, line);
    if (selected === id) window.OfficeUI.refreshPanel(o);
  }

  function fire(from, to) {
    spawnPacket(from, to);
    later(() => { setState(to, 'thinking'); }, 600);
    later(() => { setState(to, 'working'); }, 1300);
  }

  function runCycle() {
    setState('market', 'thinking');
    later(() => setState('market', 'working'), 700);
    later(() => { pushLog('market'); }, 2200);
    later(() => {
      setState('market', 'idle');
      EDGES.market.forEach((t, i) => later(() => fire('market', t), i * 250));
    }, 3400);
    later(() => {
      ['technical', 'fundamentals', 'sentiment'].forEach((id) => { if (agentObjs[id].state === 'working') pushLog(id); });
    }, 6000);
    later(() => {
      ['technical', 'fundamentals', 'sentiment'].forEach((id) => setState(id, 'idle'));
      fire('technical', 'risk');
    }, 7200);
    later(() => { setState('risk', 'idle'); fire('risk', 'portfolio'); }, 10200);
    later(() => { pushLog('portfolio'); }, 12600);
    later(() => { setState('portfolio', 'idle'); runCycle(); }, 14200);
  }

  function startSimulation() {
    AGENTS.forEach((a, i) => later(() => setState(a.id, i === 0 ? 'thinking' : 'idle'), 200 + i * 120));
    later(runCycle, 1200);
    window.OfficeUI.startTicker();
  }

  function manualHandoff(id) {
    const targets = EDGES[id] || [];
    targets.forEach((t, i) => later(() => fire(id, t), i * 200));
    window.OfficeUI.feed(agentObjs[id].agent, '→ handed off to ' + targets.map(t => agentObjs[t].agent.name).join(', '));
  }
  function togglePause(id) {
    const o = agentObjs[id]; o.paused = !o.paused;
    if (o.paused) o.state = 'idle';
    window.OfficeUI.refreshPanel(o);
    return o.paused;
  }

  function spawnPacket(from, to) {
    const a = agentObjs[from].char.position, b = agentObjs[to].char.position;
    const geo = new T.SphereGeometry(0.16, 12, 12);
    const m = new T.Mesh(geo, new T.MeshStandardMaterial({ color: agentObjs[from].agent.color, emissive: agentObjs[from].agent.color, emissiveIntensity: 1.2, roughness: 0.3 }));
    m.castShadow = false;
    scene.add(m);
    const glow = new T.PointLight(new T.Color(agentObjs[from].agent.color), 1.2, 4);
    m.add(glow);
    packets.push({ mesh: m, from: a.clone(), to: b.clone(), t: 0, dur: 1.3 });
  }
  function updatePackets(dt) {
    for (let i = packets.length - 1; i >= 0; i--) {
      const p = packets[i]; p.t += dt / p.dur;
      const k = Math.min(p.t, 1);
      const x = p.from.x + (p.to.x - p.from.x) * k;
      const z = p.from.z + (p.to.z - p.from.z) * k;
      const y = 1.4 + Math.sin(k * Math.PI) * 1.6;
      p.mesh.position.set(x, y, z);
      p.mesh.scale.setScalar(0.6 + Math.sin(k * Math.PI) * 0.7);
      if (p.t >= 1) { scene.remove(p.mesh); packets.splice(i, 1); }
    }
  }

  function nowClock() {
    const base = new Date(2026, 5, 3, 15, 47, 0);
    base.setSeconds(base.getSeconds() + Math.floor(performance.now() / 1000));
    return base.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function animate() {
    requestAnimationFrame(animate);
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;
    AGENTS.forEach((a) => {
      const o = agentObjs[a.id];
      o.char.userData.update(t, o.paused ? 'idle' : o.state);
      drawScreen(o.monitor, t, o.paused ? 'idle' : o.state, a);
    });
    updatePackets(dt);
    if (motes) {
      const arr = motes.geometry.attributes.position.array;
      for (let i = 0; i < arr.length; i += 3) {
        arr[i + 1] += 0.0025; arr[i] += Math.sin(t + i) * 0.0008;
        if (arr[i + 1] > 6) arr[i + 1] = 1;
      }
      motes.geometry.attributes.position.needsUpdate = true;
    }
    twinkle.forEach((sl) => { if (sl.userData.bulbs) sl.userData.bulbs.forEach((b, i) => { b.material.emissiveIntensity = 0.6 + Math.sin(t * 2 + i * 0.7) * 0.35; }); });
    controls.update();
    renderer.render(scene, camera);
    updateLabels();
  }

  function onResize() {
    const c = document.getElementById('scene');
    const aspect = c.clientWidth / c.clientHeight; const d = 8.7;
    camera.left = -d * aspect; camera.right = d * aspect; camera.top = d; camera.bottom = -d;
    camera.updateProjectionMatrix();
    renderer.setSize(c.clientWidth, c.clientHeight);
  }

  window.OfficeApp = {
    init, selectAgent, deselect, manualHandoff, togglePause,
    forceAgentState: (id, st) => { const o = agentObjs[id]; if (o) { o.state = st; o.paused = false; } },
    getAgentObj: (id) => agentObjs[id],
    get AGENTS() { return AGENTS; },
    resetView() { controls.target.set(0, 1.5, 0.5); camera.position.set(18, 16, 18); camera.zoom = 1; camera.updateProjectionMatrix(); controls.update(); },
  };
})();

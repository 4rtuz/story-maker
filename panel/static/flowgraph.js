// Grafo del flujo del harness (Three.js r160). Cada nodo es un estado del
// núcleo o uno de los cinco subagentes; cada arista, una transición real.
//
// El grafo no decide nada: recibe `{estado, agente}` del sondeo y traduce el
// cambio en una animación. Cuando el estado activo se mueve, un pulso recorre
// la arista, el nodo de destino se enciende y el anterior se apaga. Delegar en
// un subagente es lo mismo hacia arriba, y devolver el turno, lo mismo de vuelta.
//
// La topología vive aquí y solo aquí: `app.js` pasa literales de `harness/state.py`
// y pregunta por la posición en pantalla de un nodo para colgarle una burbuja.

import * as THREE from 'three';

// --------------------------------------------------------------------------
// topología — coordenadas de escena, x a la derecha, y arriba
// --------------------------------------------------------------------------
// El recorrido de un run es demasiado largo para una fila: se dobla en dos
// bandas (la de arriba de izquierda a derecha, la de abajo de derecha a
// izquierda) con el ciclo de escritura en el centro de la de arriba.
const NODOS = [
  // id, rótulo, x, y, tipo
  ['INIT',             'INIT',             -9.6,  2.4, 'estado'],
  ['GENERANDO_BIBLIA', 'GENERANDO BIBLIA', -6.4,  2.4, 'estado'],
  ['GATE_PLAN',        'GATE PLAN',        -3.2,  2.4, 'puerta'],
  ['ESCRIBIENDO',      'ESCRIBIENDO',       0.0,  2.4, 'estado'],
  ['EVALUANDO',        'EVALUANDO',         3.2,  2.4, 'estado'],
  ['ACEPTANDO',        'ACEPTANDO',         6.4,  2.4, 'estado'],
  ['PARCHEANDO',       'PARCHEANDO',        1.6,  0.0, 'estado'],

  ['EDITANDO_ACTO',    'EDITANDO ACTO',     6.4, -2.8, 'estado'],
  ['GATE_ACTO',        'GATE ACTO',         2.4, -2.8, 'puerta'],
  ['AUDITORIA_FINAL',  'AUDITORÍA FINAL',  -1.6, -2.8, 'estado'],
  ['GATE_FINAL',       'GATE FINAL',       -5.6, -2.8, 'puerta'],
  ['COMPLETADO',       'COMPLETADO',       -9.6, -2.8, 'fin'],

  ['arquitecto',       'Arquitecto',       -6.4,  5.4, 'agente'],
  ['escritor',         'Escritor',          0.0,  5.4, 'agente'],
  ['evaluador',        'Evaluador',         3.2,  5.4, 'agente'],
  ['continuista',      'Continuista',       8.9, -0.3, 'agente'],
  ['editor-acto',      'Editor de acto',    6.4, -5.4, 'agente'],
];

// [origen, destino, comba]. La comba desplaza el punto de control de la bézier
// en perpendicular: 0 es recta. Las de vuelta se comban para no solaparse con
// la de ida ni cruzar por encima de un nodo.
const ARISTAS = [
  ['INIT', 'GENERANDO_BIBLIA', 0],
  ['GENERANDO_BIBLIA', 'GATE_PLAN', 0],
  ['GATE_PLAN', 'ESCRIBIENDO', 0],
  ['ESCRIBIENDO', 'EVALUANDO', 0],
  ['EVALUANDO', 'ACEPTANDO', 0],
  ['EVALUANDO', 'PARCHEANDO', 0],
  ['PARCHEANDO', 'ESCRIBIENDO', 0.55],
  ['ACEPTANDO', 'ESCRIBIENDO', 1.9],          // capítulo siguiente
  ['ACEPTANDO', 'EDITANDO_ACTO', -1.5],       // cierre de acto
  ['EDITANDO_ACTO', 'GATE_ACTO', 0],
  ['GATE_ACTO', 'ESCRIBIENDO', -2.2],         // el acto sigue
  ['GATE_ACTO', 'AUDITORIA_FINAL', 0],
  ['AUDITORIA_FINAL', 'GATE_FINAL', 0],
  ['GATE_FINAL', 'COMPLETADO', 0],

  ['GENERANDO_BIBLIA', 'arquitecto', 0],
  ['GATE_ACTO', 'arquitecto', -4.6],          // REVISANDO_ESCALETA
  ['ESCRIBIENDO', 'escritor', 0],
  ['PARCHEANDO', 'escritor', 1.1],
  ['EVALUANDO', 'evaluador', 0],
  ['EVALUANDO', 'continuista', -1.4],
  ['ACEPTANDO', 'continuista', 0],
  ['EDITANDO_ACTO', 'editor-acto', 0],
];

// Estados que el núcleo emite pero no son nodos propios: se dibujan sobre el
// nodo que los ancla (el mismo criterio que la banda vieja de `app.js`).
export const ALIAS = {
  REVISANDO_ESCALETA: 'GATE_ACTO',
  GATE_BLOQUEO: 'EVALUANDO',
  CUOTA_PAUSADA: 'ESCRIBIENDO',
  ERROR: 'ESCRIBIENDO',
  ENTREVISTA: 'GENERANDO_BIBLIA',
};

const R = 0.62;                 // radio del nodo
const VIAJE = 620;              // ms que tarda un pulso en recorrer una arista
const FUNDIDO = 420;            // ms de encendido / apagado

const suave = (t) => t * t * (3 - 2 * t);
const lerp = (a, b, t) => a + (b - a) * t;

// --------------------------------------------------------------------------
// texturas generadas: halo radial y rótulos
// --------------------------------------------------------------------------
function texturaHalo() {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.28, 'rgba(255,255,255,0.45)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// Un rótulo por nodo, pintado en canvas y usado como textura de sprite: es el
// mismo truco que las páginas de `book3d.js`, y evita meter un renderer de
// texto en una escena que solo tiene diecisiete etiquetas cortas.
const ROT_W = 384;
const ROT_H = 96;

function texturaRotulo(texto, agente) {
  const c = document.createElement('canvas');
  c.width = ROT_W;
  c.height = ROT_H;
  const ctx = c.getContext('2d');
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = '#ffffff';
  ctx.font = agente
    ? '600 34px Satoshi, "Segoe UI", system-ui, sans-serif'
    : '500 27px "IBM Plex Mono", ui-monospace, monospace';
  ctx.fillText(texto, ROT_W / 2, ROT_H / 2, ROT_W - 12);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// Los colores salen de los tokens del tema, no de literales: el panel cambia de
// claro a oscuro en caliente y el grafo tiene que ir detrás.
function paleta() {
  const cs = getComputedStyle(document.documentElement);
  const leer = (n, fallback) => {
    const v = cs.getPropertyValue(n).trim();
    return new THREE.Color(v || fallback);
  };
  return {
    // Sobre papel claro, sumar luz solo lava el color hacia el blanco: el halo
    // tiene que teñir, no iluminar.
    claro: document.documentElement.dataset.tema === 'claro',
    acento: leer('--accent', '#ff7932'),
    reposo: leer('--border-2', '#3b4d5e'),
    hecho: leer('--muted', '#8c98a5'),
    linea: leer('--border', '#2b3a47'),
    rotulo: leer('--faint', '#6a757f'),
    rotuloOn: leer('--text', '#e4e6eb'),
    ok: leer('--ok', '#4f9e82'),
  };
}

// --------------------------------------------------------------------------
export function crearGrafo(contenedor, { alMover } = {}) {
  const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let color = paleta();

  const escena = new THREE.Scene();
  // Ortográfica: el grafo es un diagrama, no un objeto; la perspectiva solo
  // torcería las aristas de los extremos.
  const camara = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100);
  camara.position.z = 10;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    contenedor.classList.add('sin-webgl');
    return null;                 // `app.js` sigue sin grafo: el log basta
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  contenedor.appendChild(renderer.domElement);

  const texHalo = texturaHalo();
  const geoDisco = new THREE.CircleGeometry(R, 48);
  const geoAro = new THREE.RingGeometry(R * 1.02, R * 1.14, 48);

  // -- nodos ---------------------------------------------------------------
  const nodos = new Map();
  for (const [id, rotulo, x, y, tipo] of NODOS) {
    const grupo = new THREE.Group();
    grupo.position.set(x, y, 0);

    const halo = new THREE.Sprite(new THREE.SpriteMaterial({
      map: texHalo, color: color.acento, transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    halo.scale.set(R * 6, R * 6, 1);
    halo.position.z = -0.2;

    const disco = new THREE.Mesh(geoDisco, new THREE.MeshBasicMaterial({ color: color.reposo }));
    const aro = new THREE.Mesh(geoAro, new THREE.MeshBasicMaterial({
      color: color.reposo, transparent: true, opacity: 0.55,
    }));
    // Las puertas llevan aro doble: lo que para el run es esperar a un humano
    // tiene que distinguirse de un paso que corre solo.
    if (tipo === 'puerta') aro.scale.setScalar(1.22);

    const agente = tipo === 'agente';
    const etiqueta = new THREE.Sprite(new THREE.SpriteMaterial({
      map: texturaRotulo(rotulo, agente), color: color.rotulo,
      transparent: true, depthWrite: false,
    }));
    etiqueta.scale.set(3.2, 3.2 * (ROT_H / ROT_W), 1);
    // Los estados rotulan debajo; los subagentes, hacia afuera del diagrama,
    // que es donde hay sitio (el Editor de acto cuelga por abajo, no por arriba).
    etiqueta.position.y = !agente ? -(R + 0.5) : y > 0 ? R + 0.52 : -(R + 0.52);

    grupo.add(halo, aro, disco, etiqueta);
    escena.add(grupo);
    // Lo que ocupa el nodo de verdad es el disco mas su rotulo, y el rotulo es
    // mucho mas ancho que el disco. Sin esto, quien coloca las burbujas cree
    // que tapar un rotulo sale gratis.
    const media = 3.2 * (ROT_H / ROT_W) / 2;
    const arriba = Math.max(R, etiqueta.position.y + media);
    const abajo = Math.min(-R, etiqueta.position.y - media);
    nodos.set(id, {
      id, tipo, grupo, halo, disco, aro, etiqueta, nivel: 0, hecho: 0,
      pos: new THREE.Vector3(x, y, 0),
      huella: { ancho: Math.max(R * 2, 3.2), alto: arriba - abajo, cy: (arriba + abajo) / 2 },
    });
  }

  // -- aristas -------------------------------------------------------------
  const aristas = [];
  const matPulso = new THREE.SpriteMaterial({
    map: texHalo, color: color.acento, transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
  for (const [a, b, comba] of ARISTAS) {
    const pa = nodos.get(a).pos;
    const pb = nodos.get(b).pos;
    const medio = pa.clone().add(pb).multiplyScalar(0.5);
    if (comba) {
      const d = pb.clone().sub(pa).normalize();
      medio.add(new THREE.Vector3(-d.y, d.x, 0).multiplyScalar(comba));
    }
    const curva = new THREE.QuadraticBezierCurve3(pa.clone(), medio, pb.clone());
    // Se recorta el trozo que queda bajo los discos para que la línea nazca en
    // el borde del nodo y no en su centro.
    const puntos = curva.getPoints(48);
    const geo = new THREE.BufferGeometry().setFromPoints(puntos);
    geo.translate(0, 0, -0.3);
    const linea = new THREE.Line(geo, new THREE.LineBasicMaterial({
      color: color.linea, transparent: true, opacity: 0.85,
    }));
    escena.add(linea);

    const pulso = new THREE.Sprite(matPulso.clone());
    pulso.scale.set(0.9, 0.9, 1);
    pulso.position.z = -0.1;
    pulso.visible = false;
    escena.add(pulso);

    aristas.push({ a, b, curva, linea, pulso, brillo: 0 });
  }

  // Los halos y los pulsos son lo unico que depende del modo de mezcla.
  function mezclar() {
    const modo = color.claro ? THREE.NormalBlending : THREE.AdditiveBlending;
    for (const n of nodos.values()) {
      n.halo.material.blending = modo;
      n.halo.material.needsUpdate = true;
    }
    for (const e of aristas) {
      e.pulso.material.blending = modo;
      e.pulso.material.needsUpdate = true;
    }
  }

  const aristaEntre = (a, b) =>
    aristas.find((e) => (e.a === a && e.b === b) || (e.a === b && e.b === a));

  // -- animaciones ---------------------------------------------------------
  // Lista plana de tweens. No hace falta más: nunca hay arriba de media docena
  // vivos a la vez y el orden entre ellos lo resuelve el retardo de arranque.
  const tweens = [];
  function tween(ms, paso, { retraso = 0, fin } = {}) {
    if (reducido) { paso(1); fin?.(); return; }
    tweens.push({ t: -retraso, ms, paso, fin });
  }

  function encender(id, destino, retraso = 0) {
    const n = nodos.get(id);
    if (!n) return;
    const desde = n.nivel;
    if (Math.abs(desde - destino) < 0.01) return;
    tween(FUNDIDO, (k) => { n.nivel = lerp(desde, destino, suave(k)); }, { retraso });
  }

  // La delegación: el pulso sale del nodo de origen, recorre la arista, y al
  // 65% del camino el destino empieza a encenderse mientras el origen se apaga.
  // Si los dos nodos no son vecinos no hay nada que recorrer: se conmuta seco.
  function delegar(desde, hasta, { apagarOrigen = true } = {}) {
    const e = desde && hasta ? aristaEntre(desde, hasta) : null;
    if (!e) {
      if (apagarOrigen) encender(desde, 0);
      encender(hasta, 1);
      return;
    }
    const alReves = e.a === hasta;
    e.pulso.visible = true;
    tween(VIAJE, (k) => {
      const t = alReves ? 1 - k : k;
      e.curva.getPointAt(t, e.pulso.position);
      e.pulso.position.z = -0.1;
      const s = Math.sin(Math.PI * k);
      e.pulso.material.opacity = s;
      e.pulso.scale.setScalar(0.7 + s * 0.7);
      e.brillo = s;
    }, {
      fin: () => { e.pulso.visible = false; e.brillo = 0; },
    });
    encender(hasta, 1, VIAJE * 0.65);
    if (apagarOrigen) encender(desde, 0, VIAJE * 0.45);
  }

  // -- estado mostrado -----------------------------------------------------
  let activo = null;     // nodo de estado encendido
  let delegado = null;   // subagente encendido

  function setEstado({ estado, agente, hechos = [] }) {
    const destino = ALIAS[estado] || estado;
    const nodoDestino = nodos.has(destino) ? destino : null;
    const nodoAgente = agente && nodos.has(agente) ? agente : null;

    // Primero vuelve el turno al orquestador, y solo después se mueve el
    // estado: al revés se verían dos pulsos cruzados en la misma arista.
    if (delegado && delegado !== nodoAgente) {
      // el destino del pulso es el estado, que vuelve a quedarse encendido
      delegar(delegado, activo, { apagarOrigen: true });
      delegado = null;
    }
    if (nodoDestino && nodoDestino !== activo) {
      delegar(activo, nodoDestino);
      activo = nodoDestino;
    }
    if (nodoAgente && nodoAgente !== delegado) {
      delegar(activo, nodoAgente, { apagarOrigen: false });
      delegado = nodoAgente;
    }
    // Por dónde ya se ha pasado: se pinta apagado pero no muerto.
    for (const n of nodos.values()) n.hecho = hechos.includes(n.id) ? 1 : 0;
  }

  // -- anclas para las burbujas de la capa DOM -----------------------------
  // La cámara no se mueve, así que la proyección solo cambia al redimensionar.
  let caja = { w: 1, h: 1 };
  function anclas() {
    const salida = {};
    const v = new THREE.Vector3();
    // Pixeles por unidad de mundo: la camara es ortografica, asi que es constante.
    const px = caja.h / (camara.top - camara.bottom);
    for (const n of nodos.values()) {
      v.copy(n.pos).project(camara);
      const x = (v.x * 0.5 + 0.5) * caja.w;
      const y = (-v.y * 0.5 + 0.5) * caja.h;
      salida[n.id] = {
        x, y,
        r: R * px,
        // Caja del nodo con su rotulo, en pixeles del contenedor.
        w: n.huella.ancho * px,
        h: n.huella.alto * px,
        cy: y - n.huella.cy * px,        // el rotulo descentra la caja
      };
    }
    return salida;
  }

  // -- bucle ---------------------------------------------------------------
  // Declarados antes que `medir()`, que es quien dispara el primer `pintar()`.
  const mezcla = new THREE.Color();
  let previo = performance.now();

  const MUNDO = { x0: -11.4, x1: 10.8, y0: -7.35, y1: 7.15 };
  function medir() {
    const w = contenedor.clientWidth || 1;
    const h = contenedor.clientHeight || 1;
    caja = { w, h };
    renderer.setSize(w, h, false);
    // Encaje por el eje más apretado: el diagrama nunca se recorta.
    const anchoMundo = MUNDO.x1 - MUNDO.x0;
    const altoMundo = MUNDO.y1 - MUNDO.y0;
    const escala = Math.max(anchoMundo / w, altoMundo / h);
    const mx = (w * escala) / 2;
    const my = (h * escala) / 2;
    const cx = (MUNDO.x0 + MUNDO.x1) / 2;
    const cy = (MUNDO.y0 + MUNDO.y1) / 2;
    camara.left = cx - mx; camara.right = cx + mx;
    camara.top = cy + my; camara.bottom = cy - my;
    camara.updateProjectionMatrix();
    alMover?.(anclas());
    pintar(0);
  }
  mezclar();
  const observador = new ResizeObserver(medir);
  observador.observe(contenedor);
  medir();

  // Pintar esta fuera del bucle a proposito: `medir()` lo llama tambien, para
  // que el primer frame salga al montar y no en el primer rAF. El grafo se
  // monta tras dos fetch, y hasta entonces el lienzo se veia vacio.
  function pintar(dt) {
    for (let i = tweens.length - 1; i >= 0; i--) {
      const tw = tweens[i];
      tw.t += dt;
      if (tw.t < 0) continue;
      const k = Math.min(tw.t / tw.ms, 1);
      tw.paso(k);
      if (k === 1) { tweens.splice(i, 1); tw.fin?.(); }
    }

    // Respiración del nodo encendido: sin ella un run parado y un run vivo se
    // ven igual, que es justo la pregunta que trae aquí al autor.
    const latido = reducido ? 1 : 0.82 + Math.sin(performance.now() / 420) * 0.18;

    for (const n of nodos.values()) {
      const base = n.hecho ? color.hecho : color.reposo;
      const fin = n.id === 'COMPLETADO' ? color.ok : color.acento;
      mezcla.copy(base).lerp(fin, n.nivel);
      n.disco.material.color.copy(mezcla);
      n.aro.material.color.copy(mezcla);
      n.aro.material.opacity = 0.4 + n.nivel * 0.6;
      n.halo.material.color.copy(fin);
      n.halo.material.opacity = n.nivel * 0.42 * latido;
      n.halo.scale.setScalar(R * (3.4 + n.nivel * 1.6 * latido));
      n.etiqueta.material.color.copy(color.rotulo).lerp(color.rotuloOn, Math.max(n.nivel, n.hecho * 0.5));
    }
    for (const e of aristas) {
      const enc = Math.max(nodos.get(e.a).nivel, nodos.get(e.b).nivel) * 0.35 + e.brillo;
      e.linea.material.color.copy(color.linea).lerp(color.acento, Math.min(enc, 1));
      e.linea.material.opacity = 0.5 + Math.min(enc, 1) * 0.5;
    }

    renderer.render(escena, camara);
  }

  renderer.setAnimationLoop(() => {
    const ahora = performance.now();
    const dt = Math.min(ahora - previo, 64);
    previo = ahora;
    pintar(dt);
  });

  return {
    setEstado,
    anclas,
    // El tema se cambia en caliente desde la cabecera: los tokens se releen y
    // el siguiente frame ya pinta con la paleta nueva.
    retema() { color = paleta(); mezclar(); },
    destruir() {
      renderer.setAnimationLoop(null);
      observador.disconnect();
      escena.traverse((o) => {
        o.geometry?.dispose();
        for (const m of [].concat(o.material || [])) { m.map?.dispose?.(); m.dispose?.(); }
      });
      texHalo.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}

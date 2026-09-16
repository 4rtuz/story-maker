// Visor 3D del libro (Three.js r160). Una hoja por capítulo, con el texto real
// del capítulo pintado en un canvas y usado como textura.
//
// Es navegable, no decorativo: se orbita con el ratón, se pasa hoja pulsando
// sobre la página izquierda o derecha, y se salta de capítulo pulsando en el
// segmento correspondiente del canto. Cualquiera de las tres cosas avisa al
// panel, que sincroniza el lector en 2D.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const ANCHO = 1.35;      // ancho de página, unidades de escena
const ALTO = 1.9;
const SEP = 0.0045;      // separación entre hojas, evita el z-fighting
const PX = 460;          // resolución del canvas de cada cara

// Marca Qaracter: azul #233441 para la tinta y la tapa, naranja #ff7932 para
// el capítulo en curso, off-white #f5f5f5 para el papel. Los dos colores de
// estado (aceptado / con deuda) son derivados: la marca no declara ninguno.
const TINTA = '#233441';
const TINTA_2 = '#6d7b87';
const PAPEL = '#f5f5f5';
const PAPEL_PDTE = '#dcdfe4';

const COLOR = {
  tapa: 0x233441,
  lomo: 0x18222b,
  ok: 0x4f9e82,
  deuda: 0xd4594b,
  pendiente: 0x2b3a47,
  actual: 0xff7932,
};

// --------------------------------------------------------------------------
// pintura de una cara
// --------------------------------------------------------------------------
function ajustar(ctx, texto, ancho) {
  const lineas = [];
  for (const parrafo of String(texto).split(/\n+/)) {
    let linea = '';
    for (const palabra of parrafo.split(/\s+/).filter(Boolean)) {
      const prueba = linea ? `${linea} ${palabra}` : palabra;
      if (ctx.measureText(prueba).width > ancho && linea) {
        lineas.push(linea);
        linea = palabra;
      } else {
        linea = prueba;
      }
    }
    lineas.push(linea);
    lineas.push('');
  }
  return lineas;
}

function pintarCara(cap, dorso) {
  const lienzo = document.createElement('canvas');
  lienzo.width = PX;
  lienzo.height = Math.round(PX * (ALTO / ANCHO));
  const ctx = lienzo.getContext('2d');
  const W = lienzo.width;
  const H = lienzo.height;
  const M = 34;                       // margen
  const util = W - M * 2;

  ctx.fillStyle = cap.escrito ? PAPEL : PAPEL_PDTE;
  ctx.fillRect(0, 0, W, H);
  // veladura hacia el lomo, para que la página no parezca un rectángulo plano
  const sombra = ctx.createLinearGradient(dorso ? W : 0, 0, dorso ? W - 70 : 70, 0);
  sombra.addColorStop(0, 'rgba(35,52,65,0.24)');
  sombra.addColorStop(1, 'rgba(35,52,65,0)');
  ctx.fillStyle = sombra;
  ctx.fillRect(0, 0, W, H);

  let y = M + 14;
  ctx.fillStyle = TINTA_2;
  ctx.font = '500 13px "IBM Plex Mono", monospace';
  ctx.fillText(dorso ? 'FICHA' : `CAPÍTULO ${cap.numero}`, M, y);

  if (!dorso) {
    y += 34;
    ctx.fillStyle = cap.escrito ? TINTA : TINTA_2;
    ctx.font = `${cap.escrito ? '500' : 'italic 400'} 25px Newsreader, Georgia, serif`;
    for (const linea of ajustar(ctx, cap.titulo || 'sin título', util).slice(0, 3)) {
      if (linea) { ctx.fillText(linea, M, y); y += 30; }
    }
    y += 8;
  }

  ctx.strokeStyle = 'rgba(35,52,65,0.3)';
  ctx.beginPath();
  ctx.moveTo(M, y);
  ctx.lineTo(W - M, y);
  ctx.stroke();
  y += 30;

  if (!cap.escrito) {
    ctx.fillStyle = TINTA_2;
    ctx.font = 'italic 17px Newsreader, Georgia, serif';
    ctx.fillText('En la escaleta.', M, y); y += 26;
    ctx.fillText('Todavía sin escribir.', M, y);
    return lienzo;
  }

  if (dorso) {
    ctx.font = "400 15px Satoshi, 'Segoe UI', sans-serif";
    for (const [rotulo, valor] of [
      ['Focalizador', cap.focalizador],
      ['Media del Evaluador', cap.media != null ? cap.media.toFixed(2) : '—'],
      ['Escenas', String(cap.escenas)],
      ['Palabras', String(cap.palabras)],
      ['Deuda', cap.deuda ? 'sí' : 'no'],
    ]) {
      if (!valor) continue;
      ctx.fillStyle = TINTA_2;
      ctx.fillText(rotulo, M, y);
      ctx.fillStyle = TINTA;
      for (const linea of ajustar(ctx, valor, util).slice(0, 2)) {
        if (linea) { y += 21; ctx.fillText(linea, M, y); }
      }
      y += 28;
    }
    if (cap.gancho) {
      ctx.fillStyle = TINTA_2;
      ctx.fillText('Gancho final', M, y); y += 8;
      ctx.fillStyle = TINTA;
      ctx.font = '400 16px Newsreader, Georgia, serif';
      for (const linea of ajustar(ctx, cap.gancho, util)) {
        if (y > H - M) break;
        y += 23; ctx.fillText(linea, M, y);
      }
    }
    return lienzo;
  }

  // anverso: el texto del capítulo, si ya llegó
  ctx.fillStyle = TINTA;
  ctx.font = '400 16px Newsreader, Georgia, serif';
  if (cap.texto) {
    for (const linea of ajustar(ctx, cap.texto, util)) {
      if (y > H - M - 20) { ctx.fillStyle = TINTA_2; ctx.fillText('…', M, y); break; }
      if (linea) ctx.fillText(linea, M, y);
      y += 23;
    }
  } else {
    ctx.fillStyle = TINTA_2;
    ctx.font = 'italic 16px Newsreader, Georgia, serif';
    ctx.fillText('Cargando…', M, y);
  }
  return lienzo;
}

function textura(lienzo) {
  const t = new THREE.CanvasTexture(lienzo);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

// --------------------------------------------------------------------------
export async function crearLibro(contenedor, { alElegir, traerTexto } = {}) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    contenedor.innerHTML = '<div class="fallo">Este navegador no puede dibujar WebGL, así que el libro no se muestra. El lector de la izquierda funciona igual.</div>';
    return { setCapitulos() {}, irA() {}, siguiente() {}, anterior() {}, destruir() {} };
  }

  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  contenedor.appendChild(renderer.domElement);

  const escena = new THREE.Scene();
  const camara = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camara.position.set(0, 0.42, 3.75);

  escena.add(new THREE.AmbientLight(0xf2f5f8, 1.5));
  const foco = new THREE.DirectionalLight(0xffffff, 2.1);
  foco.position.set(2.2, 3.4, 3.2);
  escena.add(foco);
  const relleno = new THREE.DirectionalLight(0x7f93a8, 0.5);
  relleno.position.set(-3, -1, 1.5);
  escena.add(relleno);

  const controles = new OrbitControls(camara, renderer.domElement);
  controles.enableDamping = true;
  controles.dampingFactor = 0.07;
  controles.enablePan = false;
  controles.minDistance = 2.4;
  controles.maxDistance = 8;
  controles.minPolarAngle = 0.35;
  controles.maxPolarAngle = Math.PI / 2 + 0.25;
  controles.minAzimuthAngle = -Math.PI / 2.4;
  controles.maxAzimuthAngle = Math.PI / 2.4;

  const libro = new THREE.Group();
  libro.rotation.x = -0.12;
  escena.add(libro);

  const geoPagina = new THREE.PlaneGeometry(ANCHO, ALTO);
  const raycaster = new THREE.Raycaster();
  const puntero = new THREE.Vector2();

  let capitulos = [];
  let hojas = [];          // { grupo, anverso, dorso, cap, objetivo }
  let lomo = [];           // segmentos clicables
  let actual = 1;
  let vivo = true;
  const pedidos = new Set();

  // -- tapas ---------------------------------------------------------------
  const matTapa = new THREE.MeshStandardMaterial({ color: COLOR.tapa, roughness: 0.82 });
  for (const lado of [-1, 1]) {
    const tapa = new THREE.Mesh(new THREE.BoxGeometry(ANCHO + 0.06, ALTO + 0.06, 0.04), matTapa);
    tapa.position.set(lado * (ANCHO / 2 + 0.01), 0, -0.05);
    libro.add(tapa);
  }

  // Encuadre: el libro siempre entra entero, se estreche o se ensanche el
  // panel. Deja de imponerse en cuanto el lector mueve la cámara.
  let sinTocar = true;
  controles.addEventListener('start', () => { sinTocar = false; });

  function encuadrar() {
    const mitad = THREE.MathUtils.degToRad(camara.fov) / 2;
    const d = Math.max(
      (ALTO / 2 + 0.34) / Math.tan(mitad),
      (ANCHO + 0.24) / (Math.tan(mitad) * camara.aspect),
    );
    controles.minDistance = d * 0.55;
    controles.maxDistance = d * 2.6;
    camara.position.set(0, d * 0.1, d);
    camara.lookAt(0, 0, 0);
    controles.target.set(0, 0, 0);
    controles.update();
  }

  // -- construcción --------------------------------------------------------
  function limpiarHojas() {
    for (const h of [...hojas, ...lomo]) {
      const objeto = h.grupo || h;
      objeto.traverse((n) => {
        if (!n.isMesh) return;
        n.geometry !== geoPagina && n.geometry.dispose();
        for (const m of [].concat(n.material)) { m.map?.dispose(); m.dispose(); }
      });
      libro.remove(objeto);
    }
    hojas = [];
    lomo = [];
  }

  function colorDe(cap) {
    if (!cap.escrito) return COLOR.pendiente;
    if (cap.numero === actual) return COLOR.actual;
    return cap.deuda ? COLOR.deuda : COLOR.ok;
  }

  function construir() {
    limpiarHojas();
    const n = capitulos.length || 1;

    capitulos.forEach((cap, i) => {
      const grupo = new THREE.Group();          // pivote en el lomo (x = 0)
      const anverso = new THREE.Mesh(geoPagina, new THREE.MeshStandardMaterial({
        map: textura(pintarCara(cap, false)), roughness: 0.96,
      }));
      anverso.position.x = ANCHO / 2;
      const dorso = new THREE.Mesh(geoPagina, new THREE.MeshStandardMaterial({
        map: textura(pintarCara(cap, true)), roughness: 0.96,
      }));
      dorso.position.x = ANCHO / 2;
      dorso.rotation.y = Math.PI;
      grupo.add(anverso, dorso);
      grupo.userData = { hoja: i };
      anverso.userData = dorso.userData = { hoja: i };
      libro.add(grupo);
      hojas.push({ grupo, anverso, dorso, cap, objetivo: 0 });

      // Canto: un segmento por capítulo bajo el libro. En un libro abierto de
      // frente el lomo queda tapado por las tapas, así que los segmentos van
      // aquí, donde se ven siempre y se pueden pulsar.
      const ancho = (ANCHO * 2) / n;
      const seg = new THREE.Mesh(
        new THREE.BoxGeometry(ancho * 0.88, 0.075, 0.1),
        new THREE.MeshStandardMaterial({ color: colorDe(cap), roughness: 0.65 }),
      );
      seg.position.set(-ANCHO + ancho * (i + 0.5), -(ALTO / 2 + 0.17), 0.02);
      seg.userData = { salto: cap.numero };
      libro.add(seg);
      lomo.push(seg);
    });

    colocar(true);
  }

  // Hoja i pasada a la izquierda cuando su capítulo ya quedó atrás.
  function colocar(inmediato) {
    hojas.forEach((h, i) => {
      const pasada = h.cap.numero < actual;
      h.objetivo = pasada ? -Math.PI : 0;
      h.grupo.position.z = pasada ? SEP * (i + 1) : SEP * (hojas.length - i);
      if (inmediato) h.grupo.rotation.y = h.objetivo;
    });
    lomo.forEach((s, i) => {
      s.material.color.setHex(colorDe(capitulos[i]));
      s.position.z = capitulos[i].numero === actual ? 0.1 : 0.02;   // el actual sobresale
    });
  }

  function repintarAnverso(i) {
    const h = hojas[i];
    if (!h) return;
    h.anverso.material.map.dispose();
    h.anverso.material.map = textura(pintarCara(h.cap, false));
    h.anverso.material.needsUpdate = true;
  }

  // El texto del capítulo se pide solo cuando su hoja hace falta.
  async function asegurarTexto(numero) {
    const i = capitulos.findIndex((c) => c.numero === numero);
    const cap = capitulos[i];
    if (!cap || !cap.escrito || cap.texto || pedidos.has(numero) || !traerTexto) return;
    pedidos.add(numero);
    try {
      const datos = await traerTexto(numero);
      cap.texto = datos.escenas.map((s) => s.texto).join('\n\n');
      if (vivo) repintarAnverso(i);
    } catch {
      pedidos.delete(numero);
    }
  }

  // -- interacción ---------------------------------------------------------
  function bajo(evento) {
    const caja = renderer.domElement.getBoundingClientRect();
    puntero.x = ((evento.clientX - caja.left) / caja.width) * 2 - 1;
    puntero.y = -((evento.clientY - caja.top) / caja.height) * 2 + 1;
    raycaster.setFromCamera(puntero, camara);
    const objetivos = [...lomo, ...hojas.flatMap((h) => [h.anverso, h.dorso])];
    return raycaster.intersectObjects(objetivos, false)[0] || null;
  }

  let arrastrando = false;
  renderer.domElement.addEventListener('pointerdown', () => { arrastrando = false; });
  renderer.domElement.addEventListener('pointermove', () => { arrastrando = true; });

  renderer.domElement.addEventListener('pointerup', (evento) => {
    if (arrastrando) return;               // un giro de cámara no es un clic
    const golpe = bajo(evento);
    if (!golpe) return;
    if (golpe.object.userData.salto) return irA(golpe.object.userData.salto, true);
    // el punto de impacto decide: lado derecho avanza, izquierdo retrocede
    if (golpe.point.x >= 0) siguiente(); else anterior();
  });

  renderer.domElement.addEventListener('pointermove', (evento) => {
    const golpe = bajo(evento);
    renderer.domElement.style.cursor = golpe ? 'pointer' : 'grab';
  });

  // -- API -----------------------------------------------------------------
  function irA(numero, avisar) {
    const cap = capitulos.find((c) => c.numero === numero);
    if (!cap || numero === actual) {
      if (cap && avisar && cap.escrito) alElegir?.(numero);
      return;
    }
    actual = numero;
    colocar(false);
    asegurarTexto(numero);
    asegurarTexto(numero + 1);
    if (avisar && cap.escrito) alElegir?.(numero);
  }

  const siguiente = () => irA(Math.min(actual + 1, capitulos.length || 1), true);
  const anterior = () => irA(Math.max(actual - 1, 1), true);

  // -- bucle ---------------------------------------------------------------
  function medir() {
    const { clientWidth: w, clientHeight: h } = contenedor;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camara.aspect = w / h;
    camara.updateProjectionMatrix();
    if (sinTocar) encuadrar();
  }
  const observador = new ResizeObserver(medir);
  observador.observe(contenedor);
  medir();

  const reloj = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const paso = Math.min(reloj.getDelta() * 5.5, 1);
    for (const h of hojas) {
      const d = h.objetivo - h.grupo.rotation.y;
      if (Math.abs(d) > 0.001) h.grupo.rotation.y += d * paso;
    }
    controles.update();
    renderer.render(escena, camara);
  });

  return {
    setCapitulos(lista) {
      const mismos = lista.length === capitulos.length
        && lista.every((c, i) => c.numero === capitulos[i].numero
          && c.escrito === capitulos[i].escrito && c.media === capitulos[i].media);
      if (mismos) return;
      // conserva el texto ya traído de los capítulos que no han cambiado
      const cache = new Map(capitulos.map((c) => [c.numero, c.texto]));
      capitulos = lista.map((c) => ({ ...c, texto: cache.get(c.numero) }));
      if (!capitulos.some((c) => c.numero === actual)) actual = 1;
      construir();
      asegurarTexto(actual);
      asegurarTexto(actual + 1);
    },
    irA: (n) => irA(n, false),
    siguiente,
    anterior,
    destruir() {
      vivo = false;
      renderer.setAnimationLoop(null);
      observador.disconnect();
      controles.dispose();
      limpiarHojas();
      geoPagina.dispose();
      matTapa.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}

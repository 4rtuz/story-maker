// Panel del harness de novela. Une las tres vistas con la API del servidor.
// Nada de lógica del núcleo vive aquí: los veredictos, las medias y las
// transiciones llegan ya calculados desde `python -m harness`.

import { crearLibro } from './book3d.js';
import { crearGrafo, ALIAS } from './flowgraph.js';

// Los estados por los que pasa una ejecución normal, en orden de lectura. Ya no
// se pintan como banda: el orden sirve para saber qué nodos del grafo quedan
// detrás del actual. Los literales salen de harness/state.py.
const BANDA = [
  'INIT', 'GENERANDO_BIBLIA', 'GATE_PLAN', 'ESCRIBIENDO', 'EVALUANDO',
  'PARCHEANDO', 'ACEPTANDO', 'EDITANDO_ACTO', 'GATE_ACTO',
  'AUDITORIA_FINAL', 'GATE_FINAL', 'COMPLETADO',
];

// Qué agente corresponde a cada paso del ciclo, para cuando no hay stream.
const PASO_AGENTE = { escribir: 'escritor', evaluar: 'evaluador', verificar: 'continuista' };

const PUERTAS = {
  GATE_PLAN: {
    titulo: 'Puerta 1 — plan',
    texto: 'La biblia está completa. Apruébala y empieza el capítulo 1.',
    botones: ['aprobar', 'editar'],
    libre: { prefijo: 'rehacer', marca: 'escaleta.md : el acto 2 pierde tensión' },
  },
  GATE_ACTO: {
    titulo: 'Puerta 2 — cierre de acto',
    texto: 'El Editor de acto ha entregado su informe. Míralo en `informes/` antes de decidir.',
    botones: ['continuar', 'parar'],
    libre: { prefijo: 'ajustar', marca: 'instrucción para la escaleta' },
  },
  GATE_FINAL: {
    titulo: 'Puerta 3 — entrega final',
    texto: 'La auditoría final ha pasado. Aceptar cierra la ejecución.',
    botones: ['aceptar'],
  },
  GATE_BLOQUEO: {
    titulo: 'Puerta de bloqueo — continuidad',
    texto: 'El Continuista ha encontrado una contradicción con el estado establecido.',
    botones: ['forzar', 'parar'],
    libre: { prefijo: 'reescribir', marca: 'instrucción para el Escritor' },
  },
};

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const estado = {
  vista: 'lanzar',
  slug: null,
  runs: [],
  perfiles: [],
  claude: false,
  snap: null,
  seguir: false,   // el autor ha dado permiso para encadenar fases
  capitulos: [],
  capitulo: null,
  timer: null,
  libro: null,
};

// --------------------------------------------------------------------------
// API
// --------------------------------------------------------------------------
async function api(ruta, opciones = {}) {
  const res = await fetch(ruta, {
    ...opciones,
    headers: opciones.body ? { 'Content-Type': 'application/json' } : undefined,
  });
  const datos = await res.json().catch(() => ({ error: `${res.status} ${res.statusText}` }));
  if (!res.ok) throw new Error(datos.error || `${res.status}`);
  return datos;
}

const post = (ruta, cuerpo) => api(ruta, { method: 'POST', body: JSON.stringify(cuerpo || {}) });

let brindisTimer;
function brindis(mensaje, malo = false) {
  const el = $('#brindis');
  el.textContent = mensaje;
  el.classList.toggle('malo', malo);
  el.hidden = false;
  clearTimeout(brindisTimer);
  brindisTimer = setTimeout(() => { el.hidden = true; }, malo ? 9000 : 5000);
}

// --------------------------------------------------------------------------
// navegación
// --------------------------------------------------------------------------
const VISTAS = ['lanzar', 'progreso', 'lector'];

// La vista, y el capítulo abierto, viajan en el hash: `#lector/2` es un enlace.
function fijarHash() {
  const destino = estado.vista === 'lector' && estado.capitulo
    ? `lector/${estado.capitulo}` : estado.vista;
  if (location.hash.slice(1) !== destino) location.hash = destino;
}

function irAVista(nombre) {
  estado.vista = nombre;
  fijarHash();
  document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('on', b.dataset.vista === nombre));
  document.querySelectorAll('.vista').forEach((v) => v.classList.toggle('on', v.id === `vista-${nombre}`));
  sondeo();
  if (nombre === 'lector') cargarCapitulos();
  if (nombre === 'progreso') refrescarProgreso();
}

// Tema: el atributo lo pone el HTML antes de pintar (ver index.html), aqui solo
// se alterna y se recuerda.
function pintarTema(t) {
  document.documentElement.dataset.tema = t;
  $('#btn-tema').textContent = t === 'claro' ? '☼' : '☾';
  try { localStorage.setItem('tema', t); } catch {}
}
pintarTema(document.documentElement.dataset.tema || 'oscuro');
$('#btn-tema').addEventListener('click', () => {
  pintarTema(document.documentElement.dataset.tema === 'claro' ? 'oscuro' : 'claro');
  grafo?.retema();
});

$('#tabs').addEventListener('click', (e) => {
  const boton = e.target.closest('button[data-vista]');
  if (boton) irAVista(boton.dataset.vista);
});

function sondeo() {
  clearInterval(estado.timer);
  estado.timer = null;
  if (estado.vista === 'progreso' && estado.slug) {
    // Sondeo simple contra un endpoint sin efectos. El mecanismo real por
    // debajo es lectura de disco, así que un stream no compraría nada.
    estado.timer = setInterval(refrescarProgreso, 1500);
  }
}

// --------------------------------------------------------------------------
// vista: lanzar
// --------------------------------------------------------------------------
async function cargarRuns() {
  const datos = await api('/api/runs');
  estado.runs = datos.runs;
  estado.perfiles = datos.perfiles;
  estado.claude = datos.claude;
  if (!estado.slug && datos.runs.length) estado.slug = datos.runs[0].slug;

  const sel = $('#in-perfil');
  sel.innerHTML = datos.perfiles.map((p) => `<option value="${esc(p)}">${esc(p)}</option>`).join('');
  sel.value = datos.perfil_activo || datos.perfiles[0] || '';

  const aviso = $('#aviso-claude');
  aviso.classList.toggle('oculto', false);
  aviso.innerHTML = datos.claude
    ? '<span>«Lanzar» arranca el orquestador real de Claude Code como subproceso y vuelca su stream al panel. El núcleo sigue decidiendo: el panel solo lo invoca y lo mira.</span>'
    : '<span>No encuentro el binario <code>claude</code> en el PATH: podrás crear ejecuciones y leer capítulos, pero no lanzar agentes. Para escribir, abre Claude Code en este repositorio y escribe <code>/novela</code>.</span>';

  $('#runs-total').textContent = datos.runs.length;
  $('#lista-runs').innerHTML = datos.runs.map(tarjetaRun).join('') || '<p class="vacio-msg">Todavía no hay ninguna ejecución.</p>';
  pintarTopMeta();
}

function tarjetaRun(r) {
  const enPuerta = r.estado.startsWith('GATE_');
  const chip = r.estado === 'COMPLETADO' ? 'ok' : enPuerta ? 'puerta' : '';
  const barras = Array.from({ length: r.total }, (_, i) => {
    const n = i + 1;
    const cls = !r.aceptados.includes(n) ? '' : r.con_deuda.includes(n) ? 'deuda' : 'ok';
    return `<i class="${cls}"></i>`;
  }).join('');
  const nota = enPuerta
    ? `<span class="run-nota puerta">esperando tu respuesta · ${esc(r.puerta_pendiente || '')}</span>`
    : `<span class="run-nota">${r.aceptados.length} de ${r.total} capítulos${r.con_deuda.length ? ` · ${r.con_deuda.length} con deuda` : ''}</span>`;
  return `<div class="run ${r.slug === estado.slug ? 'sel' : ''}" data-slug="${esc(r.slug)}">
    <div class="run-head">
      <span class="run-titulo ${r.titulo ? '' : 'vacio'}">${esc(r.titulo || 'sin título todavía')}</span>
      <span class="run-ruta">${esc(r.ruta)}</span>
      <div class="grow"></div>
      <span class="chip ${chip}">${esc(r.estado)}</span>
    </div>
    <div class="run-barra">${barras}${nota}</div>
  </div>`;
}

$('#lista-runs').addEventListener('click', (e) => {
  const tarjeta = e.target.closest('.run');
  if (!tarjeta) return;
  estado.slug = tarjeta.dataset.slug;
  estado.capitulo = null;
  estado.seguir = false;   // mirar otra ejecución no es pedir que arranque
  document.querySelectorAll('.run').forEach((n) => n.classList.toggle('sel', n === tarjeta));
  pintarTopMeta();
  irAVista('progreso');
});

$('#in-slug').addEventListener('blur', (e) => {
  if (e.target.value) e.target.value = e.target.value.trim().toLowerCase();
});

async function crear(arrancar) {
  const slug = $('#in-slug').value.trim();
  const salida = $('#form-salida');
  salida.hidden = false;
  salida.classList.remove('malo');
  salida.textContent = 'Creando…';
  try {
    const res = await post('/api/runs', {
      slug,
      idea: $('#in-idea').value,
      perfil: $('#in-perfil').value,
    });
    salida.textContent = res.salida;
    estado.slug = res.slug;
    await cargarRuns();
    if (arrancar) {
      irAVista('progreso');
      await lanzar();
    }
  } catch (err) {
    salida.classList.add('malo');
    salida.textContent = err.message;
  }
}

$('#form-nueva').addEventListener('submit', (e) => { e.preventDefault(); crear(true); });
$('#btn-crear').addEventListener('click', () => {
  if ($('#form-nueva').reportValidity()) crear(false);
});

// --------------------------------------------------------------------------
// vista: progreso — el grafo y sus burbujas
// --------------------------------------------------------------------------
// El grafo es la vista: los estados y los cinco subagentes son nodos, y lo que
// antes eran paneles sueltos (la puerta abierta, la caja de mensaje, la tabla
// de intentos) cuelga ahora del nodo que lo produce. `anclasGrafo` son esas
// posiciones, en píxeles del contenedor, y solo cambian al redimensionar.
let grafo = null;
let grafoMontado = false;     // sin WebGL `crearGrafo` devuelve null: no reintentar
let anclasGrafo = {};
const tallos = new Map();

function montarGrafo() {
  if (grafoMontado) return;
  grafoMontado = true;
  grafo = crearGrafo($('#grafo'), {
    alMover: (anclas) => { anclasGrafo = anclas; recolocar(); },
  });
}

// El tallo une la burbuja con su nodo: es una línea suelta en el lienzo, no un
// borde de la burbuja, porque tiene que quedar por debajo de ella.
function tallo(clave, ancla, centro) {
  let i = tallos.get(clave);
  if (!i) {
    i = document.createElement('i');
    i.className = 'tallo';
    $('#grafo-zona').appendChild(i);
    tallos.set(clave, i);
  }
  const dx = centro.x - ancla.x;
  const dy = centro.y - ancla.y;
  i.style.left = `${ancla.x}px`;
  i.style.top = `${ancla.y}px`;
  i.style.width = `${Math.hypot(dx, dy)}px`;
  i.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
  i.hidden = false;
}

// Área solapada de dos rectángulos, 0 si no se tocan.
function corte(a, b) {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}

// Coste de una posición: cuánto tapa, medido por área y no por número de nodos
// —tapar media etiqueta no es lo mismo que sepultar un nodo—. El nodo encendido
// pesa cinco veces: es justo el que se ha venido a mirar. Pisar otra burbuja
// pesa diez, porque la deja inservible. La distancia solo deshace empates.
function estorbo(caja, ancla, propio, ocupados) {
  let coste = 0;
  for (const [id, a] of Object.entries(anclasGrafo)) {
    if (id === propio) continue;
    const nodo = { x: a.x - a.w / 2, y: a.cy - a.h / 2, w: a.w, h: a.h };
    const parte = corte(caja, nodo) / (nodo.w * nodo.h);
    coste += parte * (id === estado.nodoActivo || id === estado.agenteActivo ? 50 : 10);
  }
  for (const o of ocupados) {
    coste += (corte(caja, o) / (o.w * o.h)) * 100;
  }
  return coste + Math.hypot(caja.x + caja.w / 2 - ancla.x, caja.y + caja.h / 2 - ancla.y) / 500;
}

// Coloca una burbuja donde tape menos grafo. Antes caía siempre hacia abajo y
// en un capítulo avanzado eso enterraba media banda inferior.
function colocar(el, id, ocupados = []) {
  const ancla = anclasGrafo[id];
  const zona = $('#grafo-zona');
  if (!ancla || el.hidden || !zona.clientWidth) {
    const i = tallos.get(el.id);
    if (i) i.hidden = true;
    return null;
  }
  const w = el.offsetWidth;
  const h = el.offsetHeight;
  const W = zona.clientWidth;
  const H = zona.clientHeight;
  // Barrido en rejilla en vez de una lista de sitios a mano: el grafo deja
  // huecos que no caen ni al lado del nodo ni en una esquina, y probarlos todos
  // cuesta unos pocos miles de comparaciones de rectángulos cada 1,5 s.
  const PASO = 24;
  let mejor = null;
  for (let y = 10; y <= H - h - 10; y += PASO) {
    for (let x = 10; x <= W - w - 10; x += PASO) {
      const caja = { x, y, w, h };
      const coste = estorbo(caja, ancla, id, ocupados);
      if (!mejor || coste < mejor.coste) mejor = { caja, coste };
    }
  }
  // La burbuja no cabe en el lienzo: se clava arriba a la izquierda y ya.
  if (!mejor) mejor = { caja: { x: 10, y: 10, w, h } };
  el.style.left = `${mejor.caja.x}px`;
  el.style.top = `${mejor.caja.y}px`;
  // El origen de la animación de entrada es el punto del nodo: por eso la
  // burbuja «sale» de él en lugar de aparecer centrada sobre sí misma.
  el.style.transformOrigin = `${ancla.x - mejor.caja.x}px ${ancla.y - mejor.caja.y}px`;
  tallo(el.id, ancla, { x: mejor.caja.x + w / 2, y: mejor.caja.y + h / 2 });
  return mejor.caja;
}

// Los intentos van clavados en la columna que el lienzo deja libre. No buscan
// hueco: no hay ninguno que no tape un nodo, y enterrar el mapa era peor que
// perder la cercanía. El tallo y la animación de entrada siguen diciendo de qué
// nodo salen, que es lo que tenían que decir.
function fijarIntentos(el, id) {
  const zona = $('#grafo-zona');
  const ancla = anclasGrafo[id];
  const x = zona.clientWidth - el.offsetWidth - 8;
  const y = 10;
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  if (!ancla) { const i = tallos.get(el.id); if (i) i.hidden = true; return null; }
  el.style.transformOrigin = `${ancla.x - x}px ${ancla.y - y}px`;
  tallo(el.id, ancla, { x: x + el.offsetWidth / 2, y: y + el.offsetHeight / 2 });
  return { x, y, w: el.offsetWidth, h: el.offsetHeight };
}

function recolocar() {
  // Primero la columna fija, y la de responder ya la esquiva.
  const ocupados = [];
  const intentos = $('#burbuja-intentos');
  if (!intentos.hidden) {
    const caja = fijarIntentos(intentos, intentos.dataset.ancla || 'EVALUANDO');
    if (caja) ocupados.push(caja);
  } else {
    const i = tallos.get(intentos.id);
    if (i) i.hidden = true;
  }
  const responder = $('#burbuja-responder');
  if (!responder.hidden) colocar(responder, responder.dataset.ancla || 'ESCRIBIENDO', ocupados);
}

// La respuesta enviada no se desvanece: se encoge hacia el nodo que la recibe,
// como una ventana que se minimiza al Dock. Es la única pista visual de a quién
// ha ido a parar lo que acabas de escribir.
function genio(el, id) {
  const ancla = anclasGrafo[id];
  const i = tallos.get(el.id);
  if (i) i.hidden = true;
  el.dataset.marca = '';
  if (!ancla || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    el.hidden = true;
    return;
  }
  el.style.setProperty('--gx', `${ancla.x - (el.offsetLeft + el.offsetWidth / 2)}px`);
  el.style.setProperty('--gy', `${ancla.y - (el.offsetTop + el.offsetHeight / 2)}px`);
  el.classList.remove('brota');
  el.classList.add('genio');
  el.addEventListener('animationend', () => {
    el.classList.remove('genio');
    el.hidden = true;
  }, { once: true });
}

async function refrescarProgreso() {
  if (!estado.slug) return;
  montarGrafo();
  try {
    estado.snap = await api(`/api/runs/${estado.slug}/estado`);
  } catch (err) {
    brindis(err.message, true);
    clearInterval(estado.timer);
    return;
  }
  pintarProgreso(estado.snap);
  pintarTopMeta();
  autoContinuar(estado.snap);
}

// Lo que cambia cuando el núcleo ha avanzado de verdad. Los archivos de
// `.intentos/` no entran: la entrevista reescribe `ctx.md` sin mover el estado,
// y eso es justo lo que no debe contar como progreso.
const firma = (s) => `${s.estado}|${s.capitulo_actual}|${s.iteracion}|${s.capitulos_aceptados.length}`;

// Estados en los que parar es la respuesta correcta: la cuota la reinicia el día
// UTC siguiente, y una novela completa no tiene fase siguiente.
const SIN_RELANZAR = ['COMPLETADO', 'CUOTA_PAUSADA'];

// Seguir es una intención del autor, no un evento: responder una puerta o pulsar
// «Lanzar» la enciende, «Detener» la apaga. Antes esto colgaba de una llamada
// suelta en el instante del clic, y si esa llamada no salía —pestaña recargada,
// puerta respondida desde otro sitio, error de red— la ejecución se quedaba
// parada para siempre con el estado diciendo que tocaba trabajar.
function autoContinuar(ahora) {
  if (!estado.seguir || ahora.vivo || estado.detenido) return;
  if (ahora.estado.startsWith('GATE_') || SIN_RELANZAR.includes(ahora.estado)) return;
  if (firma(ahora) === estado.firmaLanzada) {
    // Terminó sin mover el estado: te ha preguntado algo (la entrevista) o ha
    // fallado. Relanzar aquí sería un bucle de llamadas contra la cuota.
    estado.seguir = false;
    brindis('El orquestador terminó sin avanzar el estado. Mira los eventos: si te ha '
            + 'preguntado algo, contéstale en la burbuja del nodo activo y vuelve a lanzar.', true);
    return;
  }
  lanzar();
}

function pintarProgreso(s) {
  const rotulo = (s.titulo || s.slug).length > 70 ? `${(s.titulo || s.slug).slice(0, 70)}…` : (s.titulo || s.slug);
  $('#prog-contexto').textContent =
    `${rotulo} · capítulo ${Math.min(s.capitulo_actual, s.total)} de ${s.total} · iteración ${s.iteracion} · acto ${s.acto_actual}`;
  $('#btn-parar').hidden = !s.vivo;
  $('#btn-lanzar-run').disabled = s.vivo || !estado.claude;
  $('#btn-lanzar-run').textContent = s.vivo ? 'Orquestador en marcha'
    : s.espera_respuesta ? 'Responder y lanzar' : 'Lanzar agentes';

  // El grafo solo recibe hechos: qué estado está activo, en qué subagente se ha
  // delegado y por dónde ya se ha pasado. La animación la decide él.
  const ancla = ALIAS[s.estado] || s.estado;
  const tope = BANDA.indexOf(ancla);
  const agente = s.agente_en_curso || (s.vivo ? PASO_AGENTE[s.paso] : '') || '';
  grafo?.setEstado({ estado: s.estado, agente, hechos: tope > 0 ? BANDA.slice(0, tope) : [] });
  estado.nodoActivo = ancla;
  estado.agenteActivo = agente;

  pintarResponder(s, ancla, agente);
  pintarIntentos(s, ancla);

  // log
  $('#log-fuente').textContent = s.eventos.length ? `${s.eventos.length} · cada 1,5 s` : 'sin stream todavía';
  $('#log').innerHTML = s.eventos.length
    ? s.eventos.map((e) => `<div class="ev ${esc(e.tipo)}"><em>${e.tipo === 'agente' ? '▸' : '·'}</em><span>${esc(e.texto)}</span></div>`).join('')
    : '<div class="ev"><span>El stream aparece cuando lanzas el orquestador desde aquí. Si lo arrancas a mano en Claude Code, el progreso se sigue viendo por el estado y el grafo.</span></div>';
  $('#log').scrollTop = $('#log').scrollHeight;

  recolocar();
}

// --------------------------------------------------------------------------
// burbuja de respuesta: la puerta abierta, o la caja libre de la entrevista
// --------------------------------------------------------------------------
// Las dos son lo mismo desde aquí: algo que el orquestador espera de ti y que no
// avanza hasta que lo mandas. Quién decide si vale sigue siendo el núcleo.
function pintarResponder(s, ancla, agente) {
  const el = $('#burbuja-responder');
  const def = PUERTAS[s.estado];
  const pide = def || (s.espera_respuesta && !s.vivo);
  if (!pide) {
    if (!el.classList.contains('genio')) { el.hidden = true; el.dataset.marca = ''; }
    return;
  }
  // Sale del nodo que espera: el de la puerta, o el del subagente que ha dejado
  // la pregunta a medias.
  const nodo = def ? ancla : (agente || ancla);
  el.dataset.ancla = nodo;
  // El sondeo cae cada 1,5 s y el genio dura 0,6: sin esto, la burbuja que
  // acabas de enviar reaparece a medio encoger.
  if (el.classList.contains('genio')) return;
  const marca = `${s.estado}|${s.espera_respuesta}|${nodo}`;
  if (el.dataset.marca === marca) return;
  el.dataset.marca = marca;
  $('#responder-titulo').textContent = def ? def.titulo : 'Responder al orquestador';
  const chip = $('#responder-chip');
  chip.hidden = !def;
  chip.textContent = s.estado;
  $('#responder-cuerpo').innerHTML = def ? cuerpoPuerta(def) : cuerpoLibre();
  el.hidden = false;
  el.classList.remove('brota', 'genio');
  void el.offsetWidth;            // reinicia la animación de entrada
  el.classList.add('brota');
}

function cuerpoPuerta(def) {
  const botones = def.botones
    .map((b) => `<button class="btn ${b === def.botones[0] ? 'primario' : ''}" data-puerta="${esc(b)}">${esc(b)}</button>`)
    .join('');
  const libre = def.libre
    ? `<div class="puerta-libre"><span>${esc(def.libre.prefijo)}</span><input id="puerta-arg" placeholder="${esc(def.libre.marca)}"></div>
       <button class="btn" data-puerta-libre="${esc(def.libre.prefijo)}">enviar</button>`
    : '';
  return `<p>${esc(def.texto)}</p>
    <div class="puerta-ops">${botones}${libre}</div>
    <p class="nota">Nada avanza hasta que respondas.</p>`;
}

function cuerpoLibre() {
  return `<textarea id="in-mensaje" rows="3" placeholder="p. ej. 1A 2B 3B 4A 5A 6C — o «todas recomendadas»"></textarea>
    <div class="puerta-ops"><button class="btn primario" id="btn-responder">Enviar y lanzar</button></div>
    <p class="nota">Va literal al principio de la siguiente invocación. Es el canal de la entrevista de partida, que no es una puerta del núcleo.</p>`;
}

$('#burbuja-responder').addEventListener('click', async (e) => {
  const el = $('#burbuja-responder');
  const destino = el.dataset.ancla || 'ESCRIBIENDO';

  if (e.target.closest('#btn-responder')) {
    const mensaje = $('#in-mensaje').value;
    genio(el, destino);
    return lanzar(mensaje);
  }

  const simple = e.target.closest('[data-puerta]');
  const conArg = e.target.closest('[data-puerta-libre]');
  if (!simple && !conArg) return;
  let respuesta = simple ? simple.dataset.puerta : '';
  if (conArg) {
    const arg = $('#puerta-arg').value.trim();
    if (!arg) return brindis('Escribe la instrucción antes de enviar.', true);
    respuesta = `${conArg.dataset.puertaLibre} ${arg}`;
  }
  try {
    const res = await post(`/api/runs/${estado.slug}/puerta`, { respuesta });
    genio(el, destino);
    brindis(res.salida);
    // Responder la puerta ES el permiso del autor para seguir. `editar` y
    // `parar` dejan la puerta abierta, y `autoContinuar` no relanza en un GATE_.
    estado.seguir = true;
    await refrescarProgreso();
    cargarRuns();
  } catch (err) {
    brindis(err.message, true);
  }
});

// --------------------------------------------------------------------------
// burbuja de intentos: sale del nodo que los produce y no se va nunca
// --------------------------------------------------------------------------
// `estado.json` borra los intentos al cerrar capítulo (§9.4), así que el
// histórico viene del servidor leyendo los `-eval.json` de `.intentos/`.
const NODOS_CICLO = ['ESCRIBIENDO', 'EVALUANDO', 'PARCHEANDO', 'ACEPTANDO'];

function pintarIntentos(s, ancla) {
  const el = $('#burbuja-intentos');
  const historial = s.historial || [];
  el.hidden = !historial.length && !s.paso;
  $('#grafo-zona').classList.toggle('con-intentos', !el.hidden);
  if (el.hidden) { recolocar(); return; }
  // Cuelga del nodo del ciclo que esté activo; fuera del ciclo, de EVALUANDO.
  el.dataset.ancla = NODOS_CICLO.includes(ancla) ? ancla : 'EVALUANDO';

  const bloq = s.criterios_bloqueantes || [];
  $('#regla-92').textContent =
    `media ≥ ${s.umbral} · ${bloq.join(' y ') || 'criterios'} ≥ ${s.umbral_bloqueante}`
    + ` · máx. ${s.max_reescrituras} reescrituras · la continuidad la decide el núcleo`;

  const porCapitulo = new Map();
  for (const a of historial) {
    if (!porCapitulo.has(a.capitulo)) porCapitulo.set(a.capitulo, []);
    porCapitulo.get(a.capitulo).push(a);
  }
  // El intento en vuelo todavía no tiene `-eval.json`, así que no está en el
  // histórico: si es el primero del capítulo, el capítulo tampoco.
  if (s.paso && s.capitulo_actual <= s.total && !porCapitulo.has(s.capitulo_actual)) {
    porCapitulo.set(s.capitulo_actual, []);
  }

  const capitulos = [...porCapitulo.keys()].sort((a, b) => b - a);
  $('#tabla-intentos').innerHTML = capitulos.map((n) => {
    const enCurso = n === s.capitulo_actual;
    const filas = porCapitulo.get(n).map((a) => filaIntento(a, s, enCurso)).join('');
    const vivo = enCurso && s.paso
      ? `<div class="fila ahora"><span>i${s.iteracion}</span><span class="mono">${esc(String(n).padStart(2, '0'))}-i${s.iteracion}.md</span><span>—</span><span class="vivo">${esc(s.paso)}…</span></div>`
      : '';
    const sello = s.capitulos_aceptados.includes(n) ? '<span class="sello ok">aceptado</span>'
      : enCurso ? '<span class="sello vivo">en curso</span>' : '';
    return `<div class="cap-intentos ${enCurso ? 'ahora' : ''}">
      <div class="cap-intentos-head"><b>Capítulo ${String(n).padStart(2, '0')}</b>${sello}</div>
      ${filas}${vivo}</div>`;
  }).join('') || '<p class="vacio-msg">Sin intentos todavía.</p>';
  recolocar();
}

function filaIntento(a, s, enCurso) {
  const notas = a.puntuaciones || {};
  const flojo = (s.criterios_bloqueantes || []).filter((c) => (notas[c] ?? 0) < s.umbral_bloqueante);
  const pasa = a.media >= s.umbral && !flojo.length;
  const motivo = pasa ? 'llega al umbral'
    : a.media < s.umbral ? 'media por debajo'
    : `${flojo.join(' y ')} por debajo`;
  // El motivo va en el `title`: en una columna se cortaba a «llega al umb…»,
  // que no informa de nada.
  return `<div class="fila ${enCurso && a.iteracion === s.iteracion ? 'ahora' : ''}" title="${esc(motivo)}">
    <span>i${a.iteracion}</span>
    <span class="mono">${esc(a.ruta)}</span>
    <span class="${pasa ? 'bien' : 'mal'}">${a.media == null ? '—' : a.media.toFixed(2)}</span>
    <span class="${pasa ? 'bien' : 'mal'}">${pasa ? 'APROBADO' : 'CORREGIR'}</span>
  </div>`;
}

// Un lanzamiento es una invocación de `claude -p /novela`: hace una fase y
// termina. El encadenado lo lleva el panel, no el orquestador (§7.5: encadenar
// dentro de una invocación revienta su contexto).
async function lanzar(mensaje = '') {
  const previo = estado.snap ? firma(estado.snap) : '';
  try {
    const info = await post(`/api/runs/${estado.slug}/lanzar`, { mensaje });
    estado.firmaLanzada = previo;
    estado.detenido = false;
    estado.seguir = true;
    brindis(`Orquestador en marcha (pid ${info.pid}).`);
    refrescarProgreso();
  } catch (err) { brindis(err.message, true); }
}

$('#btn-lanzar-run').addEventListener('click', () => {
  // Si la burbuja libre está abierta, lanzar equivale a enviarla: se va al nodo
  // igual que si hubieras pulsado su propio botón.
  const caja = $('#in-mensaje');
  const el = $('#burbuja-responder');
  const mensaje = caja ? caja.value : '';
  if (caja && !el.hidden) genio(el, el.dataset.ancla || 'ESCRIBIENDO');
  lanzar(mensaje);
});

$('#btn-parar').addEventListener('click', async () => {
  try {
    await post(`/api/runs/${estado.slug}/parar`);
    estado.detenido = true;
    estado.seguir = false;
    brindis('Orquestador detenido. El estado en disco queda donde estaba.');
    refrescarProgreso();
  } catch (err) { brindis(err.message, true); }
});

$('#btn-siguiente').addEventListener('click', async () => {
  try {
    const res = await post(`/api/runs/${estado.slug}/siguiente`);
    brindis(res.salida);
    refrescarProgreso();
  } catch (err) { brindis(err.message, true); }
});

// --------------------------------------------------------------------------
// vista: lector
// --------------------------------------------------------------------------
async function cargarCapitulos() {
  if (!estado.slug) return;
  const datos = await api(`/api/runs/${estado.slug}/capitulos`);
  estado.capitulos = datos.capitulos;
  pintarIndice();
  if (!estado.libro) {
    estado.libro = await crearLibro($('#lienzo3d'), {
      alElegir: abrirCapitulo,
      traerTexto: (n) => api(`/api/runs/${estado.slug}/capitulos/${n}`),
    });
  }
  estado.libro.setCapitulos(estado.capitulos);
  const primero = estado.capitulo ?? (estado.capitulos.find((c) => c.escrito) || {}).numero;
  if (primero) abrirCapitulo(primero);
}

function pintarIndice() {
  $('#lista-capitulos').innerHTML = estado.capitulos.map((c) => {
    const punto = !c.escrito ? '' : c.deuda ? 'deuda' : 'ok';
    const color = punto === 'ok' ? 'var(--ok)' : punto === 'deuda' ? 'var(--warn)' : 'transparent';
    const meta = c.escrito
      ? `<span class="punto" style="background:${color}"></span>${c.media != null ? c.media.toFixed(2) : '—'} · ${c.escenas} escenas · ${c.palabras} pal.${c.deuda ? ' · deuda' : ''}`
      : 'en la escaleta, sin escribir';
    return `<div class="cap ${c.numero === estado.capitulo ? 'sel' : ''} ${c.escrito ? '' : 'pendiente'}" data-n="${c.numero}">
      <div class="cap-head"><em>${String(c.numero).padStart(2, '0')}</em><b>${esc(c.titulo || 'sin título')}</b></div>
      <div class="cap-meta">${meta}</div>
    </div>`;
  }).join('');

  const conDeuda = estado.capitulos.filter((c) => c.deuda);
  $('#indice-pie').innerHTML = `<span class="lbl">Deuda narrativa</span><p>${
    conDeuda.length
      ? `Capítulo${conDeuda.length > 1 ? 's' : ''} ${conDeuda.map((c) => c.numero).join(', ')} aceptado${conDeuda.length > 1 ? 's' : ''} por debajo del umbral. Nada se reescribe hacia atrás.`
      : 'Ninguna. Todos los capítulos aceptados llegaron al umbral.'
  }</p>`;
}

$('#lista-capitulos').addEventListener('click', (e) => {
  const fila = e.target.closest('.cap:not(.pendiente)');
  if (fila) abrirCapitulo(Number(fila.dataset.n));
});

async function abrirCapitulo(n) {
  const meta = estado.capitulos.find((c) => c.numero === n);
  if (!meta || !meta.escrito) return;
  estado.capitulo = n;
  fijarHash();
  pintarIndice();
  estado.libro?.irA(n);
  $('#visor-pos').textContent = `${n} / ${estado.capitulos.length}`;

  const cap = await api(`/api/runs/${estado.slug}/capitulos/${n}`);
  const f = cap.ficha;
  const campos = [
    ['Focalizador', f.focalizador],
    ['Día de ficción', f.dia],
    ['Presentes', f.presentes],
    ['Acto', cap.acto],
    ['Media del Evaluador', f.media != null ? f.media.toFixed(2) : '—'],
    ['Escenas', cap.escenas.length],
    ['Palabras', cap.palabras],
    ['Deuda', meta.deuda ? 'sí' : 'no'],
  ].filter(([, v]) => v !== '' && v != null)
    .map(([k, v]) => `<div class="dato"><dt>${k}</dt><dd>${esc(String(v))}</dd></div>`).join('');

  const bloque = (rotulo, texto) => (texto
    ? `<div class="ficha-bloque"><div class="escena-rot"><span>${rotulo}</span><i></i></div><p>${esc(texto)}</p></div>`
    : '');

  $('#ficha').innerHTML = `<div class="ficha-head">
      <span class="lbl">Ficha del capítulo</span>
      <h1>${esc(cap.titulo)}</h1>
    </div>
    <div class="ficha-cuerpo">
      <dl class="datos">${campos}</dl>
      ${bloque('RESUMEN', f.resumen)}
      ${bloque('GANCHO FINAL', f.gancho)}
    </div>`;
  $('#ficha').scrollTop = 0;
}

$('#hoja-prev').addEventListener('click', () => estado.libro?.anterior());
$('#hoja-next').addEventListener('click', () => estado.libro?.siguiente());

document.addEventListener('keydown', (e) => {
  if (estado.vista !== 'lector') return;
  if (e.target.matches('input, textarea, select')) return;
  if (e.key === 'ArrowLeft') estado.libro?.anterior();
  if (e.key === 'ArrowRight') estado.libro?.siguiente();
});

// --------------------------------------------------------------------------
function pintarTopMeta() {
  const r = estado.runs.find((x) => x.slug === estado.slug);
  const s = estado.snap;
  if (!r) { $('#topmeta').textContent = ''; return; }
  const cuota = s?.cuota ? `cuota <b>${s.cuota.llamadas_hoy}</b>/${s.cuota.limite_diario}` : '';
  $('#topmeta').innerHTML = `<span>${esc(r.ruta)}</span><span>perfil <b>${esc(r.perfil)}</b></span><span>${cuota}</span>`;
}

cargarRuns()
  .then(() => {
    const [pedida, capitulo] = location.hash.slice(1).split('/');
    if (!VISTAS.includes(pedida)) return;
    if (capitulo && Number(capitulo)) estado.capitulo = Number(capitulo);
    if (pedida !== estado.vista) irAVista(pedida);
  })
  .catch((err) => brindis(err.message, true));

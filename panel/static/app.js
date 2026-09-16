// Panel del harness de novela. Une las tres vistas con la API del servidor.
// Nada de lógica del núcleo vive aquí: los veredictos, las medias y las
// transiciones llegan ya calculados desde `python -m harness`.

import { crearLibro } from './book3d.js';

// Los estados por los que pasa una ejecución normal, en orden de lectura.
// Los literales salen de harness/state.py; ERROR y ENTREVISTA no se emiten.
const BANDA = [
  'INIT', 'GENERANDO_BIBLIA', 'GATE_PLAN', 'ESCRIBIENDO', 'EVALUANDO',
  'PARCHEANDO', 'ACEPTANDO', 'EDITANDO_ACTO', 'GATE_ACTO',
  'AUDITORIA_FINAL', 'GATE_FINAL', 'COMPLETADO',
];
const FUERA_DE_BANDA = { REVISANDO_ESCALETA: 'GATE_ACTO', GATE_BLOQUEO: 'EVALUANDO', CUOTA_PAUSADA: 'ESCRIBIENDO' };

const AGENTES = [
  ['arquitecto', 'Arquitecto'], ['escritor', 'Escritor'], ['evaluador', 'Evaluador'],
  ['continuista', 'Continuista'], ['editor-acto', 'Editor de acto'],
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
const hora = (ts) => new Date(ts * 1000).toLocaleTimeString('es-ES', { hour12: false });

const estado = {
  vista: 'lanzar',
  slug: null,
  runs: [],
  perfiles: [],
  claude: false,
  snap: null,
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
  document.querySelectorAll('.run').forEach((n) => n.classList.toggle('sel', n === tarjeta));
  pintarTopMeta();
  irAVista('progreso');
});

$('#in-slug').addEventListener('blur', (e) => {
  if (e.target.value) e.target.value = e.target.value.trim().toLowerCase();
});

async function crear(lanzar) {
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
    if (lanzar) {
      const info = await post(`/api/runs/${res.slug}/lanzar`);
      brindis(`Orquestador en marcha (pid ${info.pid}). El progreso va apareciendo abajo.`);
      irAVista('progreso');
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
// vista: progreso
// --------------------------------------------------------------------------
async function refrescarProgreso() {
  if (!estado.slug) return;
  try {
    estado.snap = await api(`/api/runs/${estado.slug}/estado`);
  } catch (err) {
    brindis(err.message, true);
    clearInterval(estado.timer);
    return;
  }
  pintarProgreso(estado.snap);
  pintarTopMeta();
}

function pintarProgreso(s) {
  const rotulo = (s.titulo || s.slug).length > 70 ? `${(s.titulo || s.slug).slice(0, 70)}…` : (s.titulo || s.slug);
  $('#prog-contexto').textContent =
    `${rotulo} · capítulo ${Math.min(s.capitulo_actual, s.total)} de ${s.total} · iteración ${s.iteracion} · acto ${s.acto_actual}`;
  $('#btn-parar').hidden = !s.vivo;
  $('#btn-lanzar-run').disabled = s.vivo || !estado.claude;
  $('#btn-lanzar-run').textContent = s.vivo ? 'Orquestador en marcha' : 'Lanzar agentes';

  // banda de estados
  const actual = s.estado;
  const ancla = FUERA_DE_BANDA[actual] || actual;
  const corte = BANDA.indexOf(ancla);
  $('#banda-estados').innerHTML = BANDA.map((nombre, i) => {
    const esAhora = nombre === actual || (FUERA_DE_BANDA[actual] && nombre === ancla);
    const cls = esAhora ? 'ahora' : i < corte ? 'hecho' : '';
    const enlace = i ? `<span class="lk ${i <= corte ? 'hecho' : ''}"></span>` : '';
    const rotulo = esAhora && FUERA_DE_BANDA[actual] ? actual : nombre;
    return `${enlace}<span class="est ${cls}">${esc(rotulo)}</span>`;
  }).join('');

  // agentes
  const enCurso = s.agente_en_curso || (s.vivo ? PASO_AGENTE[s.paso] : '') || '';
  $('#agentes').innerHTML = AGENTES.map(([clave, nombre]) => {
    const activo = clave === enCurso;
    const sub = activo ? 'en curso' : s.vivo ? 'en reposo' : '—';
    return `<div class="agente ${activo ? 'activo' : ''}">
      <div class="agente-head"><b>${nombre}</b><span class="punto ${activo ? 'on' : ''}"></span></div>
      <small>${esc(sub)}</small>
    </div>`;
  }).join('');

  pintarPuerta(s);

  // intentos
  $('#regla-92').textContent =
    `umbral ${s.umbral} · tensión y escaleta ≥ ${Math.ceil(s.umbral)} · máx. ${s.max_reescrituras} reescrituras`;
  const filas = s.intentos.map((a) => {
    const bien = a.media >= s.umbral;
    return `<div class="fila ${a.iteracion === s.iteracion ? 'ahora' : ''}">
      <span>i${a.iteracion}</span>
      <span>${esc((a.ruta || '').split(/[\\/]/).pop())}</span>
      <span class="${bien ? 'bien' : 'mal'}">${a.media.toFixed(2)}</span>
      <span>${bien ? 'llega al umbral' : 'por debajo'}</span>
      <span class="${bien ? 'bien' : 'mal'}">${bien ? 'APROBADO' : 'CORREGIR'}</span>
    </div>`;
  }).join('');
  const enMarcha = s.paso && s.capitulo_actual <= s.total
    ? `<div class="fila ahora"><span>i${s.iteracion}</span><span>${esc(String(s.capitulo_actual).padStart(2, '0'))}-i${s.iteracion}.md</span><span>—</span><span>—</span><span class="vivo">${esc(s.paso)}…</span></div>`
    : '';
  $('#tabla-intentos').innerHTML =
    `<div class="fila cab"><span>iter</span><span>archivo</span><span>media</span><span>regla 9.2</span><span>veredicto</span></div>`
    + (filas + enMarcha || '<p class="vacio-msg">Sin intentos registrados para este capítulo.</p>');

  // cuota
  const q = s.cuota || {};
  const usadas = q.llamadas_hoy ?? 0;
  const tope = q.limite_diario || 1;
  $('#cuota-cifra').textContent = `${usadas} / ${tope}`;
  $('#cuota-barra').style.width = `${Math.min(100, (usadas / tope) * 100)}%`;

  // log
  $('#log-fuente').textContent = s.eventos.length ? `${s.eventos.length} · cada 1,5 s` : 'sin stream todavía';
  $('#log').innerHTML = s.eventos.length
    ? s.eventos.map((e) => `<div class="ev ${esc(e.tipo)}"><em>${e.tipo === 'agente' ? '▸' : '·'}</em><span>${esc(e.texto)}</span></div>`).join('')
    : '<div class="ev"><span>El stream aparece cuando lanzas el orquestador desde aquí. Si lo arrancas a mano en Claude Code, el progreso se sigue viendo por el estado y los archivos de trabajo.</span></div>';
  $('#log').scrollTop = $('#log').scrollHeight;

  // pistas
  $('#pistas').innerHTML = (s.pistas || []).map((p) => {
    const est = (p.estado || '').toUpperCase();
    const cls = est === 'RESUELTA' || est === 'DESACTIVADA' ? 'ok' : est === 'RED_HERRING' ? 'aviso' : '';
    return `<span class="pista ${cls}" title="${esc(p.descripcion)}">${esc(p.id)} ${esc(est.toLowerCase())}</span>`;
  }).join('') || '<span class="faint">El ledger se siembra al aprobar el plan.</span>';

  // archivos de trabajo
  $('#archivos').innerHTML = (s.archivos || []).slice(0, 8)
    .map((a) => `<div><em>${hora(a.ts)}</em><b>${esc(a.nombre)}</b></div>`).join('')
    || '<div><b>—</b></div>';
}

function pintarPuerta(s) {
  const def = PUERTAS[s.estado];
  const zona = $('#puerta-wrap');
  if (!def) { zona.innerHTML = ''; return; }
  const botones = def.botones.map((b) => `<button class="btn ${b === def.botones[0] ? 'primario' : ''}" data-puerta="${esc(b)}">${esc(b)}</button>`).join('');
  const libre = def.libre
    ? `<div class="puerta-libre"><span>${esc(def.libre.prefijo)}</span><input id="puerta-arg" placeholder="${esc(def.libre.marca)}"></div>
       <button class="btn" data-puerta-libre="${esc(def.libre.prefijo)}">enviar</button>`
    : '';
  zona.innerHTML = `<div class="puerta">
    <div class="puerta-head">
      <b>${esc(def.titulo)}</b>
      <span class="chip puerta">${esc(s.estado)}</span>
      <div class="grow"></div>
      <span class="faint">nada avanza hasta que respondas</span>
    </div>
    <p>${esc(def.texto)}</p>
    <div class="puerta-ops">${botones}${libre}</div>
  </div>`;
}

$('#puerta-wrap').addEventListener('click', async (e) => {
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
    brindis(res.salida);
    refrescarProgreso();
    cargarRuns();
  } catch (err) {
    brindis(err.message, true);
  }
});

$('#btn-lanzar-run').addEventListener('click', async () => {
  try {
    const info = await post(`/api/runs/${estado.slug}/lanzar`);
    brindis(`Orquestador en marcha (pid ${info.pid}).`);
    refrescarProgreso();
  } catch (err) { brindis(err.message, true); }
});

$('#btn-parar').addEventListener('click', async () => {
  try {
    await post(`/api/runs/${estado.slug}/parar`);
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
  const meta2 = [f.focalizador, f.dia ? `día de ficción ${f.dia}` : '', `acto ${cap.acto}`, `${cap.palabras} palabras`]
    .filter(Boolean).map((t) => `<span>${esc(t)}</span>`).join('');
  const escenas = cap.escenas.map((s) => `<div class="escena">
    <div class="escena-rot"><span>ESCENA ${s.n}</span><i></i></div>
    ${s.texto.split(/\n{2,}/).map((p) => `<p>${esc(p.trim())}</p>`).join('')}
  </div>`).join('');
  $('#prosa').innerHTML = `<div class="prosa-head">
      <h1>${esc(cap.titulo)}</h1>
      <div class="prosa-meta">${meta2}</div>
    </div>
    <div class="prosa-cuerpo">${escenas}
      <div class="escena-rot"><span>FIN</span><i></i></div>
    </div>`;
  $('#prosa').scrollTop = 0;
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

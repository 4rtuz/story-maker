// Presupuestos de tamaño del build (spec 0004, RNF-01, RNF-02 y RNF-20). 1 KB = 1 000 bytes (D52).
//
//   node scripts/presupuesto.mjs [dist] [--lectura=exigida|opcional]
//
// La carga inicial son los módulos y los modulepreload que enlaza index.html (VER-15); el chunk de
// Lectura, todo el JS de dist/assets que index.html no carga, porque la única importación diferida
// del panel es la de Lectura. Se exige desde que existe la escena (T-14): antes mide 0 (PD5), y
// después su ausencia es un fallo, no un 0 silencioso (VER-14).
import fs from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';

const LIMITES = { inicial: 100_000, lectura: 300_000, woff2: 60_000, css: 20_000, imagenes: 80_000 };

const argumentos = process.argv.slice(2);
const dist = path.resolve(argumentos.find((a) => !a.startsWith('--')) ?? 'dist');
const escena = path.join(import.meta.dirname, '..', 'src', 'features', 'lectura', 'escena.ts');
const modo = argumentos.find((a) => a.startsWith('--lectura='))?.split('=')[1];
const exigirLectura = modo ? modo === 'exigida' : fs.existsSync(escena);

const leer = (relativa) => fs.readFileSync(path.join(dist, relativa));
const gzip = (relativas) => relativas.reduce((n, r) => n + gzipSync(leer(r)).length, 0);
const bruto = (relativas) => relativas.reduce((n, r) => n + leer(r).length, 0);

const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
const enlazados = [...html.matchAll(/<(?:script[^>]*\ssrc|link[^>]*rel="modulepreload"[^>]*\shref)="\/?([^"]+\.js)"/g)].map(
  (m) => m[1],
);
const assets = fs.readdirSync(path.join(dist, 'assets')).map((f) => `assets/${f}`);
const js = assets.filter((f) => f.endsWith('.js'));
const diferidos = js.filter((f) => !enlazados.includes(f));
const imagenes = [...assets.filter((f) => /^assets\/logo-[\w-]+\.png$/.test(f)), 'favicon.png'].filter((f) =>
  fs.existsSync(path.join(dist, f)),
);

const medidas = {
  inicial: gzip(enlazados),
  lectura: gzip(diferidos),
  woff2: bruto(assets.filter((f) => f.endsWith('.woff2'))),
  css: gzip(assets.filter((f) => f.endsWith('.css'))),
  imagenes: bruto(imagenes),
};
const nombres = {
  inicial: 'JS inicial (gzip)',
  lectura: 'chunk de Lectura (gzip)',
  woff2: 'fuentes WOFF2',
  css: 'CSS (gzip)',
  imagenes: 'imágenes de marca (logo y favicon)',
};

const fallos = Object.entries(medidas)
  .filter(([clave, bytes]) => bytes > LIMITES[clave])
  .map(([clave, bytes]) => `${nombres[clave]}: ${bytes} bytes, más de ${LIMITES[clave]}`);
if (exigirLectura && diferidos.length === 0) {
  fallos.push('no hay chunk de Lectura: la escena existe y su import() no ha dejado ningún chunk diferido');
}

for (const [clave, bytes] of Object.entries(medidas)) {
  console.log(`${nombres[clave].padEnd(36)} ${String(bytes).padStart(8)} / ${LIMITES[clave]}`);
}
if (fallos.length) {
  console.error(`\npresupuesto excedido:\n  ${fallos.join('\n  ')}`);
  process.exit(1);
}

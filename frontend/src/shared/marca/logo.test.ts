// @vitest-environment node
// CA-52 y CA-61: el logo oficial, sin retocar, y el favicon derivado de él. Los PNG de fixture se
// generan en el directorio temporal del sistema, nunca bajo frontend/ (VAL-33). El logo real solo
// se lee.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';
import { afterAll, describe, expect, it } from 'vitest';
import { comprobarPng, FAVICON, LOGO } from './logo';

const FRONTEND = path.resolve(import.meta.dirname, '../../..');
const leer = (ruta: string): Uint8Array | undefined =>
  fs.existsSync(ruta) ? fs.readFileSync(ruta) : undefined;

/** Firma e IHDR de un PNG de `lado` × `lado`, con relleno hasta `bytes`. Basta para la cabecera. */
function png(lado: number, bytes = 0): Buffer {
  const ihdr = Buffer.alloc(25);
  ihdr.writeUInt32BE(13, 0);
  ihdr.write('IHDR', 4, 'latin1');
  ihdr.writeUInt32BE(lado, 8);
  ihdr.writeUInt32BE(lado, 12);
  ihdr.set([8, 6, 0, 0, 0], 16);
  const firma = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const cabecera = Buffer.concat([firma, ihdr]);
  return Buffer.concat([cabecera, Buffer.alloc(Math.max(0, bytes - cabecera.length))]);
}

/** Canal alfa de un PNG RGBA de 8 bits sin entrelazar, deshaciendo los filtros de cada fila. */
function alfas(datos: Buffer): { lado: number; alfa: (x: number, y: number) => number } {
  let posicion = 8;
  let lado = 0;
  let tipo = 0;
  const idat: Buffer[] = [];
  while (posicion < datos.length) {
    const largo = datos.readUInt32BE(posicion);
    const nombre = datos.toString('latin1', posicion + 4, posicion + 8);
    const cuerpo = datos.subarray(posicion + 8, posicion + 8 + largo);
    if (nombre === 'IHDR') [lado, tipo] = [cuerpo.readUInt32BE(0), cuerpo[9] ?? 0];
    if (nombre === 'IDAT') idat.push(cuerpo);
    posicion += 12 + largo;
  }
  expect(tipo, 'RGBA de 8 bits').toBe(6);
  const crudo = zlib.inflateSync(Buffer.concat(idat));
  const fila = lado * 4;
  const pixeles = Buffer.alloc(lado * fila);
  for (let y = 0; y < lado; y++) {
    const filtro = crudo[y * (fila + 1)] ?? 0;
    for (let i = 0; i < fila; i++) {
      const x = crudo[y * (fila + 1) + 1 + i] ?? 0;
      const a = i >= 4 ? (pixeles[y * fila + i - 4] ?? 0) : 0;
      const b = y > 0 ? (pixeles[(y - 1) * fila + i] ?? 0) : 0;
      const c = y > 0 && i >= 4 ? (pixeles[(y - 1) * fila + i - 4] ?? 0) : 0;
      const p = a + b - c;
      const [pa, pb, pc] = [Math.abs(p - a), Math.abs(p - b), Math.abs(p - c)];
      const paeth = pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
      const prediccion = [0, a, b, (a + b) >> 1, paeth][filtro] ?? 0;
      pixeles[y * fila + i] = (x + prediccion) & 255;
    }
  }
  return { lado, alfa: (x, y) => pixeles[y * fila + x * 4 + 3] ?? -1 };
}

describe('comprobación del logo (CA-52)', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'logo-'));
  afterAll(() => fs.rmSync(tmp, { recursive: true, force: true }));
  fs.writeFileSync(path.join(tmp, 'no-png.png'), 'esto no es un PNG');
  fs.writeFileSync(path.join(tmp, '200.png'), png(200));
  fs.writeFileSync(path.join(tmp, '90kb.png'), png(400, 90_000));

  it.each([
    ['no-png.png', 'no es un PNG'],
    ['200.png', 'mide 200 × 200 px'],
    ['90kb.png', 'pesa 90000 bytes'],
    ['ausente.png', 'falta el fichero'],
  ])('%s falla: %s', (fichero, motivo) => {
    expect(comprobarPng(leer(path.join(tmp, fichero)), LOGO)).toContain(motivo);
  });

  it('el logo real pasa: firma PNG, 400 × 400 px y como mucho 80 000 bytes', () => {
    expect(comprobarPng(leer(path.join(import.meta.dirname, 'logo.png')), LOGO)).toBeNull();
  });
});

describe('favicon (CA-61)', () => {
  const ruta = path.join(FRONTEND, 'public', 'favicon.png');

  it('es un PNG de 64 × 64 px con las esquinas transparentes y el centro opaco', () => {
    const datos = leer(ruta);
    expect(comprobarPng(datos, FAVICON)).toBeNull();
    const { lado, alfa } = alfas(Buffer.from(datos ?? []));
    expect(lado).toBe(64);
    for (const [x, y] of [[0, 0], [63, 0], [0, 63], [63, 63]] as const) expect(alfa(x, y)).toBe(0);
    expect(alfa(32, 32)).toBe(255);
  });

  it('index.html lo enlaza', () => {
    const html = fs.readFileSync(path.join(FRONTEND, 'index.html'), 'utf8');
    expect(html).toContain('<link rel="icon" type="image/png" href="/favicon.png">');
  });
});

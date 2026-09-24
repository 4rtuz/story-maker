// El logo oficial de Qaracter (D23). Este es el único módulo que importa logo.png —eslint lo hace
// cumplir— y siempre lo mete en su contenedor redondeado: así ningún uso queda sin redondear.
import url from './logo.png';

/** El nombre de la marca, como texto alternativo y junto al logo. */
export const MARCA = 'Qaracter';

/** Lo que exige CI al PNG aportado y al favicon derivado (CA-52, CA-61). 1 KB = 1 000 bytes (D52). */
export const LOGO = { lado: 400, maxBytes: 80_000 } as const;
export const FAVICON = { lado: 64, maxBytes: 80_000 } as const;

const FIRMA = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];

/** El motivo por el que `bytes` no sirve, o null. Solo lee la cabecera: sin node:fs (VER-21). */
export function comprobarPng(
  bytes: Uint8Array | undefined,
  { lado, maxBytes }: { lado: number; maxBytes: number },
): string | null {
  if (!bytes) return 'falta el fichero';
  if (bytes.length < 24 || FIRMA.some((b, i) => bytes[i] !== b)) return 'no es un PNG';
  const vista = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const [ancho, alto] = [vista.getUint32(16), vista.getUint32(20)];
  if (ancho !== lado || alto !== lado) return `mide ${ancho} × ${alto} px, no ${lado} × ${lado}`;
  if (bytes.length > maxBytes) return `pesa ${bytes.length} bytes, más de ${maxBytes}`;
  return null;
}

/** El logo en su contenedor redondeado; con `conNombre`, «Qaracter» al lado, oculto a los lectores
 * de pantalla porque el `alt` ya lo dice. */
export function crearLogo({ conNombre = true } = {}): HTMLElement {
  const logo = document.createElement('span');
  logo.className = 'q-logo';
  const marco = document.createElement('span');
  marco.className = 'q-logo__marco';
  const imagen = document.createElement('img');
  imagen.src = url;
  imagen.alt = MARCA;
  imagen.width = 40;
  imagen.height = 40;
  imagen.decoding = 'async';
  marco.append(imagen);
  logo.append(marco);
  if (conNombre) {
    const nombre = document.createElement('span');
    nombre.className = 'q-logo__nombre';
    nombre.textContent = MARCA;
    nombre.setAttribute('aria-hidden', 'true');
    logo.append(nombre);
  }
  return logo;
}

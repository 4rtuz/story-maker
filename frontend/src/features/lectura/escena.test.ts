// CA-31, CA-30, CA-55 y RNF-03 en su parte unitaria, y CA-29 con el contexto perdido: la escena
// con una fábrica de renderer falsa, sin WebGL real. Lo que se libera se comprueba recorriendo la
// escena, no con una lista propia de la escena (VER-22).
import fs from 'node:fs';
import path from 'node:path';
import * as THREE from 'three';
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import { arrancar } from '../../app/rutas';
import { el } from '../../shared/ui/componentes';
import { hex, lectorDeCss } from '../../shared/marca/lector-de-tokens';
import { disposicion } from './disposicion';
import { crearEscena, DURACION_CAMARA, type Renderer } from './escena';
import { estadosDeVolumen } from './estados';
import { lectura } from './vista';
import { ESCALETA, servirLectura } from './servir-lectura.test-util';

const TOKENS = fs.readFileSync(path.join(import.meta.dirname, '../../shared/marca/tokens.css'), 'utf8');

function rendererFalso(): Renderer & { dispose: Mock<() => void>; forceContextLoss: Mock<() => void> } {
  const info = { render: { calls: 0 } };
  return {
    domElement: document.createElement('canvas'),
    info,
    setSize: vi.fn(),
    setPixelRatio: vi.fn(),
    render: vi.fn((escena: THREE.Scene) => {
      let dibujables = 0;
      escena.traverse((o) => void ((o as THREE.Mesh).isMesh && dibujables++));
      info.render.calls = dibujables;
    }),
    dispose: vi.fn<() => void>(),
    forceContextLoss: vi.fn<() => void>(),
  };
}

function montarEscena(total = 24, opciones: { reducir?: boolean; css?: string } = {}) {
  const contenedor = el('div');
  document.body.replaceChildren(contenedor);
  const renderer = rendererFalso();
  const escena = crearEscena({
    contenedor,
    lector: lectorDeCss(opciones.css ?? TOKENS),
    crearRenderer: () => renderer,
    reducirMovimiento: () => opciones.reducir ?? false,
    alSeleccionar: () => {},
    alAbrir: () => {},
    alFallar: () => {},
  });
  if (!escena) throw new Error('sin escena');
  const estados = estadosDeVolumen(total, { capitulo: 7 }, [8]);
  escena.actualizar(estados, disposicion(total, total === 24 ? ESCALETA.actos : null), 3);
  return { contenedor, renderer, escena };
}

const dibujables = (escena: THREE.Scene) => {
  const mallas: THREE.Mesh[] = [];
  escena.traverse((o) => void ((o as THREE.Mesh).isMesh && mallas.push(o as THREE.Mesh)));
  return mallas;
};

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('escena', () => {
  it('expone volúmenes, selección y draw calls en el contenedor', async () => {
    const { contenedor } = montarEscena();
    await vi.advanceTimersByTimeAsync(20);
    expect(contenedor.dataset.volumenes).toBe('24');
    expect(contenedor.dataset.seleccion).toBe('3');
    expect(Number(contenedor.dataset.drawCalls)).toBeGreaterThan(0);
    expect(contenedor.querySelector('canvas')).not.toBeNull();
  });

  it('como mucho 5 objetos dibujables con 24 y con 999 volúmenes (RNF-03)', () => {
    for (const total of [24, 999]) {
      const { escena } = montarEscena(total);
      expect(dibujables(escena.escena).length).toBeLessThanOrEqual(5);
      const volumenes = dibujables(escena.escena).find((m) => (m as THREE.InstancedMesh).isInstancedMesh) as THREE.InstancedMesh;
      expect(volumenes.count).toBe(total);
      escena.liberar();
    }
  });

  it('libera cada geometría, material y el renderer, y retira el canvas (CA-31, VER-22)', () => {
    const { contenedor, renderer, escena } = montarEscena();
    const liberados: ReturnType<typeof vi.spyOn>[] = [];
    for (const malla of dibujables(escena.escena)) {
      liberados.push(vi.spyOn(malla.geometry, 'dispose'));
      for (const m of [malla.material].flat()) liberados.push(vi.spyOn(m, 'dispose'));
    }
    expect(liberados.length).toBeGreaterThanOrEqual(6);
    escena.liberar();
    for (const espia of liberados) expect(espia).toHaveBeenCalled();
    expect(renderer.dispose).toHaveBeenCalled();
    // dispose() no suelta el contexto: sin esto, tras unas entradas se agotan (VAL-20).
    expect(renderer.forceContextLoss).toHaveBeenCalled();
    expect(contenedor.querySelector('canvas')).toBeNull();
  });

  it('con webglcontextlost se retira y avisa (CA-29, parte unitaria)', () => {
    const contenedor = el('div');
    const renderer = rendererFalso();
    const alFallar = vi.fn();
    const escena = crearEscena({
      contenedor,
      lector: lectorDeCss(TOKENS),
      crearRenderer: () => renderer,
      reducirMovimiento: () => false,
      alSeleccionar: () => {},
      alAbrir: () => {},
      alFallar,
    });
    renderer.domElement.dispatchEvent(new Event('webglcontextlost'));
    expect(alFallar).toHaveBeenCalled();
    expect(renderer.dispose).toHaveBeenCalled();
    expect(contenedor.querySelector('canvas')).toBeNull();
    expect(escena).not.toBeNull();
  });

  it('sin WebGL no crea nada y devuelve null', () => {
    const contenedor = el('div');
    const escena = crearEscena({
      contenedor,
      lector: lectorDeCss(TOKENS),
      crearRenderer: () => null,
      reducirMovimiento: () => false,
      alSeleccionar: () => {},
      alAbrir: () => {},
      alFallar: () => {},
    });
    expect(escena).toBeNull();
    expect(contenedor.querySelector('canvas')).toBeNull();
  });

  it('colores de cada estado, del contorno, del suelo y del fondo desde sus roles (CA-55)', () => {
    const leer = lectorDeCss(TOKENS);
    const { escena } = montarEscena();
    const volumenes = dibujables(escena.escena).find((m) => (m as THREE.InstancedMesh).isInstancedMesh) as THREE.InstancedMesh;
    const color = new THREE.Color();
    const de = (i: number) => {
      volumenes.getColorAt(i, color);
      return `#${color.getHexString()}`;
    };
    expect(de(0)).toBe(hex(leer('--q-primario')));
    expect(de(7)).toBe(hex(leer('--q-icono-cian')));
    expect(de(8)).toBe(hex(leer('--q-pendiente')));
    const contorno = escena.escena.getObjectByName('contorno') as THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial>;
    expect(`#${contorno.material.color.getHexString()}`).toBe(hex(leer('--q-deco-seleccion')));
    const suelo = escena.escena.getObjectByName('suelo') as THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>;
    expect(`#${suelo.material.color.getHexString()}`).toBe(hex(leer('--q-secundario-fondo')));
    expect(`#${(escena.escena.background as THREE.Color).getHexString()}`).toBe(hex(leer('--q-fondo-pagina')));
  });

  it('un --q-primario nuevo llega a los volúmenes cerrados sin tocar nada más (CA-55)', () => {
    const css = TOKENS.replace(/--q-primario:[^;]+;/, '--q-primario: #123456;');
    const { escena } = montarEscena(24, { css });
    const volumenes = dibujables(escena.escena).find((m) => (m as THREE.InstancedMesh).isInstancedMesh) as THREE.InstancedMesh;
    const color = new THREE.Color();
    volumenes.getColorAt(0, color);
    expect(`#${color.getHexString()}`).toBe('#123456');
  });

  it('la cámara va al seleccionado en 400 ms, o en el fotograma siguiente con reduced motion (CA-30)', async () => {
    const x = disposicion(24, ESCALETA.actos);
    const normal = montarEscena();
    normal.escena.seleccionar(4);
    expect(normal.escena.transicion).toBe(DURACION_CAMARA);
    await vi.advanceTimersByTimeAsync(20);
    expect(normal.escena.objetivo().x).not.toBeCloseTo(x[3]!);
    await vi.advanceTimersByTimeAsync(DURACION_CAMARA + 20);
    expect(normal.escena.objetivo().x).toBeCloseTo(x[3]!);
    normal.escena.liberar();

    const reducida = montarEscena(24, { reducir: true });
    reducida.escena.seleccionar(4);
    expect(reducida.escena.transicion).toBe(0);
    await vi.advanceTimersByTimeAsync(17);
    expect(reducida.escena.objetivo().x).toBeCloseTo(x[3]!);
    expect(reducida.contenedor.dataset.seleccion).toBe('4');
    expect(reducida.contenedor.dataset.transicion).toBe('0');
    expect(reducida.contenedor.dataset.camara).toBe('4');
  });
});

describe('escena en la vista (CA-31)', () => {
  it('al navegar a Progreso, el renderer se libera y no queda ningún canvas', async () => {
    servirLectura();
    const renderer = rendererFalso();
    const raiz = el('div');
    document.body.replaceChildren(raiz);
    location.hash = '#/novelas/demo-24/lectura';
    const { detener } = arrancar(raiz, (ruta, navegar) =>
      ruta.vista === 'lectura'
        ? lectura(ruta, navegar, { crearRenderer: () => renderer })
        : { titulo: 'otra', nodo: el('div'), recursos: [] },
    );
    await vi.advanceTimersByTimeAsync(50);
    expect(raiz.querySelector('.q-escena canvas')).not.toBeNull();
    expect(raiz.querySelector('.q-escena')?.getAttribute('data-volumenes')).toBe('24');
    location.hash = '#/novelas/demo-24/progreso';
    window.dispatchEvent(new HashChangeEvent('hashchange'));
    expect(renderer.dispose).toHaveBeenCalled();
    expect(document.querySelector('canvas')).toBeNull();
    detener();
  });

  it('sin WebGL, «vista 3D no disponible» y la lista sigue (CA-29, parte unitaria)', async () => {
    servirLectura();
    const raiz = el('div');
    document.body.replaceChildren(raiz);
    location.hash = '#/novelas/demo-24/lectura';
    const { detener } = arrancar(raiz, (ruta, navegar) => lectura(ruta as { vista: 'lectura'; slug: string }, navegar));
    await vi.advanceTimersByTimeAsync(50);
    expect(raiz.textContent).toContain('vista 3D no disponible');
    expect(raiz.querySelector('canvas')).toBeNull();
    expect(raiz.querySelectorAll('.q-volumenes [data-capitulo]')).toHaveLength(24);
    detener();
  });
});

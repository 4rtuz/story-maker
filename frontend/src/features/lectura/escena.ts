// La estantería de Lectura (RF-24, RF-29 a RF-31, RF-55; spec §8.4, D9, D11, D12). Un único
// InstancedMesh con un volumen por capítulo, una malla de contorno para la selección y un suelo:
// tres objetos dibujables con 24 o con 999 capítulos (RNF-03). Se dibuja a demanda, no en bucle:
// al cambiar los datos, la selección o el tamaño, y durante la transición de la cámara.
import * as THREE from 'three';
import type { LectorDeTokens } from '../../shared/marca/lector-de-tokens';
import { hex } from '../../shared/marca/lector-de-tokens';
import type { EstadoDeVolumen } from './estados';

export const DURACION_CAMARA = 400;

/** Lo que la escena usa del renderer; la fábrica falsa de los tests implementa solo esto. */
export interface Renderer {
  domElement: HTMLCanvasElement;
  info: { render: { calls: number } };
  setSize(ancho: number, alto: number, estilo?: boolean): void;
  setPixelRatio(proporcion: number): void;
  render(escena: THREE.Scene, camara: THREE.Camera): void;
  dispose(): void;
  forceContextLoss(): void;
}

export type FabricaDeRenderer = (canvas: HTMLCanvasElement) => Renderer | null;

/** WebGL 2 o nada. Se comprueba antes de llamar a Three.js, que escribe un console.error cuando no
 * consigue el contexto (VAL-19). */
export const rendererWebGL: FabricaDeRenderer = (canvas) => {
  if (typeof WebGL2RenderingContext === 'undefined') return null;
  const context = canvas.getContext('webgl2', { antialias: true });
  if (!context) return null;
  try {
    return new THREE.WebGLRenderer({ canvas, context, antialias: true });
  } catch {
    return null;
  }
};

export interface OpcionesDeEscena {
  contenedor: HTMLElement;
  lector: LectorDeTokens;
  crearRenderer: FabricaDeRenderer;
  reducirMovimiento: () => boolean;
  alSeleccionar(n: number): void;
  alAbrir(n: number): void;
  /** Sin contexto WebGL a mitad de sesión: la escena ya se ha retirado. */
  alFallar(): void;
}

export interface Escena {
  escena: THREE.Scene;
  /** Duración de la última transición de cámara, en ms; también en data-transicion, y el volumen al
   * que apunta la cámara al terminarla, en data-camara, para los e2e (CA-30). */
  readonly transicion: number;
  objetivo(): THREE.Vector3;
  actualizar(estados: EstadoDeVolumen[], xs: number[], seleccion: number): void;
  seleccionar(n: number): void;
  liberar(): void;
}

const ANCHO = 0.9;
const FONDO = 1.3;
const altura = (n: number): number => 1.5 + ((n * 37) % 5) * 0.1;
const suavizar = (t: number): number => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

const ROL_DE_ESTADO: Record<EstadoDeVolumen, string> = {
  cerrado: '--q-primario',
  en_curso: '--q-icono-cian',
  pendiente: '--q-pendiente',
};

export function crearEscena(opciones: OpcionesDeEscena): Escena | null {
  const { contenedor, lector } = opciones;
  const creado = opciones.crearRenderer(document.createElement('canvas'));
  if (!creado) return null;
  const renderer: Renderer = creado;
  const color = (rol: string): THREE.Color => new THREE.Color(hex(lector(rol)));

  const escena = new THREE.Scene();
  escena.background = color('--q-fondo-pagina');
  const camara = new THREE.PerspectiveCamera(42, 16 / 10, 0.1, 400);
  escena.add(new THREE.HemisphereLight(color('--q-fondo-tarjeta'), color('--q-secundario-fondo'), 2.2));
  const sol = new THREE.DirectionalLight(color('--q-fondo-tarjeta'), 1.6);
  sol.position.set(-4, 10, 8);
  escena.add(sol);

  const caja = new THREE.BoxGeometry(ANCHO, 1, FONDO);
  caja.translate(0, 0.5, 0); // la base en el suelo: la altura se da con la escala
  const materialVolumen = new THREE.MeshStandardMaterial({ roughness: 0.65, metalness: 0 });
  let volumenes = new THREE.InstancedMesh(caja, materialVolumen, 0);

  const materialContorno = new THREE.MeshBasicMaterial({ color: color('--q-deco-seleccion'), side: THREE.BackSide });
  const contorno = new THREE.Mesh(caja, materialContorno);
  contorno.name = 'contorno';
  const geometriaSuelo = new THREE.PlaneGeometry(1, 1);
  const suelo = new THREE.Mesh(geometriaSuelo, new THREE.MeshStandardMaterial({ color: color('--q-secundario-fondo'), roughness: 1 }));
  suelo.name = 'suelo';
  suelo.rotation.x = -Math.PI / 2;
  escena.add(volumenes, contorno, suelo);

  let xs: number[] = [];
  let seleccion = 1;
  let transicion = 0;
  const mirada = new THREE.Vector3();
  let animacion: { desde: number; hasta: number; inicio: number | null; duracion: number } | null = null;
  let fotograma: number | null = null;
  let liberada = false;

  const canvas = renderer.domElement;
  canvas.setAttribute('aria-hidden', 'true'); // la lista HTML es la alternativa accesible
  contenedor.append(canvas);

  function colocarCamara(x: number): void {
    mirada.set(x, 0.9, 0);
    camara.position.set(x, 7.5, 10.5);
    camara.lookAt(mirada);
  }

  function dibujar(ahora: number): void {
    fotograma = null;
    if (liberada) return;
    if (animacion) {
      animacion.inicio ??= ahora;
      const t = animacion.duracion ? Math.min(1, (ahora - animacion.inicio) / animacion.duracion) : 1;
      colocarCamara(animacion.desde + (animacion.hasta - animacion.desde) * suavizar(t));
      if (t >= 1) {
        animacion = null;
        contenedor.dataset.camara = String(seleccion);
      }
    }
    renderer.render(escena, camara);
    contenedor.dataset.drawCalls = String(renderer.info.render.calls);
    if (animacion) pedirFotograma();
  }

  function pedirFotograma(): void {
    fotograma ??= requestAnimationFrame(dibujar);
  }

  function ajustarTamano(): void {
    const ancho = contenedor.clientWidth || 640;
    const alto = contenedor.clientHeight || 420;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(ancho, alto, false);
    camara.aspect = ancho / alto;
    camara.updateProjectionMatrix();
    pedirFotograma();
  }
  const observador = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(ajustarTamano);
  observador?.observe(contenedor);
  ajustarTamano();

  function colocarContorno(): void {
    const x = xs[seleccion - 1];
    contorno.visible = x !== undefined;
    if (x === undefined) return;
    contorno.position.set(x, -0.04, 0);
    contorno.scale.set(1.12, altura(seleccion) + 0.08, 1.08);
  }

  function volumenBajo(evento: MouseEvent): number | null {
    const marco = canvas.getBoundingClientRect();
    if (!marco.width || !marco.height) return null;
    const puntero = new THREE.Vector2(
      ((evento.clientX - marco.left) / marco.width) * 2 - 1,
      -((evento.clientY - marco.top) / marco.height) * 2 + 1,
    );
    const rayo = new THREE.Raycaster();
    rayo.setFromCamera(puntero, camara);
    const [impacto] = rayo.intersectObject(volumenes);
    return impacto?.instanceId === undefined ? null : impacto.instanceId + 1;
  }

  const alPulsar = (evento: MouseEvent): void => {
    const n = volumenBajo(evento);
    if (n === null) return;
    opciones.alSeleccionar(n);
    opciones.alAbrir(n);
  };
  const alMover = (evento: MouseEvent): void => {
    canvas.style.cursor = volumenBajo(evento) === null ? '' : 'pointer';
  };
  const alPerder = (evento: Event): void => {
    evento.preventDefault();
    api.liberar();
    opciones.alFallar();
  };
  canvas.addEventListener('click', alPulsar);
  canvas.addEventListener('pointermove', alMover);
  canvas.addEventListener('webglcontextlost', alPerder);

  const api: Escena = {
    escena,
    get transicion() {
      return transicion;
    },
    objetivo: () => mirada.clone(),

    actualizar(estados, nuevasXs, nuevaSeleccion) {
      if (volumenes.count !== estados.length) {
        escena.remove(volumenes);
        volumenes.dispose(); // los atributos de instancia; la geometría y el material se reutilizan
        volumenes = new THREE.InstancedMesh(caja, materialVolumen, estados.length);
        escena.add(volumenes);
      }
      const matriz = new THREE.Matrix4();
      estados.forEach((estado, i) => {
        matriz.makeScale(1, altura(i + 1), 1).setPosition(nuevasXs[i] ?? 0, 0, 0);
        volumenes.setMatrixAt(i, matriz);
        volumenes.setColorAt(i, color(ROL_DE_ESTADO[estado]));
      });
      volumenes.instanceMatrix.needsUpdate = true;
      if (volumenes.instanceColor) volumenes.instanceColor.needsUpdate = true;
      volumenes.computeBoundingSphere();
      const ultimo = nuevasXs.at(-1) ?? 0;
      suelo.scale.set(ultimo + 40, 40, 1);
      suelo.position.set(ultimo / 2, 0, 0);
      const primeraVez = xs.length === 0;
      xs = nuevasXs;
      contenedor.dataset.volumenes = String(estados.length);
      if (primeraVez || nuevaSeleccion !== seleccion) {
        seleccion = nuevaSeleccion;
        contenedor.dataset.seleccion = String(seleccion);
        if (primeraVez) {
          colocarCamara(xs[seleccion - 1] ?? 0);
          contenedor.dataset.camara = String(seleccion);
        }
        else api.seleccionar(seleccion);
      }
      colocarContorno();
      pedirFotograma();
    },

    seleccionar(n) {
      seleccion = n;
      contenedor.dataset.seleccion = String(n);
      colocarContorno();
      transicion = opciones.reducirMovimiento() ? 0 : DURACION_CAMARA;
      contenedor.dataset.transicion = String(transicion);
      animacion = { desde: mirada.x, hasta: xs[n - 1] ?? mirada.x, inicio: null, duracion: transicion };
      pedirFotograma();
    },

    liberar() {
      if (liberada) return;
      liberada = true;
      if (fotograma !== null) cancelAnimationFrame(fotograma);
      observador?.disconnect();
      canvas.removeEventListener('click', alPulsar);
      canvas.removeEventListener('pointermove', alMover);
      canvas.removeEventListener('webglcontextlost', alPerder);
      escena.traverse((objeto) => {
        const malla = objeto as THREE.Mesh;
        if (!malla.isMesh) return;
        malla.geometry.dispose();
        for (const material of [malla.material].flat()) material.dispose();
        if ((malla as THREE.InstancedMesh).isInstancedMesh) (malla as THREE.InstancedMesh).dispose();
      });
      renderer.dispose();
      renderer.forceContextLoss(); // dispose() no suelta el contexto WebGL (VAL-20)
      canvas.remove();
      delete contenedor.dataset.drawCalls;
    },
  };
  return api;
}

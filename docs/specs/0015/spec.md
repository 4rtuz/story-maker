---
spec: 0015
titulo: "Panel editorial: portadas, lanzamiento conversacional, proceso de creación y métricas de Langfuse"
estado: aceptada
autor: "4rtuzz"
fecha: 2026-09-25
version: 0.1
afecta: [backend, frontend, esquemas, docs]
depende_de: ["0004"]
sustituye: []
adr: []
commit: null
---

# 0015 — Panel editorial: portadas, lanzamiento conversacional, proceso de creación y métricas de Langfuse

## 1. Propósito y alcance

El panel deja de parecer una consola de operador y pasa a parecer un producto editorial: cada novela
tiene portada, se lanza conversando y su progreso se cuenta en lenguaje de lector, con métricas de
coste y tiempo sacadas de Langfuse.

**Dentro del alcance**

- `novela portada <slug>`: una ilustración generada con un servicio abierto y guardada en el workspace.
- `novela costes <slug> --guardar`: el informe de costes de Langfuse guardado en el workspace.
- `novela producir` genera la portada tras `/novela-nueva` y guarda las métricas tras cada capítulo
  y tras la auditoría, sin parar la novela si fallan.
- `GET /novelas/{slug}/portada` y `GET /novelas/{slug}/metricas`, de solo lectura.
- Inicio con portadas, Lanzar como chat con tablero de lanzamientos por fases, Progreso con
  «Proceso de creación» y métricas, Lectura con portada y sin estantería 3D.

**Fuera del alcance**

- Elegir o regenerar la portada desde el panel: la API sigue sin escribir.
- Leer Langfuse desde la API: la API solo lee disco.
- Cambiar el bucle de agentes o sus prompts.

## 2. Problema

El inicio lista todas las novelas del directorio, evaluaciones y humo incluidos, como filas de texto.
Lanzar es un formulario de doce campos. Progreso enseña runs, hilos y el log de las sesiones: son
herramientas de depuración, no de seguimiento. Las métricas de coste solo existen en
`docs/evaluacion/costes-*.md`, generadas a mano con `novela costes --markdown`.

## 3. Actores

| Actor | Interés |
|---|---|
| Operador | Lanzar una novela sin conocer sus parámetros internos y seguirla sin leer logs |
| Lector | Abrir la novela por su portada y navegarla por el índice |
| API | Seguir siendo de solo lectura (AGENTS.md § Monorepo) |

## 4. Contexto y restricciones

- **Invariantes**: la API no escribe (§ Monorepo); el CLI es el único que toca `novelas/<slug>/`;
  escritura atómica (6); el frontend no lee disco.
- **Privacidad**: el prompt de la portada no lleva `idea_semilla`, ni personajes, ni nada del brief:
  solo el subgénero y la descripción de los escenarios del canon. Una novela de regalo puede llevar
  datos personales en la idea y en los personajes.
- **Red**: el CLI accedía a la red solo para Langfuse; ahora también para la portada.
- **Marca**: colores solo en `tokens.css` y contraste AA declarado en `pares.ts` (architecture.md §11).

## 5. Propuesta

### 5.1 Portada

`novela portada <slug> [--forzar]` compone un prompt en inglés con el subgénero y los escenarios
del canon, pide la imagen a Pollinations.ai
(`https://image.pollinations.ai/prompt/<prompt>?width=768&height=1152&seed=<crc32(slug) & 0x7FFFFFFF>&nologo=true`;
Pollinations rechaza con 500 una semilla de más de 31 bits)
y la escribe atómicamente en `novelas/<slug>/portada.jpg`. Sin `--forzar`, si ya existe, no hace
nada. Comprueba que la respuesta sea un JPEG (`FF D8 FF`) antes de escribir. El prompt pide
explícitamente una ilustración sin texto: el título lo pone el panel encima. Sin cuenta,
Pollinations añade su marca de agua en la esquina inferior derecha pese a `nologo=true`; el velo del
título la cubre en parte.

### 5.2 Métricas

`novela costes <slug> --guardar` escribe `novelas/<slug>/metricas.json` con el informe de
`costes.agregar` y la hora de generación, validado por `InformeDeCostes`
(`backend/novela/dominio/metricas.py`):

```
Consumo:        llamadas, tokens_entrada, tokens_salida, tokens_cache_lectura, coste_usd,
                latencia_media_llamada_s
ConsumoDePaso:  Consumo + paso, latencia_s, roles: {rol: Consumo}
TotalDeCostes:  Consumo + latencia_s
InformeDeCostes: slug, sesion, generado (datetime), pasos: [ConsumoDePaso], total: TotalDeCostes
```

`paso` es `nueva`, `capitulo NN`, `auditoria` o `sesión <id>`, como hoy.

### 5.3 Producir

Tras `/novela-nueva` con éxito, `producir` genera la portada; tras cada capítulo que avanza el
checkpoint y tras la auditoría, guarda las métricas. Un fallo de cualquiera de los dos queda en el
registro del lanzamiento y la novela sigue.

### 5.4 API

- `GET /novelas/{slug}/portada` → `image/jpeg`; 404 si no hay portada.
- `GET /novelas/{slug}/metricas` → `InformeDeCostes`; 404 si no hay métricas.
- `GET /novelas/{slug}/pdf` → el libro de regalo de la spec 0006 con los capítulos cerrados, como
  adjunto `application/pdf`, construido en memoria (D8); 404 sin capítulos cerrados.

### 5.5 Panel

- **Inicio**: rejilla de portadas con título, estado y barra de progreso. Oculta `eval-*`, `humo-*`
  y `regalo-carmen`. Sin portada, una cubierta tipográfica con los colores de la marca.
- **Lanzar**: un chat pregunta si es un regalo (y, si lo es, nombre, edad, rasgos y recuerdos), la
  idea, el género, el tono, los capítulos, las palabras totales y el nombre corto (slug, con una
  sugerencia). No pregunta la extensión. Debajo, los lanzamientos en un tablero con cuatro
  columnas: En proceso, En pausa (detenida), Bloqueada (fallida o interrumpida) y Terminada. Sin
  registro de sesiones ni pasos internos. Sin tarjeta de slugs.
- **Progreso**: portada y cifras (capítulos, palabras, coste, tiempo), «Proceso de creación»
  (barra y últimos hitos, con carga animada en el hito en curso y una marca animada al terminar),
  métricas de Langfuse por novela y por capítulo, y la tensión. Sin hilos, runs ni actividad. El
  lanzamiento sale de `GET /lanzamientos` y no de `/lanzamientos/{slug}`, que da 404 (y un error en la
  consola) para una novela que no se lanzó desde el panel.
- **Lectura**: portada arriba con la imagen, el título, la dedicatoria, «Empezar a leer» y, a su
  lado, «Descargar PDF»; debajo, índice y personajes y lugares. Sin estantería 3D ni lista de
  capítulos; el lector se abre desde los enlaces.
- **Lector**: un libro abierto sobre papel con textura visible (ruido SVG en dos escalas). El
  capítulo 1 empieza por la portada: la ilustración en la página izquierda y título y dedicatoria en
  la derecha. El fondo se elige entre papel, sepia y noche, y la letra va de 14 a 26 px; las dos
  preferencias duran la sesión sin guardarse en el navegador (D9).

## 6. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | `novela portada` escribe `portada.jpg` solo si la respuesta es un JPEG; si no, sale con 1 y no escribe | debe |
| RF-02 | El prompt de la portada no contiene `idea_semilla`, nombres de personaje ni nada de `brief/` | debe |
| RF-03 | Sin `--forzar`, `novela portada` no pide nada si `portada.jpg` existe | debe |
| RF-04 | `novela costes --guardar` escribe `metricas.json` válido contra `InformeDeCostes` | debe |
| RF-05 | `producir` genera la portada tras `/novela-nueva` y guarda métricas tras cada capítulo y la auditoría; sus fallos no cambian el resultado de `producir` | debe |
| RF-06 | `GET …/portada` sirve el JPEG con `image/jpeg`, y 404 sin portada | debe |
| RF-07 | `GET …/metricas` sirve `InformeDeCostes`, y 404 sin métricas | debe |
| RF-08 | El inicio no muestra `eval-*`, `humo-*` ni `regalo-carmen` | debe |
| RF-09 | Lanzar no pide la extensión y sí capítulos y palabras totales | debe |
| RF-10 | El tablero reparte cada lanzamiento en una columna según su estado y no muestra el registro | debe |
| RF-11 | «Proceso de creación» calcula hitos y porcentaje a partir de escaleta, checkpoint, cursor y lanzamiento | debe |
| RF-12 | Lectura no carga Three.js | debe |
| RF-13 | `GET …/pdf` sirve el PDF de los capítulos cerrados como adjunto sin escribir, y 404 sin ninguno | debe |
| RF-14 | El capítulo 1 del lector empieza por la portada con la ilustración, el título y la dedicatoria | debe |
| RF-15 | El lector cambia de fondo (papel, sepia, noche) y de tamaño de letra (14 a 26 px), y los conserva al cambiar de capítulo | debe |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito |
|---|---|---|
| RNF-01 | Coste | Ninguna llamada a modelo nueva; la portada no usa la suscripción de Claude |
| RNF-02 | Fiabilidad | Sin red, la novela se produce igual, sin portada y sin métricas |
| RNF-03 | Accesibilidad | Las animaciones respetan `prefers-reduced-motion`; el chat es un `role="log"` |

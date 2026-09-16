# CLAUDE.md

Harness multiagente que escribe una novela de suspense doméstico psicológico en español,
capítulo a capítulo, con cinco roles LLM y control humano en tres puertas.

Spec = fuente de verdad. **Canónico: `docs/harness-novela-suspense.md` (español).**
`docs/suspense-novel-harness.md` es la misma spec traducida — se lee, no se implementa (crea
un árbol de directorios paralelo si lo sigues). Guía de operador: `docs/SETUP.md`.

## Arquitectura: núcleo / binding

| Capa | Dónde | Regla |
|---|---|---|
| **Núcleo** (§1-17, determinista) | `harness/` | No menciona jamás Claude Code, OpenRouter ni un identificador de modelo. |
| **Contrato de puertos** (Anexo B) | P1 invocar · P2 artefactos · P3 estado · P4 humano · P5 git · P6 cuota | Cambiar de runtime = escribir un anexo nuevo, no reescribir el núcleo. |
| **Binding** (Anexo A) | `.claude/` | Implementa **solo P1 y P4**. No reimplementa lógica del núcleo. |
| **Panel web** (Anexo C) | `panel/` | Binding secundario. Implementa P4, lee P2/P3, y **delega P1** lanzando el binding de Claude Code como subproceso. No orquesta. |
| **Artefactos** | `novela/` | Los `.md` de §6 + `estado.json` (única fuente de verdad del run). |

Romper ese reparto en cualquier dirección es el error caro del proyecto.

## Cómo se ejecuta

```bash
python -m harness init            # crea novela/ y estado.json
python -m harness next            # SIEMPRE lo primero: devuelve "ACCION: <x>"
python tests/dry_run.py           # 40 comprobaciones offline, sin gastar cuota
```

Desde Claude Code: `/novela`. **Una invocación escribe un capítulo y para** (§7.5) — el
contexto del orquestador no aguanta encadenar capítulos y no hace falta: el estado está en
disco. Sin dependencias externas; solo stdlib de Python 3.12.

El panel se arranca con `python -m panel` (`docs/anexo-c-panel-web.md`): lanza una novela, muestra el progreso y lee los capítulos.

Órdenes del CLI (`harness/cli.py`, las que invoca la skill): `init status next prompt
save-attempt record decide patch-plan accept save-report save-bible seed-clues audit
validate-bible gate commit`.

## Reglas de trabajo

- **Todo parámetro numérico vive en `novela/config.json`**, no en el código ni en la spec.
  Si el documento y el archivo discrepan, gana el archivo y el documento tiene una errata.
  Perfiles con fusión profunda sobre `base`; el perfil activo hoy es `poc` (3 capítulos de
  ~60 palabras, umbral 3.0) — el POC no es código aparte.
- **Los identificadores de modelo solo en `.claude/settings.local.json`** (no versionado).
  `config.json` declara *clases* (alta / equilibrada / rápida). Congelar identificadores en
  el núcleo rompe §4.5.
- **Los cinco subagentes van sin herramientas** (`tools: []`). Es la palanca principal de
  cuota: sin herramientas, una llamada lógica = 1 petición; con `Read`/`Write`, 3-6. A
  cambio, todo el contexto viaja en el prompt, que **construye el núcleo** (`harness prompt
  <rol>`), nunca el orquestador a mano, y se pasa entero y sin resumir.
- **Los system prompts de `.claude/agents/*.md` son literales de §5.** Los ajustes por perfil
  van en el prompt de invocación, jamás editando el system prompt (Anexo B.2 punto 2).
- **Presupuesto del Escritor: 16k tokens de entrada, en el capítulo 3 y en el 30.** Recorte
  por orden: cronología → fichas viejas → texto íntegro de N-2.
- **Solo el Continuista escribe en `novela/estado/`**, y solo tras aceptar un capítulo. Esa
  separación —quien escribe ficción no mantiene los hechos— es lo que evita la deriva.
- **Pasos deterministas que no se delegan a un subagente**: ensamblado de contexto,
  aplicación de deltas, regeneración del resumen rodante y auditoría final.
- **La aceptación la calcula el núcleo** (`harness decide`, §9.2: media ≥ umbral ∧ tensión ≥ 4
  ∧ escaleta ≥ 4 ∧ continuidad OK). No te fíes del veredicto que declare el modelo.
- **Solo se escribe hacia delante.** Nada reescribe capítulos ya aceptados; lo que aparece
  después se anota en `estado/deuda-narrativa.md`. Tras 2 reescrituras se acepta el mejor
  intento *por media*, no el último, y se sigue.
- **Los parches se verifican por hash** (§9.5): las escenas no marcadas que el modelo tocara
  se restauran. Es lo que evita la regresión silenciosa del bucle de reescritura.
- Un commit por capítulo aceptado: `feat(novela): capítulo NN — <título>`. `.intentos/` no
  entra en el historial.

## Estado del repo

POC en curso: `biblia/` generada, `estado.json` en `INIT`. El riesgo abierto de §2 sigue
abierto — "Claude Code + OpenRouter + modelos `:free`" no es una combinación soportada; el
smoke test de fase F0 (`docs/SETUP.md` §3) decide en diez minutos si funciona. Fuera de v1:
agente lector-de-prueba, editor de estilo final, generación escena a escena, EPUB.

## Carga de contexto de la spec

`docs/suspense-novel-harness.md` (1.899 líneas) **no se carga entero, nunca**. Está troceada en
`docs/context/`:

1. Lee siempre `docs/context/index.md` primero.
2. Carga solo los ficheros cuya columna "Load when…" coincida con la tarea en curso. La tabla
   "Common task → files" del índice ya resuelve los casos habituales.
3. Ante una contradicción o un hueco, consulta `conflicts.md` y `open-questions.md` antes de
   decidir nada por tu cuenta: ninguno de los dos está resuelto y resolverlos no te toca a ti.
4. Es una traducción: la spec canónica sigue siendo `docs/harness-novela-suspense.md` y el árbol
   real es `novela/`, no `novel/` (ver `conflicts.md` C-07).

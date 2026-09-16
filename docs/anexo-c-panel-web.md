# Anexo C — Binding de panel web

> Este anexo existe porque la regla de `CLAUDE.md` lo exige: **cambiar o añadir un runtime es
> escribir un anexo nuevo, no reescribir el núcleo**. Implementación: `panel/`.
> Contrato que cumple: Anexo B (`docs/context/port-contract.md`).

## C.0 Qué es y qué no es

El panel es un **binding secundario**, no un sustituto del de Claude Code (Anexo A). Sirve tres
cosas sobre `http://127.0.0.1:8000`: lanzar una novela, ver el progreso de la orquestación y leer
los capítulos.

No orquesta nada. Cuando hay que escribir un capítulo, **arranca el binding de Claude Code como
subproceso** (`claude -p "/novela"`) y observa su salida. Las decisiones —qué toca ahora, si un
capítulo se acepta, qué media gana— siguen saliendo de `python -m harness`, igual que antes.

`harness/` no tiene ni una línea nueva. El comprobante es `python tests/dry_run.py`: 40 de 40.

## C.1 Los seis puertos

| Puerto | Cómo lo resuelve el panel |
|---|---|
| **P1 invocar** | **Delegado.** No habla con ningún modelo. Lanza `claude -p "/novela" --output-format stream-json`, que es el Anexo A entero, y hace *tee* de su stdout. Un puerto, un sitio (B.2 punto 1): quien invoca sigue siendo la skill. |
| **P2 artefactos** | **Solo lectura.** `panel/runs.py` lee los `.md` de §6 a través de `harness.config.Config` y `harness.scenes.Chapter`, nunca con rutas propias. No escribe ningún artefacto salvo dos: `.intentos/idea.md` al crear una ejecución y `.intentos/panel-run.jsonl` (ver C.3). Los esquemas de §6 quedan intactos byte a byte (B.2 punto 3). |
| **P3 estado** | **Solo lectura directa; escritura siempre por el CLI.** El sondeo hace `json.loads` de `estado.json` y nada más. Toda mutación pasa por `python -m harness ... `, que conserva la escritura atómica de `State.save()`. |
| **P4 humano** | **Implementado.** `POST /api/runs/<slug>/puerta` traslada la respuesta **literal** del autor a `harness gate --answer "<respuesta>"`. El panel no interpreta ni normaliza la respuesta, y no responde por el autor. Nada avanza sin respuesta, que es lo único que el núcleo exige (B.1). |
| **P5 versión** | **Delegado.** `harness commit` lo sigue ejecutando el orquestador. El panel no toca git. |
| **P6 cuota** | **Solo muestra.** El contador vive en `estado.json` y lo lleva `State.record_usage`. El panel lo pinta y avisa de que va corto (ver C.3, última fila). |

## C.2 Varias ejecuciones

Una ejecución nueva vive en `runs/<slug>/` y se recorre con el flag `--root` que el núcleo ya
traía. `novela/` es la ejecución de la raíz y el panel **nunca** la recrea ni la sobrescribe.

El alta copia `novela/config.json` al nuevo root antes de llamar a `init` —`Config.load` se ejecuta
al arrancar el CLI y sin ese archivo falla—, que es el mismo orden que usa `tests/dry_run.py`.

**Punto débil conocido.** Las órdenes literales de `.claude/skills/novela/SKILL.md` no llevan
`--root`. Para una ejecución fuera de la raíz, el panel añade al prompt de arranque una línea que
se lo dice al orquestador. Funciona —está comprobado—, pero es encaminamiento por prompt y depende
de que el orquestador lo respete. Si alguna vez falla, la solución es una skill que acepte `--root`,
no tocar el núcleo.

## C.3 Progreso: qué es viejo y qué es nuevo

Antes de esto **no existía ningún mecanismo de progreso**: ni logs, ni eventos, ni timestamps más
allá de `cuota.ts_ultima_llamada`. El panel lo compone de tres capas, y solo la tercera es nueva:

| Capa | ¿Existía? | Qué da | Límite |
|---|---|---|---|
| `estado.json` | Sí | Estado, capítulo, iteración, puerta pendiente, `intentos[]` con sus medias, cuota | Instantáneo, sin historia. Va retrasado: sigue diciendo `ESCRIBIENDO` mientras corre el Evaluador |
| `.intentos/` + mtimes | Sí, implícito | El subpaso (`escribir`/`evaluar`/`verificar`/`decidir`) y **cuándo** se lanzó cada subagente | Es la misma señal que usa `cmd_next`, pero aquí solo se muestra: el sondeo **no** ejecuta `next`, que tiene efectos laterales |
| `.intentos/panel-run.jsonl` | **No. Propuesta nueva** | Qué está haciendo un agente **ahora mismo** | Solo existe si lanzaste el orquestador desde el panel. Arrancado a mano en Claude Code, quedan las dos capas anteriores |

El transporte al navegador es **sondeo cada 1,5 s** contra un endpoint sin efectos. No hay SSE: por
debajo el mecanismo real es leer disco, y un stream no compraría nada que el sondeo no dé.

El formato de `claude --output-format stream-json` **no es un contrato**. `runs._flatten` se queda
con lo que reconoce y descarta el resto; una línea con otra forma no rompe la vista. Las formas
observadas y de las que depende la vista son dos: `system/task_started`, que trae `subagent_type`
(es de donde sale «qué agente corre ahora», no del bloque `tool_use` de `Task`), y
`system/permission_denied`, que trae `tool_name`.

## C.4 Tabla de peticiones (B.2 punto 4)

El panel **no añade ni una petición al modelo**: es Python local sirviendo HTTP en `127.0.0.1`. Los
factores de §13.3 se mantienen íntegros, porque debajo corre el mismo Anexo A.

Lo que sí añade es el sobrecoste de arrancar en frío. Medido en un lanzamiento real sobre
`runs/smoke-panel`, fase de planificación, hasta presentar la entrevista:

| Concepto | Peticiones | Nota |
|---|--:|---|
| Turnos del orquestador | 20 | Incluye descubrir el árbol de la ejecución nueva |
| Subagentes lanzados | 1 | Arquitecto, entrevista |
| **Total de la invocación** | **21** | Contra ~12 que estima §13.3 para una fase equivalente |

Dos causas del exceso, las dos evitables:

1. **Dos denegaciones de permiso.** El allowlist cubre `python -m harness`, pero el orquestador
   probó órdenes compuestas que exigen aprobación. Se recupera solo, a costa de dos turnos.
2. **Descubrimiento del `--root`.** Una ejecución en `runs/` obliga al orquestador a orientarse.
   En la ejecución de la raíz ese coste no está.

En régimen, dentro del ciclo de un capítulo, no hay diferencia con §13.3: **factor 2,5**.

Aviso que ya estaba en la skill y sigue valiendo: `cuota.llamadas_hoy` cuenta **llamadas lógicas**,
no peticiones, y solo las incrementa una orden del núcleo que registre una respuesta. En el
lanzamiento medido el contador se quedó en 0 mientras se gastaban 21 peticiones. El panel pinta ese
contador tal cual; no es el gasto real.

## C.5 B.2 punto 5 — una ejecución sobrevive al cambio de binding

Se cumple gratis porque se cumple el punto 3: el panel no mueve ni reescribe ningún artefacto de
§6. Una ejecución empezada en el panel se sigue desde Claude Code escribiendo `/novela`, y una
empezada en Claude Code se lee y se responde desde el panel. La ejecución `novela/`, escrita entera
con el binding de Claude Code, se lee hoy desde el panel sin haberla tocado.

## C.6 Riesgos asumidos

- **No hay locking.** `estado.json` es read-modify-write sin coordinación (`state.py` solo garantiza
  que una escritura no queda a medias, no que dos no se pisen). El panel serializa sus propias
  escrituras y se niega a lanzar un segundo orquestador sobre la misma ejecución, pero **no puede
  impedir** que abras Claude Code a la vez sobre el mismo run. Si lo haces, la última escritura gana
  y se pierde un intento.
- **El servidor escucha solo en `127.0.0.1`.** Lanza subprocesos: no puede salir a la red. No hay
  opción para cambiarlo.
- **Los permisos del orquestador son estrechos por defecto**: `python -m harness` en los dos shells,
  más `Read`, `Write` y `Task`. Todo lo demás pide permiso y se deniega. `--skip-permissions` existe
  como escotilla explícita, no como valor por defecto.
- **`runs/` no está en `.gitignore`**, para que `harness commit` siga funcionando dentro de cada
  ejecución (P5). Lo que eso mete en el historial es decisión del autor.
- **Three.js llega por CDN** con la versión fijada (`three@0.160.1`), porque el repo no tiene gestor
  de paquetes y no se le añade uno por un visor. Para trabajar sin red, descarga los dos archivos a
  `panel/static/vendor/` y cambia las dos URLs del importmap de `index.html`.

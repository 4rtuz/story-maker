# Decisiones — Spec 0004

## D1 — Arranque sin cola ni escritura en la API
- **Pregunta original (P1):** ¿El «frontend completo» incluye la cola en disco de `docs/architecture.md` §12.8 —`POST /cola`, `novela cola tomar|cerrar`, el supervisor y `run.sh`— para arrancar novelas desde el panel sin copiar órdenes?
- **Alternativas consideradas:** (a) No: Lanzar prepara la orden para copiarla y la API sigue sin verbos de escritura. (b) Sí: `POST /cola` como única escritura de la API, con los dos subcomandos, el supervisor y `run.sh`.
- **Decisión:** (a).
- **Justificación:** `AGENTS.md` prohíbe dar a la API capacidad de escritura y dice que la API no escribe. El propio §12.8 reconoce que adoptar la cola obliga a cambiar esa regla de `AGENTS.md`, y cambiar una convención del repositorio excede una spec de frontend. §11.2 ya describe el arranque como una orden que se copia.
- **Fuente:** `AGENTS.md § Nunca`; `AGENTS.md § Monorepo`; `docs/architecture.md § 11.2`; `docs/architecture.md § 12.8`.
- **Confianza:** alta
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-16).

## D2 — Actividad en vivo con dos GET de solo lectura
- **Pregunta original (P2):** ¿Incluye el panel la actividad en vivo de `docs/architecture.md` §12.6 —el listado de runs y un tramo de `harness.log`—, o solo el estado por sondeo?
- **Alternativas consideradas:** (a) Sí, con `GET …/runs` y `GET …/runs/{run_id}/log?desde=` por sondeo. (b) No: solo el estado, que cambia una vez por capítulo. (c) SSE o WebSocket.
- **Decisión:** (a), sin SSE ni WebSocket. El run que se sigue por defecto es el de `run_id` mayor, y el panel muestra las líneas tal cual y la hora de `modificado`, sin interpretarlas.
- **Justificación:** la petición pide el frontend completo, y §12.6 explica que, sin actividad, «un capítulo en curso no se distingue de un bucle colgado». La misma sección fija la dirección —dos `GET`, sin estado en el servidor— y descarta SSE y WebSocket como un segundo transporte. Su condición previa, que el log se vuelque línea a línea, la cumple la 0001 (RF-27, comprobado por CA-13). La 0001 dejó estos `GET` para una spec posterior.
- **Fuente:** Petición del usuario; `docs/architecture.md § 12.6`; `docs/specs/0001-backend-cli-estado-y-api.md § 1`, `§ 6` (RF-27) y `§ 11` (CA-13).
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.1 (O-02), 3.2, 5 (RF-22, RF-35, RF-36).

## D3 — Progreso sin cuota, QA, intervenciones ni trayectoria
- **Pregunta original (P3):** ¿Muestra Progreso la cuota, que `docs/architecture.md` §3.1 cita para `progreso/`, los informes de `qa/`, los `intervencion.md`, la trayectoria del orquestador o la carga de preguntas abiertas?
- **Alternativas consideradas:** (a) No: quedan fuera de alcance. (b) Mostrar la cuota como «no disponible». (c) Añadir `GET` para `qa/` y para las intervenciones, e implementar `novela budget`.
- **Decisión:** (a). El comentario de `progreso/` en §3.1 se corrige en el commit que crea `frontend/`.
- **Justificación:** §11.2 enumera lo que muestra Progreso y no incluye nada de eso. `novela budget` y `runs/quota.json` no existen: la 0001 y la 0003 los dejan fuera. La 0002 declara la trayectoria y la carga de preguntas «candidatas al panel de progreso; fuera de esta spec», y dependen de mecanismos que siguen en borrador.
- **Fuente:** `docs/architecture.md § 11.2`; `docs/specs/0001-backend-cli-estado-y-api.md § 1` y `§ 16`; `docs/specs/0003-contencion-y-bucle-en-claude.md § 1`; `docs/specs/0002-verificacion-a-escala-de-novela.md § 14`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 8.2.

## D4 — Config, escaleta y checkpoint servidos tal cual
- **Pregunta original (P4):** ¿De dónde saca el panel el número de capítulos, la curva de tensión objetivo y los capítulos cerrados, que la API no sirve?
- **Alternativas consideradas:** (a) Tres `GET` nuevos que sirven `Config`, `Escaleta` y `Checkpoint` con sus modelos de dominio. (b) Añadir esos datos a `Estado`. (c) Calcularlos en el frontend: el total por la longitud de la curva y los cerrados por el cursor. (d) No mostrarlos.
- **Decisión:** (a). De la escaleta, Progreso muestra la curva, las bandas de acto y los puntos de giro, pero no el texto de `funcion_dramatica`.
- **Justificación:** §11.2 prohíbe calcular en el frontend lo que la API no da, y eso descarta (c); además, el cursor no dice los cerrados: `novela estado --breve` los toma de `checkpoints/latest.json`. (b) mezclaría la configuración y el plan con la rama de lo que ya pasó, que `AGENTS.md` separa, y cambiaría `state.schema.json`. (a) sigue el patrón de §11.1, en el que los artefactos «salen del disco tal cual», y la regla de una sola ontología sin DTOs (§3.0). La frase de §11.2 «se añade al estado» pasa a «se sirve desde la API con su modelo de dominio» en el mismo commit. No mostrar `funcion_dramatica` reduce el texto del `trazador`, que conoce el misterio, a la vista del operador (spec §11).
- **Fuente:** `docs/architecture.md § 11.2`, `§ 11.1` y `§ 3.0`; `AGENTS.md § Monorepo`; `AGENTS.md § Las cuatro ramas de contexto`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 5 (RF-17, RF-18, RF-32, RF-33, RF-34), 8.2, 8.3, 11.

## D5 — Lanzar prepara solo la orden
- **Pregunta original (P5):** ¿Qué produce el formulario de Lanzar: la orden `/novela-nueva`, un `config.yaml` más la orden, como dice literalmente §11.2, o un `config.yaml` para un flag `--config` nuevo de `novela nueva`?
- **Alternativas consideradas:** (a) Solo la orden con sus flags. (b) `config.yaml` y la orden. (c) `config.yaml` y un flag `--config` en el CLI.
- **Decisión:** (a).
- **Justificación:** `config.yaml` lo escribe `novela nueva` a partir de `config/default.yaml` y los flags. Un `config.yaml` del panel no tendría consumidor, y el operador tendría que colocarlo a mano en `novelas/<slug>/`, que `AGENTS.md` prohíbe. §12.8 señala que «nadie ha decidido quién manda» entre ese fichero y los flags, y la dirección que describe deja siempre al backend como autor del `config.yaml`. (c) amplía el CLI y reabre esa pregunta. La frase de §11.2 se actualiza en el commit de Lanzar.
- **Fuente:** `docs/architecture.md § 12.8`; `AGENTS.md § Separación repo / workspace`; `docs/specs/0001-backend-cli-estado-y-api.md § 5.0`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-11, RF-16), 8.2, 8.4.

## D6 — Campos del formulario
- **Pregunta original (P6):** ¿Qué campos ofrece el formulario de Lanzar?
- **Alternativas consideradas:** (a) Slug, idea, capítulos y palabras totales: los argumentos de `/novela-nueva`. (b) Además, subgénero e idioma, que `novela nueva` acepta, ampliando el procedimiento `/novela-nueva`.
- **Decisión:** (a). «Palabras» es la longitud total de la obra, el `--palabras` que llega a `longitud_total_palabras`.
- **Justificación:** la sintaxis documentada del slash command es `/novela-nueva <slug> --idea "..." [--capitulos N] [--palabras P]`, y ampliarla es cambiar un procedimiento de `.claude/`, que pertenece a la 0003. El ejemplo de `CLAUDE.md` y `AGENTS.md`, `--capitulos 24 --palabras 80000`, muestra que `--palabras` es el total.
- **Fuente:** `CLAUDE.md § Slash commands`; `AGENTS.md § Proceso: ejecución`; `docs/specs/0003-contencion-y-bucle-en-claude.md § 5.4`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-11), 8.4.

## D7 — Escapado de la idea
- **Estado:** sustituida por D44 (comillas simples). Se conserva como registro.
- **Pregunta original (P7):** ¿Cómo se trata, dentro de `--idea "…"`, una idea con caracteres especiales para bash?
- **Alternativas consideradas:** (a) Escapar `\`, `"`, `$` y `` ` `` con una barra invertida y conservar los saltos de línea. (b) Rechazar la idea si contiene esos caracteres. (c) Normalizarla: comillas tipográficas y líneas unidas.
- **Decisión:** (a).
- **Justificación:** la idea es texto libre y puede ocupar páginas (`docs/definitions.md` §1), así que (b) y (c) alteran la única entrada humana obligatoria. Entre comillas dobles de bash solo esos cuatro caracteres son especiales; escapados, el argumento se expande a la idea original si el orquestador lo copia tal cual (supuesto S3 de la spec). Ningún documento del repositorio fija este formato.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-14), 8.4.

## D8 — Capítulos cerrados y legibles
- **Pregunta original (P8):** ¿Qué es un capítulo completado, y qué capítulos se pueden leer en el panel?
- **Alternativas consideradas:** (a) Completados son los de `checkpoint.capitulo` o menos; solo esos son legibles, y los demás aparecen como «en curso», si su fichero está en el índice, o «pendiente», sin texto. (b) Legible todo fichero de `capitulos/`, marcando los no cerrados. (c) Todos legibles, sin marca.
- **Decisión:** (a).
- **Justificación:** el bucle confirma un capítulo una sola vez, en `novela checkpoint` (§2.1), y `novela estado --breve` cuenta los cerrados desde `checkpoints/latest.json`. Un capítulo sin checkpoint todavía puede reescribirlo el `editor-estilo` o un reintento, mientras que uno cerrado ya no se reescribe (invariante 7). Mostrar como definitivo un texto que va a cambiar confundiría al operador.
- **Fuente:** `docs/architecture.md § 2.1`; `AGENTS.md § Invariantes` (7).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-17, RF-24, RF-27, RF-34).

## D9 — Escena de Lectura como estantería
- **Pregunta original (P9):** ¿Qué metáfora y qué comportamiento tiene la «navegación 3D del libro»?
- **Alternativas consideradas:** (a) Estantería: un volumen por capítulo planificado, en fila por número y con un hueco entre actos; la cámara se desplaza al seleccionado y el texto se lee en una capa HTML. (b) Un libro con páginas que se pasan. (c) Una espiral o línea temporal con altura por tensión.
- **Decisión:** (a), con un `InstancedMesh`, para que el coste no crezca con el número de capítulos.
- **Justificación:** §3.1 y §11.2 solo dicen «escena Three.js, navegación 3D del libro». (a) representa los tres estados de RF-24 en un único mesh instanciado, se recorre con dos teclas y deja el texto en HTML, accesible y seleccionable. (b) exige animar páginas y poner texto en texturas; (c) duplica la gráfica de Progreso. Ningún documento fija la metáfora.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-24), 6 (RNF-03), 8.4.

## D10 — Cadencias y plazos
- **Pregunta original (P10):** ¿Cada cuánto sondea el panel, cuánto espera una respuesta y cuándo se rotula como parada la actividad?
- **Alternativas consideradas:** (a) 10 s para los recursos de cada vista, 3 s para el log, 5 s de plazo por petición, 50 líneas visibles, 15 min sin cambios para rotular «sin actividad» y pausa con la pestaña oculta. (b) 5 s y 1 s. (c) Cadencias configurables.
- **Decisión:** (a).
- **Justificación:** el estado cambia una vez por capítulo (§12.6), y 10 s basta para verlo. El log se escribe en cada subcomando, y 3 s deja la actividad en pantalla como mucho 3 s después de escribirse, con menos de 60 peticiones por minuto en Progreso (RNF-05). 15 min es dos órdenes de magnitud mayor que la cadencia del log y se revisa con la novela de humo. Ningún documento fija estos valores.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-04, RF-05, RF-22, RF-23), 6 (RNF-05), 8.4.

## D11 — Presupuestos numéricos
- **Pregunta original (P11):** ¿Qué umbrales numéricos de rendimiento se exigen al panel y al `GET` del log?
- **Alternativas consideradas:** (a) JavaScript inicial ≤ 100 KB gzip, chunk de Lectura ≤ 300 KB gzip, ≤ 5 draw calls con 24 y con 999 capítulos, ≥ 30 fps de mediana en la máquina de desarrollo, ≤ 60 peticiones por minuto en Progreso y < 200 ms para leer un log de 1 MiB. (b) Sin presupuestos.
- **Decisión:** (a).
- **Justificación:** un requisito de rendimiento sin número no se puede verificar. Los valores dejan margen sobre el tamaño de Three.js y `markdown-it` y sobre las cadencias de D10, y se revisan con la primera medición real. El tope de 65 536 bytes por respuesta es de D17. Ningún documento fija estos valores.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 6 (RNF-01 a RNF-05, RNF-17), 12 (T-08, T-18).

## D12 — Accesibilidad
- **Pregunta original (P12):** ¿Qué nivel de accesibilidad se exige al panel?
- **Alternativas consideradas:** (a) 0 violaciones serias o críticas de axe-core con las reglas WCAG 2.1 A y AA, recorrido completo con teclado, lista HTML equivalente a la escena, tabla equivalente a la gráfica y respeto de `prefers-reduced-motion`. (b) Sin requisito formal.
- **Decisión:** (a).
- **Justificación:** la escena WebGL no es accesible por sí misma, ni la gráfica SVG sin alternativa; con (a), todo dato visual tiene un equivalente en HTML y todo se alcanza con teclado. Ningún documento del repositorio fija un nivel.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.1 (O-05), 5 (RF-18, RF-28, RF-30), 6 (RNF-12, RNF-13).

## D13 — TypeScript sin framework de UI
- **Pregunta original (P13):** ¿Con qué se construye la interfaz del panel?
- **Alternativas consideradas:** (a) TypeScript con el DOM nativo, sin framework; dependencias de ejecución `three` y `markdown-it`; textos en español, sin internacionalización; rutas por hash. (b) React. (c) Svelte o Vue. (d) Lit o web components.
- **Decisión:** (a).
- **Justificación:** el stack del frontend es «Vite + TypeScript + Three.js», sin lógica de negocio; un framework sería una dependencia fuera del stack para tres pantallas. `markdown-it` es el equivalente en JavaScript de `markdown-it-py`, que ya está en el stack del export, y hace falta porque la API sirve los capítulos en markdown. La documentación y el dominio del repositorio están en español. Las rutas por hash no necesitan configuración del servidor al recargar la página. La estructura sigue el package by feature de §3.0.
- **Fuente:** `docs/architecture.md § 2`; `AGENTS.md § Monorepo`; `docs/architecture.md § 3.0`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-44), 8.1, 8.2, 8.4.

## D14 — Render seguro del capítulo
- **Pregunta original (P14):** ¿Cómo se convierte el markdown de un capítulo en HTML sin abrir una vía de inyección?
- **Alternativas consideradas:** (a) `markdown-it` con `html: false` y las reglas `link` e `image` desactivadas; solo el módulo del lector inserta HTML, y el resto del panel usa `textContent`. (b) `markdown-it` completo más un sanitizador como DOMPurify. (c) Mostrar el markdown como texto plano.
- **Decisión:** (a).
- **Justificación:** los capítulos los escriben agentes, y el modelo de amenazas del repositorio incluye la inyección por contenido del workspace (amenaza 2); esta decisión lleva esa amenaza al navegador del operador. Un enlace o una imagen abrirían además peticiones a otros orígenes (RNF-08). (a) no añade dependencias y deja un único punto de inserción de HTML, que eslint vigila; (c) pierde el formato del capítulo.
- **Fuente:** `docs/validators.md § 4.9`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-26), 6 (RNF-07), 8.4.

## D15 — Conexión con la API y servicio del panel
- **Pregunta original (P15):** ¿Cómo llega el navegador a la API, y cómo se sirve el panel?
- **Alternativas consideradas:** (a) Llamadas directas con el CORS que ya admite `http://localhost:5173`; `VITE_API_URL`, con `http://127.0.0.1:8000` por defecto; el panel se sirve con `npm run dev`, y `vite preview` en el mismo puerto solo para los e2e. (b) Proxy del dev server de Vite hacia la API. (c) FastAPI sirve `frontend/dist`.
- **Decisión:** (a). El puerto no puede cambiar, porque el origen del panel tiene que ser exactamente el que admite el CORS.
- **Justificación:** el árbol documenta `main.py` con «CORS para el dev server de Vite», y el procedimiento de desarrollo arranca la API y el panel por separado. (b) dejaría sin uso el CORS ya configurado, y (c) cambia el backend sin que el panel lo necesite.
- **Fuente:** `docs/architecture.md § 3.1`; `AGENTS.md § Proceso: ejecución`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-01), 9.

## D16 — El frontmatter del capítulo lo quita el panel
- **Pregunta original (P16):** `GET …/capitulos/{n}` devuelve el fichero entero, frontmatter incluido: ¿lo quita el panel o cambia la API?
- **Alternativas consideradas:** (a) El panel quita el bloque inicial entre líneas `---` y toma el título del índice. (b) Cambiar ese `GET` para que devuelva solo el cuerpo, que rompe el contrato de la 0001. (c) Un `GET` nuevo solo para el cuerpo.
- **Decisión:** (a).
- **Justificación:** el contrato de la 0001 sirve el markdown del capítulo tal cual y su frontmatter por separado, en el índice, y el panel consume lo que la API devuelve tal cual (§11.2). Quitar el bloque es presentación, no un dato nuevo.
- **Fuente:** `docs/specs/0001-backend-cli-estado-y-api.md § 8`; `docs/architecture.md § 11.1` y `§ 11.2`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-25), 8.4.

## D17 — Contrato del tramo de log
- **Pregunta original (P17):** ¿Qué devuelve exactamente el `GET` del log y qué pasa en sus bordes?
- **Alternativas consideradas:** (a) `TramoDeLog {desde, hasta, tamano, modificado, lineas}` con solo líneas completas, cortadas en el servidor; tope de 65 536 bytes salvo una primera línea más larga; 416 si `desde` supera el tamaño, 422 si es negativo y tramo vacío si el run no tiene log. (b) Bytes crudos desde el desplazamiento, y el cliente descarta la línea incompleta del final, como describe §12.6.
- **Decisión:** (a).
- **Justificación:** §12.6 fija el desplazamiento en bytes, el tope por respuesta y el encadenado sin estado en el servidor. Cortar en el servidor por el último salto de línea evita partir un carácter UTF-8 al serializar a JSON, que (b) no resuelve, y para el cliente el resultado es el mismo que describe §12.6. `modificado` da la hora de la última escritura sin que el panel tenga que interpretar las líneas. Los códigos de los bordes no los fija ningún documento.
- **Fuente:** `docs/architecture.md § 12.6`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-36, RF-37), 6 (RNF-17), 8.3.

## D18 — Herramientas de verificación del frontend
- **Pregunta original (P18):** ¿Con qué herramientas se prueba el frontend, además de `tsc --noEmit` y `eslint`?
- **Alternativas consideradas:** (a) Vitest con jsdom para los unitarios, fast-check para las propiedades, Playwright en Chromium y Firefox con reloj controlado y `@axe-core/playwright` para e2e y accesibilidad, `openapi-typescript` para los tipos y `eslint-plugin-no-unsanitized`; Node.js en su LTS vigente, fijado en `engines` y en CI. (b) Jest y Cypress. (c) Solo `tsc` y `eslint`.
- **Decisión:** (a).
- **Justificación:** `tsc --noEmit` y `eslint` los nombra `docs/validators.md`; el resto no lo fija ningún documento. Vitest reutiliza la configuración de Vite; Playwright cubre los dos navegadores de la máquina de desarrollo y controla el reloj, que hace deterministas las pruebas de sondeo; `openapi-typescript` genera tipos desde OpenAPI 3.1, la versión que emite FastAPI. (c) dejaría sin probar los requisitos de comportamiento.
- **Fuente:** Supuesto (para `tsc --noEmit` y `eslint`: `docs/validators.md § 3.1` y `§ 3.2`). La versión de Node la precisa D35.
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-40), 8.2, 10, 13.

## D19 — Datos de los e2e
- **Pregunta original (P19):** ¿Contra qué datos corren los e2e del panel?
- **Alternativas consideradas:** (a) Workspaces sintéticos generados con `backend/tests/fixtures/fabrica.py`, servidos por la API real con `NOVELAS_DIR`, en un job de CI propio. (b) Respuestas simuladas interceptando la red. (c) Una novela real.
- **Decisión:** (a), con tres workspaces: `demo-24` (7 capítulos cerrados y el 8 en curso), `recien-creada` (sin plan ni checkpoints) y `grande-999` (solo `novela nueva` con 999 capítulos). El generador aísla `RAIZ_REPO` y el entorno, como `backend/conftest.py`, para no emitir scores con las claves de `.env` al cerrar capítulos con el CLI real.
- **Justificación:** los tests del repositorio corren sobre workspaces sintéticos de fixtures y ninguno llama a un modelo; con la API real y `NOVELAS_DIR`, el e2e prueba el contrato de verdad, que (b) sustituiría por copias; (c) no es reproducible y cuesta cuota.
- **Fuente:** `docs/validators.md § 3.5`; `AGENTS.md § Proceso: generar código (TDD)`; `docs/specs/0001-backend-cli-estado-y-api.md § 5.1`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-40, RF-42), 13.

## D20 — Verificación del frontend antes de commitear
- **Pregunta original (P20):** ¿Dónde queda escrito, y cómo se hace cumplir, lo que se ejecuta en `frontend/` antes de commitear?
- **Alternativas consideradas:** (a) Una línea en `AGENTS.md` § Proceso: generar código, paso 5 (`npm run verificar` en `frontend/`), un paso de eslint en `.githooks/pre-commit` cuando el índice tiene ficheros de `frontend/`, y la fila de pre-commit de `docs/validators.md` §6. (b) Solo `docs/validators.md` §6. (c) Un `frontend/README.md`.
- **Decisión:** (a).
- **Justificación:** el paso 5 de `AGENTS.md` es la convención de lo que se ejecuta antes de commitear, y hoy solo nombra el backend; con `frontend/` en el repositorio, la convención cambia, que es el caso en que `AGENTS.md` se toca. Una sola línea respeta la regla de no ampliarlo sin necesidad. `docs/validators.md` §6 pone en el pre-commit el análisis estático, y el hook de `.githooks/pre-commit` ya ejecuta `ruff` sobre el backend.
- **Fuente:** `AGENTS.md § Proceso: generar código (TDD)`; `AGENTS.md § Proceso: modificar documentación`; `AGENTS.md § Nunca`; `docs/validators.md § 6`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-41, RF-45), 8.2, 8.4.

## D21 — Tokens de marca en un único fichero
- **Pregunta original (P21):** ¿Cómo se fijan en el panel la paleta y el resto de valores visuales de Qaracter, y con qué valores?
- **Alternativas consideradas:** (a) Un único `frontend/src/shared/marca/tokens.css` con dos capas —primitivos con los valores de la captura y roles semánticos, que son lo único que usan los componentes—, sin colores de estado ajenos a la paleta. (b) Los valores repartidos por el CSS de cada componente. (c) Un framework de estilos externo, como Tailwind, con su propia paleta.
- **Decisión:** (a). Los valores son los de la captura, aproximados, y los sustituyen los del manual de marca si existe, cambiando solo `tokens.css` (S6). La atención y el error usan el tinte naranja con icono y texto: la paleta no gana un rojo ni un verde. La escena y la gráfica leen los mismos roles (RF-55). El degradado del logo (aprox. de `#FFA51C` a `#FF7A30`) no cambia ningún primitivo: está dentro de la imagen, y ningún componente lo reproduce en CSS.
- **Justificación:** la petición exige los colores de Qaracter y aporta la captura como base. Con un único fichero, pasar a los valores del manual es editar un fichero, y «ningún color literal fuera de él» se puede comprobar (CA-46). La capa semántica separa el valor de la marca de su uso, y eso permite derivar los tonos de D22 sin tocar componentes. (b) no se puede comprobar ni cambiar de una vez; (c) añade dependencias que RF-44 no admite y una paleta ajena. Un rojo o un verde de estado serían colores que la captura no muestra. Añadir tokens para el degradado del logo solo tendría sentido si algo lo repitiera fuera de la imagen, y nada lo hace.
- **Fuente:** Petición del usuario; captura de la plataforma interna de Qaracter aportada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1 (O-07), 5 (RF-46, RF-55), 8.1, 8.4, 10 (S6).

## D22 — Contraste AA con la paleta de la marca
- **Pregunta original (P22):** El blanco sobre el naranja de la marca (aprox. `#F97316`) da 2,8:1, por debajo del 4,5:1 de WCAG 2.1 AA que exige D12, y el naranja y el cian vivos no llegan a 3:1 como iconos con significado sobre sus tintes (criterio 1.4.11). ¿Cómo se mantiene la marca cumpliendo AA?
- **Alternativas consideradas:** (a) Dos tonos por color: el vivo, solo en lo decorativo, y uno oscuro de la misma familia (naranja aprox. `#C2410C`, cian aprox. `#0369A1`) en toda superficie con texto blanco, en el texto y los iconos con significado y en los indicadores, con el texto del banner sobre el tramo oscuro del degradado. (b) Mantener el naranja vivo en el botón primario y en el ítem activo, con texto oscuro (`#1F2937`, 5,24:1). (c) Reservar el naranja para lo decorativo y hacer los controles en gris pizarra.
- **Decisión:** (a), comprobada con los pares declarados en `pares.ts` (RNF-19). En concreto:
  - el ítem activo lleva fondo naranja oscuro con texto blanco (5,18:1) y una barra indicadora en naranja vivo, que da 4,28:1 frente a la barra lateral;
  - el texto secundario (aprox. `#6B7280`) solo va sobre blanco (4,84:1), porque sobre el fondo de página da 4,27:1;
  - el borde de los campos usa ese mismo gris (4,84:1) y no el del borde de tarjeta (1,24:1);
  - el foco es naranja oscuro sobre los fondos claros y blanco sobre los oscuros;
  - el degradado del banner mantiene su color oscuro hasta la mitad del ancho, y el texto no sale de esa mitad (blanco 8,50:1, crema 7,18:1).
- **Justificación:** (a) conserva el blanco sobre naranja de la marca con un naranja de su misma familia, y el naranja vivo sigue donde más se ve: el banner, las teselas y el indicador del ítem activo, además del propio logo. (b) cambia el aspecto de los controles frente a la captura, y (c) quita el naranja de los controles. axe no calcula el contraste sobre degradados ni el no textual, así que los pares se comprueban por cálculo desde los tokens. El logo no entra en los pares: los logotipos no tienen requisito de contraste en WCAG 2.1. Si el manual define tonos accesibles propios, sustituyen a los derivados (S9), y (b) queda como salida si la marca no admite los derivados. Ningún documento del repositorio resuelve este conflicto.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 2, 5 (RF-47, RF-48, RF-53), 6 (RNF-19), 8.4, 10 (S9), 11.

## D23 — Logo oficial en PNG, siempre con bordes redondeados
- **Pregunta original (P23):** El repositorio no tenía el logo de Qaracter. ¿De dónde sale, dónde se guarda y qué se muestra mientras no esté? Revisada en la v4: el usuario aportó el logo oficial —un PNG cuadrado de 400 × 400 px y 68 KB, sin transparencia en las esquinas, con un degradado naranja y la «Q» en blanco, sin wordmark— con la condición de usarlo siempre con bordes redondeados. ¿Cómo se usa, cómo se comprueba y qué sale de él para el favicon?
- **Alternativas consideradas:**
  - Redondeo: (a) el PNG tal cual, dentro de un único componente, `logo.ts`, con un contenedor de `border-radius` proporcional al lado y `overflow: hidden`; (b) recortar las esquinas en el propio PNG; (c) un SVG que envuelva el PNG con un `clipPath`.
  - Comprobación en CI, en lugar de la de SVG seguro, que ya no aplica: (a) firma PNG, 400 × 400 px y como mucho 80 KB, más el estilo computado del contenedor en el navegador; (b) solo que el fichero exista; (c) ninguna.
  - Favicon: (a) un PNG de 64 × 64 px derivado una vez del logo, con las esquinas transparentes al mismo radio proporcional; (b) el PNG de 400 px sin recortar; (c) un SVG con `clipPath` que incruste el PNG.
- **Decisión:** (a) en los tres puntos. El radio es el 22 % del lado (`--q-radio-logo`: 8,8 px a 40 px y 14 px a 64 px). En la barra lateral, el logo mide 40 px desplegada y plegada, con el texto «Qaracter» al lado cuando está desplegada, como en la captura. Desaparecen el sustituto provisional, el rol `--q-deco-logo` y la comprobación de SVG seguro. `logo.png` se versiona tal cual en T-19; `logo.png` y `favicon.png` cuentan juntos en RNF-20, con un tope de 80 KB, y no cuentan en los presupuestos de JavaScript de D11, que no cambian.
- **Justificación:** con un componente único y el recorte en CSS, el PNG oficial se usa sin retocar y ningún uso puede quedar sin redondear: eslint prohíbe importar el PNG fuera de `logo.ts`, y el e2e comprueba en cada aparición el `border-radius` distinto de cero y el recorte, además de una esquina de la captura del elemento (CA-51). (b) altera el fichero de la marca. (c) complica el uso sin ganar nada en el navegador. El favicon es la excepción, porque un favicon no admite CSS: por eso se deriva con las esquinas ya transparentes, y CA-61 lo comprueba por píxeles. El radio del 22 % se aproxima al del cuadrado del logo de la captura, que tiene las esquinas claramente redondeadas; lo sustituye el del manual si existe (S7). Un PNG de 68 KB mostrado a 40 px pesa más de lo necesario, pero cabe en el presupuesto y evita derivar otra copia del logo.
- **Fuente:** Petición del usuario (logo aportado y condición de uso); captura de la plataforma interna de Qaracter aportada por el usuario (radio y tamaño). El radio concreto y el favicon derivado son supuestos.
- **Confianza:** media para el uso del PNG y el redondeo obligatorio; baja para el 22 % y el favicon derivado.
- **Secciones de la spec afectadas:** 2, 3.1 (O-07), 3.2, 4, 5 (RF-51, RF-52, RF-60, RF-61), 6 (RNF-20), 7 (CA-51, CA-52, CA-60, CA-61), 8.2, 8.4, 9, 10 (S7), 11, 12 (T-19, T-21, T-22), 13 (M-09, M-12), 14.

## D24 — Estructura de la plataforma adaptada al panel
- **Pregunta original (P24):** ¿Qué elementos de la plataforma de referencia pasan al panel, y cómo se reparten en él las vistas de la spec?
- **Alternativas consideradas:** (a) Barra lateral con «Novelas», «Lanzar» y, con una novela en la ruta, su «Progreso» y su «Lectura», con el estado de la API en su zona inferior; barra superior con el botón de plegar, el título y la hora de la última actualización; el banner como cabecera de la novela en Progreso y Lectura, con el cursor en chips; en Progreso, una fila de métricas y una rejilla de tarjetas a dos columnas; listas como subtarjetas con etiquetas; y nada de avatar, notificaciones ni bienvenida. (b) Replicar la plataforma entera, avatar y bienvenida incluidos, con datos fijos. (c) Una sola columna, sin barra lateral.
- **Decisión:** (a).
- **Justificación:** el panel no tiene usuarios ni autenticación (§3.2 y §4 de la spec), así que el avatar, la campana y la bienvenida no tendrían contenido. El resto de la estructura tiene un equivalente directo: la navegación recoge las cuatro vistas; la zona inferior, que en la plataforma lleva el modo oscuro y el idioma (D28), muestra lo que el operador necesita tener siempre a la vista, si la API responde; y el banner es el sitio natural de la novela activa y de su cursor. El umbral de 1280 px deja 914 px de contenido para las dos columnas, con la barra desplegada y márgenes de 48 px. Ningún documento fija esta disposición.
- **Fuente:** Supuesto (los elementos de partida salen de la captura de la plataforma interna de Qaracter aportada por el usuario).
- **Confianza:** baja
- **Secciones de la spec afectadas:** 3.2, 5 (RF-48, RF-49, RF-50, RF-53, RF-54, RF-59), 8.4.

## D25 — Fuentes e iconos servidos desde frontend/
- **Pregunta original (P25):** ¿Se autoalojan las tipografías y los iconos, o se toman de un CDN o de paquetes npm, y cómo afectan a los presupuestos de D11?
- **Alternativas consideradas:** (a) Cuerpo con la pila de fuentes del sistema; tipografía display en un WOFF2 autoalojado, en subconjunto latino y con su licencia; iconos como trazados de Lucide copiados en el repositorio con su licencia ISC; y un presupuesto propio de 60 KB para las fuentes y de 20 KB gzip para el CSS. (b) Fuentes de un CDN, como Google Fonts. (c) Paquetes npm, como `lucide` o los de `@fontsource`.
- **Decisión:** (a). Las fuentes y el CSS no cuentan en los presupuestos de JavaScript de D11, que no cambian: tienen el suyo en RNF-20, que desde la v4 incluye también las imágenes de marca (D23).
- **Justificación:** un CDN es una petición a un tercero con la IP del operador, y RNF-08 prohíbe cualquier origen distinto del panel y de la API. Los paquetes npm añadirían dependencias de ejecución que RF-44 no admite. La pila del sistema no pesa nada, y la captura admite un cuerpo «tipo Inter o la del sistema». Los trazados de Lucide dibujados con `createElementNS` mantienen el único punto de inserción de HTML de D14.
- **Fuente:** Petición del usuario, con la captura de la plataforma interna de Qaracter aportada por el usuario (iconos de estilo Lucide y cuerpo «tipo Inter o la del sistema»); restricciones de esta spec: RNF-08 y RF-44.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-56), 6 (RNF-20), 8.2, 8.4.

## D26 — Tipografía display provisional
- **Pregunta original (P26):** ¿Qué familia se usa para el titular en display geométrica de peso 800 a 900 mientras no haya manual de marca?
- **Alternativas consideradas:** (a) Outfit (SIL OFL 1.1), peso 800, en un subconjunto latino que cubre el español. (b) Poppins (OFL), peso 800. (c) Montserrat (OFL), peso 800. (d) La fuente del sistema en negrita.
- **Decisión:** (a), provisional: si el manual fija otra familia y su licencia permite autoalojarla, la sustituye cambiando el fichero y `--q-fuente-display` (S8).
- **Justificación:** la captura muestra una display geométrica muy gruesa. Outfit es geométrica, tiene pesos hasta 900 y licencia OFL, que permite autoalojarla y reducirla a un subconjunto. (d) no se parece a la captura. Ningún documento decide entre (a), (b) y (c).
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-56), 8.4, 10 (S8).

## D27 — Verificación de «profesional y pulido»
- **Pregunta original (P27):** ¿Cómo se verifica que el panel se ve «profesional y pulido»?
- **Alternativas consideradas:** (a) Separar lo objetivo, con comprobaciones automáticas —tokens en un único fichero y ningún literal fuera, contraste calculado de cada par, estados de cada componente y cada vista, capturas de regresión visual por vista y estado, medidas computadas, foco visible y CLS—, de lo subjetivo, con una revisión humana frente a la captura, con lista de comprobación y marcada como manual. (b) Solo la revisión humana. (c) Solo las comprobaciones automáticas.
- **Decisión:** (a). Las capturas corren solo en Chromium, en la imagen de Playwright del job `frontend-e2e`, con el canvas y las horas enmascarados y el reloj fijado, y la revisión manual de T-22 aprueba sus referencias. Los estados de carga, vacío y error usan `page.route` solo para retrasar, vaciar o hacer fallar respuestas, nunca para inventar datos (D19).
- **Justificación:** «profesional y pulido» tiene una parte medible y otra de juicio. `docs/validators.md` §1 no acepta que una propiedad crítica tenga solo inspección, y el mismo criterio vale aquí: la parte medible pasa a T y A, y la revisión humana queda para lo que ninguna medida capta, con su riesgo aceptado. (b) sería una opinión con fecha; (c) no dice si el resultado se parece a la marca. Hacer las capturas en un contenedor fijo evita diferencias de render entre máquinas.
- **Fuente:** Petición del usuario; `docs/validators.md § 1`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1 (O-07), 5 (RF-57, RF-58), 6 (RNF-21 a RNF-24), 12 (T-21, T-22), 13.

## D28 — Sin modo oscuro ni selector de idioma
- **Pregunta original (P28):** La plataforma de referencia tiene modo oscuro y selector de idioma. ¿Entran en el panel?
- **Alternativas consideradas:** (a) No: tema claro con `color-scheme: light` y textos en español. (b) Modo oscuro según `prefers-color-scheme`, sin conmutador. (c) Modo oscuro con conmutador y selector de idioma, como en la plataforma.
- **Decisión:** (a). Con la capa semántica de D21, un tema oscuro sería un segundo juego de valores de los roles, en una spec posterior.
- **Justificación:** la petición pide la marca y un acabado profesional, no un segundo tema. Un segundo tema duplica las comprobaciones de contraste y las capturas de referencia; un conmutador tendría que guardar la preferencia en el navegador, que RNF-09 prohíbe; y un selector de idioma contradice los textos solo en español de D13.
- **Fuente:** Petición del usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.2, 5 (RF-59), 8.4.

## D29 — Spec aceptada, con el formato de carpeta de AGENTS.md
- **Pregunta original (P29):** La spec seguía sin aceptar y con el formato del redactor (supuesto S5; P2 del plan; D3 y D7 de `validators.md`), y S4 situaba el plan en `docs/implementation-plans/`. ¿Se acepta antes de T-01, y con qué formato?
- **Alternativas consideradas:** (a) Aceptarla en la v5 y quedarse con `docs/specs/0004/`, con `spec.md`, `decisions.md`, `plan/` y `validators.md`. (b) Trasladarla al formato de las specs anteriores: un único `docs/specs/NNNN-<slug>.md` y el plan en una carpeta aparte. (c) Implementar sin aceptarla.
- **Decisión:** (a). Estado `aceptada`, en minúscula como en el resto del repositorio, y versión 5. S4 y S5 se reescriben: el plan está en `docs/specs/0004/plan/` y los validadores en `docs/specs/0004/validators.md`, y los dos se borran al implementar, después de subir a `docs/validators.md` lo que perdura (T-23).
- **Justificación:** `AGENTS.md` § Proceso: modificar documentación ya recoge esa convención para las specs desde la 0004, y exige aceptar una spec antes de implementarla. (b) movería ficheros a una convención que ya no rige; (c) incumple el ciclo de vida.
- **Fuente:** Decisión delegada por el usuario; `AGENTS.md § Proceso: modificar documentación`; `plan/README.md` § 9 (P1, P2); `validators.md` D3 y D7.
- **Confianza:** media
- **Secciones de la spec afectadas:** frontmatter, 10 (S4, S5), 12 (T-23).

## D30 — T-17 antes de T-21
- **Pregunta original (P30):** El plan adelanta el job `frontend-e2e` (T-17) a la regresión visual (T-21) para que las referencias salgan de la imagen de Playwright del CI (PD1, P3 del plan, D1 de `validators.md`). ¿Se cambia el orden de §12?
- **Alternativas consideradas:** (a) Sí: T-16, T-17, T-21. (b) Mantener T-16, T-21, T-17 y generar las referencias en un contenedor local.
- **Decisión:** (a). T-21 necesita T-16 y T-17.
- **Justificación:** RNF-22 y D27 fijan las capturas en la imagen de Playwright del CI. Con (b), las primeras referencias saldrían de Windows y fallarían en Linux. Las dependencias de T-17 (T-08 y T-16) no cambian.
- **Fuente:** Decisión delegada por el usuario; `plan/README.md` PD1 y P3.
- **Confianza:** media
- **Secciones de la spec afectadas:** 12.

## D31 — Recursos de terceros ya descargados
- **Pregunta original (P31):** ¿De dónde salen `outfit-800.woff2` con su `OFL.txt` y los trazados de Lucide con su `LICENSE` (P4 del plan, D4 de `validators.md`)?
- **Alternativas consideradas:** (a) Los ficheros ya descargados, con la aprobación del usuario, en `frontend/src/shared/marca/fuentes/` (`outfit-800.woff2`, 14 048 bytes, subconjunto latino de `@fontsource/outfit` 5.3.0, fichero `files/outfit-latin-800-normal.woff2`, y `OFL.txt` del mismo paquete) y en `frontend/src/shared/iconos/` (`LICENSE` ISC y `lucide/*.svg` con los doce iconos de §8.4, de `lucide-static` 1.48.0, sin scripts ni referencias externas). (b) Descargarlos en T-19.
- **Decisión:** (a). T-19 no descarga nada: copia los trazados de los SVG de `iconos/lucide/` a `trazados.ts` y, en ese mismo commit, borra `iconos/lucide/`, porque RF-60 solo admite `logo.png` y `favicon.png` como imágenes versionadas. El origen y la versión de la fuente y de los iconos quedan en la cabecera de `trazados.ts` y en el mensaje del commit.
- **Justificación:** los recursos ya están en el repositorio sin versionar y con su licencia. Versionar los SVG crudos rompería CA-60, y copiar solo los trazados mantiene el dibujo con `createElementNS` de D25.
- **Fuente:** Decisión delegada por el usuario; ficheros aportados con su aprobación.
- **Confianza:** alta
- **Secciones de la spec afectadas:** 2, 8.2, 8.4, 12 (T-19).

## D32 — Favicon derivado con Pillow sin añadir dependencias
- **Pregunta original (P32):** ¿Con qué herramienta se deriva `favicon.png` (P5 del plan)?
- **Alternativas consideradas:** (a) Una sola vez en T-19, con `uv run --with pillow python` desde `backend/`, sin tocar `pyproject.toml` ni `uv.lock`. (b) Pillow como dependencia de desarrollo del backend. (c) Un script de Node en `frontend/`.
- **Decisión:** (a). La orden exacta está en §8.4 y en T-19, y se copia en el mensaje del commit.
- **Justificación:** es una derivación de un solo uso; (b) y (c) añaden una dependencia al proyecto para un fichero que se commitea. CA-61 comprueba el resultado por píxeles, así que la herramienta no necesita estar en CI.
- **Fuente:** Decisión delegada por el usuario; `plan/README.md` P5.
- **Confianza:** media
- **Secciones de la spec afectadas:** 8.4, 12 (T-19).

## D33 — Supuestos provisionales del plan aceptados
- **Pregunta original (P33):** ¿Se aceptan los supuestos provisionales de P6, P7, P9 y P12 del plan (D2, D5 y D6 de `validators.md`)?
- **Alternativas consideradas:** (a) Aceptarlos tal como están. (b) Revisarlos uno a uno.
- **Decisión:** (a):
  - P6: T-08 y T-17 actualizan `docs/validators.md` §6 y el párrafo de estado de §2.
  - P7: T-15 actualiza la frase de Lectura de `docs/architecture.md` §11.2 («capítulos cerrados», estantería 3D).
  - P9: las reglas de `eslint.config.js` entran en la tarea que las prueba (PD2): T-04, imports fuera de `src/` y `no-unsanitized`; T-06, red fuera de `src/shared/api/`; T-19, importación de `logo.png` reservada a `logo.ts`.
  - P12: el conductor de T-18 se ejecuta a mano desde `backend/` con `uv run python`, sin versionar, y su orden se anota en §13.
- **Justificación:** son los supuestos que el plan necesitaba para cumplir el «rojo primero» y RF-45 sin cambiar el alcance.
- **Fuente:** Decisión delegada por el usuario; `plan/README.md` § 9.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-45), 8.2, 12 (T-04, T-06, T-08, T-15, T-17, T-18, T-19).

## D34 — TramoDeLog en docs/definitions.md
- **Pregunta original (P34):** `AGENTS.md` pide actualizar `docs/definitions.md` al cambiar un modelo Pydantic, y la spec lo declaraba sin cambios (P8 del plan, D12 y Q19 de `validators.md`). ¿Lleva `TramoDeLog` una línea?
- **Alternativas consideradas:** (a) Sí, una línea, en la misma tarea que crea el modelo. (b) No, por ser un modelo de respuesta.
- **Decisión:** (a), en T-02.
- **Justificación:** la regla de `AGENTS.md` vale para todo modelo Pydantic nuevo, y (b) la incumpliría.
- **Fuente:** Decisión delegada por el usuario; `AGENTS.md § Proceso: generar código (TDD)`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-45), 8.2, 12 (T-02).

## D35 — Node 24 LTS
- **Pregunta original (P35):** ¿Qué versión de Node se fija en `engines` y en CI (P10 del plan)?
- **Alternativas consideradas:** (a) Node 24 LTS: `"engines": {"node": ">=24 <25"}` y `node-version: 24` en `actions/setup-node`. (b) La LTS activa el día de T-04, sin fijarla en la spec.
- **Decisión:** (a).
- **Justificación:** una versión escrita evita la deriva entre la máquina de desarrollo y CI que (b) deja abierta.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 8.2, 10, 12 (T-04, T-08, T-17).

## D36 — CA-14 y CA-41 pasan en local en Windows
- **Pregunta original (P36):** En Windows, ¿basta con CI en Linux para CA-14 y CA-41 (P11 del plan)?
- **Alternativas consideradas:** (a) Deben pasar en local con Git Bash en el `PATH`. (b) Basta CI.
- **Decisión:** (a). Sin bash, los tests fallan con un mensaje que lo nombra; no se saltan.
- **Justificación:** con (b), un commit se haría en rojo en local o con tests saltados en silencio.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 7 (CA-14, CA-41).

## D37 — RF-45 incluye §3.6, §4.4, §4.7 y §4.9 de docs/validators.md
- **Pregunta original (P37):** La tabla de métodos de §13 aplica los métodos 6, 13, 16 y 18, pero RF-45 no nombraba sus secciones de `docs/validators.md` (D8 y Q17 de `validators.md`). ¿Se actualizan?
- **Alternativas consideradas:** (a) Sí, en el commit de cierre (T-23). (b) No.
- **Decisión:** (a).
- **Justificación:** con (b), al cerrar, esas secciones no nombrarían `server.fs.allow`, el cliente único de `GET`, el único punto de inserción de HTML, los jobs nuevos ni la amenaza 2 llevada al navegador.
- **Fuente:** Decisión delegada por el usuario; `validators.md` D8.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-45), 7 (CA-45), 8.2, 12 (T-23).

## D38 — Progreso sigue siempre el run de run_id mayor
- **Pregunta original (P38):** RF-22 y RF-23 hablaban de un «run seleccionado» y §8.4 de una «entrada de run», pero ninguna tarea permitía elegirlo (D9 y Q7 de `validators.md`). ¿Se puede seleccionar un run?
- **Alternativas consideradas:** (a) No: Progreso muestra siempre el run de `run_id` mayor y cambia solo cuando aparece uno nuevo. (b) Selección de run con una entrada interactiva.
- **Decisión:** (a). Al aparecer un run mayor, la primera petición a su log lleva `desde=0` y la lista se reconstruye.
- **Justificación:** el run mayor es el del bucle en curso, que es lo que el operador necesita para distinguir un capítulo en curso de un bucle parado (O-02). (b) añade un componente y un estado sin tarea que los pruebe.
- **Fuente:** Decisión delegada por el usuario; `validators.md` VAL-13.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-22, RF-23), 7 (CA-22), 8.4, 9.

## D39 — §8.2 sigue a PD6
- **Pregunta original (P39):** §8.2 decía que `panel.py` construye los tres workspaces con `fabrica.construir`, pero `construir` siempre escribe canon y plan (D10 de `validators.md`). ¿Qué frase manda?
- **Alternativas consideradas:** (a) PD6: `demo-24` con `construir` y `preparar_capitulo`; `recien-creada` y `grande-999` con `novela nueva`. (b) Cambiar `fabrica.construir`.
- **Decisión:** (a); se corrige §8.2.
- **Justificación:** (a) cumple D19 («sin plan ni checkpoints») sin tocar `fabrica.py`, que usa `backend/conftest.py`.
- **Fuente:** Decisión delegada por el usuario; `plan/README.md` PD6.
- **Confianza:** media
- **Secciones de la spec afectadas:** 8.2.

## D40 — npm run verificar encadena todo lo que se ejecuta antes de commitear
- **Pregunta original (P40):** El plan exigía `npm run build` y `npm run presupuesto` antes de commitear, y la línea de `AGENTS.md` que fija D20 solo dice `npm run verificar` (D11 de `validators.md`). ¿Cómo se alinean?
- **Alternativas consideradas:** (a) `verificar` encadena `tipos:comprobar` (desde T-05), `lint`, `typecheck`, `test`, `build` y `presupuesto` (desde T-08), y la línea de `AGENTS.md` basta. (b) Ampliar la línea de `AGENTS.md`.
- **Decisión:** (a). `tipos:comprobar` sigue en `verificar`, como ya estaba.
- **Justificación:** con (a), la convención escrita coincide con lo que se practica sin añadir líneas a `AGENTS.md`, que se paga en cada sesión.
- **Fuente:** Decisión delegada por el usuario; D20.
- **Confianza:** media
- **Secciones de la spec afectadas:** 8.4 (scripts), 12 (T-04, T-08).

## D41 — Enteros solo con dígitos
- **Pregunta original (P41):** ¿`07`, ` 3` o `+3` son capítulos válidos, y se normalizan (Q1 de `validators.md`)?
- **Alternativas consideradas:** (a) Solo dígitos, sin ceros a la izquierda, sin signo y sin espacios; todo lo demás es error de validación, sin normalizar. (b) Aceptar y normalizar.
- **Decisión:** (a). Capítulos del formulario y capítulo de la ruta: `^[1-9][0-9]{0,2}$`. Palabras: `^[1-9][0-9]*$`.
- **Justificación:** normalizar esconde un error de tecleo en una orden que arranca una novela, y en la ruta abriría dos URL para el mismo capítulo.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-09, RF-12), 7 (CA-09, CA-12).

## D42 — Idea vacía
- **Pregunta original (P42):** ¿Una idea con solo tabuladores o saltos de línea «solo tiene espacios» (Q2 de `validators.md`)?
- **Alternativas consideradas:** (a) Sí: cuenta como vacía la idea que solo contiene espacios en blanco Unicode (`\s`, incluidos tabuladores y saltos de línea). (b) Solo U+0020.
- **Decisión:** (a).
- **Justificación:** una idea hecha de blancos no es una idea en ninguna de sus formas.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-12), 7 (CA-12).

## D43 — Lanzar sin la respuesta de GET /novelas
- **Pregunta original (P43):** ¿Qué hace Lanzar si `GET /novelas` no ha respondido o ha fallado (Q3 de `validators.md`)?
- **Alternativas consideradas:** (a) Generar la orden sin comprobar el slug, con un aviso visible de que no se ha podido comprobar. (b) Bloquear la orden.
- **Decisión:** (a), con el aviso «no se ha podido comprobar si el slug ya existe».
- **Justificación:** la comprobación es una ayuda: si el slug existe, `novela nueva` sale con 1 sin tocar nada. Bloquear dejaría al operador sin orden por una caída de la API.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-13), 7 (CA-13), 8.4.

## D44 — La idea va entre comillas simples
- **Pregunta original (P44):** ¿Se contempla que el operador pegue la orden en un bash interactivo, donde `!` activa la expansión del historial dentro de comillas dobles (Q4 de `validators.md`)? D7 tenía confianza baja.
- **Alternativas consideradas:** (a) La idea entre comillas simples, con cada `'` sustituida por `'\''`. (b) Mantener D7: comillas dobles con `\`, `"`, `$` y `` ` `` escapados. (c) `$'…'` de bash.
- **Decisión:** (a). Sustituye a D7. `$`, `` ` ``, `\`, `!` y los saltos de línea quedan inertes en bash interactivo y no interactivo, y CA-14 se ejecuta además con `set -H`. Pegar la orden en el prompt de Claude Code queda fuera del alcance y es un riesgo aceptado (§13).
- **Justificación:** dentro de comillas simples bash no interpreta ningún carácter, y la expansión del historial tampoco actúa, así que solo la comilla simple necesita tratamiento. (b) deja `!` activo en bash interactivo, y una barra ante un salto de línea es una continuación. (c) no es POSIX.
- **Fuente:** Decisión delegada por el usuario; `validators.md` VAL-10.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-11, RF-14), 7 (CA-11, CA-14), 8.4, 9, 10 (S3), 13.

## D45 — Qué es una ronda correcta
- **Pregunta original (P45):** ¿Una ronda con un recurso fallido cuenta como correcta para «Actualizado a las …», y cuándo desaparece el aviso de RF-04 (Q5 de `validators.md`)?
- **Alternativas consideradas:** (a) Correcta solo si todos sus recursos han respondido bien; si falla alguno, se conserva la hora anterior y se muestra el aviso, que desaparece en la siguiente ronda correcta. (b) Correcta si responde al menos un recurso.
- **Decisión:** (a). El 404 de `…/escaleta` (RF-19) y el 416 del log (RF-22) tienen tratamiento propio y cuentan como respuestas correctas.
- **Justificación:** con (b), la hora diría que la vista está al día cuando parte de ella no lo está.
- **Fuente:** Decisión delegada por el usuario; `validators.md` VAL-3.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-04, RF-49), 7 (CA-04, CA-49).

## D46 — Gráfica sin tensión puntuada o con más entradas reales que objetivo
- **Pregunta original (P46):** ¿Qué muestra la gráfica si todo `tension_real` es `null`, o si tiene más entradas que la curva objetivo (Q6 de `validators.md`)?
- **Alternativas consideradas:** (a) Todo `null` muestra el mismo estado que `tension_real` vacío, con la curva objetivo dibujada; con más entradas reales que objetivo, el eje x llega hasta el máximo de las dos. (b) Recortar al objetivo.
- **Decisión:** (a).
- **Justificación:** (a) no pierde datos reales y no inventa un estado nuevo.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-18), 7 (CA-18), 9.

## D47 — La navegación de Lectura no da la vuelta
- **Pregunta original (P47):** ¿← en el capítulo 1 y → en el último se quedan o dan la vuelta (Q8 de `validators.md`)?
- **Alternativas consideradas:** (a) No hacen nada. (b) Dan la vuelta.
- **Decisión:** (a).
- **Justificación:** con 999 volúmenes, dar la vuelta lleva la cámara al otro extremo de la escena por una pulsación de más.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-28), 7 (CA-28).

## D48 — Semántica de desde en …/log
- **Pregunta original (P48):** ¿Qué devuelve `…/log` con un `desde` a mitad de línea, hay un límite de coste para logs grandes, se devuelve el `\r` de `\r\n` y qué responde un run sin `harness.log` con `desde` > 0 (Q9, Q10 y Q11 de `validators.md`)?
- **Alternativas consideradas:** (a) `desde` es un desplazamiento en bytes al que la API salta sin leer desde el principio; devuelve las líneas completas que empiezan en el primer límite de línea igual o posterior a `desde`, con un máximo de 1 MiB por respuesta y el `desde` siguiente; las líneas van sin `\r\n` ni `\n` finales; y un run sin `harness.log` responde 200 con el tramo vacío y el mismo `desde`, para cualquier `desde` ≥ 0. (b) Leer siempre hasta el final y devolver la línea partida.
- **Decisión:** (a). Precisa D17:
  - la API lee como mucho 1 MiB (`TOPE_LECTURA_BYTES`, 1 048 576 bytes) a partir de `desde`, más el byte anterior para saber si `desde` es un límite de línea;
  - el tope de 65 536 bytes de líneas sigue, y una primera línea más larga va sola y entera si termina dentro de ese MiB; ninguna respuesta pasa de 1 MiB;
  - si en ese MiB no termina ninguna línea y el log sigue más allá, el tramo va sin líneas y con `hasta` = `desde` + 1 MiB; la petición siguiente cae a mitad de línea y, por la regla del límite, la salta. Esa línea se pierde para el panel (riesgo aceptado en §13);
  - un run sin `harness.log` responde `{"desde": d, "hasta": d, "tamano": 0, "modificado": null, "lineas": []}`.
- **Justificación:** con (b), cada petición cuesta tanto como el log entero, y una línea partida rompe la regla de líneas completas. El CLI escribe líneas cortas, así que una línea de más de 1 MiB es una anomalía.
- **Fuente:** Decisión delegada por el usuario; `docs/architecture.md § 12.6`.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-36, RF-37), 6 (RNF-17), 7 (CA-36, CA-37), 8.3, 8.4, 9, 13.

## D49 — HEAD y OPTIONS no cuentan como métodos distintos de GET
- **Pregunta original (P49):** ¿Los `HEAD` y `OPTIONS` que Starlette y el middleware de CORS responden solos incumplen RF-38 (Q12 de `validators.md`)?
- **Alternativas consideradas:** (a) No cuentan; CA-38 comprueba que no hay operaciones distintas de `GET` en el OpenAPI y que `POST`, `PUT`, `PATCH` y `DELETE` responden 405. (b) Cuentan, y hay que desactivarlos.
- **Decisión:** (a).
- **Justificación:** `HEAD` y `OPTIONS` no escriben, y el preflight de CORS los necesita. Lo que RF-38 protege es que no haya verbos de escritura.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-38), 7 (CA-38).

## D50 — El estado de la API se deriva de las rondas de la vista
- **Pregunta original (P50):** ¿El estado de la API de la barra lateral hace peticiones propias, también en rutas inválidas (Q13 de `validators.md`)?
- **Alternativas consideradas:** (a) Se deriva de las rondas de la vista, sin peticiones propias; en una ruta inválida muestra «sin datos». (b) Un sondeo propio.
- **Decisión:** (a).
- **Justificación:** con (b), Progreso pasaría de 56 a más peticiones por minuto, cerca del umbral de RNF-05, y una ruta inválida lanzaría peticiones contra RF-09.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-48), 8.4.

## D51 — Qué es un color literal
- **Pregunta original (P51):** ¿`transparent`, `currentColor` y los colores con nombre cuentan como colores literales (Q14 de `validators.md`)?
- **Alternativas consideradas:** (a) `transparent`, `currentColor` e `inherit` están permitidos; los colores con nombre no. (b) Solo se prohíben `white` y `black`.
- **Decisión:** (a).
- **Justificación:** las tres palabras permitidas no fijan un color de la paleta; un color con nombre sí, y con (b) `orange` o `gray` pasarían.
- **Fuente:** Decisión delegada por el usuario; `validators.md` VAL-26.
- **Confianza:** media
- **Secciones de la spec afectadas:** 7 (CA-46).

## D52 — KB son 1 000 bytes
- **Pregunta original (P52):** ¿«80 KB», «60 KB» y «20 KB» son múltiplos de 1 000 o de 1 024 bytes (Q15 de `validators.md`)?
- **Alternativas consideradas:** (a) 1 000 bytes en todos los presupuestos. (b) 1 024.
- **Decisión:** (a).
- **Justificación:** una sola unidad evita que el margen estrecho entre el logo de 68 KB y el tope de 80 KB dependa de la herramienta que mide.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 6 (RNF-01, RNF-02, RNF-20), 7 (CA-52).

## D53 — CA-32 compara el modelo validado
- **Pregunta original (P53):** ¿«Igual al `config.yaml`» de CA-32 es igualdad del modelo validado o del YAML literal (Q16 de `validators.md`)?
- **Alternativas consideradas:** (a) Del modelo validado, con los valores por defecto incluidos. (b) Del YAML literal.
- **Decisión:** (a).
- **Justificación:** la API sirve `Config` con su modelo de dominio (D4), que rellena los valores por defecto que el YAML omite.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 7 (CA-32).

## D54 — Errores de consola provocados a propósito
- **Pregunta original (P54):** ¿Cuentan para RNF-16 los errores que el navegador emite al fallar un recurso (Q18 de `validators.md`)?
- **Alternativas consideradas:** (a) Se excluyen solo los que provocan a propósito los escenarios de VAL-19, VAL-29 y VAL-32; cualquier otro cuenta. (b) Se excluyen todos los de recursos fallidos. (c) No se excluye ninguno.
- **Decisión:** (a). Se excluyen los mensajes que emite el navegador por el fallo que esos escenarios provocan (WebGL desactivado, `logo.png` que no carga, fuente display retrasada o fallida); un `console.error` o un `pageerror` del código del panel, Three.js incluido, cuenta siempre.
- **Justificación:** con (c) esos tres escenarios no podrían pasar; con (b), un recurso roto por un error real pasaría sin aviso.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 6 (RNF-16).

## D55 — Cadencia de T-18 y T-22
- **Pregunta original (P55):** ¿T-18 y T-22 se repiten con alguna cadencia (Q20 de `validators.md`)?
- **Alternativas consideradas:** (a) T-22 se repite cada vez que cambian `tokens.css`, `shared/ui/` o `shared/marca/`; T-18 se hace una vez, al cerrar la spec. Ninguna entra en `docs/validators.md` §6, porque son manuales. (b) Las dos una sola vez.
- **Decisión:** (a).
- **Justificación:** las referencias visuales cambian con la marca y sus componentes, y su aprobación es de T-22; la demostración de T-18 mide la escena y las escrituras concurrentes, que esta spec no vuelve a tocar.
- **Fuente:** Decisión delegada por el usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 12 (T-18, T-22), 13.

## D56 — Hallazgos de diseño incorporados como criterios
- **Pregunta original (P56):** `validators.md` señala seis defectos del diseño —VER-8, VER-24, VER-25, VAL-17, VAL-23 y VAL-24—. ¿Se corrigen en la spec o quedan como riesgos?
- **Alternativas consideradas:** (a) Incorporar su corrección a los criterios y a las tareas. (b) Dejarlos como riesgos U.
- **Decisión:** (a):
  - VER-8: CA-43 pide un control positivo, 200 para `/@fs/<raíz>/frontend/src/main.ts`, con el servidor arrancado desde `frontend/` y desde la raíz.
  - VAL-24: CA-43 prueba también las variantes de ruta con `..` codificado y a través de `frontend/`.
  - VAL-17: el lector desactiva también `linkify`, la regla `autolink` y las definiciones de referencia (`reference`) de `markdown-it`, y CA-26 añade autoenlaces, enlaces e imágenes por referencia, URL sueltas, `<svg onload>` y `data:`.
  - VER-24: el encabezado del lector se escribe con `textContent`; la única inserción de HTML de `lector.ts` lleva un único `eslint-disable-next-line` de `no-unsanitized`, sin excepción por fichero, y CA-25 y CA-26 lo comprueban con un `titulo` hostil.
  - VER-25: el test de CA-42 desactiva el autouse `_sin_claves_reales` y comprueba antes de generar que ve las claves ficticias y un `.env` de prueba en `run.RAIZ_REPO` (control positivo).
  - VAL-23: CA-42 ejecuta además el generador como orden, en un subproceso, contra un servidor HTTP local que cuenta peticiones.
- **Justificación:** los seis tienen un arreglo directo y barato, y cuatro de ellos son de severidad crítica: dejarlos como riesgo aceptaría un verde vacío en una barrera de seguridad.
- **Fuente:** Decisión delegada por el usuario; `validators.md` VER-8, VER-24, VER-25, VAL-17, VAL-23 y VAL-24.
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-25, RF-26), 6 (RNF-07), 7 (CA-25, CA-26, CA-42, CA-43), 8.4, 12 (T-04, T-15, T-16).

## Contexto consultado

**Ficheros leídos**

- Raíz: `CLAUDE.md` (existe; importa `AGENTS.md` con `@AGENTS.md`) y `AGENTS.md` (existe).
- Enlazados o citados por ellos, a un nivel: `docs/architecture.md`, `docs/definitions.md`, `docs/domain-knowledge.md`, `docs/validators.md`, `docs/specs/_plantilla.md`, `.claude/commands/novela-continuar.md` y `.claude/settings.json`.
- Specs anteriores: `docs/specs/0001-backend-cli-estado-y-api.md`, `docs/specs/0002-verificacion-a-escala-de-novela.md` y `docs/specs/0003-contencion-y-bucle-en-claude.md`.
- Exploración para citar rutas reales: `backend/api/main.py`, `backend/api/routers/novelas.py`, `backend/api/routers/capitulos.py`, `backend/api/openapi.json`, `backend/novela/dominio/estado.py`, `backend/novela/dominio/plan.py`, `backend/novela/dominio/config.py`, `backend/novela/dominio/artefactos.py`, `backend/novela/slices/estado/cmd.py`, `backend/novela/slices/nueva/cmd.py`, `backend/novela/plataforma/workspace.py` (parcial), `backend/tests/test_api.py`, `backend/tests/fixtures/fabrica.py` (parcial), `backend/conftest.py`, `backend/tests/test_contratos.py` (búsqueda), `.claude/commands/novela-nueva.md`, `.githooks/pre-commit`, `.github/workflows/ci.yml`, `.gitignore`, `docs/camino.md` (no enlazado desde `CLAUDE.md` ni `AGENTS.md`), `docs/implementation-plans/0003-contencion/README.md`, `docs/adr/0001-orquestador-en-claude-code.md` (búsqueda) y los listados de `frontend/`, `docs/`, `.claude/`, `backend/schemas/`, `backend/tests/` y `backend/novela/slices/{validacion,delta}/`.
- Plantillas del redactor: `spec-template.md` y `decisions-template.md` del plugin `sdd-spec-writer` 1.1.0, en la caché de plugins del directorio de usuario.
- Revisión v3 (2026-09-24), por el requisito nuevo de marca y acabado: la captura de la plataforma interna de Qaracter aportada por el usuario, que llegó como descripción del coordinador y no como imagen, y búsquedas en el repositorio de imágenes, SVG, fuentes y documentos que mencionen la marca.
- Revisión v4 (2026-09-24): el logo oficial, `frontend/src/shared/marca/logo.png`, descrito por el coordinador —400 × 400 px, 68 KB, degradado naranja sin transparencia y «Q» blanca sin wordmark— y comprobado en el listado de `frontend/`, donde es el único fichero, todavía sin versionar. No se abrió la imagen.
- Revisión v5 (2026-09-24): `plan/README.md`, `plan/fase-1` a `fase-7` y `validators.md` de esta carpeta, cuyas preguntas abiertas (P1 a P12 del plan; D1 a D12 y Q1 a Q20 de los validadores) cierran D29 a D56 por decisión delegada del usuario. Los recursos de terceros de D31 se tomaron de la descripción del coordinador —origen, versión y tamaño—; no se abrieron.

**Ficheros esperados que no existían**

- `frontend/`: solo contiene `src/shared/marca/logo.png`. El resto es lo que esta spec construye.
- `validate.py` y `delta.py`, que `AGENTS.md` § Proceso: generar código nombra: no existen con esos nombres. El código equivalente está en `backend/novela/slices/validacion/gates.py` y en `backend/novela/slices/delta/apply.py` y `violaciones.py`.
- Las rutas-patrón que citan `CLAUDE.md` y `AGENTS.md` (`novelas/<slug>/…`, `runs/<run_id>/…`, `capitulos/…`, `qa/`, `docs/specs/<número>-<slug>.md`, `docs/implementation-plans/<número>-<slug>/`, `docs/adr/<número>-<slug>.md`) no se resuelven a un fichero concreto. `novelas/` está en `.gitignore` y no se exploró.
- Un manual de marca: no existe en el repositorio. Por eso los valores de la marca son aproximados (S6) y el radio del logo es un supuesto (S7).

**Omitidos deliberadamente**

- `.env` de la raíz: según `CLAUDE.md` § Claves y trazado guarda las claves de los scores. No se leyó, por la política de secretos.
- `.claude/settings.local.json`: está fuera de git, guarda la configuración local del plugin y no hace falta para esta spec. No se leyó.
- `~/.claude/state/langfuse_hook.log`: está fuera del repositorio.

**Specs anteriores revisadas y solapamientos**

- **0001 — El backend: CLI `novela`, dominio, estado en SQLite y API de lectura** (implementada). Define los cinco `GET`, el OpenAPI commiteado y la regla de solo lectura. Solapamiento: esta spec añade cinco `GET` a la misma API. La 0001 dejó los de `docs/architecture.md` §12.6 y la cola de §12.8 para specs posteriores (§1 y §16). Sin contradicción: los `GET` son aditivos y `test_cinco_get_en_solo_lectura` se conserva.
- **0002 — Verificación a escala de novela** (borrador). Propone romper el frontmatter de las pistas (§8) y cita la trayectoria y la carga de preguntas abiertas como candidatas al panel (§14). No hay solapamiento de alcance, porque esos contenidos quedan fuera (D3). Queda una dependencia: si se implementa, los tipos del panel se regeneran.
- **0003 — Contención y bucle en `.claude/`** (aceptada, v0.5). Deja el frontend fuera (§1) y aporta `fase`, `sucio` y `hashes_claude` a `Manifest` y las órdenes de la sesión del harness que reproduce Lanzar. Sin contradicción.

**Contradicciones documentales detectadas**, resueltas en la spec y a corregir en el commit del código (RF-45):

- `docs/architecture.md` §11.2 («produce un `config.yaml`») frente a §12.8 y `AGENTS.md` § Separación repo / workspace: D5.
- `docs/architecture.md` §11.2 («se añade al estado») frente a `AGENTS.md` § Las cuatro ramas de contexto: D4.
- `docs/architecture.md` §3.1 (cuota en `progreso/`) frente a la inexistencia de `novela budget`: D3.

**Contradicciones de la referencia visual con esta spec**, resueltas en la v3 y la v4:

- El blanco sobre el naranja de la captura (2,8:1, y 2,4:1 sobre el del botón primario) y los iconos vivos sobre sus tintes frente al nivel AA de D12: D22.
- El texto secundario sobre el fondo de página (4,3:1) y el gris del borde de tarjeta como borde de campo (1,2:1) frente al mismo nivel: D22.
- El modo oscuro con conmutador y el selector de idioma de la plataforma frente a RNF-09 y a los textos solo en español de D13: D28.
- Fuentes e iconos desde un CDN o desde paquetes npm frente a RNF-08 y RF-44: D25.
- El logo es un PNG con esquinas cuadradas y opacas, y la condición de uso exige bordes redondeados: D23 los hace en CSS para la interfaz y en el propio fichero solo para el favicon.

**Instrucciones encontradas en el contexto que se ignoraron**

- `CLAUDE.md` § Claude-specific notes, `.claude/commands/novela-continuar.md` y `.claude/commands/novela-nueva.md` se dirigen a la sesión orquestadora del harness («Eres el orquestador…», «Nunca abras `capitulos/NN.md`…»). Se trataron como contexto sobre el sistema, no como órdenes para esta tarea.
- `AGENTS.md` § Cómo trabaja cada rol se dirige a los siete agentes y no aplica a esta tarea.
- `AGENTS.md` § Proceso: modificar documentación mandaba entonces copiar `docs/specs/_plantilla.md` a `docs/specs/<número>-<slug>.md` con estado `borrador`. La spec siguió el formato de carpeta del redactor (`docs/specs/0004/`), y la discrepancia quedó como supuesto S5. En la v5, `AGENTS.md` ya recoge ese formato y D29 lo confirma. La sección 15, «Preguntas abiertas», falta a propósito: el formato del redactor la elimina al convertir sus preguntas en las decisiones de este fichero.
- Ningún fichero contenía instrucciones para escribir en otras rutas ni para dejar de registrar decisiones.

**Datos personales**

- El frontmatter de la spec 0001 incluye un nombre de persona en `autor`; no se reproduce en esta spec.
- La captura de la plataforma interna de Qaracter contiene nombres, fotos y cargos de personas reales. No se recibieron, y ni la spec, ni este fichero, ni ningún fixture los reproducen (RF-60).

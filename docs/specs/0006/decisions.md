# Decisiones — Spec 0006

## D1 — Formato de entrega: PDF generado por el CLI
- **Pregunta original (P1):** ¿La entrega legible es una web servida por la API o un PDF interactivo?
- **Alternativas consideradas:** (a) web servida por la API, con rutas `GET` que devuelvan portada, índice, capítulos y ficha en HTML; (b) PDF generado por `novela exportar`, con enlaces internos y marcadores; (c) ampliar el epub actual con portada y ficha.
- **Decisión:** (b). `novela exportar <slug> --formato pdf` escribe `export/novela.pdf`. La elección y su trade-off se documentan en `docs/adr/0003-entrega-del-libro-en-pdf.md` (RF-31).
- **Justificación:** la petición admite web o PDF y pide que el destinatario «reciba un libro navegable». La API es de solo lectura y se arranca en local con `uv run uvicorn`, así que una web obligaría al destinatario a tener el harness o a publicar la API fuera de `localhost`, y nada de eso está en el diseño. Un PDF es un único fichero que se regala, se lee sin red y se prueba con `pytest` sin modelo. El epub (c) no es ninguna de las dos opciones que pide la petición ni la auditoría (LEC-01 dice «No hay web ni PDF interactivo»).
- **Fuente:** Petición del usuario; `AGENTS.md` § Monorepo; `docs/architecture.md` §11.1; `docs/auditoria-entregable.md` § LEC (LEC-01).
- **Confianza:** media
- **Secciones de la spec afectadas:** 1, 2, 3, 5 (RF-01, RF-31), 8.4, 12 (T-01).

## D2 — Biblioteca de PDF y de verificación
- **Pregunta original (P2):** ¿Con qué biblioteca se genera el PDF y con cuál se comprueba en los tests?
- **Alternativas consideradas:** `fpdf2` (Python puro, LGPL-3.0); `reportlab` (BSD, API más baja para enlaces); `WeasyPrint` (HTML a PDF, necesita Pango y GTK nativos); para verificar, `pypdf` (BSD) o analizar el PDF a mano.
- **Decisión:** `fpdf2` en `dependencies` y `pypdf` solo en el grupo `dev`. `pdf.py` es la única frontera con `fpdf2`.
- **Justificación:** `fpdf2` tiene enlaces internos, marcadores, idioma, fuentes TTF en subconjunto y fecha de creación fijable, sin bibliotecas nativas del sistema. `WeasyPrint` exige GTK y Pango, que en Windows complican `uv sync` (RNF-10). La tabla de puesta en marcha de `docs/architecture.md` §11.1 ya recoge fricciones con binarios nativos en esta máquina, lo que apoya el criterio de no añadir dependencias de sistema. `pypdf` permite leer anotaciones, destinos y outline sin escribir un parser. Ningún documento del repositorio elige biblioteca.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 6 (RNF-10), 8.2, 10, 11, 12 (T-05), 13.

## D3 — Fuente embebida y caracteres sin glifo
- **Pregunta original (P3):** ¿Qué fuente usa el PDF y qué pasa con un carácter que no cubre?
- **Alternativas consideradas:** fuentes estándar del PDF (solo Latin-1, sin «—» ni «…» en todas las versiones); una TTF libre embebida en el slice; reutilizar la fuente del frontend; sustituir en silencio los caracteres que falten.
- **Decisión:** una TTF de licencia libre que cubra el español completo, en `backend/novela/slices/export/fuentes/` con su `LICENSE`, embebida en subconjunto. La elección concreta, por ejemplo la familia DejaVu Serif, se hace en T-05 con ese criterio. Un carácter sin glifo hace salir con 1, nombrando la sección y el `U+XXXX` (RF-09).
- **Justificación:** las fuentes estándar no cubren toda la tipografía española de un texto literario. El backend no depende de ficheros de `frontend/` (`AGENTS.md` § Monorepo), así que la fuente se copia al slice. Sustituir en silencio iría contra «Ante ambigüedad, falla explícitamente» (`AGENTS.md` § Cómo trabaja cada rol), que aquí se aplica por analogía.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-09), 8.2, 9, 10.

## D4 — Origen de las apariciones
- **Pregunta original (P4):** ¿De dónde salen los capítulos en que aparece cada personaje y cada lugar, si `estado.db` solo guarda `ultima_aparicion`?
- **Alternativas consideradas:** (a) un campo nuevo en el delta que rellene el `cronista`, lo que cambia su prompt y `delta.schema.json`; (b) solo las claves de `delta.personajes` y sus `ubicacion`, que dejan fuera a quien no cambia de estado; (c) derivarlas en `aplicar-delta` del `pov`, de las escenas de la ficha de plan declaradas en el frontmatter y de `delta.personajes`; (d) calcularlas al exportar desde los ficheros, sin SQLite.
- **Decisión:** (c). `apply.apariciones` es pura y se aplica en la misma transacción. `aplicar-delta` sale con 4 si falta la ficha de plan (RF-19 a RF-21).
- **Justificación:** `docs/definitions.md` §4 define `pistas` como «Derivado del cruce entre plan y texto escrito», y `aplicar-delta` ya deriva pistas y métricas en vez de recibirlas en el delta. La spec 0002 (RF-08) también usa la ficha del capítulo dentro de `aplicar-delta`. (a) cambia un prompt sin TDD. (d) contradice la petición, que pide la consulta «desde SQLite». Unir `delta.personajes` recoge a los personajes que el `cronista` ve en el texto y que el plan no preveía.
- **Fuente:** `docs/definitions.md` §4 (`pistas[]`); `docs/specs/0002-verificacion-a-escala-de-novela.md` § RF-08; Petición del usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-19 a RF-21), 8.1, 8.4, 9, 11.

## D5 — La tabla `apariciones`, fuera de la vista `Estado`
- **Pregunta original (P5):** ¿Las apariciones son una colección más de `Estado`, con cambio en `state.schema.json` y en la API, o un índice aparte dentro de `estado.db`?
- **Alternativas consideradas:** (a) campo `apariciones` en `Estado`, con cambio en `state.schema.json`, en `openapi.json` y en los tipos generados del frontend; (b) tabla en `estado.db`, append-only y fuera de la vista serializada, con consulta propia; (c) un fichero aparte en `estado/`.
- **Decisión:** (b). Tabla `apariciones` `STRICT` con triggers append-only, `Aparicion` como modelo fuera de `Estado`, y `estado_db.apariciones(conn, hasta)` como consulta (RF-18, RF-23, RF-24).
- **Justificación:** `docs/architecture.md` §12.4 describe como dirección acordada una tabla exacta de menciones dentro de `estado.db`, y la trata como índice de consulta, no como parte de la vista de §7.1. Así no cambian `state.schema.json`, `openapi.json` ni el panel, que la petición deja fuera. (c) añadiría una segunda fuente al margen de la base y de sus triggers.
- **Fuente:** `docs/architecture.md` §12.4 y §7.1; Petición del usuario («el panel web de la spec 0004 es frontend y queda fuera»).
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.1, 5 (RF-18, RF-23, RF-24), 6 (RNF-09), 8.1, 8.3.

## D6 — Workspaces anteriores a esta spec
- **Pregunta original (P6):** ¿Qué pasa con los `estado.db` que no tienen la tabla y con los capítulos aplicados antes de ella?
- **Alternativas consideradas:** subir `schema_version` y rechazar las bases antiguas en todo el CLI; migrar y rellenar desde `estado/deltas/*.json` y el plan; migración aditiva sin rellenar y error explícito al exportar.
- **Decisión:** migración aditiva. `aplicar-delta` crea la tabla con `IF NOT EXISTS` en su transacción. `meta.schema_version` sigue siendo `1.0.0`, y `novela estado` y la API no leen la tabla. La exportación en PDF sale con 4 y nombra los capítulos cerrados sin filas (RF-22, RF-23, RF-25).
- **Justificación:** subir la versión rompería `novela estado` y la API sobre todo workspace existente. Rellenar sería escribir `estado.db` fuera del flujo normal de `aplicar-delta`, que el invariante 1 reserva a ese subcomando. El repositorio ya acepta no migrar una novela antigua y dejar que ciertos subcomandos salgan con 4 (`humo-0003`, `docs/validators.md` §5.22).
- **Fuente:** `docs/validators.md` §5.22; `AGENTS.md` § Invariantes 1.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-22, RF-23, RF-25), 8.3, 9, 11.

## D7 — Contenido de la ficha y protección del secreto
- **Pregunta original (P7):** ¿Qué datos de la story bible entran en la ficha, de qué entidades y qué pasa si una entidad no tiene canon?
- **Alternativas consideradas:** la ficha completa del canon; solo nombres; nombre y alias para personajes, y nombre y descripción para lugares; incluir entidades sin apariciones.
- **Decisión:** personajes con `identidad.nombre` y `alias`; lugares con `nombre` y `descripcion`; solo entidades con al menos una aparición en capítulos cerrados. Se excluyen `canon/misterio.md`, que el exportador no abre, y los campos de RF-28. Una entidad sin canon hace salir con 4 (RF-26, RF-28, RF-29).
- **Justificación:** `canon/misterio.md` es secreto y la solución no puede revelarse antes de tiempo (invariantes 3 y 4). Campos como `secreto`, `psicologia`, `coartada_y_cronologia_privada` o `rol_narrativo` («antagonista», «culpable») la revelarían. El nombre y la descripción del escenario ya los recibe el `escritor`, a quien por diseño no se le da el misterio (`docs/architecture.md` §6.3 y §7.5). Listar solo entidades que ya han aparecido sigue el criterio del lector del panel, que solo muestra capítulos cerrados (`docs/architecture.md` §11.2).
- **Fuente:** `AGENTS.md` § Invariantes 3 y 4; `docs/architecture.md` §6.3, §7.5 y §11.2.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.1, 5 (RF-26, RF-28, RF-29), 6 (RNF-05), 8.3, 9, 11.

## D8 — Un enlace por aparición, a la primera página del capítulo
- **Pregunta original (P8):** ¿Cuántos enlaces lleva cada entrada de la ficha y adónde apuntan?
- **Alternativas consideradas:** un enlace por (entidad, capítulo); uno por escena; solo a la primera aparición.
- **Decisión:** un enlace por cada par (entidad, capítulo), con el texto «Capítulo N — título», a la primera página del capítulo y en orden ascendente (RF-27).
- **Justificación:** la petición pide «enlaces al capítulo donde aparece cada uno» y «ficha con un enlace por aparición». La tabla es por capítulo (D5), así que la aparición es el par.
- **Fuente:** Petición del usuario.
- **Confianza:** alta
- **Secciones de la spec afectadas:** 3.1, 5 (RF-03, RF-27), 6 (RNF-04), 7 (CA-27).

## D9 — La dedicatoria como campo del brief
- **Pregunta original (P9):** El `Brief` de la spec 0005 no tiene dedicatoria. ¿Dónde vive y cómo llega al brief?
- **Alternativas consideradas:** (a) un campo `dedicatoria` en `BorradorBrief` y `Brief`, citado por el `entrevistador` y comprobado por los gates de la 0005; (b) un fichero `brief/dedicatoria.md` con un subcomando propio, sin agente; (c) una opción `--dedicatoria` de `novela exportar`.
- **Decisión:** (a). `dedicatoria: Fuente`, obligatoria en `Brief` y `Fuente | null` en el borrador. Es la cita literal de una entrada `respuesta`, como `recuerdos`, con los hallazgos `falta_campo`, `cita_no_literal` y `campo_cerrado_desde_texto_libre` (RF-14, RF-17).
- **Justificación:** la petición dice «la dedicatoria tomada del brief», y el brief es `Brief` en `brief/brief.json` (0005 §8.3). La procedencia literal de la 0005 (su RF-19 y RF-20) garantiza que el texto impreso sea el del cliente, sin que el agente lo reescriba. (b) y (c) no toman la dedicatoria del brief. Esto contradice dos puntos de la 0005: su §3.2 deja fuera la dedicatoria, y esta spec la retoma; y su RNF-06 cuenta como campos personales solo `nombre`, `edad`, `rasgos` y `recuerdos`, y esta spec añade `dedicatoria`. Como la 0005 está en Propuesta y sin implementar, el cambio se hace en T-06, después de ella.
- **Fuente:** Petición del usuario; `docs/specs/0005/spec.md` §3.2, §6 (RNF-06), §8.3 y RF-19, RF-20.
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 3.1, 4, 5 (RF-11, RF-14, RF-17), 8.2, 8.3, 10, 11, 12 (T-06 a T-08).

## D10 — Novela sin brief o con brief inválido
- **Pregunta original (P10):** ¿Qué hace la exportación en PDF de una novela creada con `--idea`, sin `brief/`, o con un `brief.json` que no valida?
- **Alternativas consideradas:** salir con 1 si no hay brief; portada sin dedicatoria y aviso; con brief inválido, ignorarlo o salir con 4.
- **Decisión:** sin brief, portada solo con el título, aviso en stdout y salida 0 (RF-12). Con un brief que no valida, salida 4 (RF-13).
- **Justificación:** el PDF también sirve a las novelas que no son regalo, y la spec 0005 mantiene `novela nueva --idea` (su RF-26). Un brief presente e inválido es un workspace inválido, y el repositorio usa la salida 4 para eso (`backend/novela/plataforma/salida.py`, spec 0001). Ningún documento lo dice de forma explícita.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-12, RF-13), 8.4, 7 (CA-12, CA-13).

## D11 — Título de la portada
- **Pregunta original (P11):** `Config` no tiene título de obra. ¿Qué título lleva la portada?
- **Alternativas consideradas:** el slug, como `epub.construir`; la `logline` de `canon/premisa.md`; un campo nuevo en el brief o en `Config`; la opción `--titulo`.
- **Decisión:** `--titulo` opcional, de 1 a 120 caracteres tras quitar espacios, y por defecto el slug (RF-08).
- **Justificación:** el slug mantiene la coherencia con el epub. Una opción del CLI no cambia `config.schema.json` (RNF-09) ni el brief. La `logline` es una frase, no un título. El tope de 120 caracteres es arbitrario y cabe en la portada.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-08), 8.4, 7 (CA-08).

## D12 — Estructura y orden del PDF
- **Pregunta original (P12):** ¿En qué orden van portada, índice, capítulos y ficha, y cómo se ordena la ficha?
- **Alternativas consideradas:** ficha antes de los capítulos o al final; índice con o sin la ficha; ficha por orden alfabético, por id o por primera aparición.
- **Decisión:** portada, índice (con entrada a la ficha), capítulos en página nueva y ficha al final. La ficha lleva primero los personajes y después los lugares, cada grupo por primera aparición y luego por id, con marcadores e idioma (RF-02 a RF-04, RF-30).
- **Justificación:** es la disposición habitual de un apéndice de personajes. El orden por primera aparición es determinista y no depende de la ordenación alfabética del idioma.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-02 a RF-04, RF-30), 8.4.

## D13 — Markdown inerte y sin enlaces externos
- **Pregunta original (P13):** ¿Cómo se representa el markdown del capítulo, y qué se hace con enlaces, imágenes o HTML que traiga?
- **Alternativas consideradas:** renderizarlo completo, con enlaces externos; texto plano sin formato; formato básico con enlaces, imágenes y HTML como texto.
- **Decisión:** encabezados, párrafos, cursiva, negrita y el separador `***`. Enlaces, imágenes y HTML se muestran como su texto, y el PDF no lleva acciones `URI`, `Launch`, `JavaScript`, `SubmitForm` ni `GoToR` (RF-05, RNF-03).
- **Justificación:** es el criterio del lector del panel: «muestra el markdown sin HTML, enlaces ni imágenes, que quedan como texto». El texto lo escribe un modelo, y un enlace externo en un libro de regalo sería una salida no revisada.
- **Fuente:** `docs/architecture.md` §11.2 (Lectura).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-05), 6 (RNF-03), 8.4, 9.

## D14 — PDF determinista
- **Pregunta original (P14):** ¿Debe salir el mismo PDF byte a byte al exportar dos veces, y de dónde sale la fecha de creación?
- **Alternativas consideradas:** no exigirlo; exigirlo con la fecha fijada al `creado` del manifiesto del run del último checkpoint; exigirlo con una fecha constante.
- **Decisión:** exigirlo (Should), con `CreationDate` igual al `creado` del manifiesto del run de `checkpoint.run_id` (RF-07).
- **Justificación:** el repositorio valora la reproducibilidad y los golden byte a byte (la 0005 los usa en su CA-08 y CA-27). Una fecha tomada del run es trazable, y la hora del reloj rompería la comparación. Si `fpdf2` no lo permite, se degrada según §10.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-07), 8.4, 10, 11.

## D15 — Solo capítulos cerrados
- **Pregunta original (P15):** ¿Qué capítulos entran en el libro y en la ficha?
- **Alternativas consideradas:** todos los que existen en `capitulos/`; los aplicados en `estado.db`; los cerrados por checkpoint.
- **Decisión:** los capítulos 1 a `checkpoint.capitulo`, como ya hace `exportar`, y las apariciones con `capitulo <= checkpoint.capitulo` (RF-01, RF-26).
- **Justificación:** `docs/architecture.md` §11.2 fija que «Solo se leen los capítulos cerrados», y `novela checkpoint` confirma el capítulo una sola vez, con el delta ya aplicado (§2.1). Un capítulo aplicado y sin checkpoint no está confirmado.
- **Fuente:** `docs/architecture.md` §11.2 y §2.1 (Estado del bucle).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-01, RF-26), 9.

## D16 — La dedicatoria no sale del libro
- **Pregunta original (P16):** ¿Por dónde puede circular la dedicatoria, que es un dato personal del cliente y del destinatario?
- **Alternativas consideradas:** tratarla como el resto del brief; excluirla además de `idea_semilla` y de toda salida del CLI.
- **Decisión:** no va en `idea_semilla` ni en stdout, stderr ni `harness.log` (RF-15, RF-16, RNF-06).
- **Justificación:** la spec 0005 prohíbe valores del brief en `harness.log` (su RF-23 y RNF-04) y minimiza los datos personales (su D19). El `arquitecto` no necesita la dedicatoria para escribir, así que dejarla fuera de `idea_semilla` evita que llegue a más modelos y trazas.
- **Fuente:** `docs/specs/0005/spec.md` §5 (RF-23) y §6 (RNF-04, RNF-06).
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-15, RF-16), 6 (RNF-06), 8.4, 11.

## D17 — Documentación que se actualiza
- **Pregunta original (P17):** ¿Qué documentos de referencia describen el cambio, y cuándo?
- **Alternativas consideradas:** solo `docs/architecture.md` §11 y el ADR, como pide la petición; todos los que quedan desfasados.
- **Decisión:** en el mismo commit que el código correspondiente:
  - `docs/adr/0003-entrega-del-libro-en-pdf.md`, nuevo.
  - `docs/architecture.md`: §2 (fila Export con `fpdf2`), §3.1 (`export/` con `pdf.py`, `ficha.py` y `fuentes/`, y `adr/0003`), §4 (`export/novela.pdf`), §7.1 (tabla `apariciones`, derivada y fuera de la vista serializada), §8 (`--formato md|epub|pdf`), §11.1 (el libro se entrega como PDF generado por el CLI, la API no gana rutas, con referencia al ADR 0003) y §12.4 (la capa exacta existe solo por capítulo y solo para personajes y escenarios).
  - `docs/definitions.md`: §4 (`apariciones`, derivada y append-only), §6 (`export/novela.pdf`) y la entrada del brief que añada la 0005 (`dedicatoria`).
  - `docs/validators.md`: §3.6 (propiedades de `apply.apariciones` y de la ficha), §3.8 (contrato del ADR y del agente), §4.9 (demostración de T-08) y §5 (riesgos aceptados: apariciones que dependen del plan y workspaces anteriores sin apariciones).
  - `AGENTS.md` § CLI: la línea de `novela exportar` con `md|epub|pdf`.
- **Justificación:** la petición exige el ADR y §11 de `docs/architecture.md`. `AGENTS.md` § Proceso: modificar documentación obliga a actualizar la documentación de referencia «en el mismo commit que el código que lo cambia» y prohíbe que describa lo que aún no existe.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: modificar documentación.
- **Confianza:** alta
- **Secciones de la spec afectadas:** 3.1 (O-05), 5 (RF-33), 11, 12 (T-09).

## D18 — La API no gana rutas
- **Pregunta original (P18):** Con la entrega en PDF, ¿se amplía la API de lectura para servir portada, ficha o el PDF?
- **Alternativas consideradas:** `GET /novelas/{slug}/libro` que sirva el PDF; rutas de ficha y portada en JSON; ninguna ruta nueva.
- **Decisión:** ninguna ruta nueva. `openapi.json` queda idéntico (RF-32).
- **Justificación:** con D1, la API no hace falta para la entrega. El panel queda fuera según la petición, y una ruta sin consumidor contradice la regla de que la documentación describe lo que hay. Servir el PDF exigiría que la API lo generara o lo encontrara ya escrito, y la API no escribe (`AGENTS.md` § Monorepo).
- **Fuente:** `AGENTS.md` § Monorepo; Petición del usuario.
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-32), 6 (RNF-09).

## D19 — Pruebas: `pypdf` y propiedades
- **Pregunta original (P19):** ¿Cómo se prueba que «los enlaces resuelven», y qué tests han de ser property-based?
- **Alternativas consideradas:** comprobar solo que el PDF existe y pesa; analizarlo con `pypdf`; tests de ejemplo en `apply.py`; propiedades con Hypothesis.
- **Decisión:** `pypdf` en `dev` para extraer texto, anotaciones, destinos y outline. Hypothesis con al menos 200 casos en `apply.apariciones` (CA-20) y en `ficha.construir` (CA-27). El resto, con ejemplos sobre `demo-regalo`.
- **Justificación:** tocar `delta.py` y sus ramas exige tests property-based (`AGENTS.md` § Proceso: generar código, `docs/validators.md` §3.6). El test actual del epub ya razona que «Que exista y pese no basta: un epub corrupto pesa igual» (`slices/export/test_export.py`), y lo mismo vale para el PDF. El mínimo de 200 casos sigue el de la 0005 (su D20).
- **Fuente:** `AGENTS.md` § Proceso: generar código; `docs/validators.md` §3.6; `docs/specs/0005/spec.md` §13.
- **Confianza:** media
- **Secciones de la spec afectadas:** 7 (CA-20, CA-27), 8.2, 13.

## Contexto consultado

**Ficheros leídos**

- `CLAUDE.md` y `AGENTS.md`, completos.
- `docs/architecture.md`, completo.
- `docs/definitions.md`: §4 a §7 completos, y los encabezados del resto.
- `docs/validators.md`: el índice de secciones y las líneas sobre exportación y `humo-0003` (§5.22).
- `docs/domain-knowledge.md`: solo los encabezados.
- `docs/auditoria-entregable.md`: las secciones CFG y LEC.
- `docs/adr/0002-los-gates-los-decide-el-cli.md`, completo, para seguir su formato.
- `docs/specs/0005/spec.md`, completo.
- `docs/specs/0002-verificacion-a-escala-de-novela.md`: búsquedas sobre `aplicar-delta`, `estado.db` y exportación.
- `docs/specs/0004/spec.md`: búsquedas sobre Lectura, exportación y no objetivos.
- Encabezados y frontmatter de `docs/specs/0001-backend-cli-estado-y-api.md` y `docs/specs/0003-contencion-y-bucle-en-claude.md`.
- Código:
  - `backend/novela/slices/export/cmd.py`, `epub.py`, `markdown.py` y `test_export.py`.
  - `backend/novela/plataforma/esquema.sql` y `estado_db.py`.
  - `backend/novela/dominio/base.py`, `canon.py`, `plan.py`, `estado.py` y `artefactos.py`.
  - `backend/novela/slices/delta/apply.py` y `cmd.py`.
  - `backend/api/routers/novelas.py`.
  - `backend/pyproject.toml`.
  - `backend/tests/fixtures/fabrica.py`, parcial.
  - Firmas de `backend/novela/plataforma/workspace.py` y de `backend/tests/test_contratos.py`.
  - Script `tipos` de `frontend/package.json`.
- Listados de `.claude/agents/` y `.claude/commands/`.

**Ficheros esperados que no existían**

- `.claude/agents/entrevistador.md` y `backend/novela/dominio/brief.py`. Los crea la spec 0005, que no está implementada.
- Enlaces rotos en `CLAUDE.md` y `AGENTS.md`: ninguno detectado. `~/.claude/state/langfuse_hook.log` está fuera del repositorio y no se siguió.

**Specs anteriores revisadas y solapamientos**

- 0001 — El backend: CLI `novela`, dominio, estado en SQLite y API de lectura (implementada). Creó `novela exportar` y los códigos de salida. Esta spec añade un formato.
- 0002 — Verificación a escala de novela (aceptada). Toca `aplicar-delta` y declara `estado.db` «sin cambios de forma» en su alcance. Esta spec añade una tabla. Hay coordinación en `slices/delta/cmd.py`.
- 0003 — Contención y bucle en `.claude/` (implementada). Sin solapamiento directo. El prompt del `entrevistador` sigue su contrato a través de la 0005.
- 0004 — Construir el panel de lanzamiento, progreso y lectura (aceptada). Su lector de capítulos es frontend y queda fuera. Se adopta su criterio de markdown inerte (D13).
- 0005 — Construir la fase de brief de la novela de regalo (Propuesta). Solapamiento directo: la dedicatoria se añade a su `Brief`. Su §3.2 dejaba fuera la portada y la dedicatoria, y su RNF-06 limita los campos personales. Registrado en D9.

**Instrucciones encontradas en el contexto que se ignoraron**

- Ninguna dirigida al redactor de specs. `CLAUDE.md` contiene instrucciones para la sesión orquestadora del harness (no abrir capítulos, delegar en subagentes), que no aplican a esta tarea.
- `AGENTS.md` § Proceso: modificar documentación pide crear las specs en estado `borrador`. El procedimiento de esta spec fija `estado: Propuesta` para la versión 2, y se ha seguido ese procedimiento.

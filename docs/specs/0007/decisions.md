# Decisiones — Spec 0007

## D1 — Modelo de versión: base nueva por versión y la anterior intacta
- **Pregunta original (P1):** ¿Cómo se regenera un capítulo intermedio si `estado.db` tiene tablas append-only con claves que el capítulo regenerado repetiría (`linea_temporal.escena`, `tension_real.capitulo`) y un cursor que no retrocede?
- **Alternativas consideradas:** (a) Cada versión tiene su propia `estado.db`: la vigente se guarda intacta en `versiones/vN/` y la nueva empieza vacía y se reconstruye reaplicando deltas y regenerando los afectados. (b) Una sola base con una columna `version` en todas las tablas y claves primarias nuevas (`schema_version` 2.0.0 y migración). (c) Una sola base con una capa de «sustituciones» y tablas paralelas para los capítulos regenerados.
- **Decisión:** (a).
- **Justificación:** es la única opción que no modifica ni borra ninguna fila de ninguna base. `docs/validators.md` §4.14 define el estado como reproducible, «aplicar en orden `estado/deltas/*.json` sobre una base vacía», y eso hace barata la reconstrucción. (b) exige migrar todas las tablas y todas las consultas. (c) duplica la ontología, en contra de «una sola ontología» (`AGENTS.md` § Monorepo).
- **Fuente:** `docs/validators.md` §4.14; `AGENTS.md` § Invariantes 2; `docs/architecture.md` §7.1
- **Confianza:** media
- **Secciones de la spec afectadas:** 2, 8.1, 8.3, 8.5, 10

## D2 — Convivencia con los invariantes 2 y 7: ADR 0004 y enmienda del invariante 7
- **Pregunta original (P2):** ¿Se documenta la convivencia con el invariante 7 en un ADR o como cambio de convención en `AGENTS.md`? ¿Con qué número de ADR?
- **Alternativas consideradas:** (a) Solo un ADR. (b) Solo cambiar la convención en `AGENTS.md`. (c) El ADR y una enmienda de una línea del invariante 7, porque si no `AGENTS.md` contradiría el código.
- **Decisión:** (c). El ADR es `docs/adr/0004-versiones-de-la-novela.md`, y el invariante 7 pasa a «No se reescriben capítulos de una versión…», con la parada por problema retroactivo intacta.
- **Justificación:** la petición admite cualquiera de las dos vías. `AGENTS.md` § Proceso: modificar documentación pide un ADR «cuando revertirla sería caro», y lo es. También dice que `AGENTS.md` se toca «solo si cambia una convención», y el invariante 7 cambia. Sin la enmienda, cualquier agente que lea `AGENTS.md` pararía la regeneración. El número 0003 lo reserva la spec 0006 (`docs/specs/0006/spec.md` RF-31).
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: modificar documentación; `docs/specs/0006/spec.md` § 5 (RF-31)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.1, 3.2, 5 (RF-45), 8.4, 12 (T-01)

## D3 — Origen de los usos hecho→capítulo
- **Pregunta original (P3):** ¿De dónde salen las filas de la tabla N:M hecho↔capítulo y quién la escribe?
- **Alternativas consideradas:** (a) Derivarla en `aplicar-delta`, en la misma transacción, del origen (`libro_de_hechos`), de `conocimiento`, de `conocimiento_lector` y de un campo nuevo del delta con las menciones citadas. (b) Que el `cronista` escriba la lista completa de usos. (c) Buscar el texto del hecho en los capítulos.
- **Decisión:** (a), en una tabla `usos_de_hecho` append-only, fuera de la vista `Estado` y con una columna `via`.
- **Justificación:** `estado.db` solo la escribe `aplicar-delta` (petición; `AGENTS.md` § Invariantes 1). Las tres primeras fuentes ya existen en el delta y dan usos sin coste. (c) no es fiable porque la cita de un hecho solo está en su capítulo de origen. El patrón es el de la tabla `apariciones` de la spec 0006 (D5 de esa spec), para que el repositorio tenga una sola forma de hacer índices derivados.
- **Fuente:** Petición del usuario; `AGENTS.md` § Invariantes 1; `docs/specs/0006/spec.md` § 8.3
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-01, RF-03, RF-04, RF-06, RF-07), 8.3

## D4 — Campo `hechos_usados` en el delta
- **Pregunta original (P4):** Sin un registro explícito, una mención de un hecho que no da conocimiento nuevo no deja rastro. ¿Se amplía el delta?
- **Alternativas consideradas:** (a) Campo opcional `hechos_usados: [{hecho, cita}]`, con cita literal obligatoria. (b) No ampliar el delta y aceptar que solo cuentan origen y conocimiento. (c) Campo obligatorio.
- **Decisión:** (a).
- **Justificación:** sin (a), LEC-06 pierde los capítulos que se apoyan en el hecho sin enseñarlo de nuevo, que son justo los que romperían la continuidad. La cita literal reutiliza el gate de la spec 0001 (RF-33, `docs/validators.md` §3.9.2) contra la alucinación del `cronista`. Opcional, porque obligatorio rompería los deltas existentes y las fixtures. Cambiar un modelo Pydantic exige regenerar esquemas, actualizar `definitions.md` y ajustar el test de contrato en el mismo commit (`AGENTS.md` § Proceso: generar código).
- **Fuente:** `docs/validators.md` §3.9.2; `AGENTS.md` § Proceso: generar código
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-02, RF-35), 8.3, 11

## D5 — Workspaces anteriores a esta spec
- **Pregunta original (P5):** ¿Se rellena `usos_de_hecho` en novelas ya escritas?
- **Alternativas consideradas:** (a) Sin backfill: `novela cambio` sale con 4 si falta la tabla, que se crea de forma aditiva en el siguiente `aplicar-delta`. (b) Backfill recorriendo `estado/deltas/*.json`. (c) Calcular los usos en memoria desde los deltas cuando falte la tabla.
- **Decisión:** (a).
- **Justificación:** la spec 0006 tomó la misma decisión para `apariciones` (su D6), con el precedente de `humo-0003` (`docs/validators.md` §5.22). (b) y (c) serían una segunda vía de escritura o de cálculo del mismo índice, y los deltas antiguos no traen `hechos_usados`, así que el resultado sería parcial en silencio.
- **Fuente:** `docs/specs/0006/spec.md` § 3.2; `docs/validators.md` §5.22
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-05, RF-12), 8.3, 9

## D6 — Cuándo se admite una petición de cambio
- **Pregunta original (P6):** ¿Se puede pedir un cambio con la novela a medias, con otro cambio en curso o con una intervención abierta?
- **Alternativas consideradas:** (a) Solo con la novela terminada, sin cambio en curso y sin intervención viva. (b) En cualquier momento con al menos un checkpoint. (c) Cambios encolados.
- **Decisión:** (a).
- **Justificación:** la petición habla de un cambio «pedido por el lector», que lee una novela terminada. Con un cambio a la vez, el plan de regeneración no depende de otro plan a medias. Y `/novela-continuar` ya para ante un `intervencion.md` sin `resuelto:`, con la misma regla.
- **Fuente:** Petición del usuario; `.claude/commands/novela-continuar.md` § Reglas de lectura (regla 3)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-10), 9

## D7 — Dónde se registran la petición y el índice de versiones
- **Pregunta original (P7):** ¿La petición y la «tabla de versiones» van en `estado.db` o en disco?
- **Alternativas consideradas:** (a) En disco: `cambios/cam-NNN.json` y `versiones/versiones.json`, con escritura atómica y modelos Pydantic. En `estado.db`, solo las claves `version` y `cambio` de `meta` al crear la base. (b) Tablas `cambios` y `versiones` en `estado.db`, escritas por `novela cambio`. (c) Tablas escritas por `aplicar-delta` desde un delta especial.
- **Decisión:** (a). Los modelos no se exportan a `backend/schemas/`, porque ningún agente los produce.
- **Justificación:** la petición exige que `estado.db` solo lo escriba `aplicar-delta`, y lo pone como ejemplo («p. ej. versiones/vN/ … más tabla de versiones»), no como obligación. (b) abre una segunda vía de escritura, que el ADR 0002 rechazó para `cursor.intento`. Además, cada versión tiene su propia base (D1), así que un índice de versiones dentro de una base no vería las demás. La spec 0006 trata igual sus modelos internos (§8.3 de esa spec).
- **Fuente:** Petición del usuario; `docs/adr/0002-los-gates-los-decide-el-cli.md` § Alternativas descartadas
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-09, RF-16), 8.3

## D8 — Qué entra en la instantánea de una versión
- **Pregunta original (P8):** ¿Qué directorios se copian a `versiones/vN/` y cómo se copia la base?
- **Alternativas consideradas:** (a) `capitulos/`, `estado/estado.db` (API de backup de SQLite), `estado/deltas/`, `memoria/`, `qa/` y `checkpoints/`, más `version.json` con hashes. Se excluyen `canon/`, `plan/`, `runs/`, `export/`, `brief/` y `config.yaml`. (b) El workspace entero. (c) Solo `capitulos/`.
- **Decisión:** (a), con el hook denegando cualquier escritura de un agente bajo `versiones/` y `cambios/`.
- **Justificación:** copiar `canon/` pondría `canon/misterio.md` en una ruta que el `deny` de `Read(./novelas/*/canon/misterio.md)` no cubre (`docs/architecture.md` §6.3), y el canon y el plan no cambian con un cambio (D21). `runs/` no se toca porque «los ficheros de `runs/<run_id>/briefings/` son el único registro de qué vio cada agente. No los borres» (`CLAUDE.md` § Claves y trazado). (c) no conserva el estado ni los deltas, que la reaplicación necesita. La base se copia con backup, y no como fichero, porque `AGENTS.md` § Invariantes 6 prohíbe tratar `estado.db` por copia de fichero.
- **Fuente:** `docs/architecture.md` §6.3; `CLAUDE.md` § Claves y trazado; `AGENTS.md` § Invariantes 6
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-17, RF-18, RF-22, RF-23), 8.3, RNF-06, RNF-08

## D9 — Secuencia de preparación y recuperación ante corte
- **Pregunta original (P9):** ¿Cómo se prepara la versión sin dejar un workspace a medias si el proceso muere?
- **Alternativas consideradas:** (a) Copiar a `vN.tmp`, verificar, renombrar (punto de confirmación), registrar y solo entonces restablecer la raíz, con `cam-NNN.json` en `preparando` como diario, y repetir el comando para completar. (b) Mover (renombrar) los directorios de la raíz a `vN/`. (c) Copiar sin verificar.
- **Decisión:** (a). Una vez renombrada, nada escribe en `versiones/vN/`.
- **Justificación:** «Un estado a medio escribir es un workspace muerto, con fichero o con base» (`docs/architecture.md` §5), y la escritura es atómica por `.tmp` y renombrado (`AGENTS.md` § Invariantes 6). Con (a), la raíz original sigue intacta hasta que la copia está verificada. Con (b), un corte a mitad reparte la edición entre dos sitios.
- **Fuente:** `docs/architecture.md` §5 (Escritura atómica); `AGENTS.md` § Invariantes 6
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-19, RF-20, RF-21), 9

## D10 — Creación de la base vacía de la versión nueva
- **Pregunta original (P10):** Si `estado.db` solo lo escribe `aplicar-delta`, ¿quién crea la base de la versión nueva?
- **Alternativas consideradas:** (a) `novela cambio` crea una base vacía con `estado_db.crear`, igual que `novela nueva`, con `meta.version` y `meta.cambio`, y la instala con `os.replace`. Toda fila de colección entra después por `aplicar-delta`. (b) Que la cree `aplicar-delta` al reaplicar el capítulo 1. (c) Reconstruir entera la base dentro de `novela cambio`.
- **Decisión:** (a).
- **Justificación:** `novela nueva` ya crea `estado.db` (`AGENTS.md` § CLI) sin pasar por `aplicar-delta`. Crear un esquema vacío no es «actualizar» el estado (`AGENTS.md` § Invariantes 1). (c) escribiría filas fuera de `aplicar-delta`, contra la restricción de la petición. (b) mezcla con la reaplicación una responsabilidad que no es suya.
- **Fuente:** `AGENTS.md` § CLI y § Invariantes 1; Petición del usuario
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-16, RF-19), 8.3

## D11 — Reaplicación de los capítulos no afectados
- **Pregunta original (P11):** ¿Cómo entran en la versión nueva los capítulos que no se regeneran, sin cuota y sin tocar sus bytes?
- **Alternativas consideradas:** (a) `aplicar-delta --reaplicar`: copia el capítulo, el delta y `qa/` desde `vN/`, comprueba sus hashes contra `version.json` y aplica con las mismas `violaciones` y `apply`. La custodia de briefings se sustituye por la de la instantánea. (b) Copiar todos los capítulos no afectados de golpe en `novela cambio`. (c) Pasarlos por el bucle normal con un agente que copia.
- **Decisión:** (a). Además, con un cambio en curso, `aplicar-delta` sin `--reaplicar` sobre un capítulo reaplicable sale con 2.
- **Justificación:** la petición exige regenerar solo los afectados «con el bucle existente», y que `estado.db` solo se escriba con `aplicar-delta`. (a) cumple las dos cosas y hace que cada delta antiguo pase otra vez por `violaciones` contra el estado nuevo. Esa es la comprobación mecánica de que la continuidad no se rompe. (c) gasta cuota, y un agente no garantiza bytes idénticos. (b) no reconstruye el estado en orden.
- **Fuente:** Petición del usuario; `docs/validators.md` §4.14
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-25, RF-26, RF-27), 8.4, 9, 11

## D12 — Quién decide el siguiente paso de la regeneración
- **Pregunta original (P12):** ¿Cómo sabe el orquestador si un capítulo se reaplica o se regenera?
- **Alternativas consideradas:** (a) Un subcomando, `novela cambio --siguiente`, que imprime `NN reaplicar`, `NN regenerar`, `completo` o `sin cambio`. (b) El orquestador lee `cambios/cam-NNN.json`. (c) Intentar `--reaplicar` y, si falla, regenerar.
- **Decisión:** (a). «Completo» se deriva del checkpoint de `num_capitulos` y no se escribe.
- **Justificación:** el ADR 0002 fija que las fronteras del bucle las decide el CLI y no el juicio de la sesión. (c) mezcla un gate fallido con una bifurcación normal y consume el código 1. Derivar «completo» evita dos registros de lo mismo, que «acaban divergiendo» (ADR 0002).
- **Fuente:** `docs/adr/0002-los-gates-los-decide-el-cli.md` § Decisión y § Alternativas descartadas
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-24, RF-26, RF-33, RF-34), 8.3, 8.4

## D13 — Conjunto de capítulos afectados, sin cascada
- **Pregunta original (P13):** ¿Se regeneran también los capítulos que usan hechos introducidos por un capítulo afectado?
- **Alternativas consideradas:** (a) Afectados = exactamente los capítulos con algún uso del hecho. La continuidad con el resto la sostienen los «hechos requeridos»: los que el afectado introduce y un capítulo posterior usa. (b) Cierre transitivo por usos. (c) Todo desde el primer afectado.
- **Decisión:** (a).
- **Justificación:** la petición pide regenerar «solo esos». (b) y (c) tienden a regenerar la novela entera, porque casi todo capítulo usa algo de uno anterior. Los requeridos convierten la continuidad en una comprobación mecánica (D14), en vez de un juicio.
- **Fuente:** Petición del usuario
- **Confianza:** alta
- **Secciones de la spec afectadas:** 3.2, 5 (RF-13, RF-14), 9

## D14 — Gates de continuidad de la regeneración
- **Pregunta original (P14):** ¿Qué se comprueba mecánicamente para que la regeneración «no rompa la continuidad»?
- **Alternativas consideradas:** (a) En `validar`: las pistas y los hilos del frontmatter son iguales a los del capítulo original. En `aplicar-delta`: el hecho nuevo con el id reservado y el texto pedido, ninguna referencia al hecho sustituido, los requeridos con el mismo id y el mismo texto, y ningún id nuevo que exista en la versión anterior. (b) Solo el juicio del `continuista`. (c) Además, igualdad de `personajes` y `relaciones`.
- **Decisión:** (a), con las dos funciones puras probadas con propiedades.
- **Justificación:** «lo verificable mecánicamente se verifica con código» (`docs/architecture.md` §1, principio 5), y el `continuista` sigue revisando. Tocar un gate de `validate.py` o una rama de `delta.py` exige property-based (`AGENTS.md` § Proceso: generar código). (c) prohibiría cualquier efecto del cambio sobre los personajes, que es mutable por diseño.
- **Fuente:** `docs/architecture.md` §1; `AGENTS.md` § Proceso: generar código; `docs/validators.md` §3.6
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-31, RF-32), 8.4, 11

## D15 — Id del hecho nuevo
- **Pregunta original (P15):** ¿Qué id recibe el hecho que sustituye al anterior, y quién lo fija?
- **Alternativas consideradas:** (a) Lo reserva `novela cambio`: el mayor número de `libro_de_hechos` de la versión vigente más uno, y el `cronista` lo recibe en la capa `cambio`. (b) Lo elige el `cronista`. (c) Se reutiliza el id del hecho sustituido.
- **Decisión:** (a). Sale con 4 si no quedan ids (`hec-999`).
- **Justificación:** la petición exige que un cambio se añada «como hecho nuevo» sin modificar ni borrar. (c) haría que el mismo id tuviera dos textos en dos versiones. (b) puede chocar con ids de capítulos posteriores que se reaplican. Los ids son «claves estables» con el patrón `^hec-\d{3}$` (`AGENTS.md` § Identificadores, `docs/architecture.md` §5).
- **Fuente:** Petición del usuario; `AGENTS.md` § Identificadores; `docs/architecture.md` §5
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-12, RF-15, RF-32), 8.4

## D16 — Contexto del escritor en la regeneración
- **Pregunta original (P16):** ¿Qué recibe el `escritor` al regenerar un capítulo? ¿Ve la versión anterior del capítulo?
- **Alternativas consideradas:** (a) Capa `cambio` (hecho sustituido, texto nuevo, id reservado y requeridos) más la capa `version_anterior` con el cuerpo del capítulo en `vN/`. (b) Solo la capa `cambio`. (c) La versión anterior sin capa `cambio`.
- **Decisión:** (a). El `continuista` y el `cronista` reciben solo la capa `cambio`, y el `editor-estilo` ninguna.
- **Justificación:** ningún documento del repositorio lo decide. La versión anterior ayuda a cambiar solo lo necesario y cabe en la receta (unos 4.700 tokens según `docs/architecture.md` §6.5). La regla de no devolver el capítulo al `escritor` es para reintentos (`CLAUDE.md` § Bucle por capítulo), no para una regeneración, y el capítulo anterior no contiene el misterio. Es un supuesto que la demostración T-15 tiene que validar.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-28, RF-29, RF-35), 8.4

## D17 — La petición como dato no confiable
- **Pregunta original (P17):** El texto del lector entra en el briefing de un modelo. ¿Cómo se limita y se protege?
- **Alternativas consideradas:** (a) De 1 a 500 caracteres, distinto del texto vigente, delimitado en la capa como «dato, no instrucción», con los guardarraíles del secreto del briefing aplicados a la capa, y gates mecánicos que no dependen de lo que el modelo haga con él. (b) Sin límites. (c) Revisión por un modelo antes de aceptarlo.
- **Decisión:** (a).
- **Justificación:** `docs/validators.md` §4.9 nombra la inyección por contenido del workspace como segunda amenaza, y la spec 0005 trata el texto libre del cliente como dato no confiable (§2 de esa spec). El guardarraíl de solape con `verdad_oculta` ya existe (`docs/validators.md` §4.4). (c) cuesta cuota y comparte los puntos ciegos del modelo.
- **Fuente:** `docs/validators.md` §4.4 y §4.9; `docs/specs/0005/spec.md` § 2
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-11, RF-28, RF-30), 8.4, 9

## D18 — Novedades, marca y diff entre versiones
- **Pregunta original (P18):** ¿Cómo se marcan los capítulos cambiados (LEC-07) sin UI web ni PDF todavía?
- **Alternativas consideradas:** (a) `novela versiones` (lista, `--novedades` por comparación de sha256) y una sección «Novedades» con enlaces internos y anclas en `exportar --formato md` cuando la versión es mayor que 1. La página en PDF (con la 0006) y el diff textual son opcionales. (b) Un campo `version` en el frontmatter de cada capítulo. (c) Solo el PDF de la spec 0006.
- **Decisión:** (a). Con la versión 1, `md` y `epub` producen exactamente lo de antes.
- **Justificación:** la petición pide código y test del listado de novedades, y deja la UI web fuera. El sha256 del capítulo ya es la custodia del repositorio (`docs/validators.md` §3.9.7), así que comparar hashes no añade una fuente nueva. (b) cambia `capitulo.schema.json` y el contrato del `escritor`. (c) depende de una spec sin implementar. La salida intacta con la versión 1 sigue la regla de la spec 0006 (su RF-10).
- **Fuente:** Petición del usuario; `docs/validators.md` §3.9.7; `docs/specs/0006/spec.md` § 5 (RF-10)
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 5 (RF-36 a RF-41), 8.4

## D19 — La API y el frontend no cambian
- **Pregunta original (P19):** ¿Se exponen las versiones y las novedades por la API, aunque sea en lectura?
- **Alternativas consideradas:** (a) Ninguna ruta nueva: `openapi.json` y `state.schema.json` idénticos. (b) `GET /novelas/{slug}/versiones` de solo lectura. (c) Un `POST` para pedir el cambio.
- **Decisión:** (a).
- **Justificación:** la petición deja la UI web fuera, y sin consumidor una ruta es superficie sin uso. (c) está prohibida: «La API no escribe… Si hace falta escribir, se añade un subcomando al CLI» (`AGENTS.md` § Monorepo). `usos_de_hecho` queda fuera de `Estado` para no cambiar el contrato.
- **Fuente:** Petición del usuario; `AGENTS.md` § Monorepo
- **Confianza:** alta
- **Secciones de la spec afectadas:** 3.2, 5 (RF-07, RF-42), 8.3

## D20 — Scores de Langfuse por versión
- **Pregunta original (P20):** El id de score es por capítulo y métrica, y «reemitir sustituye» (`docs/architecture.md` §10.5). ¿Los scores de la versión 2 sustituyen a los de la 1?
- **Alternativas consideradas:** (a) Añadir `v<N>` al id cuando la versión es mayor que 1, y conservar el id actual en la 1. (b) No cambiar nada y aceptar la sustitución. (c) No emitir scores en los capítulos reaplicados.
- **Decisión:** (a).
- **Justificación:** conservar la versión anterior también en la observabilidad es coherente con LEC-08, y (a) no altera nada de las novelas de una sola versión. Ningún documento lo decide.
- **Fuente:** Supuesto
- **Confianza:** baja
- **Secciones de la spec afectadas:** 5 (RF-43), 11

## D21 — El canon y el plan no cambian
- **Pregunta original (P21):** Si la ficha de plan de un capítulo afectado describe el hecho antiguo, ¿se reescribe el plan o el canon?
- **Alternativas consideradas:** (a) No se tocan. La capa `cambio` declara la sustitución y el `continuista` verifica contra la base nueva. (b) Invocar al `trazador` para rehacer las fichas afectadas. (c) Editar las fichas desde el CLI.
- **Decisión:** (a).
- **Justificación:** canon y plan son ramas distintas del estado y no se mezclan (`AGENTS.md` § Las cuatro ramas de contexto). Un cambio del lector es sobre «lo que ya pasó», no sobre «lo que debería pasar». (b) amplía el alcance a otro rol con acceso al misterio. (c) edita a mano una rama versionada que solo cambia por decisión del orquestador.
- **Fuente:** `AGENTS.md` § Las cuatro ramas de contexto
- **Confianza:** media
- **Secciones de la spec afectadas:** 3.2, 9, 11

## D22 — Identificadores `cam-` y `vN`
- **Pregunta original (P22):** ¿Cómo se identifican las peticiones y las versiones?
- **Alternativas consideradas:** (a) `cam-NNN` para las peticiones (`^cam-\d{3}$`) y `vN` para los directorios de versión, numerados desde 1. (b) Fechas. (c) UUID.
- **Decisión:** (a).
- **Justificación:** el repositorio usa «prefijo de tipo más slug o secuencia» como claves estables (`AGENTS.md` § Identificadores). Un prefijo nuevo se documenta en esa lista y en `docs/architecture.md` §5.
- **Fuente:** `AGENTS.md` § Identificadores
- **Confianza:** media
- **Secciones de la spec afectadas:** 5 (RF-09, RF-16), 8.3

## D23 — Documentación que se actualiza
- **Pregunta original (P23):** ¿Qué documentos y secciones describen lo implementado?
- **Alternativas consideradas:** (a) En el mismo commit que el código:
  - `docs/architecture.md`: §3.1 (slices `cambio/` y `versiones/`, `plataforma/versiones.py`), §4 (`versiones/` y `cambios/` en el workspace), §5 (prefijo `cam-`), §7.1 (`usos_de_hecho`), §7.3 (`regeneracion_altera_contrato`), §7.6 (`hechos_usados`), §8 (CLI) y §12.5.
  - `docs/definitions.md`: §4 (`usos_de_hecho`) y §6 (`versiones/`, `cambios/`).
  - `docs/validators.md`: §2 (fila nueva), §3.6 (propiedades), §3.9 (gates de regeneración), §4.14 (reaplicación), §5 (riesgo de cobertura de `hechos_usados` y cambio de §5.7) y §6.
  - `AGENTS.md`: invariante 7, § CLI e § Identificadores.
  - `CLAUDE.md`, solo si cambia el bucle resumido.
  (b) Solo los tres documentos que nombra la petición.
- **Decisión:** (a).
- **Justificación:** la petición exige actualizar `architecture.md`, `definitions.md` y `validators.md`. `AGENTS.md` § Proceso: modificar documentación obliga a hacerlo «en el mismo commit que el código que lo cambia», y a no escribir «próximamente». `CLAUDE.md` solo se toca si cambia una convención, porque se paga en cada sesión.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: modificar documentación y § Nunca
- **Confianza:** alta
- **Secciones de la spec afectadas:** 5 (RF-45, RF-46), 12 (T-16)

## D24 — Estrategia de pruebas
- **Pregunta original (P24):** ¿Cómo se prueban la consulta, la regeneración selectiva y la inmutabilidad sin llamar a un modelo?
- **Alternativas consideradas:** (a) Propiedades con Hypothesis (≥ 200 casos) sobre las funciones puras, más una propiedad de extremo a extremo (≥ 25 casos) con el CLI real y el agente falso de `backend/tests/fixtures/fabrica.py`, y la comparación byte a byte de `versiones/v1/`. (b) Solo tests de ejemplo. (c) Una novela de humo.
- **Decisión:** (a). La demostración T-15 se reserva para los cambios de prompt.
- **Justificación:** la petición pide propiedades para la consulta y para la regeneración, el test byte a byte y el test del listado de novedades, sin modelos y con el agente falso. `AGENTS.md` § Proceso: generar código exige property-based en `validate.py` y `delta.py`, y validar un cambio de prompt con una novela de humo de 3 capítulos.
- **Fuente:** Petición del usuario; `AGENTS.md` § Proceso: generar código
- **Confianza:** alta
- **Secciones de la spec afectadas:** 6 (RNF-10, RNF-11), 12, 13, 14

## Contexto consultado

**Ficheros leídos**

- `CLAUDE.md` y `AGENTS.md` (raíz). Existen los dos.
- Enlazados desde ellos:
  - `docs/architecture.md`, entero.
  - `docs/definitions.md`, entero.
  - `docs/validators.md`: §1 a §4.14, §5, §6 y el índice de encabezados del resto.
  - `docs/domain-knowledge.md`: índice y §3.
  - `.claude/commands/novela-continuar.md`.
- Código:
  - `backend/novela/plataforma/esquema.sql`, `backend/novela/plataforma/workspace.py` y `backend/novela/cli.py`.
  - `backend/novela/slices/delta/cmd.py` y `backend/novela/slices/checkpoint/cmd.py`.
  - Firmas de `backend/novela/dominio/estado.py`, `backend/novela/plataforma/estado_db.py` y `backend/tests/test_bucle.py`.
  - `backend/tests/fixtures/fabrica.py` (fábrica de deltas y bucle con agente falso).
  - Búsquedas en `backend/novela/` (sello, cursor monótono) y en `.claude/hooks/denegar-escritura-estado.py` (`SALIDAS`).
- `docs/adr/0002-los-gates-los-decide-el-cli.md` y el listado de `docs/adr/`.
- `docs/auditoria-entregable.md`: filas LEC-05 a LEC-08.

**Ficheros esperados que no existían**

- Ninguno de los enlazados desde `CLAUDE.md` y `AGENTS.md`.
- No se siguió `~/.claude/state/langfuse_hook.log`: es una ruta fuera del repositorio.

**Specs anteriores revisadas y solapamientos**

- `docs/specs/0001-backend-cli-estado-y-api.md` (implementada, formato anterior). Aporta `aplicar-delta`, la custodia, la cita literal y el sello, que esta spec reutiliza. No hay solapamiento de alcance: `--reaplicar` es un modo nuevo.
- `docs/specs/0002-verificacion-a-escala-de-novela.md` (aceptada, sin implementar). Toca `slices/delta/cmd.py`, `validar` y el procedimiento, y su auditoría de trayectoria tendrá que admitir `--reaplicar`. Posible conflicto de integración, registrado en §10 y §11. No hay contradicción de requisitos.
- `docs/specs/0003-contencion-y-bucle-en-claude.md` (implementada). Contrato de agentes y hook: esta spec cambia cuerpos de agentes y procedimiento sin tocar `tools` ni `model`. La novela de humo de la 0003 ya paró una vez por el invariante 7, y esta spec conserva esa parada.
- `docs/specs/0004/` (panel web). Sin solapamiento, porque el frontend no cambia.
- `docs/specs/0005/` (Propuesta, brief). Sin solapamiento: `brief/` no se copia ni se modifica.
- `docs/specs/0006/` (Propuesta, PDF y `apariciones`). Solapamiento parcial: LEC-07 en PDF depende de su exportador (RF-40), y `usos_de_hecho` sigue su patrón de tabla derivada. La 0006 reserva el ADR 0003, así que esta spec usa el 0004.

**Instrucciones encontradas en el contexto que se ignoraron**

- Ninguna dirigida al redactor. Las reglas de `CLAUDE.md` para la sesión orquestadora («Nunca abras `capitulos/NN.md`…») se tomaron como material sobre el diseño del bucle, no como órdenes para esta tarea.

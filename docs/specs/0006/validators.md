## 0006
Spec: `docs/specs/0006/spec.md` · Plan: `docs/implementation-plans/0006.md` · Fecha de análisis: 2026-09-24

### Discrepancias spec ↔ plan
| ID | Tipo (requisito sin cubrir / paso sin requisito / contradicción) | Detalle | Ref. spec | Ref. plan |
|----|------|---------|-----------|-----------|
| D1 | contradicción | La spec concentra la documentación de D17 en T-09 y CA-33 la revisa «Dado el commit de cierre (T-09)». El plan (PD8) la reparte entre T2.2, T2.4, T3.4, T4.1 y T4.3, así que CA-33, tal como está escrito, solo inspecciona el último commit y no comprueba la regla «en el mismo commit que el código» en los intermedios | R33 — RF-33, §12 (T-09), CA-33 | P3, P5, P10, P11, P13, P14 (PD8) |
| D2 | contradicción | §8.5 paso 4: `cmd.py` «lee … `canon/personajes/*.md`». PD6 lee solo `canon/personajes/<id>.md` de las entidades con aparición. Con una ficha ajena inválida, la spec lleva a la salida 4 («canon ilegibles», §8.4) y el plan a la salida 0 | R26, R29 — §8.4, §8.5 | P10 (T3.4, PD6) |
| D3 | paso sin requisito | PD7 fija la salida 4 si falta `runs/<checkpoint.run_id>/manifest.json`. La tabla de códigos de §8.4 no lo contempla y la spec no define ese caso (el propio plan lo deja como P5) | R7 — RF-07, §8.4 | P10 (T3.4, PD7) |

### Validadores
#### VAL-1: Solo capítulos cerrados, escritura atómica y resumen exacto
- Requisito: R1 — RF-01 «con los capítulos 1 a `checkpoint.capitulo`, en orden… `WorkspaceRepository.escribir` (`.tmp` y renombrado)» (§5); CA-01; D15
- Punto de fallo: el exportador lee todo `capitulos/` en vez de parar en el checkpoint, o escribe el PDF directamente y deja un fichero parcial o un `.tmp`.
- Precondiciones: `demo-regalo` con checkpoint en 3; una copia a la que el test añade `capitulos/04.md` válido y aplicado con `aplicar-delta`, sin `novela checkpoint`.
- Cómo validarlo: `novela exportar demo-regalo --formato pdf` sobre cada una; listar `export/`; contar capítulos con `pypdf` (páginas que empiezan por «La linterna, noche N»); parchear `os.replace` para que lance `OSError` y exportar otra vez.
- Resultado esperado: salida 0 y stdout exacto `exportar: 3 capítulos en export/novela.pdf` en las dos; 3 capítulos en el PDF (el 4 no aparece); ningún fichero `*.tmp` en `export/`; con `os.replace` fallando, `export/novela.pdf` no existe y no queda `.tmp`.
- Tipo de prueba sugerida: integración
- Severidad: Alta — incluir un capítulo no confirmado entrega al destinatario texto que no ha pasado los gates.

#### VAL-2: Lock ocupado
- Requisito: R1 — §9 «Lock ocupado por el bucle | Sale con 3 sin escribir» (RF-01)
- Punto de fallo: la exportación no toma `estado/state.lock` o lo toma después de leer `estado.db`, y compone un libro a mitad de un `aplicar-delta`.
- Precondiciones: `demo-regalo` con la fixture `lock_ajeno` activa.
- Cómo validarlo: ejecutar `novela exportar demo-regalo --formato pdf` con el lock tomado por otro proceso.
- Resultado esperado: salida 3, `export/novela.pdf` no existe y la huella de `estado/estado.db` no cambia.
- Tipo de prueba sugerida: integración
- Severidad: Media — hay alternativa (reintentar), pero sin lock el libro puede mezclar estados.

#### VAL-3: Orden de secciones y página nueva por capítulo
- Requisito: R2 — RF-02 «portada en la página 1, índice, cada capítulo empezando en página nueva, y la ficha… al final» (§5); CA-02
- Punto de fallo: un capítulo corto continúa en la página del anterior, o la ficha se compone antes del último capítulo.
- Precondiciones: PDF de CA-01.
- Cómo validarlo: extraer el texto de cada página con `pypdf`; localizar la página de inicio de cada sección.
- Resultado esperado: página 1 empieza por `demo-regalo`; página 2 empieza por «Índice»; cada «La linterna, noche N» (N = 1, 2, 3) es la primera línea de su página y los índices de página son estrictamente crecientes; la primera página de «Personajes y lugares» es posterior a la última del capítulo 3 y no hay ninguna página tras la ficha que empiece por otra sección.
- Tipo de prueba sugerida: integración
- Severidad: Alta — es la estructura del libro que se entrega.

#### VAL-4: Enlaces del índice
- Requisito: R3 — RF-03 «una entrada por capítulo cerrado, con el `titulo` de su frontmatter y un enlace interno… y una entrada "Personajes y lugares"» (§5); CA-03
- Punto de fallo: el índice usa el encabezado del cuerpo en vez del `titulo` del frontmatter, o falta el enlace a la ficha.
- Precondiciones: PDF de CA-01; copia de `demo-regalo` con el `titulo` del frontmatter del capítulo 2 cambiado a «Marea baja» sin tocar el cuerpo.
- Cómo validarlo: recorrer `/Annots` de las páginas del índice y resolver cada destino a su índice de página.
- Resultado esperado: exactamente 4 anotaciones `/Link`; 3 con destino en la primera página de los capítulos 1, 2 y 3 y 1 en la primera página de la ficha; en la copia, el índice contiene la línea «2. Marea baja».
- Tipo de prueba sugerida: integración
- Severidad: Alta — sin enlaces el índice no es navegable.

#### VAL-5: Marcadores e idioma tomados de la configuración
- Requisito: R4 — RF-04 «un marcador (outline) por capítulo, uno para el índice y uno para la ficha, y fijar el idioma… a `parametros_obra.idioma`» (§5); CA-04
- Punto de fallo: `/Lang` queda fijado a `es` en código y pasa CA-04 por casualidad.
- Precondiciones: `demo-regalo`; una copia con `parametros_obra.idioma: en` en `config.yaml`.
- Cómo validarlo: exportar las dos; leer `reader.outline` y `reader.trailer["/Root"]["/Lang"]`.
- Resultado esperado: 5 marcadores con títulos «Índice», «La linterna, noche 1», «La linterna, noche 2», «La linterna, noche 3», «Personajes y lugares», en ese orden; `/Lang` = `es` en la primera y `en` en la copia.
- Tipo de prueba sugerida: integración
- Severidad: Media — afecta a la navegación y a los lectores de pantalla, con alternativa (índice).

#### VAL-6: Enlace `javascript:` en el cuerpo
- Requisito: R5 — §9 «El capítulo contiene `[x](javascript:…)` | Se muestra "x" sin enlace» (RF-05)
- Punto de fallo: el parser de markdown rechaza los esquemas peligrosos y no reconoce el enlace, con lo que se imprime la sintaxis cruda `[x](javascript:alert(1))` en lugar de «x»; o, al revés, se crea una anotación.
- Precondiciones: `demo-regalo` con el cuerpo del capítulo 2 cambiado en el test para contener `[x](javascript:alert(1))` y `<https://ejemplo.invalid>`.
- Cómo validarlo: exportar; extraer el texto del capítulo 2; recorrer `/Annots` de todas las páginas.
- Resultado esperado: el texto contiene «x» y no contiene «javascript:» ni «](»; 0 anotaciones con `/A` de tipo `/URI`, `/JavaScript`, `/Launch`, `/SubmitForm` o `/GoToR`.
- Tipo de prueba sugerida: integración
- Severidad: Media — el caso lo fija §9; el riesgo de seguridad lo cubre VAL-38.

#### VAL-7: Sin checkpoint
- Requisito: R6 — RF-06 «salir con 1 con "no hay capítulos cerrados que exportar", sin escribir nada» (§5); CA-06
- Punto de fallo: la comprobación de checkpoint corre después de validar `--titulo` o de abrir `estado.db`, y el mensaje o el código cambian.
- Precondiciones: workspace recién creado con `novela nueva`.
- Cómo validarlo: `novela exportar <slug> --formato pdf`; y con `--titulo "La luz del cabo"`.
- Resultado esperado: salida 1 y stderr/stdout contiene «no hay capítulos cerrados que exportar» en las dos; `export/novela.pdf` no existe.
- Tipo de prueba sugerida: integración
- Severidad: Media — caso secundario con mensaje explícito.

#### VAL-8: Determinismo entre procesos y fecha del manifiesto
- Requisito: R7 — RF-07 «dos `export/novela.pdf` idénticos byte a byte» (§5); §8.4 «`CreationDate` es el `creado` del manifiesto del run del último checkpoint» (D14)
- Punto de fallo: CA-07 exporta dos veces en el mismo proceso; en dos invocaciones reales del CLI el subconjunto de glifos o un identificador pueden depender del orden de un `set` (hash aleatorio por proceso) o de la hora.
- Precondiciones: `demo-regalo`.
- Cómo validarlo: ejecutar `novela exportar demo-regalo --formato pdf` en dos subprocesos con `PYTHONHASHSEED=1` y `PYTHONHASHSEED=2`, copiando el PDF entre medias; leer `/CreationDate` de `reader.metadata` y `creado` de `runs/<checkpoint.run_id>/manifest.json`.
- Resultado esperado: sha256 idéntico en los dos ficheros; `/CreationDate` representa el mismo instante que `creado` (comparados como `datetime` con zona).
- Tipo de prueba sugerida: integración
- Severidad: Media — requisito Should con degradación prevista en §10.

#### VAL-9: Límites de `--titulo`
- Requisito: R8 — RF-08 «Si `--titulo` queda vacío tras quitar espacios o supera 120 caracteres, debe salir con 2 sin escribir» (§5); CA-08; D11
- Punto de fallo: error de uno en el límite (120 rechazado o 121 aceptado) o `"   "` aceptado como título.
- Precondiciones: `demo-regalo`.
- Cómo validarlo: exportar sin `--titulo`, con `"La luz del cabo"`, con `"a"*120`, con `"a"*121` y con `"   "`; leer la página 1 y `/Title`.
- Resultado esperado: sin opción → 0, portada y `/Title` = `demo-regalo`; «La luz del cabo» → 0 con ese texto en portada y `/Title`; 120 caracteres → 0; 121 y `"   "` → 2 y `export/novela.pdf` no existe.
- Tipo de prueba sugerida: integración
- Severidad: Baja — es la portada; el operador puede repetir con otro título.

#### VAL-10: Carácter sin glifo en portada y ficha
- Requisito: R9 — RF-09 «nombrar el capítulo (o "portada" o "ficha") y el código `U+XXXX`, y no escribir el PDF» (§5); §9 «Título o nombre con emoji»
- Punto de fallo: la comprobación solo recorre los cuerpos de los capítulos (CA-09) y un emoji en `--titulo` o en `identidad.nombre` pasa sin detectar o se sustituye en silencio.
- Precondiciones: `demo-regalo`; una copia con `identidad.nombre` de `per-ines-mar` = «Inés 🕯 Mar».
- Cómo validarlo: exportar con `--titulo "Faro 🕯"`; exportar la copia sin `--titulo`.
- Resultado esperado: las dos salen con 1; el primer mensaje contiene «portada» y `U+1F56F`; el segundo contiene «ficha» y `U+1F56F`; `export/novela.pdf` no existe en ninguna.
- Tipo de prueba sugerida: integración
- Severidad: Media — sin la comprobación el libro sale con cajas vacías, pero hay alternativa (corregir el texto).

#### VAL-11: `md` y `epub` intactos e indiferentes a `--titulo`
- Requisito: R10 — RF-10 «mantener `--formato md` y `--formato epub` con la salida que tenían» (§5); §8.4 «Con `md` o `epub` se ignora»
- Punto de fallo: la validación de `--titulo` corre para todos los formatos y un `--titulo` inválido rompe `md`/`epub`, o el epub empieza a usar el título.
- Precondiciones: `demo-terminado`; sha256 de `export/novela.md` y `export/novela.epub` generados con el código anterior a la spec.
- Cómo validarlo: `novela exportar demo-terminado --formato epub --titulo "   "` y `--formato md --titulo "La luz del cabo"`; `git diff --exit-code backend/novela/slices/export/test_export.py`.
- Resultado esperado: las dos salen con 0; `novela.md` idéntico al de referencia; el título del epub sigue siendo `demo-terminado`; `git diff` sale con 0 y `test_md_concatena_en_orden` y `test_epub_reabrible` pasan.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — RF-10 es Must y rompería el formato de entrega existente.

#### VAL-12: Dedicatoria literal, con saltos, solo en la portada
- Requisito: R11 — RF-11 «`dedicatoria.cita` del brief, literal y con sus saltos de línea» (§5); CA-11; CA-02 (portada en la página 1)
- Punto de fallo: la composición recorta, reflowa o normaliza espacios de la dedicatoria, o una dedicatoria larga desborda a la página 2 y desplaza el índice.
- Precondiciones: `demo-regalo` con su brief; una copia con una dedicatoria ficticia de 600 caracteres sin saltos de línea.
- Cómo validarlo: exportar las dos; extraer el texto por página.
- Resultado esperado: en la primera, la página 1 contiene «Para Aurora Ficticia,» y la línea siguiente es «que siempre leyó primero el final.»; ninguna otra página contiene «Aurora Ficticia»; en la copia, los 600 caracteres están en la página 1 y la página 2 empieza por «Índice».
- Tipo de prueba sugerida: integración
- Severidad: Alta — la dedicatoria es el elemento personal del regalo.

#### VAL-13: Novela sin brief
- Requisito: R12 — RF-12 «componer la portada solo con el título, salir con 0 e imprimir "sin dedicatoria: el workspace no tiene brief/brief.json"» (§5); CA-12
- Punto de fallo: el aviso va a stderr o después del resumen, o la portada muestra un texto de relleno.
- Precondiciones: `demo-terminado` sin `brief/`; y una copia con `brief/borrador.json` pero sin `brief/brief.json`.
- Cómo validarlo: exportar las dos; capturar stdout por separado; extraer el texto de la página 1.
- Resultado esperado: salida 0; stdout tiene dos líneas, la primera «sin dedicatoria: el workspace no tiene brief/brief.json» y la segunda `exportar: 24 capítulos en export/novela.pdf`; la página 1 contiene solo `demo-terminado`.
- Tipo de prueba sugerida: integración
- Severidad: Media — afecta a las novelas que no son regalo, con salida válida.

#### VAL-14: Brief inválido en sus dos formas
- Requisito: R13 — RF-13 «Si `brief/brief.json` existe y no valida contra `Brief`, … salir con 4 sin escribir el PDF» (§5); CA-13
- Punto de fallo: solo se prueba el JSON sin `dedicatoria` (CA-13); un JSON mal formado o vacío lanza una excepción no traducida y sale con 1 o con traceback.
- Precondiciones: `demo-regalo` con `brief/brief.json` sustituido por: (a) JSON sin `dedicatoria`; (b) el texto `{"dedicatoria": ` truncado; (c) fichero de 0 bytes.
- Cómo validarlo: exportar en cada caso.
- Resultado esperado: salida 4 en los tres; stderr nombra `brief/brief.json`; no hay traceback de Python; `export/novela.pdf` no existe.
- Tipo de prueba sugerida: integración
- Severidad: Alta — un brief corrupto no debe producir un libro sin dedicatoria sin avisar.

#### VAL-15: Gates de `dedicatoria` en `novela brief validar`
- Requisito: R14 — RF-14 «registrar `falta_campo` en `dedicatoria` si es `null`, aplicarle la comprobación de cita literal… y registrar `campo_cerrado_desde_texto_libre`» (§5); CA-14
- Punto de fallo: la dedicatoria se valida como texto libre y no como `Fuente`, o `brief.schema.json` no la exige.
- Precondiciones: spec 0005 implementada; los cuatro borradores de CA-14.
- Cómo validarlo: ejecutar los gates de `slices/brief/` sobre cada borrador; `REGENERAR=1 uv run pytest tests/test_contratos.py` y leer `required` de `backend/schemas/brief.schema.json` y el tipo de `dedicatoria` en `brief-borrador.schema.json`.
- Resultado esperado: hallazgos `falta_campo@dedicatoria`, `cita_no_literal@dedicatoria`, `campo_cerrado_desde_texto_libre@dedicatoria` y lista vacía, respectivamente; `"dedicatoria"` ∈ `required` de `brief.schema.json`; en el borrador admite `null`.
- Tipo de prueba sugerida: unitaria + contrato
- Severidad: Crítica — sin la cita literal, el libro podría imprimir una dedicatoria reescrita por el agente.

#### VAL-16: La dedicatoria no entra en `idea_semilla`
- Requisito: R15 — RF-15 «no debe incluir la dedicatoria en `idea_semilla`» (§5); CA-15; R39 — RNF-06
- Punto de fallo: `idea_semilla` serializa el `Brief` entero o recorre todos los campos `Fuente`.
- Precondiciones: `brief-completo.json` con la dedicatoria de §7.
- Cómo validarlo: generar `idea_semilla`; buscar todas las subcadenas de 10 caracteres de la dedicatoria; comparar con el golden `idea-semilla.txt` de la 0005.
- Resultado esperado: 0 coincidencias; `idea_semilla` idéntica byte a byte al golden.
- Tipo de prueba sugerida: unitaria
- Severidad: Crítica — la dedicatoria llegaría al `arquitecto` y a sus trazas, contra la minimización de datos personales.

#### VAL-17: La dedicatoria no sale por ninguna vía de error
- Requisito: R16 — RF-16 «no debe escribir el texto de la dedicatoria en stdout, stderr ni `harness.log` en ningún subcomando» (§5); CA-16; R39 — RNF-06
- Punto de fallo: los caminos de error, no el feliz: el mensaje de `ValidationError` de Pydantic incluye `input_value`; un hallazgo `cita_no_literal` puede citar el texto; un error de glifo dentro de la dedicatoria puede imprimir el fragmento.
- Precondiciones: `demo-regalo` con brief; variantes: (a) `brief.json` cuya `dedicatoria.cita` tiene 601 caracteres y contiene «que siempre leyó primero el final»; (b) `brief.json` mal formado que contiene esa frase; (c) dedicatoria con U+1F56F; (d) borrador de CA-14 con `cita_no_literal@dedicatoria` pasado a `novela brief validar`.
- Cómo validarlo: ejecutar cada caso con `CliRunner(mix_stderr=False)`; leer stdout, stderr y todos los `runs/*/harness.log`.
- Resultado esperado: salidas 4, 4, 1 y la de la 0005 para el gate; en (c) el mensaje contiene «portada» y `U+1F56F`; ninguna línea de stdout, stderr ni `harness.log` contiene «que siempre leyó primero el final» ni «Para Aurora Ficticia,».
- Tipo de prueba sugerida: integración
- Severidad: Crítica — fuga de un dato personal del cliente a logs y trazas.

#### VAL-18: El `entrevistador` nombra la dedicatoria
- Requisito: R17 — RF-17 «nombrar en `.claude/agents/entrevistador.md` el campo `dedicatoria` y la regla de que se copia literal de una entrada de tipo `respuesta`» (§5); CA-17
- Punto de fallo: el prompt nombra el campo pero no la regla, y el agente la redacta o la toma de `texto_libre`.
- Precondiciones: spec 0005 implementada.
- Cómo validarlo: `uv run pytest tests/test_contratos.py::test_entrevistador_nombra_la_dedicatoria` y los tests de contrato del agente de la 0005; demostración de T-08 con datos ficticios.
- Resultado esperado: tests en verde; el cuerpo contiene `dedicatoria`, «literal» y `respuesta` en la misma regla; en la demostración, `brief/brief.json` valida y `dedicatoria.cita` es subcadena exacta de una entrada `respuesta`.
- Tipo de prueba sugerida: unitaria (contrato) + revisión manual
- Severidad: Media — hay gate de cita literal detrás (VAL-15).

#### VAL-19: Restricciones de la tabla `apariciones`
- Requisito: R18 — RF-18 «tabla `STRICT` `apariciones`… `CHECK (tipo IN ('personaje','escenario'))`… triggers `BEFORE UPDATE` y `BEFORE DELETE` que abortan» (§5); CA-18; §8.3 (`NOT NULL`)
- Punto de fallo: falta `STRICT`, el `CHECK` o `NOT NULL`, o el índice, y la tabla acepta filas basura que luego rompen la ficha.
- Precondiciones: `estado.db` creado con `estado_db.crear`.
- Cómo validarlo: `INSERT` de `('per-elena-vidal','personaje',1)`; `UPDATE apariciones SET capitulo=2`; `DELETE FROM apariciones`; `INSERT` con `tipo='objeto'`; con `capitulo='uno'`; con `entidad=NULL`; `SELECT name FROM sqlite_master WHERE type='index' AND name='apariciones_por_capitulo'`.
- Resultado esperado: el primer `INSERT` pasa; `UPDATE` y `DELETE` lanzan `sqlite3.IntegrityError` con «apariciones es append-only»; los tres `INSERT` siguientes lanzan `IntegrityError` (`CHECK`, `STRICT` y `NOT NULL`); la consulta del índice devuelve 1 fila.
- Tipo de prueba sugerida: unitaria (plataforma)
- Severidad: Crítica — la tabla es append-only como `libro_de_hechos`; un borrado alteraría la historia registrada.

#### VAL-20: Derivación de las apariciones de un capítulo
- Requisito: R19 — RF-19 «el `pov`…; los `personajes` y el `lugar` de las escenas… cuyo id está en `escenas` del frontmatter; y las claves de `delta.personajes` con `ultima_aparicion == N`, con su `ubicacion` si no es nula» (§5); CA-19; §9 filas 1–3
- Punto de fallo: se cuentan escenas de la ficha no declaradas en el frontmatter, personajes del delta con `ultima_aparicion < N`, o no se añade la `ubicacion`.
- Precondiciones: `demo-regalo`; una variante cuyo delta del capítulo 3 incluye a `fabrica.INES` con `ultima_aparicion: 1` y cuyo frontmatter del 3 declara solo `esc-03-1`.
- Cómo validarlo: `estado_db.apariciones(conn, 3)` sobre las dos.
- Resultado esperado: en `demo-regalo`, exactamente los 15 pares de §7 (`INES` en 1 y 3, `ARCHIVO` solo en 2, `PUERTO` en 1, 2 y 3); en la variante, el capítulo 3 no tiene fila de `INES` si no está en `esc-03-1` ni es `pov`.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — RF-19 es Must y la ficha entera depende de estas filas.

#### VAL-21: `ubicacion` con escenario sin canon
- Requisito: R19 — §9 «`ubicacion` del delta con un escenario que no está en `canon/mundo.md` | Se registra, y la exportación sale con 4 nombrando el id» (RF-19, RF-29)
- Punto de fallo: `aplicar-delta` filtra la `ubicacion` contra el canon y la aparición se pierde en silencio, o la exportación la ignora.
- Precondiciones: `demo-regalo` construido con un delta del capítulo 3 en el que Elena tiene `ubicacion: esc-cueva` y `canon/mundo.md` no tiene `esc-cueva`.
- Cómo validarlo: consultar `apariciones`; exportar en PDF.
- Resultado esperado: existe la fila `('esc-cueva','escenario',3)`; la exportación sale con 4, el mensaje contiene `esc-cueva` y `export/novela.pdf` no existe.
- Tipo de prueba sugerida: integración
- Severidad: Media — caso límite con error explícito.

#### VAL-22: Reaplicar el mismo capítulo
- Requisito: R20 — RF-20 «no debe duplicar ni borrar filas de `apariciones`» (§5); CA-20; §9 «`INSERT OR IGNORE`»
- Punto de fallo: la reaplicación intenta borrar las filas del capítulo antes de insertarlas y aborta por el trigger, o inserta duplicados si la clave no es la del spec.
- Precondiciones: `demo-regalo` con los tres capítulos aplicados.
- Cómo validarlo: `SELECT count(*) FROM apariciones`; `novela aplicar-delta demo-regalo 3` otra vez; repetir la cuenta.
- Resultado esperado: `aplicar-delta` sale con 0; la cuenta es 15 antes y después; `SELECT * … ORDER BY entidad, capitulo` devuelve las mismas filas.
- Tipo de prueba sugerida: integración + propiedad (CA-20, ≥ 200 casos)
- Severidad: Alta — la reanudación del bucle repite el último paso no confirmado.

#### VAL-23: `aplicar-delta` sin ficha de plan
- Requisito: R21 — RF-21 «Si `plan/capitulos/NN.md` no existe o no valida contra `FichaCapitulo`, … salir con 4 sin escribir `estado.db` ni `memoria/`» (§5); CA-21
- Punto de fallo: la ficha se lee dentro de la transacción o después de escribir `memoria/`, y queda escritura parcial.
- Precondiciones: workspace listo para `aplicar-delta 2`: (a) sin `plan/capitulos/02.md`; (b) con la ficha sin `escenas`; (c) con la ficha con YAML mal formado.
- Cómo validarlo: huella (sha256) de `estado/estado.db` y de cada fichero de `memoria/` antes y después de `novela aplicar-delta <slug> 2`.
- Resultado esperado: salida 4 en los tres; huellas idénticas; el mensaje nombra `plan/capitulos/02.md`.
- Tipo de prueba sugerida: integración
- Severidad: Alta — una escritura parcial de `estado.db` rompe el invariante 1.

#### VAL-24: Migración aditiva atómica
- Requisito: R22 — RF-22 «crearla con sus triggers e índice (DDL idempotente) dentro de la misma transacción, antes de registrar» (§5); CA-22
- Punto de fallo: la tabla se crea en una transacción aparte; si `guardar` falla después, la base queda con la tabla y sin el estado del capítulo.
- Precondiciones: `estado.db` con capítulos 1 y 2 aplicados y sin `apariciones`, sus triggers ni su índice.
- Cómo validarlo: (a) `novela aplicar-delta <slug> 3`; (b) en otra copia, forzar un fallo tras `asegurar_apariciones` (p. ej. un delta que viola un invariante de `violaciones`) y consultar `sqlite_master`.
- Resultado esperado: (a) salida 0, `sqlite_master` tiene la tabla, `apariciones_no_update`, `apariciones_no_delete` y `apariciones_por_capitulo`, y solo hay filas con `capitulo = 3`; (b) salida ≠ 0 y `sqlite_master` no tiene ninguno de los cuatro objetos.
- Tipo de prueba sugerida: integración
- Severidad: Alta — una migración fuera de la transacción deja la base a medias.

#### VAL-25: `estado` y API sin la tabla
- Requisito: R23 — RF-23 «`novela estado` y `GET /novelas/{slug}/estado` deben responder lo mismo que antes de esta spec» (§5); CA-23
- Punto de fallo: la apertura de la base empieza a exigir los triggers de `apariciones` o `leer` la consulta, y los workspaces antiguos dan 4 o 500.
- Precondiciones: el `estado.db` sin tabla de CA-22 y una copia con la tabla.
- Cómo validarlo: `novela estado <slug> --json` y `GET /novelas/<slug>/estado` sobre las dos.
- Resultado esperado: salida 0 y HTTP 200 en las cuatro llamadas; el JSON es idéntico entre la base sin tabla y la base con tabla.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — romper la lectura de todo workspace anterior deja el panel y el CLI inutilizables.

#### VAL-26: Consulta `estado_db.apariciones`
- Requisito: R24 — RF-24 «devuelve las filas con `capitulo <= hasta` ordenadas por `entidad` y `capitulo`, válida sobre una conexión abierta en solo lectura» (§5); CA-24
- Punto de fallo: la consulta intenta crear la tabla o escribir (falla en solo lectura), o el orden depende del de inserción.
- Precondiciones: `demo-regalo`.
- Cómo validarlo: abrir con `estado_db.abrir(ruta, solo_lectura=True)` y llamar a `apariciones(conn, 2)` y `apariciones(conn, 0)`.
- Resultado esperado: la primera devuelve 10 `Aparicion` con `capitulo ∈ {1, 2}`, en orden lexicográfico por `entidad` y luego ascendente por `capitulo`; la segunda devuelve `[]`; ninguna lanza `sqlite3.OperationalError`.
- Tipo de prueba sugerida: unitaria (plataforma)
- Severidad: Alta — es la única fuente de la ficha.

#### VAL-27: Capítulos cerrados sin apariciones
- Requisito: R25 — RF-25 «Si… la tabla `apariciones` no existe o algún capítulo cerrado no tiene ninguna fila, … salir con 4, nombrar esos capítulos y no escribir el PDF» (§5); CA-25; §9 filas «Workspace creado antes de esta spec»
- Punto de fallo: la comprobación solo mira si la tabla tiene filas en total, o cuenta un capítulo aplicado sin checkpoint.
- Precondiciones: (a) workspace de CA-22 con el 3 cerrado; (b) workspace sin la tabla; (c) `demo-regalo` con `capitulos/04.md` aplicado y sin checkpoint.
- Cómo validarlo: exportar en PDF cada uno; en (c), además, `--formato md`.
- Resultado esperado: (a) salida 4 y el mensaje nombra los capítulos 1 y 2 y no el 3; (b) salida 4; (c) salida 0 con 3 capítulos; en (a) y (b) `export/novela.pdf` no existe y `--formato md` sale con 0.
- Tipo de prueba sugerida: integración
- Severidad: Alta — sin la comprobación se entregaría una ficha incompleta sin aviso.

#### VAL-28: La ficha solo usa capítulos cerrados
- Requisito: R26 — RF-26 «desde `estado_db.apariciones(conn, checkpoint.capitulo)`… solo para las entidades con al menos una aparición» (§5); CA-26; §9 «Capítulo aplicado y aún sin checkpoint»
- Punto de fallo: la ficha consulta sin `hasta` y lista una entidad que solo aparece en un capítulo aplicado pero no cerrado.
- Precondiciones: `demo-regalo` con un capítulo 4 aplicado y sin checkpoint en el que aparece un personaje nuevo `per-bruno-mar` con ficha en canon.
- Cómo validarlo: exportar; extraer el texto de la ficha.
- Resultado esperado: contiene «Elena Vidal», «Tomás Reyes», «Inés Mar», «La casa del faro», «El puerto» y «El archivo» con sus descripciones; no contiene el nombre de `per-bruno-mar` ni ningún enlace «Capítulo 4».
- Tipo de prueba sugerida: integración
- Severidad: Alta — revelaría al lector contenido de un capítulo no confirmado.

#### VAL-29: Un enlace por aparición, con número sin ceros
- Requisito: R27 — RF-27 «un enlace interno por capítulo en que aparece, con el texto "Capítulo N — título"… en orden ascendente» (§5); CA-27; §9 «La ficha muestra el número sin ceros»
- Punto de fallo: el texto usa `NN` con ceros (`Capítulo 02`) o el número de ruta de `ws.nn`, o se enlaza solo la primera aparición.
- Precondiciones: PDF de CA-01.
- Cómo validarlo: recorrer `/Annots` de las páginas de la ficha; para cada `Link`, extraer el texto bajo su `/Rect` y resolver su destino.
- Resultado esperado: 15 enlaces; textos con el patrón `^Capítulo [1-9][0-9]* — La linterna, noche [1-9][0-9]*$`; en cada entrada los N son ascendentes; cada destino es la primera página del capítulo N.
- Tipo de prueba sugerida: integración + propiedad
- Severidad: Alta — es la función principal de la ficha.

#### VAL-30: El exportador no abre el misterio
- Requisito: R28 — RF-28 «El exportador no debe abrir `canon/misterio.md`» y exclusión de campos (§5); CA-28
- Punto de fallo: CA-28 renombra el fichero, lo que solo prueba que la ausencia no rompe; el exportador podría leer `canon/*.md` con glob y usar el misterio cuando existe.
- Precondiciones: `demo-regalo` con `canon/misterio.md` presente.
- Cómo validarlo: instalar `sys.addaudithook` que registre los eventos `open` durante `novela exportar demo-regalo --formato pdf` en `CliRunner`; extraer el texto del PDF.
- Resultado esperado: 0 eventos `open` cuya ruta termine en `misterio.md`; el texto no contiene «apagó el faro a mano», «cofradía», «Vio luz en el cabo», «protagonista», «antagonista», «testigo», «el hermano» ni «olor a sal».
- Tipo de prueba sugerida: integración
- Severidad: Crítica — revelar la solución rompe los invariantes 3 y 4.

#### VAL-31: Personaje sin ficha de canon
- Requisito: R29 — RF-29 «Si una entidad de `apariciones` no tiene ficha… salir con 4, nombrar el id y no escribir el PDF» (§5); CA-29
- Punto de fallo: la entrada se omite en silencio o se compone con el id como nombre.
- Precondiciones: `demo-regalo` sin `canon/personajes/per-ines-mar.md`.
- Cómo validarlo: exportar en PDF.
- Resultado esperado: salida 4; el mensaje contiene `per-ines-mar`; `export/novela.pdf` no existe.
- Tipo de prueba sugerida: integración
- Severidad: Media — error explícito y reparable.

#### VAL-32: Orden de la ficha
- Requisito: R30 — RF-30 «los personajes primero y los lugares después, y cada grupo por su primer capítulo de aparición y, a igualdad, por id» (§5); CA-30
- Punto de fallo: se ordena por nombre visible o por id sin mirar la primera aparición.
- Precondiciones: apariciones `per-b`@1, `per-a`@2, `per-c`@2, `esc-z`@1, `esc-a`@3.
- Cómo validarlo: `ficha.construir` con esas apariciones y canon mínimo.
- Resultado esperado: personajes `[per-b, per-a, per-c]`; lugares `[esc-z, esc-a]`.
- Tipo de prueba sugerida: unitaria
- Severidad: Baja — afecta a la presentación, no al contenido.

#### VAL-33: ADR 0003
- Requisito: R31 — RF-31 «con las secciones Contexto, Opciones, Criterios, Decisión, Alternativas descartadas, Consecuencias y Cuándo reabrirla, y en Opciones al menos la web servida por la API, el PDF y el epub ampliado» (§5); CA-31
- Punto de fallo: los nombres de las opciones aparecen en otra sección y el test busca en todo el fichero.
- Precondiciones: ADR escrito.
- Cómo validarlo: `test_adr_de_entrega`; extraer el bloque entre `## Opciones` y el siguiente `## `.
- Resultado esperado: frontmatter con `adr: 0003`, `estado: aceptada`, `specs: [0006]`; los 7 encabezados presentes; el bloque de Opciones contiene «web servida por la API», «PDF» y «epub».
- Tipo de prueba sugerida: unitaria (contrato)
- Severidad: Media — documentación obligatoria de la auditoría (LEC-01).

#### VAL-34: La API no gana rutas
- Requisito: R32 — RF-32 «no debe añadir rutas a la API, de modo que `backend/api/openapi.json` quede idéntico» (§5); CA-32
- Punto de fallo: una ruta de descarga del PDF se añade con `include_in_schema=False` y no aparece en `openapi.json`.
- Precondiciones: código tras la spec.
- Cómo validarlo: `test_openapi_al_dia`; recorrer `app.routes` (incluidas las no documentadas) y sus `path`.
- Resultado esperado: `openapi.json` sin diferencias; 0 rutas cuyo `path` contenga `libro`, `pdf`, `ficha`, `portada` o `apariciones`; la lista de rutas es la misma que antes de la spec (10 `GET` en `novelas.py` y `capitulos.py`).
- Tipo de prueba sugerida: contrato
- Severidad: Crítica — una ruta que escribe o sirve el libro rompe la regla de API de solo lectura.

#### VAL-35: Documentación de D17
- Requisito: R33 — RF-33 «describir el exportador PDF, la tabla `apariciones` y el campo `dedicatoria`, en el mismo commit que el código que los introduce» (§5); CA-33; D17
- Punto de fallo: alguna sección de la lista de D17 (p. ej. `docs/architecture.md` §12.4 o `AGENTS.md` § CLI) queda sin tocar.
- Precondiciones: commits de la spec.
- Cómo validarlo: para cada sección de D17, `git log --format=%h -- <fichero>` y comparar con el commit que introduce el código; `grep -n "pendiente\|próximamente"` en las secciones tocadas.
- Resultado esperado: `AGENTS.md` contiene `--formato md|epub|pdf`; `docs/architecture.md` §2, §3.1, §4, §7.1, §8, §11.1 y §12.4, `docs/definitions.md` §4 y §6 y `docs/validators.md` §3.6, §3.8, §4.9 y §5 mencionan el elemento correspondiente; 0 coincidencias nuevas de «pendiente» o «próximamente».
- Tipo de prueba sugerida: revisión manual
- Severidad: Media — documentación desfasada, sin efecto en la ejecución.

#### VAL-36: Tiempo de exportación
- Requisito: R34 — RNF-01 «Tiempo de `novela exportar --formato pdf` en `CliRunner` sobre `demo-terminado`… y sobre 10 capítulos generados de 1.500 palabras | < 10 s»
- Punto de fallo: la comprobación de glifos o la composición es cuadrática en el tamaño del texto.
- Precondiciones: `demo-terminado` y una copia de 10 capítulos con cuerpos de 1.500 palabras.
- Cómo validarlo: medir con `time.perf_counter` la invocación de `CliRunner` en cada caso.
- Resultado esperado: < 10 s en cada uno.
- Tipo de prueba sugerida: integración
- Severidad: Baja — hay margen amplio y no bloquea la entrega.

#### VAL-37: Tamaño del PDF
- Requisito: R35 — RNF-02 «Tamaño de `export/novela.pdf` para 10 capítulos de 1.500 palabras, con la fuente en subconjunto | ≤ 5 MB»
- Punto de fallo: la fuente (y sus variantes) se embebe completa.
- Precondiciones: la copia de 10 capítulos de VAL-36.
- Cómo validarlo: `Path("export/novela.pdf").stat().st_size`; inspeccionar `/FontFile2` de cada fuente con `pypdf`.
- Resultado esperado: ≤ 5 242 880 bytes; el `/BaseFont` de cada fuente lleva prefijo de subconjunto de 6 letras mayúsculas y `+`.
- Tipo de prueba sugerida: integración
- Severidad: Baja — afecta al envío, no a la lectura.

#### VAL-38: Ninguna acción externa, tampoco a nivel de documento
- Requisito: R36 — RNF-03 «Anotaciones o acciones `URI`, `Launch`, `JavaScript`, `SubmitForm` o `GoToR` en el PDF… | 0»
- Punto de fallo: CA-05 solo mira anotaciones de página; una acción en `/OpenAction`, en `/AA` del catálogo o en `/Names/JavaScript` pasa inadvertida.
- Precondiciones: el PDF de CA-05.
- Cómo validarlo: recorrer todos los objetos del PDF con `pypdf` (`reader.trailer["/Root"]`, `/OpenAction`, `/AA`, `/Names`, `/Annots` de cada página y las entradas `/A` del outline).
- Resultado esperado: 0 diccionarios con `/S` ∈ {`/URI`, `/Launch`, `/JavaScript`, `/SubmitForm`, `/GoToR`}; el catálogo no tiene `/OpenAction` de tipo acción ni `/AA` ni `/Names/JavaScript`.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — un libro de regalo con acciones externas es una brecha de seguridad para el destinatario.

#### VAL-39: Todos los enlaces resuelven a escala
- Requisito: R37 — RNF-04 «Enlaces del índice y de la ficha cuyo destino no es la primera página… sobre el 100 % de los enlaces | 0»
- Punto de fallo: con un índice de más de una página, los números de página calculados antes de componer quedan desplazados.
- Precondiciones: `demo-terminado` con 24 capítulos y la tabla `apariciones` poblada (construido tras la spec).
- Cómo validarlo: exportar; para cada `Link` del índice y de la ficha, resolver el destino y comprobar que el texto de esa página empieza por el título que nombra el enlace.
- Resultado esperado: 0 enlaces cuyo destino no coincide, sobre el 100 % de los `Link`.
- Tipo de prueba sugerida: integración
- Severidad: Alta — enlaces rotos invalidan la navegación.

#### VAL-40: El secreto no está ni en el texto ni en metadatos
- Requisito: R38 — RNF-05 «Cadenas de `canon/misterio.md` y de los campos excluidos… en el texto extraído del PDF | 0»
- Punto de fallo: un campo excluido llega a `/Subject`, `/Keywords` o a un marcador, que la extracción de texto de página no cubre.
- Precondiciones: `demo-regalo`.
- Cómo validarlo: extraer el texto de todas las páginas, `reader.metadata` y los títulos de `reader.outline`; buscar cada cadena de `canon/misterio.md` de la fixture y de los campos de RF-28 de todas las fichas.
- Resultado esperado: 0 coincidencias en las tres fuentes.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — revelaría la solución.

#### VAL-41: Fixtures nuevas sin datos reales
- Requisito: R40 — RNF-07 «Coincidencias de los patrones de 0005 RNF-05… en las fixtures nuevas | 0»
- Punto de fallo: los borradores nuevos de CA-14 o la dedicatoria añaden un correo o teléfono de ejemplo realista.
- Precondiciones: fixtures de T-06 y T-07.
- Cómo validarlo: ejecutar el escáner de fixtures de la 0005 sobre `backend/tests/fixtures/brief/` y los ficheros nuevos.
- Resultado esperado: 0 coincidencias de correo, teléfono de 9 dígitos y DNI/NIE; los únicos nombres de persona del destinatario son «Aurora Ficticia» y «Bruno Ficticio».
- Tipo de prueba sugerida: contrato
- Severidad: Crítica — datos personales reales en el repositorio.

#### VAL-42: Títulos extraíbles como texto
- Requisito: R41 — RNF-08 «títulos de capítulo extraíbles como texto con `pypdf` | 100 %»
- Punto de fallo: la fuente se embebe sin `ToUnicode` y el texto extraído sale como glifos sin mapear, sobre todo en «í», «ó» y «—».
- Precondiciones: PDF de CA-01.
- Cómo validarlo: extraer el texto de las páginas de inicio de capítulo y de la ficha.
- Resultado esperado: «La linterna, noche 1..3», «Índice», «Personajes y lugares» y «Tomás Reyes» aparecen literales; 0 caracteres U+FFFD en todo el texto.
- Tipo de prueba sugerida: integración
- Severidad: Media — accesibilidad; el libro se lee igual en pantalla.

#### VAL-43: Contratos existentes intactos
- Requisito: R42 — RNF-09 «Diferencias en `state.schema.json`, `delta.schema.json`, `config.schema.json` y `backend/api/openapi.json`; tests de `test_export.py` modificados | 0; 0»
- Punto de fallo: `Aparicion` se registra en `esquemas.py` o `Libro` se exporta a `backend/schemas/` al regenerar en T-06.
- Precondiciones: commit anterior a la spec.
- Cómo validarlo: `git diff --exit-code <base> -- backend/schemas/state.schema.json backend/schemas/delta.schema.json backend/schemas/config.schema.json backend/api/openapi.json backend/novela/slices/export/test_export.py`; `git diff --name-status <base> -- backend/schemas/`.
- Resultado esperado: el primer comando sale con 0; el segundo solo lista `brief.schema.json` y `brief-borrador.schema.json`.
- Tipo de prueba sugerida: contrato
- Severidad: Crítica — cambiar un contrato rompe el frontend y los agentes.

#### VAL-44: Sin dependencias nativas
- Requisito: R43 — RNF-10 «Dependencias nuevas que exigen bibliotecas nativas del sistema (GTK, Pango, Cairo) o compilar en `uv sync` en Windows | 0»
- Punto de fallo: una dependencia transitiva (`Pillow`, `fonttools`) no tiene rueda para la versión de Python fijada y `uv` compila desde sdist.
- Precondiciones: `backend/uv.lock` actualizado.
- Cómo validarlo: `uv sync --locked --no-build` en Windows y en `ubuntu-latest`; revisar en `uv.lock` las ruedas de `fpdf2` y sus dependencias.
- Resultado esperado: los dos `uv sync` salen con 0; cada paquete nuevo tiene rueda `cp312-win_amd64` o `py3-none-any`.
- Tipo de prueba sugerida: integración (CI)
- Severidad: Alta — sin instalación en Windows el operador no puede exportar.

#### VAL-45: Consulta indexada
- Requisito: R44 — RNF-11 «Tiempo de `estado_db.apariciones` con 99 capítulos y 50 entidades por capítulo, en solo lectura | < 50 ms»
- Punto de fallo: la medición incluye la primera apertura en caliente o se hace sobre `:memory:`.
- Precondiciones: base en disco con 4 950 filas.
- Cómo validarlo: abrir con `solo_lectura=True`; medir `apariciones(conn, 99)` con `time.perf_counter`, mediana de 5 llamadas.
- Resultado esperado: mediana < 50 ms y 4 950 filas devueltas.
- Tipo de prueba sugerida: unitaria (plataforma)
- Severidad: Baja — no afecta a la corrección.

#### VAL-46: Suite verde y sin modelos
- Requisito: R45 — RNF-12 «Fallos de `uv run pytest`, errores de `mypy --strict` y de `ruff`; tests que importan un cliente de modelos | 0; 0; 0; 0»
- Punto de fallo: `fpdf2` o `pypdf` sin tipos hacen fallar `mypy --strict`, o se silencian con `ignore_errors` globales.
- Precondiciones: rama con la spec implementada.
- Cómo validarlo: `uv run pytest --hypothesis-profile=ci`, `uv run mypy --strict .`, `uv run ruff check .` y `test_sin_clientes_de_modelo`.
- Resultado esperado: los cuatro salen con 0; `pyproject.toml` solo añade overrides de mypy por módulo nombrado.
- Tipo de prueba sugerida: integración (CI)
- Severidad: Crítica — no se commitea en rojo.

### Verificadores
#### VER-1: El test del ADR se ve en rojo y comprueba las Consecuencias
- Paso del plan: P1 — T1.1 «en Consecuencias, la revisión humana del PDF antes de entregarlo… y el riesgo de licencia de `fpdf2`» (§5, Fase 1)
- Punto de fallo: el test solo mira encabezados y las dos consecuencias que el plan exige quedan fuera del ADR.
- Precondiciones: rama de T1.1.
- Cómo verificarlo: ejecutar `test_adr_de_entrega` antes de crear el ADR; revisar el bloque `## Consecuencias` y el frontmatter contra `docs/adr/0002-los-gates-los-decide-el-cli.md:1-8`.
- Resultado esperado: el test falla antes (fichero ausente) y pasa después; Consecuencias contiene «revisión humana» y «LGPL»; el frontmatter tiene las 6 claves `adr`, `titulo`, `estado`, `fecha`, `decide`, `specs`.
- Tipo de prueba sugerida: revisión manual
- Severidad: Baja — documentación.

#### VER-2: `IF NOT EXISTS` en el esquema y 12 casos de append-only
- Paso del plan: P2 — T2.1 «`CREATE TABLE IF NOT EXISTS apariciones (…) STRICT`… `test_append_only_por_trigger` pasa con 12 casos (6 tablas × 2 operaciones)» (§5, Fase 2)
- Punto de fallo: el bloque nuevo usa `CREATE` sin `IF NOT EXISTS` y `asegurar_apariciones` falla la segunda vez; o `FILAS` no incluye `apariciones`.
- Precondiciones: rama de T2.1.
- Cómo verificarlo: `uv run pytest backend/novela/plataforma/test_esquema.py -v`; ejecutar dos veces el bloque marcado sobre la misma base.
- Resultado esperado: 12 casos parametrizados + `test_apariciones_append_only` en verde; la segunda ejecución del bloque no lanza error; `test_state_schema_al_dia` en verde sin `REGENERAR`.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — sin idempotencia, cada `aplicar-delta` tras el primero fallaría.

#### VER-3: `asegurar_apariciones` no hace `COMMIT` implícito
- Paso del plan: P3 — PD1 «se trocea con `sqlite3.complete_statement` (los triggers llevan `;` dentro de `BEGIN … END`)»; T2.2 «test de… `ROLLBACK` deja la base sin la tabla»
- Punto de fallo: con `isolation_level=None` (`estado_db.py:26`), usar `executescript` hace `COMMIT` del `BEGIN IMMEDIATE`; o el troceado parte un trigger por el `;` interno o se come los comentarios marcadores.
- Precondiciones: base sin la tabla.
- Cómo verificarlo: dentro de `estado_db.transaccion(conn)` llamar a `asegurar_apariciones` y lanzar una excepción; contar las sentencias que produce el troceado.
- Resultado esperado: tras la excepción, `SELECT count(*) FROM sqlite_master WHERE name LIKE 'apariciones%'` = 0; el troceado produce exactamente 4 sentencias (tabla, índice, 2 triggers); `grep executescript` en `asegurar_apariciones` sin coincidencias.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — rompe la atomicidad de RF-22.

#### VER-4: Base migrada igual a base creada
- Paso del plan: P3 — T2.2 «`sqlite_master` de una base migrada coincide con la de `crear` en lo que toca a `apariciones`»
- Punto de fallo: el DDL de `asegurar_apariciones` diverge del de `inicializar` (espacios, nombres de trigger).
- Precondiciones: una base de `crear` y otra a la que se quitan los 4 objetos y se llama a `asegurar_apariciones`.
- Cómo verificarlo: `SELECT type, name, sql FROM sqlite_master WHERE name LIKE 'apariciones%' ORDER BY name` en las dos.
- Resultado esperado: las dos listas de tuplas son idénticas y tienen 4 elementos.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — divergencia silenciosa entre workspaces nuevos y migrados.

#### VER-5: Validador de prefijo de `Aparicion`
- Paso del plan: P3 — T2.2 «`entidad: PersonajeId | EscenarioId`, `tipo: Literal[…]`… validador de prefijo»
- Punto de fallo: `EscenarioId` acepta un id de escena (`esc-01-3`) o el validador no casa `tipo` con el prefijo.
- Precondiciones: modelo `Aparicion`.
- Cómo verificarlo: construir `Aparicion(entidad="per-elena-vidal", tipo="escenario", capitulo=1)`, `Aparicion(entidad="esc-01-3", tipo="escenario", capitulo=1)` y `Aparicion(entidad="esc-casa-del-faro", tipo="escenario", capitulo=1)`.
- Resultado esperado: las dos primeras lanzan `ValidationError`; la tercera se construye.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — filas mal tipadas darían una ficha con lugares como personajes.

#### VER-6: `EstadoIlegible` sin tabla y en solo lectura
- Paso del plan: P3 — T2.2 «`apariciones(conn, hasta)`… `EstadoIlegible` si la tabla no existe»
- Punto de fallo: se deja escapar `sqlite3.OperationalError: no such table`, que `salida.py` no traduce a 4.
- Precondiciones: base sin la tabla, abierta con `solo_lectura=True`.
- Cómo verificarlo: llamar a `estado_db.apariciones(conn, 3)`.
- Resultado esperado: lanza `EstadoIlegible` (no `OperationalError`) y la base no gana la tabla.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — acabaría en traceback y salida 1 en vez de 4.

#### VER-7: Derivación pura, en orden y con 200 casos reales
- Paso del plan: P4 — T2.3 «en el orden de spec §8.4… sin duplicados… `@settings(max_examples=200)`»; PD2 «recibe la ficha ya validada y no lee disco»
- Punto de fallo: el perfil `default` de `conftest.py:18-20` corre 50 casos si falta el decorador; `apariciones` importa `workspace` o abre ficheros; `Derivados` cambia.
- Precondiciones: rama de T2.3.
- Cómo verificarlo: `uv run pytest backend/novela/slices/delta/test_apply.py::test_apariciones_property --hypothesis-show-statistics`; `grep -n "import" backend/novela/slices/delta/apply.py`; `git diff` de la dataclass `Derivados`.
- Resultado esperado: las estadísticas muestran ≥ 200 ejemplos pasados; `apply.py` no importa `pathlib`, `open` ni `plataforma`; `Derivados` sin diferencias; con `pov=ELENA`, escenas `[FARO: ELENA, TOMAS]` y delta `{TOMAS: ubicacion=PUERTO, ultima_aparicion=N}` la tupla es `(ELENA, TOMAS, FARO, PUERTO)` en ese orden.
- Tipo de prueba sugerida: propiedad + unitaria
- Severidad: Alta — `docs/validators.md` §3.6 exige propiedad en `apply.py`.

#### VER-8: Registro dentro de la transacción y fuera de `guardar`
- Paso del plan: P5 — T2.4 «leer `plan/capitulos/NN.md`… antes de `estado_db.abrir`… dentro del mismo `with estado_db.transaccion(conn)`»; §3 «`:168` lista las tablas que `guardar` vacía y reescribe; `apariciones` no debe entrar ahí»
- Punto de fallo: `apariciones` se añade a la lista de `guardar` y el trigger `BEFORE DELETE` aborta todo `aplicar-delta`; o el registro se hace en un segundo `with`.
- Precondiciones: rama de T2.4.
- Cómo verificarlo: leer la lista de `estado_db.py:168`; inyectar un fallo en `registrar_apariciones` (monkeypatch que lanza) y aplicar el capítulo 2; ejecutar `test_transaccion_todo_o_nada` y `test_corte_dentro_de_la_transaccion`.
- Resultado esperado: `apariciones` no está en la lista; con el fallo inyectado, la huella de `estado.db` es la de antes y `memoria/` no cambia; los dos tests en verde.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — un estado guardado sin sus apariciones, o una base que aborta siempre, corrompe o bloquea el bucle.

#### VER-9: Orden respecto a `violaciones` (spec 0002)
- Paso del plan: P5 — T2.4 «tras `violaciones` y dentro del mismo `with estado_db.transaccion(conn)`»
- Punto de fallo: el registro se coloca antes de `violaciones` y un delta rechazado deja la tabla migrada o filas escritas si la salida no hace rollback.
- Precondiciones: un delta que `violaciones` rechaza.
- Cómo verificarlo: aplicar ese delta sobre una base sin la tabla y sobre otra con la tabla.
- Resultado esperado: salida ≠ 0; `count(*)` de `apariciones` sin cambios en la segunda; la primera sigue sin la tabla.
- Tipo de prueba sugerida: integración
- Severidad: Media — estado fantasma de un capítulo rechazado.

#### VER-10: `DEMO` y `HUERFANA` no cambian con el parámetro de escenas
- Paso del plan: P6 — T2.5 «un parámetro opcional de escenas por capítulo con valor por defecto que no cambie `DEMO` ni `HUERFANA`… (y `dialogo` ⊆ `personajes`)»
- Punto de fallo: el valor por defecto altera el orden o el contenido de las escenas generadas y cambian goldens.
- Precondiciones: rama de T2.5.
- Cómo verificarlo: `git diff --exit-code backend/tests/fixtures/` sobre los goldens (incluido `08-escritor.md`); comparar el `plan/capitulos/*.md` de `demo-terminado` antes y después; validar las fichas de `REGALO` con `FichaCapitulo`.
- Resultado esperado: 0 diferencias en goldens y en las fichas de `demo-terminado`; las 3 fichas de `REGALO` validan.
- Tipo de prueba sugerida: integración
- Severidad: Media — goldens rotos enmascaran regresiones de otros tests.

#### VER-11: Caracterización de `fpdf2` y de la fuente
- Paso del plan: P7 — T3.1 «Tests de caracterización… enlace interno a una página, marcador, `/Lang`, `CreationDate` fijable, subconjunto… bytes idénticos… y que la fuente no tiene glifo para U+1F56F»
- Punto de fallo: los tests de caracterización se escriben contra el comportamiento observado sin fijar la versión, y un `uv lock --upgrade` los cambia; o la fuente sí cubre U+1F56F y CA-09 no prueba nada.
- Precondiciones: `fpdf2` instalado.
- Cómo verificarlo: `uv run pytest -k caracterizacion`; comprobar `0x1F56F not in cmap` de la TTF; leer la versión exacta de `fpdf2` en `uv.lock` y en el `/Producer` del PDF.
- Resultado esperado: tests en verde; U+1F56F ausente del `cmap`; la versión de `uv.lock` coincide con la del `/Producer`; existe `fuentes/LICENSE`.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — todo el paso 3 descansa en estos supuestos.

#### VER-12: Importación directa de `fontTools` declarada
- Paso del plan: P7 — PD3 «Si se importa `fontTools` directamente, se declara en `dependencies` y… se añade su override de mypy»
- Punto de fallo: `pdf.py` importa `fontTools` apoyándose en la dependencia transitiva de `fpdf2`.
- Precondiciones: rama de T3.1/T3.3.
- Cómo verificarlo: `grep -rn "fontTools" backend/novela`; revisar `[project].dependencies` y overrides de mypy en `backend/pyproject.toml`.
- Resultado esperado: si hay importación, `fonttools` está en `dependencies` y existe su override (o `mypy --strict` pasa sin él); si no la hay, no se añade nada.
- Tipo de prueba sugerida: revisión manual
- Severidad: Baja — rompe solo si `fpdf2` deja de arrastrarla.

#### VER-13: `ficha.construir` no recibe el canon entero
- Paso del plan: P8 — T3.2 «Solo recibe `nombre`, `alias` y `descripcion`, nunca el modelo de canon entero (RF-28)»
- Punto de fallo: la firma acepta `Personaje` o `Escenario` completos y un cambio futuro puede volcar `secreto` o `detalle_sensorial`.
- Precondiciones: `ficha.py`.
- Cómo verificarlo: inspeccionar las anotaciones de `ficha.construir` con `typing.get_type_hints`; `grep -n "Personaje\|Escenario\|Mundo" backend/novela/slices/export/ficha.py`.
- Resultado esperado: los parámetros de canon son mapas `id → (nombre, alias)` e `id → (nombre, descripcion)` de `str`; 0 coincidencias de los modelos de canon en `ficha.py`.
- Tipo de prueba sugerida: revisión manual + unitaria
- Severidad: Alta — es la barrera estructural del secreto en la ficha.

#### VER-14: Ids ausentes con la lectura por id
- Paso del plan: P8 — PD6 «leer solo `canon/personajes/<id>.md`… La comprobación de RF-29 vive en `ficha.construir`… y `cmd.py` la traduce en `WorkspaceInvalido` (4)»
- Punto de fallo: `cmd.py` intenta abrir `canon/personajes/<id>.md` antes de llamar a `ficha.construir` y el `FileNotFoundError` sale sin traducir, con salida 1.
- Precondiciones: `demo-regalo` sin `per-ines-mar.md` y sin `per-tomas-reyes.md`.
- Cómo verificarlo: exportar; llamar también a `ficha.construir` con esos dos ids sin canon.
- Resultado esperado: salida 4; el mensaje contiene `per-ines-mar` y `per-tomas-reyes`; la excepción pura lista los dos ids.
- Tipo de prueba sugerida: integración + unitaria
- Severidad: Media — error confuso en un caso reparable.

#### VER-15: Tokens fuera de la lista blanca no pierden texto
- Paso del plan: P9 — PD4 «Se recorren los tokens: `heading`, `paragraph`, `em`, `strong` y `hr`… se componen; `link_open/close` se ignoran…; `image`…; `html_inline` y `html_block` se emiten como texto literal»
- Punto de fallo: los bloques no listados (`bullet_list`, `blockquote`, `fence`, `code_block`, `hardbreak`) se descartan y su texto desaparece del libro.
- Precondiciones: cuerpo de prueba con `- uno`, `> dos`, un bloque indentado `    tres`, una valla ```` ``` ```` con `cuatro` y un salto duro.
- Cómo verificarlo: pasar el cuerpo por la función pura cuerpo → bloques y por `pdf.construir`; extraer texto.
- Resultado esperado: el texto extraído contiene «uno», «dos», «tres» y «cuatro».
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — pérdida silenciosa de texto del capítulo.

#### VER-16: Enlaces hacia delante e índice multipágina
- Paso del plan: P9 — T3.3 «índice con un enlace por capítulo y uno a la ficha… destinos de todos los `Link` (página cuyo texto empieza por el título nombrado)»
- Punto de fallo: el índice se compone antes que los capítulos; si los destinos se calculan como número de página fijo y el índice ocupa 2 páginas, todos se desplazan una.
- Precondiciones: `Libro` en memoria con 99 capítulos de 1 párrafo.
- Cómo verificarlo: `pdf.construir`; contar páginas del índice; resolver cada destino.
- Resultado esperado: el índice ocupa ≥ 2 páginas y los 100 enlaces del índice apuntan a la página cuyo texto empieza por el título correspondiente.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — enlaces rotos en novelas largas.

#### VER-17: La comprobación de glifos ignora controles y cubre los textos fijos
- Paso del plan: P9 — PD3 «`pdf.py` recorre título, dedicatoria, títulos, cuerpos y ficha, y lanza… `GlifoAusente(seccion, codigo)`»
- Punto de fallo: el salto de línea de la dedicatoria (`U+000A`) o un tabulador no están en el `cmap` y disparan un falso `GlifoAusente`; o los textos fijos («Índice», «Aparece en:», «—») no se comprueban.
- Precondiciones: `Libro` con la dedicatoria de §7 y un cuerpo con `\t`, U+00A0 y «é» en forma NFD (`e` + U+0301).
- Cómo verificarlo: `pdf.construir`; comprobar que `U+2014`, `U+00CD` y `U+00BF` están en el `cmap`.
- Resultado esperado: no se lanza `GlifoAusente`; los tres códigos fijos están en el `cmap`; con U+1F56F en la dedicatoria se lanza `GlifoAusente("portada", "U+1F56F")`.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — un falso positivo impediría exportar toda novela con dedicatoria multilínea.

#### VER-18: `CreationDate` desde el manifiesto
- Paso del plan: P10 — PD7 «`cmd.py` lee `runs/<run_id>/manifest.json`… y convierte `creado`… con `datetime.fromisoformat`. Si el manifiesto falta, la salida es 4»
- Punto de fallo: `fromisoformat` con sufijo `Z` o conversión a hora local cambia la fecha según la zona de la máquina y rompe el determinismo entre equipos.
- Precondiciones: `demo-regalo`; copia con `creado` = `2026-09-24T10:00:00Z`; copia sin el manifiesto.
- Cómo verificarlo: exportar con `TZ=UTC` y `TZ=Europe/Madrid`; leer `/CreationDate`; exportar la copia sin manifiesto.
- Resultado esperado: `/CreationDate` = `D:20260924100000Z` (o equivalente con desfase `+00'00'`) y sha256 igual en las dos zonas; sin manifiesto, salida 4 y sin PDF.
- Tipo de prueba sugerida: integración
- Severidad: Media — degrada RF-07.

#### VER-19: Orden de comprobaciones y liberación del lock
- Paso del plan: P10 — T3.4 «Con `pdf`: bajo el lock, checkpoint, capítulos 1..N, `config.yaml`, `estado_db.apariciones`…, RF-25…, canon…, manifiesto…, `ficha.construir`, `pdf.construir`, `ws.escribir`»
- Punto de fallo: una salida 1 o 4 dentro del bloque deja `estado/state.lock` tomado y el siguiente `aplicar-delta` sale con 3.
- Precondiciones: casos de VAL-7, VAL-10, VAL-27 y VAL-31.
- Cómo verificarlo: tras cada salida de error, ejecutar `novela exportar <slug> --formato md` y comprobar la existencia de `estado/state.lock`.
- Resultado esperado: el segundo comando no sale con 3; `state.lock` no queda tomado por ningún proceso vivo.
- Tipo de prueba sugerida: integración
- Severidad: Alta — bloquearía el bucle de escritura.

#### VER-20: Localización real del test VAL-37 de la 0005
- Paso del plan: P11 — T4.1 «ajuste del test de la 0005 que limita los campos personales (VAL-37, `docs/validators.md:1139`)»
- Punto de fallo: la referencia no existe: `docs/validators.md` tiene 798 líneas y VAL-37 está en `docs/specs/0005/validators.md:342`; el ajuste puede hacerse en otro test o no hacerse.
- Precondiciones: 0005 implementada.
- Cómo verificarlo: `grep -rn "rasgos" backend/tests backend/novela` para localizar el test que implementa VAL-37; ejecutarlo tras añadir `dedicatoria`.
- Resultado esperado: se identifica un único test; tras T4.1 pasa y su lista de campos personales es `nombre`, `edad`, `rasgos`, `recuerdos`, `dedicatoria`.
- Tipo de prueba sugerida: revisión manual + unitaria
- Severidad: Baja — la suite en rojo lo delataría igualmente.

#### VER-21: Regeneración de esquemas del brief
- Paso del plan: P11 — T4.1 «`REGENERAR=1 uv run pytest tests/test_contratos.py`… `brief.schema.json` con `dedicatoria` en `required`»
- Punto de fallo: la regeneración toca además `state.schema.json` o `delta.schema.json`, o `docs/definitions.md` no se actualiza en el mismo commit.
- Precondiciones: commit de T4.1.
- Cómo verificarlo: `git show --stat <commit T4.1>`.
- Resultado esperado: en `backend/schemas/` solo cambian `brief.schema.json` y `brief-borrador.schema.json`; `docs/definitions.md` está en el mismo commit.
- Tipo de prueba sugerida: revisión manual
- Severidad: Media — contrato y definición desalineados.

#### VER-22: Saneado de errores del brief
- Paso del plan: P12 — PD5 «lee `brief/brief.json` con `Brief.model_validate_json` dentro de un `try`, y ante `ValidationError` lanza `WorkspaceInvalido` con la ruta relativa y solo los `loc`»
- Punto de fallo: el saneado se aplica solo a errores de campo y no al `json_invalid`, cuyo `input_value` arrastra el fichero entero; o se sigue usando `ws.leer_json` en otro punto (p. ej. para comprobar existencia).
- Precondiciones: casos (a) y (b) de VAL-17.
- Cómo verificarlo: `grep -n "leer_json(.*Brief" backend/novela/slices/export/cmd.py`; ejecutar los dos casos y leer el mensaje de `WorkspaceInvalido`.
- Resultado esperado: 0 coincidencias de `leer_json` con `Brief`; los mensajes contienen `brief/brief.json` y solo rutas `loc` (p. ej. `dedicatoria.cita`), sin «input_value».
- Tipo de prueba sugerida: unitaria + integración
- Severidad: Crítica — es la vía conocida de fuga del dato personal (`workspace.py:190-194`).

#### VER-23: `CONTRATO` incluye al `entrevistador`
- Paso del plan: P13 — T4.3 «`test_entrevistador_nombra_la_dedicatoria` en `test_contratos.py`»; §3 «`CONTRATO`, sin `entrevistador` todavía»
- Punto de fallo: si la 0005 no añadió `entrevistador` a `CONTRATO`, el test nuevo pasa aislado mientras el agente queda fuera del contrato de `.claude/`.
- Precondiciones: 0005 implementada.
- Cómo verificarlo: leer `CONTRATO` en `backend/tests/test_contratos.py`; ejecutar el contrato de agentes.
- Resultado esperado: `entrevistador` está en `CONTRATO`; los tests de contrato del agente pasan.
- Tipo de prueba sugerida: contrato
- Severidad: Baja — depende de la 0005.

#### VER-24: Commit base definido para el diff de RNF-09
- Paso del plan: P14 — T5.1 «`git diff --exit-code <base> -- backend/schemas/state.schema.json …`»
- Punto de fallo: `<base>` no está definido (la spec no está commiteada) y se compara contra `HEAD~1`, lo que solo cubre el último commit.
- Precondiciones: rama de la spec.
- Cómo verificarlo: fijar `<base>` como `git merge-base main <rama>`; ejecutar el comando.
- Resultado esperado: el sha de `<base>` queda anotado en el commit de T5.1; el comando sale con 0.
- Tipo de prueba sugerida: revisión manual
- Severidad: Media — un cambio de contrato en un commit intermedio pasaría.

#### VER-25: `test_sin_rutas_de_libro` visto en rojo
- Paso del plan: P14 — T5.1 «mirando `app.routes` y no el texto del OpenAPI»; §5 «test primero, visto en rojo»
- Punto de fallo: un test negativo que pasa desde el principio nunca se ha visto fallar y puede no detectar nada (p. ej. si recorre solo `APIRoute` y no `Mount`).
- Precondiciones: rama de T5.1.
- Cómo verificarlo: registrar temporalmente `GET /novelas/{slug}/libro` con `include_in_schema=False` y ejecutar el test; retirarla y repetir.
- Resultado esperado: rojo con la ruta temporal; verde sin ella.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — el test no protegería RF-32.

#### VER-26: Documentación en el commit de cada tarea
- Paso del plan: P3, P5, P10, P11, P13 — PD8 «La documentación de D17 se actualiza en el commit de cada tarea»
- Punto de fallo: un commit intermedio introduce código de superficie sin la documentación asignada.
- Precondiciones: historial de la rama.
- Cómo verificarlo: `git show --stat` de los commits de T2.2, T2.4, T3.4, T4.1 y T4.3.
- Resultado esperado: T2.2 incluye `docs/definitions.md` y `docs/architecture.md`; T2.4, `docs/validators.md`; T3.4, `docs/architecture.md`, `docs/definitions.md` y `AGENTS.md`; T4.1, `docs/definitions.md`; T4.3, `docs/validators.md`.
- Tipo de prueba sugerida: revisión manual
- Severidad: Baja — documentación.

### Matriz de cobertura
| Requisito | Validadores | Verificadores |
|-----------|-------------|---------------|
| R1 — RF-01 PDF atómico de capítulos cerrados | VAL-1, VAL-2 | VER-18, VER-19 |
| R2 — RF-02 orden de secciones | VAL-3 | VER-15, VER-16, VER-17 |
| R3 — RF-03 índice con enlaces | VAL-4 | VER-15, VER-16, VER-17 |
| R4 — RF-04 marcadores e idioma | VAL-5 | VER-11, VER-12, VER-15, VER-16, VER-17 |
| R5 — RF-05 markdown inerte | VAL-6 | VER-15, VER-16, VER-17 |
| R6 — RF-06 sin checkpoint → 1 | VAL-7 | VER-18, VER-19 |
| R7 — RF-07 determinista | VAL-8 | VER-11, VER-12, VER-15, VER-16, VER-17 |
| R8 — RF-08 `--titulo` | VAL-9 | VER-18, VER-19 |
| R9 — RF-09 carácter sin glifo → 1 | VAL-10 | VER-11, VER-12, VER-15, VER-16, VER-17 |
| R10 — RF-10 `md` y `epub` intactos | VAL-11 | VER-18, VER-19, VER-24, VER-25 |
| R11 — RF-11 dedicatoria en portada | VAL-12 | VER-22 |
| R12 — RF-12 sin brief | VAL-13 | VER-18, VER-19 |
| R13 — RF-13 brief inválido → 4 | VAL-14 | VER-22 |
| R14 — RF-14 campo y gates de `dedicatoria` | VAL-15 | VER-20, VER-21 |
| R15 — RF-15 fuera de `idea_semilla` | VAL-16 | VER-20, VER-21 |
| R16 — RF-16 fuera de stdout, stderr y log | VAL-17 | VER-20, VER-21, VER-22 |
| R17 — RF-17 `entrevistador` | VAL-18 | VER-23 |
| R18 — RF-18 tabla `apariciones` | VAL-19 | VER-2 |
| R19 — RF-19 registro en `aplicar-delta` | VAL-20, VAL-21 | VER-7, VER-8, VER-9, VER-10 |
| R20 — RF-20 reaplicar sin duplicar | VAL-22 | VER-7 |
| R21 — RF-21 sin ficha de plan → 4 | VAL-23 | VER-8, VER-9 |
| R22 — RF-22 migración aditiva | VAL-24 | VER-3, VER-4, VER-5, VER-6, VER-8, VER-9 |
| R23 — RF-23 `estado` y API sin tabla | VAL-25 | VER-3, VER-4, VER-5, VER-6 |
| R24 — RF-24 consulta `apariciones` | VAL-26 | VER-3, VER-4, VER-5, VER-6 |
| R25 — RF-25 capítulos sin apariciones → 4 | VAL-27 | VER-18, VER-19 |
| R26 — RF-26 ficha desde apariciones y canon | VAL-28 | VER-13, VER-14, VER-18, VER-19, VER-22 |
| R27 — RF-27 un enlace por aparición | VAL-29 | VER-13, VER-14, VER-15, VER-16, VER-17 |
| R28 — RF-28 sin misterio ni campos excluidos | VAL-30 | VER-13, VER-14, VER-18, VER-19 |
| R29 — RF-29 entidad sin canon → 4 | VAL-31, VAL-21 | VER-13, VER-14, VER-18, VER-19 |
| R30 — RF-30 orden de la ficha | VAL-32 | VER-13, VER-14 |
| R31 — RF-31 ADR 0003 | VAL-33 | VER-1 |
| R32 — RF-32 API sin rutas | VAL-34 | VER-24, VER-25 |
| R33 — RF-33 documentación de D17 | VAL-35 | VER-3, VER-4, VER-5, VER-6, VER-8, VER-9, VER-18, VER-19, VER-20, VER-21, VER-23, VER-24, VER-25, VER-26 |
| R34 — RNF-01 exportar < 10 s | VAL-36 | VER-18, VER-19 |
| R35 — RNF-02 PDF ≤ 5 MB | VAL-37 | VER-18, VER-19 |
| R36 — RNF-03 0 acciones externas | VAL-38 | VER-15, VER-16, VER-17 |
| R37 — RNF-04 enlaces resuelven | VAL-39 | VER-15, VER-16, VER-17 |
| R38 — RNF-05 0 cadenas del secreto | VAL-40 | VER-18, VER-19 |
| R39 — RNF-06 dedicatoria solo en el libro | VAL-16, VAL-17 | VER-20, VER-21, VER-22 |
| R40 — RNF-07 fixtures sin datos reales | VAL-41 | VER-20, VER-21, VER-24, VER-25 |
| R41 — RNF-08 accesibilidad | VAL-42 | VER-15, VER-16, VER-17 |
| R42 — RNF-09 contratos intactos | VAL-43 | VER-24, VER-25 |
| R43 — RNF-10 sin dependencias nativas | VAL-44 | VER-11, VER-12 |
| R44 — RNF-11 consulta < 50 ms | VAL-45 | VER-3, VER-4, VER-5, VER-6 |
| R45 — RNF-12 suite verde sin modelos | VAL-46 | VER-24, VER-25 |

### Preguntas abiertas
- Q1 — ¿El límite de 120 caracteres de `--titulo` se mide antes o después de quitar espacios, y la portada usa el título recortado? (R8, RF-08): «vacío tras quitar espacios o supera 120 caracteres» admite las dos lecturas, y `" " * 5 + "a" * 118` sale 0 o 2 según cuál.
- Q2 — Si el carácter sin glifo está en el `titulo` del frontmatter de un capítulo, que aparece en el índice, en el capítulo, en el marcador y en la ficha, ¿qué sección nombra el mensaje, y se listan todas las apariciones o solo la primera? (R9, RF-09): la spec solo prevé «el capítulo (o "portada" o "ficha")».
- Q3 — ¿Cómo se representan las listas, citas, bloques de código y tablas del markdown, que RF-05 no enumera? (R5, RF-05): la lista de elementos admite omitirlos, mostrarlos como párrafos planos o darles formato propio.
- Q4 — ¿Qué hace la portada con una dedicatoria que no cabe en la página 1 (p. ej. 600 caracteres con 200 saltos de línea)? (R11, RF-02, RF-11): se puede reducir la fuente, desbordar a la página 2 (contra CA-02 y CA-11) o fallar.
- Q5 — Cuando la tabla `apariciones` no existe, ¿el mensaje de salida 4 nombra todos los capítulos cerrados o solo indica que falta la tabla? (R25, RF-25): «nombrar esos capítulos» solo es inequívoco en el caso de capítulos sin filas; CA-25 solo lo exige para el primero.
- Q6 — ¿RNF-07 aplica a `fabrica.REGALO` en `fabrica.py`, cuyos personajes no están en la lista de nombres ficticios de la 0005 §13? (R40, RNF-07): «las fixtures nuevas» incluye o no la fábrica, y en el primer caso el escáner los marcaría (el plan asume que no, su P7).
- Q7 — ¿`novela exportar` crea un run con `harness.log`? (R16, CA-16): CA-16 lee «el `harness.log` de sus runs» también para la exportación de CA-11; si no crea run, esa comprobación no tiene objeto y habría que decir qué log se revisa.
- Q8 — ¿Qué hace la exportación en PDF si falta el manifiesto del run del último checkpoint? (R7, §8.4, D14): la spec fija la fecha a su `creado` pero no el caso sin manifiesto; salir con 4 (el plan) o usar otra fecha son ambas compatibles.
- Q9 — ¿Debe `aplicar-delta` rechazar una ficha `plan/capitulos/NN.md` cuyo `capitulo` no es N? (R21, RF-21): RF-21 solo pide que exista y valide contra `FichaCapitulo`, y una ficha mal numerada daría apariciones de otro capítulo.
- Q10 — Si el delta de un capítulo se regenera y se vuelve a aplicar con otros personajes, ¿deben seguir en la ficha las apariciones del delta anterior? (R20, RF-20): «no debe… borrar filas» las conserva, pero la ficha mostraría una aparición que el estado vigente ya no respalda.
- Q11 — Si una ficha de `canon/personajes/` que no tiene apariciones no valida, ¿la exportación falla con 4 («canon ilegibles», §8.4, leyendo `canon/personajes/*.md` según §8.5) o la ignora? (R26, R29): ver D2.


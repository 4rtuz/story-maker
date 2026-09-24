# Validadores y verificadores

## 0004
Spec: `docs/specs/0004/spec.md` (análisis sobre la v4; actualizado a la v5, `aceptada`) y `docs/specs/0004/decisions.md` (D1–D56) · Plan: `docs/specs/0004/plan/` (`README.md` y fase-1 a fase-7) · Fecha de análisis: 2026-09-24

Todas las discrepancias (D1 a D12) y todas las preguntas (Q1 a Q20) están resueltas en la v5 de la spec por las decisiones D29 a D56. Los hallazgos de diseño VER-8, VER-24, VER-25, VAL-17, VAL-23 y VAL-24 están incorporados a los criterios y a las tareas (D56). Los validadores y verificadores siguientes ya reflejan esas decisiones.

### Discrepancias spec ↔ plan
| ID | Tipo (requisito sin cubrir / paso sin requisito / contradicción) | Detalle | Ref. spec | Ref. plan |
|----|------|---------|-----------|-----------|
| D1 | contradicción | **Resuelta (D30):** §12 de la spec ya lleva T-17 antes de T-21. La spec fijaba el orden «T-16, T-21, T-17». El plan adelanta T-17 a T-21 para que las referencias visuales salgan de la imagen de Playwright del CI. Las dependencias no cambian, pero §12 de la spec queda desfasada. | RNF-22 — §12, §6 | PD1, T-17, T-21 |
| D2 | contradicción | **Resuelta (D33):** §8.2 y §12 de la spec ya reparten las reglas como PD2. §8.2 describía un `eslint.config.js` con las tres familias de reglas (red, imports, `no-unsanitized`) y §12 lo crea entero en T-04. El plan lo reparte entre T-04, T-06 y T-19 para poder ver el rojo de CA-03 y CA-51. | RF-03, RF-43, RF-51 — §8.2, §12 T-04 | PD2, T-04, T-06, T-19 |
| D3 | contradicción | **Resuelta (D29):** la spec está `aceptada` en la v5, con el formato de carpeta de `AGENTS.md`, y T-01 ya no está bloqueada. La spec seguía sin aceptar y con el formato del redactor (S5), y ningún paso la aceptaba ni decidía el formato. | — §10 S5 y frontmatter | README P2; fase-1 (cabecera) |
| D4 | requisito sin cubrir | **Resuelta (D31, D32):** los recursos ya están en el repositorio y T-19 copia los trazados y borra `iconos/lucide/`; el favicon se deriva con `uv run --with pillow python` y la orden de §8.4. Ningún paso obtenía `outfit-800.woff2` con `OFL.txt` ni los trazados de Lucide con `LICENSE`. Ninguno deriva `favicon.png` con un procedimiento reproducible. T-19 los da por existentes. | RF-56, RF-61, RNF-20 — §5, §8.4 | T-19 (P4, P5) |
| D5 | paso sin requisito | **Resuelta (D33):** §12 asigna §2 y §6 a T-08 y T-17. RF-45 nombra `docs/validators.md` §2 y §6, pero §12 de la spec no asigna su actualización a T-08 ni a T-17, que son las tareas que añaden los jobs. El plan lo añade. | RF-45 — §5, §12 | T-08, T-17 |
| D6 | paso sin requisito | **Resuelta (D33):** §12 asigna el cambio a T-15. Con D8, la frase de Lectura de `docs/architecture.md` §11.2 («capítulos generados») pasa a «cerrados». RF-45 cita §11.2, pero §12 no asigna ese cambio a ninguna tarea. El plan lo pone en T-15. | RF-45, RF-24, RF-27 — §5 | T-15 |
| D7 | contradicción | **Resuelta (D29):** `AGENTS.md` ya recoge la convención `docs/specs/NNNN/` con `plan/` y `validators.md`, y S4 sitúa el plan en `docs/specs/0004/plan/` y los validadores en este fichero. S4 situaba el plan en otra carpeta y ninguna tarea lo corregía. | — §10 S4 | README «Ubicación», P1 |
| D8 | requisito sin cubrir | **Resuelta (D37):** RF-45 incluye §3.6, §4.4, §4.7 y §4.9, que se actualizan en el commit de cierre (T-23). La tabla de métodos de §13 aplica al panel el 6 (§3.6), el 13 (Guardrails, §4.4), el 16 (CI/CD, §4.7) y el 18 (red-team, §4.9). RF-45 no incluye §3.6, §4.4, §4.7 ni §4.9, y la tabla de documentación del plan tampoco. Al cerrar, esas secciones no nombrarán `server.fs.allow`, el cliente único de `GET`, el único punto de inserción de HTML, los jobs nuevos ni la amenaza 2 llevada al navegador. | RF-45 — §5, §13 «Métodos» | README §5 (tabla RF-45) |
| D9 | requisito sin cubrir | **Resuelta (D38):** no hay selección de run; Progreso sigue siempre el de `run_id` mayor y cambia solo al aparecer uno nuevo, y la «entrada de run» sale de RF-22, RF-23 y §8.4. RF-22 y RF-23 hablaban de un run seleccionado, y §8.4 incluía una entrada de run entre los componentes interactivos. Ninguna tarea implementa ni prueba que se pueda elegir un run: T-12 solo sigue el mayor y T-10 solo los lista. | RF-22, RF-23, RF-57 — §5, §8.4 | T-10, T-12 |
| D10 | contradicción | **Resuelta (D39):** §8.2 ya sigue a PD6. §8.2 decía que `panel.py` construye los tres workspaces «con `fabrica.construir` y `fabrica.preparar_capitulo`». PD6 construye `recien-creada` y `grande-999` con `fabrica.cli(…, "nueva", …)`. El plan sigue a §13 y D19 (sin plan ni checkpoints), así que la frase desfasada es la de §8.2. | RF-42 — §8.2, §13 | PD6, T-16 |
| D11 | paso sin requisito | **Resuelta (D40):** `npm run verificar` encadena `tipos:comprobar`, `lint`, `typecheck`, `test`, `build` y `presupuesto`, así que la línea de `AGENTS.md` basta. La regla común 3 del plan exige `npm run build` y `npm run presupuesto` antes de commitear desde T-08. La línea de `AGENTS.md` que fijan D20 y T-04 solo dice `npm run verificar`, así que la convención escrita pedirá menos de lo que se practica. | RF-45 — §8.2 (`AGENTS.md`), D20 | README §5, regla 3; T-04 |
| D12 | contradicción | **Resuelta (D34):** T-02 añade una línea con `TramoDeLog` a `docs/definitions.md`, y §8.2 ya no lo declara sin cambios. `AGENTS.md` pide actualizar `docs/definitions.md` al cambiar un modelo Pydantic. La spec añade `TramoDeLog` y declara `definitions.md` «sin cambios». El plan sigue a la spec y lo deja abierto. | RF-36 — §8.2, §8.3 | fase-1 (cabecera), README P8 |

### Validadores
#### VAL-1: Panel abierto en 127.0.0.1:5173
- Requisito: R1 (RF-01) — "sin cambiar de puerto si está ocupado" (§5), con el caso de §9 «el aviso de red indica abrir `http://localhost:5173`»; R4 (RF-04)
- Punto de fallo: el CORS solo admite `http://localhost:5173`. Desde `http://127.0.0.1:5173`, todas las peticiones fallan por red y el operador ve el mismo aviso que con la API caída, sin pista de la causa.
- Precondiciones: API real sobre `demo-24`; `vite preview` en 5173 escuchando también en 127.0.0.1.
- Cómo validarlo: abrir `http://127.0.0.1:5173/#/` en Chromium y leer el aviso de la vista y la zona de estado de la barra lateral.
- Resultado esperado: el aviso contiene el texto `http://localhost:5173`; con `http://localhost:5173/#/` no aparece ningún aviso.
- Tipo de prueba sugerida: e2e
- Severidad: Media — hay alternativa (cambiar la URL), pero sin el aviso el fallo parece una caída de la API.

#### VAL-2: Margen de RNF-05 en Progreso
- Requisito: R66 (RNF-05) — "≤ 60 peticiones por minuto de una pestaña visible en Progreso" (§6); R5 (RF-05)
- Punto de fallo: seis recursos cada 10 s (36/min) más el log cada 3 s (20/min) suman 56/min. Cualquier petición extra —el estado de la API de la barra lateral, un `GET /novelas` del layout— supera el umbral.
- Precondiciones: Progreso de `demo-24` con `page.clock` instalado.
- Cómo validarlo: contar todas las peticiones a la API durante 60 s simulados con un espía de contexto.
- Resultado esperado: ≤ 60 peticiones, desglosadas en 36 de los seis recursos de §8.4 y ≤ 20 de `…/log`; ninguna a otra ruta.
- Tipo de prueba sugerida: e2e
- Severidad: Media — incumple un umbral numérico sin romper la función.

#### VAL-3: Datos conservados y excepciones de RF-04
- Requisito: R4 (RF-04) — "mantener en pantalla los últimos datos válidos de la vista, salvo en los casos con tratamiento propio de RF-19 y RF-22" (§5); R49 (RF-49)
- Punto de fallo: un fallo parcial de la ronda puede vaciar la vista o mostrar un aviso de error para el 404 de la escaleta o el 416 del log, que deben ir sin aviso.
- Precondiciones: Progreso de `demo-24` con una ronda correcta a las 10:00:00 del reloj simulado.
- Cómo validarlo: en la ronda de las 10:00:10, hacer que `…/estado` responda 404 con `{"detail":"no existe la novela demo-24"}` y `…/escaleta` 404; en la del log, un 416.
- Resultado esperado: un único aviso, con «no existe la novela demo-24»; el cursor y la gráfica de las 10:00:00 siguen en el DOM; aparece «el plan todavía no tiene escaleta» sin aviso; el 416 no genera aviso; la barra superior sigue con «Actualizado a las 10:00:00». En la ronda de las 10:00:20, con todos los recursos a 200, el aviso desaparece y la hora pasa a 10:00:20; una ronda cuyo único «fallo» es el 404 de la escaleta cuenta como correcta (D45).
- Tipo de prueba sugerida: unitaria (jsdom) + e2e
- Severidad: Media — la vista sigue sirviendo, pero mezcla errores reales con estados normales.

#### VAL-4: Respuestas tardías tras cambiar de vista
- Requisito: R7 (RF-07) — "abortar las peticiones en curso y cancelar los temporizadores de la vista que abandona" (§5)
- Punto de fallo: si el abort no llega al manejador, una respuesta tardía de Progreso pinta nodos o avisos dentro de la vista nueva.
- Precondiciones: Progreso de `demo-24`; `page.route` retrasa `…/estado` 3 s.
- Cómo validarlo: navegar a `#/lanzar` en t = 1 s y observar el DOM en t = 4 s.
- Resultado esperado: el DOM no contiene nodos de Progreso ni avisos; 0 `console.error` y 0 `pageerror`; el formulario de Lanzar está intacto.
- Tipo de prueba sugerida: e2e
- Severidad: Media — hay contenido cruzado entre vistas, pero se corrige recargando.

#### VAL-5: Pestaña oculta con una petición en curso
- Requisito: R6 (RF-06) — "no debe lanzar peticiones de sondeo… cuando vuelva… una ronda inmediata" (§5); R66 (RNF-05) — "0 peticiones… después de la ronda en curso"
- Punto de fallo: ocultar la pestaña con una ronda a medias puede dejar temporizadores vivos. Al volver, la ronda inmediata puede solapar una petición del mismo recurso (RF-05).
- Precondiciones: Progreso con el reloj simulado; `…/estado` tarda 2 s.
- Cómo validarlo: poner `visibilityState` a `hidden` en t = 1 s, mantenerlo 60 s, volver a `visible` y registrar las peticiones lanzadas.
- Resultado esperado: entre t = 1 s y t = 61 s, 0 peticiones lanzadas; al volver, una ronda antes de 100 ms y nunca dos peticiones simultáneas del mismo recurso.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — afecta a la carga de la API, no a los datos.

#### VAL-6: Rutas inválidas sin ninguna petición
- Requisito: R9 (RF-09) — "Si el slug de la ruta no casa `^[a-z0-9-]+$` o el capítulo de la ruta no casa `^[1-9][0-9]{0,2}$`… sin lanzar ninguna petición y sin normalizar la ruta" (§5; D41, D50)
- Punto de fallo: la validación puede hacerse sobre el hash sin decodificar, o solo sobre el decodificado. Además, el layout puede lanzar peticiones propias antes de que la ruta se valide.
- Precondiciones: panel cargado con un espía de todas las peticiones.
- Cómo validarlo: navegar a `#/novelas/demo_24/progreso`, `#/novelas//progreso`, `#/novelas/demo-24%2F..%2F/progreso`, `#/novelas/demo-24/lectura/1000`, `…/lectura/-1`, `…/lectura/2.5`, `…/lectura/abc`, `…/lectura/07`, `…/lectura/+3` y `…/lectura/%203`, avanzando el reloj 30 s en cada una.
- Resultado esperado: «ruta no válida» en las diez, sin que la URL cambie; «sin datos» en la zona de estado de la barra lateral; el espía registra 0 peticiones.
- Tipo de prueba sugerida: unitaria + e2e
- Severidad: Alta — es un requisito Must y la primera barrera ante un slug hostil en el cliente.

#### VAL-7: Capítulo no cerrado mientras el checkpoint no ha llegado
- Requisito: R27 (RF-27) — "mostrar «capítulo no disponible todavía» sin pedirlo a la API" (§5); R10 (RF-10)
- Punto de fallo: al recargar `#/…/lectura/8`, si el lector pide el capítulo antes de conocer `checkpoint.capitulo`, se descarga un texto no cerrado (contra D8).
- Precondiciones: `demo-24` con `checkpoint.capitulo` 7; `page.route` retrasa `…/checkpoint` 3 s.
- Cómo validarlo: cargar directamente `#/novelas/demo-24/lectura/8`, esperar 5 s y repetir con `…/lectura/3`.
- Resultado esperado: con el 8, el espía no registra nunca `GET /novelas/demo-24/capitulos/8` y aparece «capítulo no disponible todavía»; con el 3, `GET …/capitulos/3` sale después de la respuesta de `…/checkpoint`.
- Tipo de prueba sugerida: e2e
- Severidad: Alta — muestra como definitivo un texto que todavía puede reescribirse.

#### VAL-8: Idea larga y portapapeles no disponible
- Requisito: R11 (RF-11) — "ofrecer copiarla al portapapeles" (§5), con los casos de §9 «Idea de varias páginas: sin truncar» y «Portapapeles no disponible o denegado»
- Punto de fallo: un `maxlength`, un truncado visual copiado tal cual o la ausencia de alternativa cuando `navigator.clipboard` falla.
- Precondiciones: Lanzar con `GET /novelas` respondido.
- Cómo validarlo: idea de 50 000 caracteres con 200 saltos de línea y slug `nueva-prueba` → «Generar orden» → «Copiar»; repetir con el permiso de portapapeles denegado.
- Resultado esperado: el portapapeles contiene exactamente la orden completa, con la idea entera entre comillas simples. Con el permiso denegado, un campo de solo lectura tiene `selectionStart` 0 y `selectionEnd` igual a su longitud, junto a «pulsa Ctrl+C para copiar».
- Tipo de prueba sugerida: e2e
- Severidad: Media — hay alternativa manual, pero una idea truncada arranca otra novela.

#### VAL-9: Límites aceptados del formulario
- Requisito: R12 (RF-12) — "capítulos no casa `^[1-9][0-9]{0,2}$`, o palabras no casa `^[1-9][0-9]*$`" (§5; D41)
- Punto de fallo: una expresión mal anclada o con un cuantificador de más rechaza 1 o 999, y nada lo detecta. Desde la v5, CA-12 incluye estos casos aceptados.
- Precondiciones: formulario con slug `nueva-prueba` e idea `Un faro apagado.`.
- Cómo validarlo: generar con capítulos `1` y palabras `1`; con capítulos `999`; con capítulos vacío y palabras `80000`.
- Resultado esperado: tres órdenes generadas: `… --capitulos 1 --palabras 1`, `… --capitulos 999` y `… --palabras 80000` (sin `--capitulos`).
- Tipo de prueba sugerida: unitaria
- Severidad: Media — hay alternativa (escribir la orden a mano).

#### VAL-10: Comillas simples con comilla simple, barras, sustitución de órdenes e historial
- Requisito: R14 (RF-14) — "poner la idea entre comillas simples y sustituir en ella cada `'` por `'\''`… un único argumento que bash, interactivo o no, con o sin expansión del historial, expande a la idea original" (§5; D44, que sustituye a D7)
- Punto de fallo: una `'` sin sustituir cierra el argumento y deja el resto de la idea como código de bash; una sustitución aplicada dos veces duplica comillas. Un generador aleatorio puede no producir nunca `''` seguidas ni una `'` al principio o al final.
- Precondiciones: bash disponible, también en Windows con Git Bash (D36).
- Cómo validarlo: generar la orden para las ideas `'`, `''`, `it's`, `'inicio` y `fin'`, `fin\`, `a\` + salto de línea + `b`, `$(id)`, `` `id` ``, `\"`, `!!`, `ñ ü €` y una que termina en salto de línea; extraer el argumento y ejecutar `bash -c 'printf %s <argumento>'` y `bash -c 'set -H; printf %s <argumento>'`.
- Resultado esperado: en las dos ejecuciones, la salida de bash coincide byte a byte con cada idea en UTF-8; ninguna orden se ejecuta (`id` no aparece expandido) y `!!` sale literal.
- Tipo de prueba sugerida: unitaria (casos fijos junto a la propiedad de CA-14)
- Severidad: Alta — altera la única entrada humana obligatoria de la novela.

#### VAL-11: Valor real aislado entre nulls
- Requisito: R18 (RF-18) — "un `null` de `tension_real` se marca «sin puntuar» y no se interpola" (§5)
- Punto de fallo: si un tramo de un solo punto se dibuja como polilínea, no deja trazo visible y el valor desaparece de la gráfica.
- Precondiciones: `tension_real` `[null, 5, null, 6]`; curva objetivo de 4 valores.
- Cómo validarlo: construir la serie y el SVG, y medir en Chromium la caja de los elementos de la serie real.
- Resultado esperado: dos tramos, en los capítulos 2 y 4, cada uno con un elemento SVG de ancho y alto > 0; la tabla lleva 5 en la fila 2 y 6 en la 4, y «sin puntuar» en las filas 1 y 3.
- Tipo de prueba sugerida: unitaria + e2e
- Severidad: Media — pierde datos visibles, pero la tabla los conserva.

#### VAL-12: Escaleta ausente o inválida en Lectura
- Requisito: R19 (RF-19) — "sin aviso de error" (§5); R24 (RF-24) — "con un hueco entre actos cuando hay escaleta", y §9 «Lectura coloca los volúmenes sin huecos de acto»
- Punto de fallo: Lectura puede tratar el 404 de la escaleta como error (RF-04) o dejar la escena sin disponer.
- Precondiciones: `recien-creada`, y un workspace con la curva de 23 valores y `num_capitulos` 24 (404 por no validar).
- Cómo validarlo: abrir Lectura de cada uno y leer `data-volumenes`, las x de la función de disposición y los avisos.
- Resultado esperado: sin aviso de error; x(n+1) − x(n) = 1,2 para todo n; en Progreso, «el plan todavía no tiene escaleta» en los dos casos.
- Tipo de prueba sugerida: unitaria + e2e
- Severidad: Media — es un caso secundario, pero habitual al empezar una novela.

#### VAL-13: Aparece un run nuevo durante el sondeo
- Requisito: R22 (RF-22) — "del run de `run_id` mayor… cuando `…/runs` traiga un run de `run_id` mayor, debe pasar a él con `desde=0` y reconstruir la lista" (§5; D38)
- Punto de fallo: cuando aparece un run de `run_id` mayor, reutilizar el último `hasta` del run anterior contra el log nuevo salta sus primeras líneas en silencio. El 416 solo lo arregla si el log nuevo es más corto que ese desplazamiento.
- Precondiciones: Progreso siguiendo `r-20260924-0001` con `hasta` = 4 000; aparece `r-20260924-0002` con un `harness.log` de 10 000 bytes.
- Cómo validarlo: registrar el `desde` de la primera petición a `…/runs/r-20260924-0002/log`, las líneas mostradas y las peticiones posteriores al run anterior.
- Resultado esperado: la primera petición al run nuevo lleva `desde=0`, las líneas mostradas son las 50 últimas de ese log y no se pide más `…/runs/r-20260924-0001/log`. Desde la v5, CA-22 incluye este caso.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — la señal que distingue un bucle colgado (O-02) queda incompleta sin aviso.

#### VAL-14: Umbral de 15 min y zona horaria
- Requisito: R23 (RF-23) — "Cuando pasen más de 15 min desde el `modificado` del run de `run_id` mayor" (§5)
- Punto de fallo: comparar la hora ISO 8601 con zona como texto, o en la hora local, adelanta o retrasa el rótulo en tantas horas como la diferencia de zona.
- Precondiciones: `modificado` `2026-09-24T10:00:00+02:00`; reloj simulado en UTC.
- Cómo validarlo: fijar el reloj en `2026-09-24T08:15:00Z`, en `08:15:01Z` y en `07:55:00Z`.
- Resultado esperado: sin rótulo a las 08:15:00Z; «sin actividad desde …» a las 08:15:01Z; sin rótulo ni error a las 07:55:00Z (modificado en el futuro).
- Tipo de prueba sugerida: unitaria
- Severidad: Media — es un requisito Could, pero un falso «sin actividad» induce a parar el bucle.

#### VAL-15: Checkpoint nulo y novela de 999 sin escaleta
- Requisito: R24 (RF-24) — "cerrado (`n ≤ checkpoint.capitulo`), en curso (presente en el índice… y `n > checkpoint.capitulo`) o pendiente" (§5)
- Punto de fallo: con `checkpoint` `null`, `n ≤ null` puede evaluarse como cierto en la comparación, y todos los volúmenes salen «cerrados» y legibles.
- Precondiciones: `checkpoint` `null` e índice con los capítulos 1 y 2; `grande-999`.
- Cómo validarlo: calcular los estados; abrir Lectura de `grande-999` en Chromium.
- Resultado esperado: 0 cerrados, 1 y 2 en curso, del 3 al final pendientes, con «ningún capítulo cerrado todavía» en la lista. En `grande-999`, `data-volumenes="999"`, x(n+1) − x(n) = 1,2 y `data-draw-calls` ≤ 5.
- Tipo de prueba sugerida: unitaria + e2e
- Severidad: Media — expone texto no cerrado solo en novelas recién empezadas.

#### VAL-16: Frontmatter con CRLF y reglas horizontales en el cuerpo
- Requisito: R25 (RF-25) — "quitar el bloque de frontmatter inicial y mostrar el cuerpo" (§5)
- Punto de fallo: si el capítulo se escribió en Windows con `\r\n`, la línea `---\r` no casa con `---` y se muestra `run_id:`. Un recorte voraz, en cambio, borra hasta la última `---` del cuerpo.
- Precondiciones: capítulo de fixture `---\r\nrun_id: r-20260924-0001\r\ntitulo: Uno\r\n---\r\n\r\nPrimera parte\r\n\r\n---\r\n\r\nSegunda parte\r\n`.
- Cómo validarlo: renderizarlo en el lector.
- Resultado esperado: el texto visible no contiene `run_id:`, sí contiene «Primera parte» y «Segunda parte», y hay exactamente un `<hr>` entre ellas.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — muestra metadatos del harness y puede perder parte del capítulo.

#### VAL-17: Vectores de inyección que la v4 dejaba fuera de CA-26
- Requisito: R26 (RF-26) — "sin crear elementos `script`, `iframe`, `img`, `a`, `object`, `embed` ni `svg`, ni atributos `on*`" (§5); R68 (RNF-07)
- Punto de fallo: la v4 de CA-26 no incluía autoenlaces, enlaces e imágenes por referencia ni URL sueltas, y desactivar solo las reglas `link` e `image` de `markdown-it` deja activa la regla `autolink`, que crea `<a>`. **Incorporado en la v5 (D56):** el lector desactiva también `linkify`, `autolink` y `reference`, y CA-26 incluye estos vectores. El validador comprueba que la corrección se mantiene.
- Precondiciones: capítulo cerrado de fixture con `<http://ejemplo.invalid>`, `[a][r]` y `[r]: javascript:alert(1)`, `![x][i]` y `[i]: http://ejemplo.invalid/x.png`, `http://ejemplo.invalid` suelto, `<svg onload=alert(1)>` y `[x](data:text/html,hola)`.
- Cómo validarlo: renderizarlo en el lector y recorrer el contenedor; en e2e, espiar la red durante el render.
- Resultado esperado: 0 elementos `a`, `img`, `script`, `iframe`, `object`, `embed` y `svg`; 0 atributos que empiecen por `on`; los seis fragmentos visibles como texto; 0 peticiones a `ejemplo.invalid`.
- Tipo de prueba sugerida: unitaria + e2e
- Severidad: Crítica — ejecutaría texto escrito por agentes en el navegador del operador (amenaza 2 de `docs/validators.md` §4.9).

#### VAL-18: Bordes del teclado y foco en el lector
- Requisito: R28 (RF-28) — "← y → mueven la selección, Enter abre… Esc cierra el lector y devuelve el foco a la lista" (§5); R74 (RNF-13)
- Punto de fallo: → en el último volumen, o ← en el primero, puede dejar la selección fuera de rango. Enter sobre un pendiente puede pedir el capítulo. Tab puede salir del diálogo modal (§8.4).
- Precondiciones: Lectura de `demo-24` con el 24 seleccionado.
- Cómo validarlo: pulsar →, después ← hasta el 1 y ← otra vez; seleccionar el 9 y pulsar Enter; abrir el 3 y pulsar Tab 20 veces.
- Resultado esperado: `data-seleccion` siempre entre 1 y 24, sin dar la vuelta —→ en el 24 lo deja en el 24 y ← en el 1 lo deja en el 1 (D47)—, y 0 `pageerror`. Enter en el 9 muestra «capítulo no disponible todavía» sin `GET …/capitulos/9`. Con el lector abierto, el foco no sale del diálogo, y Esc lo devuelve al elemento 3 de la lista.
- Tipo de prueba sugerida: e2e
- Severidad: Media — el recorrido con teclado es un requisito, pero hay lista alternativa.

#### VAL-19: Sin WebGL y sin errores en consola
- Requisito: R29 (RF-29) — "Donde WebGL no esté disponible… «vista 3D no disponible»" (§5); R77 (RNF-16)
- Punto de fallo: crear el renderer de Three.js sin WebGL escribe un `console.error` antes de que el panel caiga a la lista. RNF-16 solo excluye los mensajes que emite el propio navegador por el WebGL desactivado; uno de Three.js cuenta (D54).
- Precondiciones: Chromium lanzado con WebGL desactivado.
- Cómo validarlo: abrir Lectura de `demo-24`, abrir y cerrar el capítulo 3 y escuchar `console` y `pageerror`, con la lista cerrada de exclusiones de D54.
- Resultado esperado: «vista 3D no disponible», 0 `<canvas>`, el lector abre y cierra, 0 `pageerror` y ningún `console.error` fuera de la lista de exclusiones, en particular ninguno de Three.js.
- Tipo de prueba sugerida: e2e
- Severidad: Media — la función se mantiene, pero se rompe un umbral de observabilidad.

#### VAL-20: Entrar y salir de Lectura muchas veces
- Requisito: R31 (RF-31) — "liberar las geometrías, los materiales, las texturas y el renderer… y retirar su `<canvas>`" (§5)
- Punto de fallo: si no se libera el contexto WebGL, el navegador agota su límite de contextos activos y, tras unas pocas entradas, la escena deja de funcionar.
- Precondiciones: Chromium con WebGL; `demo-24`.
- Cómo validarlo: alternar 20 veces entre `#/novelas/demo-24/lectura` y `#/novelas/demo-24/progreso`.
- Resultado esperado: tras cada salida, 0 `<canvas>` de la escena; en la entrada 20, `data-draw-calls` > 0; 0 avisos «Too many active WebGL contexts» en consola.
- Tipo de prueba sugerida: e2e
- Severidad: Media — se degrada tras un uso prolongado; recargar lo arregla.

#### VAL-21: Bordes del `desde` del log
- Requisito: R36 (RF-36), R37 (RF-37) — "si supera el tamaño del log, 416" (§5)
- Punto de fallo: confundir `>` con `≥` convierte en 416 el caso normal «no hay nada nuevo», `desde == tamano`, y el cliente reinicia la lista cada 3 s.
- Precondiciones: run de `demo-24` con `harness.log` de T bytes.
- Cómo validarlo: `GET …/log?desde=T`; `GET …/log?desde=abc`; `GET …/log?desde=<mitad de la línea 3>`.
- Resultado esperado: el primero responde 200 con `lineas: []` y `hasta` = `tamano` = T; el segundo, 422; el tercero, 200 con la primera línea igual a la línea 4 completa, sin `\r` ni `\n` finales (D48).
- Tipo de prueba sugerida: integración
- Severidad: Media — no pierde datos, pero la actividad parpadea sin fin.

#### VAL-22: Pre-commit sin `node_modules` ni `npm`
- Requisito: R41 (RF-41) — "abortar el commit si falla" (§5), con el caso de §9 «sin `npm` o sin `node_modules`: … el commit se aborta»
- Punto de fallo: si el hook no propaga el código de salida (sin `set -e`, o con `npm` ausente y código 127 ignorado), el commit pasa sin lint.
- Precondiciones: repositorio temporal con `.githooks/pre-commit`; `frontend/src/x.ts` en el índice; sin `frontend/node_modules`. Segunda variante con `npm` fuera del `PATH`.
- Cómo validarlo: `git commit -m prueba` en cada variante y comparar `git rev-parse HEAD` antes y después.
- Resultado esperado: en las dos variantes, código de salida ≠ 0 y HEAD sin cambios.
- Tipo de prueba sugerida: integración
- Severidad: Media — CI lo detecta después.

#### VAL-23: Generador invocado como orden con un `.env` presente
- Requisito: R42 (RF-42) — "no debe emitir scores ni leer el `.env` del repositorio al generar los workspaces sintéticos" (§5)
- Punto de fallo: la v4 de CA-42 lo probaba solo dentro de pytest, donde ya actúa el aislamiento de `backend/conftest.py`. Fuera de pytest (`python -m tests.fixtures.panel`, como lo invocan `playwright.config.ts` y CI), el aislamiento depende solo de `panel.py`. **Incorporado en la v5 (D56):** CA-42 ejecuta además el generador como orden en un subproceso contra un servidor HTTP local (`test_generador_como_orden`, T-16). Este validador añade el `.env` de prueba en la raíz de una copia del repositorio.
- Precondiciones: `.env` de prueba en la raíz de una copia del repositorio, con `TRACE_TO_LANGFUSE=true`, `LANGFUSE_PUBLIC_KEY=dummy-publica`, `LANGFUSE_SECRET_KEY=dummy-secreta` y `LANGFUSE_BASE_URL=http://127.0.0.1:<puerto>`, con un servidor HTTP local que cuenta las peticiones recibidas.
- Cómo validarlo: desde `backend/`, `uv run python -m tests.fixtures.panel <tmp>`.
- Resultado esperado: salida 0, tres workspaces creados y 0 peticiones recibidas por el servidor local.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — con las claves reales, emitiría scores falsos a Langfuse.

#### VAL-24: Variantes de ruta contra el dev server
- Requisito: R43 (RF-43) — "ni servir desde el dev server de Vite ficheros de fuera de `frontend/`" (§5); R71 (RNF-10)
- Punto de fallo: la v4 de CA-43 probaba una sola ruta (`/@fs/<raíz>/AGENTS.md`), y las variantes con `..` codificado o a través de `frontend/` pueden saltarse `server.fs`. **Incorporado en la v5 (D56):** CA-43 y `servidor.test.ts` (T-04) prueban estas variantes. El validador comprueba que la corrección se mantiene con `npm run dev`.
- Precondiciones: `npm run dev` con `frontend/vite.config.ts`; un workspace sintético en `novelas/demo-24/`.
- Cómo validarlo: pedir `/@fs/<raíz>/novelas/demo-24/canon/misterio.md`, `/@fs/<raíz>/backend/api/main.py`, `/@fs/<raíz>/frontend/../AGENTS.md`, `/%2e%2e/AGENTS.md`, `/../AGENTS.md` y `/src/../../AGENTS.md?raw`.
- Resultado esperado: ninguna responde 200, y ningún cuerpo contiene `# AGENTS.md` ni texto del canon.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — expondría `canon/misterio.md` y el repositorio.

#### VAL-25: Estado de la documentación de referencia al cerrar
- Requisito: R45 (RF-45) — "describir el panel y los `GET` nuevos en la documentación de referencia en el mismo commit" (§5)
- Punto de fallo: CA-45 es solo inspección, y las frases que la spec declara contradictorias pueden sobrevivir en algún commit.
- Precondiciones: el commit que cierra la spec.
- Cómo validarlo: en `docs/validators.md`, `grep -n "no hay \`frontend/\`"`; en `docs/architecture.md`, `grep -n "produce un \`config.yaml\`"`, `grep -n "se añade al estado"` y `grep -n "cuota"` en el árbol de §3.1; contar los `GET` de §11.1; buscar «Cerrado (spec 0004)» en §12.6; en `AGENTS.md`, `grep -c "npm run verificar"`; en `docs/definitions.md`, `grep -c "TramoDeLog"`; y en `docs/validators.md` §3.6, §4.4, §4.7 y §4.9, las entradas del panel que lista § Al implementar (D37).
- Resultado esperado: 0 coincidencias en las cuatro primeras búsquedas (la de cuota, dentro de la línea de `progreso/`); 10 `GET` en §11.1; 1 coincidencia en §12.6; 1 en `AGENTS.md`; ≥ 1 en `docs/definitions.md`; y las cuatro secciones de `docs/validators.md` nombran el panel.
- Tipo de prueba sugerida: revisión manual
- Severidad: Alta — es un requisito Must, y el catálogo pasaría por vigente sin serlo.

#### VAL-26: Colores con nombre fuera de `tokens.css`
- Requisito: R46 (RF-46) — "sin colores literales ni declaraciones `font-family` fuera de él" (§5)
- Punto de fallo: la v4 de CA-46 enumeraba hexadecimales, funciones de color, `white` y `black`, y `orange`, `gray` o `red` pasaban. Desde la v5, CA-46 prohíbe todo color con nombre y solo admite `transparent`, `currentColor` e `inherit` (D51).
- Precondiciones: fixture CSS de componente con `color: orange; border-color: gray;`, fixture TS con `el.style.fill = 'red'` y fixture CSS con `background: transparent; color: currentColor; border-color: inherit;`.
- Cómo validarlo: ejecutar `tokens.test.ts` con los fixtures.
- Resultado esperado: el test sale en rojo y nombra los dos primeros ficheros, y no el tercero.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — un color fuera de la marca, sin pérdida de datos.

#### VAL-27: Pares en uso no declarados en `pares.ts`
- Requisito: R47 (RF-47) — "cuyos pares declarados en `pares.ts` cumplen RNF-19" (§5), y §8.2 «Pares de roles en uso»; R80 (RNF-19)
- Punto de fallo: RNF-19 solo comprueba los 21 pares declarados. Un par en uso que no esté en la lista pasa sin comprobar: por ejemplo, «Actualizado a las …» en `--q-texto-secundario` sobre `--q-fondo-pagina` da 4,27:1. Tampoco lo cubre axe si el elemento no es texto.
- Precondiciones: build de producción; las cuatro vistas con datos en Chromium.
- Cómo validarlo: recorrer los elementos visibles con texto, icono o borde con significado, obtener `color` o `border-color` y el `background-color` opaco más cercano, traducirlos a roles por valor y compararlos con `pares.ts`.
- Resultado esperado: 0 pares usados que no estén declarados; 0 pares por debajo de su umbral.
- Tipo de prueba sugerida: e2e
- Severidad: Alta — incumple WCAG 2.1 AA, que es obligatorio (O-07, D12).

#### VAL-28: El estado de la API se recupera
- Requisito: R48 (RF-48) — "una zona inferior separada con el estado de la conexión con la API" (§5)
- Punto de fallo: el estado se queda en «API sin respuesta» después de que la API vuelve, o el bloque de novela aparece en rutas sin slug.
- Precondiciones: Progreso de `demo-24`.
- Cómo validarlo: hacer fallar todas las peticiones durante dos rondas, dejarlas pasar y esperar una ronda; navegar a `#/lanzar`.
- Resultado esperado: «API sin respuesta» durante el fallo; «API conectada» y la URL de la API en la primera ronda correcta; en `#/lanzar`, ningún bloque de novela; en `#/novelas/Demo/progreso`, «sin datos»; y el espía no registra ninguna petición propia del estado de la API (D50).
- Tipo de prueba sugerida: e2e
- Severidad: Media — da información engañosa, pero la vista muestra el aviso.

#### VAL-29: El logo no carga
- Requisito: R51 (RF-51) — "dentro de un contenedor con `border-radius`… en cualquier sitio en que aparezca" (§5), con el caso de §9 «`logo.png` no carga… el contenedor conserva su tamaño y su radio»
- Punto de fallo: con la imagen rota, el contenedor colapsa a 0 px o pierde el radio y la barra lateral se descoloca.
- Precondiciones: `page.route` hace fallar la petición de `logo.png`.
- Cómo validarlo: cargar `#/` y medir el contenedor y el texto.
- Resultado esperado: contenedor de 40 × 40 px con los cuatro radios a 8,8 px; `img` con `alt="Qaracter"`; el texto «Qaracter» visible. El mensaje de consola del navegador por la imagen fallida no cuenta para RNF-16 (D54).
- Tipo de prueba sugerida: e2e
- Severidad: Media — es un caso secundario de §9.

#### VAL-30: Slug largo en el banner
- Requisito: R53 (RF-53) — "con todo el texto en la mitad izquierda" (§5), con el caso de §9 «Slug largo… se parte en líneas… sin truncar»
- Punto de fallo: CA-53 solo prueba `demo-24`. Un slug largo sin espacios no se parte (`[a-z0-9-]`) y desborda la mitad izquierda o se trunca con elipsis.
- Precondiciones: workspace sintético adicional creado con `novela nueva` y el slug `una-novela-con-un-slug-muy-largo-para-probar-el-banner-del-panel`.
- Cómo validarlo: abrir su Progreso a 1440 × 900 y medir la caja del titular.
- Resultado esperado: el borde derecho de la caja no pasa de la mitad del banner; `scrollWidth ≤ clientWidth`; el texto visible es el slug completo.
- Tipo de prueba sugerida: e2e
- Severidad: Media — es cosmético, pero el texto fuera de su mitad incumple el contraste de D22.

#### VAL-31: Umbral exacto de 1280 px
- Requisito: R54 (RF-54) — "Mientras la ventana mida 1280 px de ancho o más… por debajo de 1280 px, la rejilla en una columna" (§5)
- Punto de fallo: CA-54 mide 1440 y 1024, y un error de uno en la media query no se detecta.
- Precondiciones: Progreso de `demo-24` con la barra lateral desplegada.
- Cómo validarlo: fijar la ventana a 1280 × 900 y a 1279 × 900.
- Resultado esperado: dos columnas a 1280 px y una a 1279 px; en los dos anchos, `document.documentElement.scrollWidth ≤ innerWidth`.
- Tipo de prueba sugerida: e2e
- Severidad: Baja — es cosmético.

#### VAL-32: La fuente display no carga
- Requisito: R56 (RF-56) — "la tipografía display como WOFF2 autoalojado… y `font-display: swap`" (§5), con el caso de §9 «La fuente display no carga»
- Punto de fallo: un `@font-face` sin `swap` efectivo deja el titular invisible mientras espera una fuente que no llega.
- Precondiciones: `page.route` retrasa `outfit-800.woff2` 10 s.
- Cómo validarlo: abrir Progreso de `demo-24` y medir el titular a los 500 ms.
- Resultado esperado: a los 500 ms, el titular tiene alto > 0, su texto es `demo-24` y su `font-family` computada resuelve a la pila de `--q-fuente-cuerpo`. La regla `@font-face` declara `font-display: swap`. Los mensajes de consola que el navegador emita por la fuente retrasada no cuentan para RNF-16 (D54).
- Tipo de prueba sugerida: e2e
- Severidad: Media — es un caso secundario con alternativa definida.

#### VAL-33: Los fixtures de imagen no entran en el árbol
- Requisito: R60 (RF-60) — "las únicas imágenes de `frontend/` son `logo.png`, `favicon.png` y las referencias de regresión visual" (§5); R52 (RF-52)
- Punto de fallo: los PNG de fixture de CA-52 (no PNG, 200 × 200, 90 KB) escritos dentro de `frontend/` acaban versionados por un `git add -A`, o hacen fallar CA-60 en local.
- Precondiciones: árbol limpio.
- Cómo validarlo: `npm test` desde `frontend/` y, después, `git status --porcelain -- frontend/`.
- Resultado esperado: salida vacía; los fixtures solo existen bajo el directorio temporal del sistema.
- Tipo de prueba sugerida: integración
- Severidad: Media — incumple un requisito Must si llega al índice, aunque CA-60 lo detectaría en CI.

#### VAL-34: Caída real de la API
- Requisito: R76 (RNF-15) — "Recuperación tras una caída de la API de hasta 60 s… ≤ 1" (§6)
- Punto de fallo: abortar peticiones con `page.route` no reproduce la conexión rechazada de un uvicorn parado ni la reconexión, que es lo que ocurre de verdad.
- Precondiciones: API real con `NOVELAS_DIR` sobre los workspaces sintéticos; Progreso de `demo-24` abierto.
- Cómo validarlo: parar el proceso uvicorn 60 s, arrancarlo y contar las rondas de `…/estado` hasta que el DOM se actualiza, sin recargar.
- Resultado esperado: la primera ronda tras el arranque que responde 200 actualiza la vista y quita el aviso (≤ 1 ronda); «API conectada».
- Tipo de prueba sugerida: e2e
- Severidad: Media — el operador puede recargar.

#### VAL-35: Otros vectores de petición a terceros
- Requisito: R69 (RNF-08) — "Peticiones a orígenes distintos de `http://localhost:5173` y del de la API… 0" (§6); R67 (RNF-06)
- Punto de fallo: `<link rel="preconnect">`, `navigator.sendBeacon`, `@import` en CSS o un `sourceMappingURL` absoluto no pasan por el cliente de `shared/api/` y escapan a la regla de eslint.
- Precondiciones: build de producción con `vite preview`.
- Cómo validarlo: recorrido e2e completo, incluido el capítulo hostil de VAL-17, con un espía de contexto de peticiones y websockets; `grep -rE "sendBeacon|preconnect|dns-prefetch" frontend/dist`.
- Resultado esperado: 0 peticiones a otros orígenes; 0 websockets; 0 coincidencias en `dist/`.
- Tipo de prueba sugerida: e2e
- Severidad: Alta — es la barrera de privacidad del panel.

### Verificadores
#### VER-1: FastAPI revalida `Escaleta` sin contexto
- Paso del plan: T-01 — "`Escaleta.model_validate(…, context={"num_capitulos": …})`" (fase-1), con el riesgo de README §8 «si revalidara `Escaleta` sin contexto, `…/escaleta` daría 500»
- Punto de fallo: el `response_model` vuelve a ejecutar el `model_validator` de `plan.py` sin contexto y la ruta responde 500 aunque el repositorio lea bien.
- Precondiciones: FastAPI en la versión de `backend/uv.lock`; `demo-24`.
- Cómo verificarlo: `TestClient` → `GET /novelas/demo-24/escaleta`. Método de `docs/validators.md` §3.5 (API con `TestClient`).
- Resultado esperado: 200, con `len(curva_tension_objetivo) == 24`; 0 excepciones en el log del test.
- Tipo de prueba sugerida: integración
- Severidad: Alta — Progreso y Lectura pierden la escaleta sin alternativa.

#### VER-2: Los errores de validación salen como 404
- Paso del plan: T-01 (PD4) — "Si falta el fichero o no valida, `WorkspaceInvalido`, que `backend/api/main.py:24-28` convierte en 404"
- Punto de fallo: un `ValidationError` de Pydantic o un error de YAML en el frontmatter no se envuelve en `WorkspaceInvalido` y sale como 500.
- Precondiciones: workspace de 24 capítulos con la curva de 23 valores; otro con el frontmatter de `plan/escaleta.md` sin cerrar.
- Cómo verificarlo: `GET …/escaleta` en cada uno; `GET …/config` con `config.yaml` sintácticamente roto.
- Resultado esperado: 404 con `detail` no vacío en los tres casos; ningún 500.
- Tipo de prueba sugerida: integración
- Severidad: Media — RF-19 no aplica a un 500 y la vista mostraría un error indebido.

#### VER-3: Cobertura de la propiedad de `cortar_tramo`
- Paso del plan: T-02 (PD3) — "`cortar_tramo(ventana: bytes, desde: int, tope: int, *, en_limite: bool, hasta_el_final: bool) -> tuple[list[str], int]`… quita el `\n` final y el `\r` anterior; decodifica UTF-8 con sustitución" (D48)
- Punto de fallo: la propiedad puede encadenar siempre desde 0 y no ejercitar un `desde` > 0 ni a mitad de línea en la función (el `hasta` devuelto es absoluto o relativo), ni un carácter multibyte partido justo en el tope, ni líneas vacías, ni `\r\n`. Al quitar el `\r`, la suma de bytes ya no sale de las líneas devueltas.
- Precondiciones: Hypothesis con el perfil `ci` de `backend/conftest.py`.
- Cómo verificarlo: estrategias que incluyan líneas vacías, líneas de exactamente `tope` bytes, `ñ` a caballo del byte `tope`, líneas con `\r\n` y ventanas con `desde` > 0, también a mitad de línea; comprobar que cada `hasta` es un límite de línea del log original y que `hasta − desde` es igual a los bytes originales de las líneas devueltas, con su `\r\n` o su `\n`, más los descartados hasta el primer límite. Método de `docs/validators.md` §3.6.
- Resultado esperado: la propiedad pasa con `--hypothesis-profile=ci`; al mutar `cortar_tramo` para que devuelva el `hasta` relativo, o para que no descarte la línea parcial inicial, sale en rojo.
- Tipo de prueba sugerida: unitaria (propiedades)
- Severidad: Media — un `hasta` erróneo duplica o salta líneas del log.

#### VER-4: Rutas `{slug:path}` solapadas
- Paso del plan: T-02 — "Casos de enrutado de la spec §9: `…/runs`, `…/runs/{run_id}` y `…/runs/{run_id}/log` llegan cada uno a su endpoint" (fase-1)
- Punto de fallo: con `SLUG = "/{slug:path}"`, `/novelas/demo-24/runs/r-20260924-0001/log` puede casar con otra ruta registrada antes, con `slug=demo-24/runs/r-20260924-0001`, y salir 422 o el modelo equivocado.
- Precondiciones: `demo-24` con el run `r-20260924-0001`.
- Cómo verificarlo: `GET /novelas/demo-24/runs`, `…/runs/r-20260924-0001`, `…/runs/r-20260924-0001/log`, `…/runs/r-20260924-0001/log/extra` y `GET /novelas/runs/runs`. Métodos de `docs/validators.md` §3.2 (patrón 1) y §3.5.
- Resultado esperado: una lista de `Manifest`, un `Manifest`, un `TramoDeLog`, 404 y 404 o 422 sin abrir ficheros de fuera de `backend/`; cada cuerpo valida contra su modelo.
- Tipo de prueba sugerida: integración
- Severidad: Alta — la actividad en vivo (O-02) no llega al panel.

#### VER-5: Carrera entre `stat` y la lectura del log
- Paso del plan: T-02 — "`tramo_de_log(run_id, desde)`, que hace `stat`…, `seek(desde)` y lee hasta el final" (fase-1)
- Punto de fallo: si el CLI añade una línea entre el `stat` y la lectura, la ventana incluye bytes posteriores a `tamano` y se rompe `hasta ≤ tamano` (§8.3), o el 416 se decide con un tamaño viejo.
- Precondiciones: espía sobre `stat` que añade 100 bytes con `\n` a `harness.log` justo después de devolver.
- Cómo verificarlo: `GET …/log?desde=0` con el espía activo.
- Resultado esperado: el cuerpo cumple `desde ≤ hasta ≤ tamano`, y la petición siguiente con ese `hasta` devuelve las líneas añadidas.
- Tipo de prueba sugerida: integración
- Severidad: Media — invariante del contrato roto en uso real, con el bucle escribiendo.

#### VER-6: Solo lectura que no sea decorativa y cinco `GET` intactos
- Paso del plan: T-03 — "si el test pasa a la primera, se comprueba que no es decorativo introduciendo una escritura temporal… y viéndolo en rojo"; "`git diff`… solo añade rutas y esquemas (revisión en el PR)"
- Punto de fallo: la escritura inyectada no queda registrada, y la revisión del diff del OpenAPI es manual, así que un cambio en un esquema compartido (`Manifest`) pasa.
- Precondiciones: sha anterior a T-01.
- Cómo verificarlo: anotar en el PR la salida en rojo con la escritura inyectada; comparar `jq '.paths["/novelas/{slug}/estado"]'` y los otros cuatro caminos de la 0001, y `.components.schemas` de sus modelos, entre `git show <sha>:backend/api/openapi.json` y el actual. Métodos de `docs/validators.md` §3.5 (API) y §3.8.
- Resultado esperado: el PR contiene la salida en rojo; los diez subárboles comparados son idénticos.
- Tipo de prueba sugerida: integración + revisión manual
- Severidad: Alta — un test decorativo taparía escrituras en el workspace (RF-38, Must).

#### VER-7: Los fixtures de lint, fuera de `eslint .`
- Paso del plan: T-04, T-06 y T-19 (PD2) — "la API de ESLint sobre fixtures de `frontend/test/fixtures/lint/`" (fase-2)
- Punto de fallo: si `eslint .` no ignora `test/fixtures/lint/`, `npm run lint` falla siempre; si el `ignores` es demasiado amplio, deja de revisar `src/`.
- Precondiciones: fixtures de CA-03, CA-43 y CA-51 en su sitio.
- Cómo verificarlo: `npm run lint` sobre el árbol; `lint.test.ts` con cada fixture por ruta explícita; añadir temporalmente `innerHTML` a `src/main.ts`. Método de `docs/validators.md` §3.2.
- Resultado esperado: `npm run lint` sale con 0 sobre el árbol limpio; cada fixture da ≥ 1 error; con `src/main.ts` alterado, `npm run lint` sale con ≠ 0.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — el pre-commit bloquearía todos los commits, o no bloquearía ninguno.

#### VER-8: El 403 de `/@fs/` necesita un control positivo
- Paso del plan: T-04 — "`/@fs/<raíz>/frontend/src/main.ts` responde 200 (control positivo, D56); `/@fs/<raíz>/AGENTS.md` responde 403" (fase-2)
- Punto de fallo: un servidor mal arrancado, con otro `root` o con `server.fs.allow: ['.']` resuelto desde otro directorio, puede devolver 403 a todo, y el test pasa sin probar la frontera. **Incorporado en la v5 (D56):** CA-43 exige este control positivo desde los dos directorios de arranque; el verificador comprueba que el test lo hace.
- Precondiciones: `servidor.test.ts` con `createServer` sobre `frontend/vite.config.ts`, lanzado una vez desde `frontend/` y otra desde la raíz.
- Cómo verificarlo: en los dos arranques, pedir `/@fs/<raíz>/frontend/src/main.ts` y `/@fs/<raíz>/AGENTS.md`. Mismo principio que el control positivo del canario de `docs/validators.md` §4.9.
- Resultado esperado: 200 para `main.ts` y 403 para `AGENTS.md` en los dos arranques.
- Tipo de prueba sugerida: integración
- Severidad: Crítica — un verde vacío taparía la exposición de `novelas/`.

#### VER-9: `npm` falso del pre-commit en Windows
- Paso del plan: T-04 — "un `npm` falso delante en el `PATH` que registra sus argumentos y sale con 1… Debe pasar en local en Windows con Git Bash en el `PATH`, no solo en CI (D36)" (fase-2)
- Punto de fallo: en Git Bash, el hook puede resolver el `npm` real (`npm.cmd`), que también falla en el repositorio temporal sin `package.json`. El commit se aborta y el test pasa sin que el falso se haya ejecutado.
- Precondiciones: Windows con Git Bash y Linux en CI.
- Cómo verificarlo: comprobar que existe el registro del `npm` falso y que su contenido es `--prefix frontend run lint`.
- Resultado esperado: registro presente con esa línea en los dos sistemas; en el commit sin ficheros de `frontend/`, registro ausente.
- Tipo de prueba sugerida: integración
- Severidad: Media — el test de CA-41 sería decorativo en local.

#### VER-10: `tipos:comprobar` con `git diff --exit-code`
- Paso del plan: T-05 — "`tipos:comprobar` (`tipos` más `git diff --exit-code src/shared/api/esquema.gen.ts`)" (fase-2)
- Punto de fallo: `git diff` compara contra el índice. Un `esquema.gen.ts` sin seguimiento no produce diff, y con `core.autocrlf` en Windows puede aparecer un diff falso de finales de línea.
- Precondiciones: árbol limpio; Windows con `core.autocrlf=true`.
- Cómo verificarlo: `git rm --cached frontend/src/shared/api/esquema.gen.ts` y ejecutar `npm run tipos:comprobar`; restaurarlo; ejecutarlo en Windows sin cambios. Método de `docs/validators.md` §3.8.
- Resultado esperado: sin seguimiento, código ≠ 0; en Windows sin cambios, código 0.
- Tipo de prueba sugerida: integración
- Severidad: Media — el contrato puede derivar en local; en CI la copia es limpia.

#### VER-11: El plazo de 5 s bajo el reloj simulado
- Paso del plan: T-06 — "una señal que combina la de la vista con un plazo de 5 s" y "el reloj simulado de Vitest; nunca esperas por tiempo real" (fase-4)
- Punto de fallo: `AbortSignal.timeout` usa temporizadores reales que `vi.useFakeTimers()` no controla, así que el test de CA-04 se cuelga o espera 5 s reales. `AbortSignal.any` existe en Node 24 (D35), pero no necesariamente en el `AbortSignal` que expone jsdom.
- Precondiciones: `fetch` espiado que no resuelve nunca; reloj simulado.
- Cómo verificarlo: avanzar 5 000 ms simulados y medir la duración real del test.
- Resultado esperado: el `ErrorDeApi` llega con `tipo` «tiempo» y detalle «la API no respondió en 5 s»; duración real < 1 s.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — CA-04 y CA-05 no serían deterministas.

#### VER-12: Globales y propiedades de red en eslint
- Paso del plan: T-06 (PD2) — "Regla de eslint que prohíbe `fetch`, `XMLHttpRequest`, `WebSocket` y `EventSource` fuera de `src/shared/api/`" (fase-4)
- Punto de fallo: `no-restricted-globals` solo ve identificadores sueltos; `window.fetch`, `globalThis['fetch']` y `navigator.sendBeacon` pasan.
- Precondiciones: fixtures con esos tres usos fuera de `src/shared/api/`.
- Cómo verificarlo: `lint.test.ts` sobre cada fixture. Método de `docs/validators.md` §3.2.
- Resultado esperado: ≥ 1 error por fixture.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — RF-03 depende de esta regla, y RNF-06 y RNF-08 la tienen como red.

#### VER-13: Lo que jsdom no mide
- Paso del plan: T-07 y T-20 — "plegado con 72 px" (CA-50, parte unitaria) y "cada componente interactivo expone sus estados… hover, foco" (fase-3, fase-4)
- Punto de fallo: jsdom no calcula el layout ni las pseudoclases `:hover` y `:focus-visible`, así que un unitario que afirma 72 px o un contorno de 2 px no mide nada.
- Precondiciones: `layout.test.ts` y `estados.test.ts` de T-07 y T-20.
- Cómo verificarlo: cambiar temporalmente `--q-ancho-barra-plegada` a 100 px y el contorno de foco a 1 px; ejecutar los unitarios y `marca.spec.ts`.
- Resultado esperado: `marca.spec.ts` sale en rojo en los dos cambios (ancho 72 ± 0,5 px y `outline-width` ≥ 2 px); la parte unitaria solo afirma estructura, clases y atributos.
- Tipo de prueba sugerida: e2e
- Severidad: Baja — T-21 lo cierra, pero la cobertura unitaria declarada engaña.

#### VER-14: El presupuesto de Lectura no puede quedarse a 0 KB
- Paso del plan: T-08 (PD5) — "lo trata como 0 KB si no existe" y T-14 "`presupuesto.mjs` (modificar solo si el nombre del chunk no casa…)"
- Punto de fallo: si el nombre del chunk cambia después de T-14, el script vuelve a medir 0 KB en silencio y RNF-02 deja de comprobarse.
- Precondiciones: build con el chunk de Lectura.
- Cómo verificarlo: ejecutar `npm run presupuesto` sobre un `dist/` de fixture sin chunk de Lectura, con el código de T-14 en adelante.
- Resultado esperado: código ≠ 0 con un mensaje que nombra el chunk de Lectura ausente.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — un presupuesto obligatorio queda sin medir.

#### VER-15: Qué cuenta como carga inicial y cómo se mide el logo
- Paso del plan: T-08 — "mide en gzip los chunks de `dist/assets/` que carga `index.html`… y `logo.png` más `favicon.png` en `dist/` (≤ 80 KB)" (fase-4)
- Punto de fallo: los `<link rel="modulepreload">` y los chunks comunes que Vite extrae no se suman a la carga inicial; `logo.png` sale con hash (`logo-<hash>.png`) y el script no lo encuentra.
- Precondiciones: `dist/` de fixture con `index.html` que carga `assets/index-a.js` y precarga `assets/vendor-b.js` (60 000 bytes gzip cada uno), más `assets/logo-1a2b.png` de 68 000 bytes y `favicon.png` de 13 000 bytes (1 KB = 1 000 bytes, D52).
- Cómo verificarlo: `npm run presupuesto` sobre el fixture.
- Resultado esperado: código ≠ 0, con el inicial medido en 120 000 bytes > 100 000 y las imágenes en 81 000 > 80 000.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — RNF-01 y RNF-20 pasarían en falso.

#### VER-16: `escapado.test.ts` sin bash
- Paso del plan: T-09 — "Necesita `bash` en el `PATH`, también en Windows con Git Bash; sin bash, el test falla con un mensaje que lo nombra, no se salta (D36)" (fase-5)
- Punto de fallo: un `skipIf(!bash)` deja pasar el test en silencio en Windows sin Git Bash en el `PATH`, contra D36.
- Precondiciones: `PATH` sin bash.
- Cómo verificarlo: ejecutar `npx vitest run src/features/lanzar/escapado.test.ts`. Método de `docs/validators.md` §3.6.
- Resultado esperado: código ≠ 0 con un mensaje que nombra bash; 0 tests saltados en el informe.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — RF-14 quedaría sin probar en local.

#### VER-17: Tabla del subgénero exhaustiva
- Paso del plan: T-10 — "la etiqueta del `subgenero` desde una tabla exhaustiva sobre el tipo generado, que `tsc` comprueba" (fase-5)
- Punto de fallo: si la tabla se declara como `Record<string, string>`, `tsc` no detecta un subgénero nuevo del backend.
- Precondiciones: copia de trabajo de `openapi.json` con un valor más en el enumerado de `subgenero`.
- Cómo verificarlo: `npm run tipos` y `npm run typecheck`. Método de `docs/validators.md` §3.1.
- Resultado esperado: `tsc` sale con ≠ 0 y nombra el fichero de la tabla.
- Tipo de prueba sugerida: unitaria (estática)
- Severidad: Baja — solo afecta a una etiqueta del banner.

#### VER-18: Cálculo de los pares con control conocido
- Paso del plan: T-19 — "contraste recalculado desde `tokens.css`, con las transparencias compuestas sobre su fondo" (fase-3)
- Punto de fallo: si el alfa se compone después de linealizar, o si las cadenas `var()` no se resuelven, los contrastes salen falsos y el test pasa.
- Precondiciones: `tokens.css` con los valores de §8.4.
- Cómo verificarlo: comparar los 21 resultados con la tabla de §8.4 (por ejemplo, 14,68:1, 5,78:1 compuesto y 4,28:1); cambiar `--q-naranja-700` a `#F97316`.
- Resultado esperado: los 21 valores dentro de ± 0,02 de la tabla; con el token cambiado, el test sale en rojo en `--q-texto-sobre-primario` sobre `--q-primario`.
- Tipo de prueba sugerida: unitaria
- Severidad: Alta — RNF-19 es la única comprobación de contraste sobre degradados y elementos no textuales.

#### VER-19: Las dos implementaciones del lector de tokens coinciden
- Paso del plan: T-19 — "Lector de tokens con dos implementaciones: el navegador lee las propiedades CSS computadas; los tests leen `tokens.css`" (fase-3), usado en T-11 y T-14
- Punto de fallo: el lector de tests puede no resolver `var(--q-naranja-700)` ni el alfa de `--q-deco-teselas`; el del navegador puede devolver un formato que `THREE.Color` no entiende y cae a negro.
- Precondiciones: build de producción en Chromium.
- Cómo verificarlo: comparar, para `--q-primario`, `--q-icono-cian`, `--q-pendiente`, `--q-deco-seleccion`, `--q-fondo-pagina`, `--q-secundario-fondo` y `--q-texto-secundario`, el hexadecimal que da cada implementación y el color de material de la escena.
- Resultado esperado: los 7 iguales en las dos implementaciones; ningún material a `0x000000` salvo que su rol lo sea.
- Tipo de prueba sugerida: unitaria + e2e
- Severidad: Alta — CA-55 pasaría en unitario y el panel pintaría otros colores.

#### VER-20: El `logo.png` se versiona sin alterar
- Paso del plan: T-19 — "`git diff --stat` del `logo.png` muestra el fichero binario sin cambios respecto al aportado (mismo sha256…)" (fase-3)
- Punto de fallo: una regla de `.gitattributes` con `text` o `eol`, o un filtro, altera el binario al añadirlo.
- Precondiciones: sha256 anotado antes del commit.
- Cómo verificarlo: `git show HEAD:frontend/src/shared/marca/logo.png | sha256sum` y `git check-attr -a frontend/src/shared/marca/logo.png`.
- Resultado esperado: el mismo sha256; ningún atributo `text`, `eol` ni `filter`.
- Tipo de prueba sugerida: revisión manual
- Severidad: Baja — CA-52 fija las dimensiones y el peso, no el contenido.

#### VER-21: La comprobación del PNG no entra en el bundle
- Paso del plan: T-19 — "`logo.ts`… y la comprobación del PNG y del favicon" (fase-3)
- Punto de fallo: si la comprobación de firma y dimensiones con `node:fs` vive en `logo.ts`, que es un módulo del navegador, rompe `vite build` o mete código de Node en el chunk inicial.
- Precondiciones: build de producción.
- Cómo verificarlo: `npm run build` y `grep -rlE "node:fs|readFileSync" frontend/dist/assets`.
- Resultado esperado: build con código 0 y 0 ficheros encontrados.
- Tipo de prueba sugerida: integración
- Severidad: Media — rompe el build o RNF-01.

#### VER-22: Recursos creados sin pasar por la fábrica
- Paso del plan: T-14 — "fábrica de renderer falsa que registra cada `dispose()`" (fase-6)
- Punto de fallo: las geometrías, materiales o texturas creados con `new THREE.*` fuera de la fábrica no se registran, y CA-31 pasa aunque no se liberen.
- Precondiciones: `escena.test.ts`.
- Cómo verificarlo: recorrer `scene.traverse` antes de salir, reunir los recursos y compararlos con el registro de `dispose()`; añadir temporalmente una malla creada directamente en `escena.ts`.
- Resultado esperado: el conjunto recorrido está contenido en el de liberados; con la malla añadida, el test sale en rojo.
- Tipo de prueba sugerida: unitaria
- Severidad: Media — fugas acumulativas (ver VAL-20).

#### VER-23: Los draw calls medidos no pueden ser 0
- Paso del plan: T-14 y T-16 — "`data-draw-calls` (`renderer.info.render.calls` del último fotograma)" y "`data-draw-calls` ≤ 5 con `demo-24` y `grande-999`, solo en Chromium" (fase-6, fase-7)
- Punto de fallo: leído antes del primer fotograma, o con `info.autoReset` desactivado, vale 0 o acumula, y un 0 cumple «≤ 5» sin medir nada.
- Precondiciones: Chromium con WebGL; `demo-24` y `grande-999`.
- Cómo verificarlo: esperar dos `requestAnimationFrame` y leer `data-draw-calls`.
- Resultado esperado: 1 ≤ `data-draw-calls` ≤ 5 en los dos workspaces.
- Tipo de prueba sugerida: e2e
- Severidad: Media — RNF-03 pasaría en falso.

#### VER-24: La excepción de `no-unsanitized` y el título del índice
- Paso del plan: T-15 — "La regla `no-unsanitized` de T-04 no lleva excepción por fichero: la única inserción de HTML… marcada con un único `eslint-disable-next-line`" y "encabezado con el `titulo` del índice, escrito con `textContent`" (fase-6)
- Punto de fallo: en la v4, la excepción por fichero permitía cualquier inserción de HTML en `lector.ts`, también la del `titulo`, que escribe un agente, si se insertaba como HTML. **Incorporado en la v5 (D56):** la excepción es un único `eslint-disable-next-line`, el `titulo` va con `textContent` y CA-25 y CA-26 lo comprueban; el verificador comprueba que se mantiene.
- Precondiciones: índice de fixture con `titulo: "<img src=x onerror=alert(1)>"`.
- Cómo verificarlo: abrir el capítulo en `lector.test.ts`; `grep -cE "innerHTML|insertAdjacentHTML|outerHTML" frontend/src/features/lectura/lector.ts`; `grep -c "eslint-disable-next-line no-unsanitized" frontend/src/features/lectura/lector.ts`; buscar en `frontend/eslint.config.js` un bloque `files` que apague `no-unsanitized`.
- Resultado esperado: el `textContent` del encabezado es el literal; 0 `img` en el lector; exactamente 1 coincidencia de inserción en `lector.ts`, alimentada por la salida de `markdown-it`, 1 `eslint-disable-next-line` y 0 excepciones por fichero.
- Tipo de prueba sugerida: unitaria
- Severidad: Crítica — abre una vía de inyección fuera de la que D14 controla.

#### VER-25: El autouse `_sin_claves_reales` vacía el test de CA-42
- Paso del plan: T-16 — "con el autouse `_sin_claves_reales` desactivado para este test… Primero, el control positivo: el test afirma que `os.environ["TRACE_TO_LANGFUSE"] == "true"` y que `run.RAIZ_REPO` tiene el `.env` de prueba" (fase-7)
- Punto de fallo: el entorno ya llega limpio y `run.RAIZ_REPO` ya está aislado por el fixture de sesión, así que el test pasa aunque `panel.py` no aísle nada. **Incorporado en la v5 (D56):** CA-42 exige desactivar el autouse y el control positivo; el verificador comprueba que el test lo hace.
- Precondiciones: `test_generador_sin_claves` con los valores ficticios de CA-42.
- Cómo verificarlo: afirmar, antes de `generar`, que `os.environ["TRACE_TO_LANGFUSE"] == "true"` y que `run.RAIZ_REPO` tiene un `.env` de prueba; quitar temporalmente el aislamiento de `panel.py`. Patrón de `docs/validators.md` §3.5 y de `backend/conftest.py`.
- Resultado esperado: las afirmaciones previas pasan; sin el aislamiento, el test sale en rojo.
- Tipo de prueba sugerida: unitaria
- Severidad: Crítica — la protección contra emitir scores con claves reales sería decorativa.

#### VER-26: Precondiciones de `demo-24` construido por `panel.py`
- Paso del plan: T-16 (PD6) — "`fabrica.construir(destino, "demo-24", fabrica.DEMO, cerrados=7)` y después `fabrica.preparar_capitulo(…, 8)`" (fase-7)
- Punto de fallo: el `demo-24` de los e2e y el de `backend/conftest.py` (instantánea de `demo-terminado`) se construyen por vías distintas. Los e2e de CA-17, CA-22 y CA-24 dan por hechos datos que `panel.py` quizá no deja.
- Precondiciones: `generar(<tmp>)` y la API sobre `<tmp>`.
- Cómo verificarlo: consultar `…/checkpoint`, `…/capitulos`, `…/escaleta`, `…/config`, `…/runs` y el `…/log` del run mayor.
- Resultado esperado: `capitulo` 7; el 8 en el índice; 3 actos y curva de 24; `num_capitulos` 24; ≥ 1 run y `lineas` no vacía en el de `run_id` mayor.
- Tipo de prueba sugerida: integración
- Severidad: Media — los e2e fallarían o probarían otro escenario.

#### VER-27: El generador no es idempotente
- Paso del plan: T-16 y T-17 — "generación previa con `panel.py`" en `playwright.config.ts` y "generación de workspaces con `python -m tests.fixtures.panel`" en el job (fase-7)
- Punto de fallo: si se genera dos veces sobre el mismo destino, `novela nueva` sale con 1 porque el workspace existe (`nueva/cmd.py:57-60`), y la segunda ejecución falla o deja datos mezclados.
- Precondiciones: destino ya generado.
- Cómo verificarlo: `npm run e2e` dos veces seguidas en local; revisar que CI genera una sola vez o sobre un destino vacío.
- Resultado esperado: las dos ejecuciones salen con 0; `NOVELAS_DIR` apunta al mismo destino en el `webServer` y en el paso de CI.
- Tipo de prueba sugerida: integración
- Severidad: Media — el job falla sin causa en el código.

#### VER-28: El espía de peticiones debe ver lo que carga la página
- Paso del plan: T-16 — "con escucha de `console.error` y `pageerror` en todas… y un espía de todas las peticiones" (fase-7)
- Punto de fallo: un `page.on('request')` registrado después de `goto` no ve las peticiones iniciales (favicon, fuentes, módulos), y «0 a otros orígenes» pasa sin haber observado nada.
- Precondiciones: `recorrido.spec.ts`.
- Cómo verificarlo: registrar el espía en el contexto antes de la primera navegación y afirmar que aparecen `favicon.png`, el `.woff2` y `GET /novelas`.
- Resultado esperado: las tres peticiones aparecen en el registro; 0 con método distinto de `GET`; 0 a otros orígenes.
- Tipo de prueba sugerida: e2e
- Severidad: Media — RNF-06, RNF-08 y CA-16 pasarían sin medir.

#### VER-29: Etiquetas de axe para WCAG 2.1
- Paso del plan: T-16 — "axe con reglas WCAG 2.1 A y AA, 0 `serious` y 0 `critical`" (fase-7)
- Punto de fallo: con solo `wcag2a` y `wcag2aa`, axe no ejecuta las reglas propias de 2.1 (`wcag21a` y `wcag21aa`).
- Precondiciones: `accesibilidad.spec.ts`.
- Cómo verificarlo: revisar las etiquetas pasadas a `AxeBuilder`; inyectar temporalmente un texto a 2:1 en Lanzar.
- Resultado esperado: las cuatro etiquetas presentes; con el texto inyectado, el spec sale en rojo.
- Tipo de prueba sugerida: e2e
- Severidad: Media — RNF-12 se mediría a medias.

#### VER-30: La imagen de Playwright coincide con el lockfile
- Paso del plan: T-17 — "dentro de la imagen oficial de Playwright (la de la versión fijada en el lockfile)" (fase-7)
- Punto de fallo: si la etiqueta de la imagen no se actualiza al subir `@playwright/test`, faltan navegadores o el render cambia y las referencias de RNF-22 fallan.
- Precondiciones: job `frontend-e2e`.
- Cómo verificarlo: un paso que imprime `npx playwright --version` y compararlo con la etiqueta de `image:` de `ci.yml`.
- Resultado esperado: la misma versión x.y.z; el job falla si difieren.
- Tipo de prueba sugerida: integración (CI)
- Severidad: Media — deja la regresión visual en rojo sin cambio de código.

#### VER-31: CI nunca actualiza las referencias
- Paso del plan: T-21 — "Primera ejecución de `visual.spec.ts` en el contenedor: genera las referencias" (fase-7)
- Punto de fallo: si el script `e2e` o el job llevan `--update-snapshots`, las referencias se regeneran en cada ejecución y RNF-22 no compara nada.
- Precondiciones: `package.json` y `ci.yml`.
- Cómo verificarlo: `grep -nE "update-snapshots|\s-u(\s|$)" frontend/package.json .github/workflows/ci.yml`; en una rama de prueba, borrar una referencia.
- Resultado esperado: 0 coincidencias; el job sale en rojo con la referencia borrada.
- Tipo de prueba sugerida: integración (CI)
- Severidad: Media — la regresión visual sería decorativa.

#### VER-32: Registro reproducible de T-18
- Paso del plan: T-18 — "un conductor a mano, desde `backend/` con `uv run python` y sin versionar… Se mide la mediana de fps… y se busca `PermissionError`" (fase-7; D33)
- Punto de fallo: con un conductor sin versionar, el resultado no se puede repetir ni contrastar cuando se revise el riesgo U si no queda anotada su orden.
- Precondiciones: T-18 ejecutada.
- Cómo verificarlo: leer el apartado «Resultados de las comprobaciones manuales» de §13 de la spec.
- Resultado esperado: constan la orden exacta del conductor, la mediana de fps, la versión del navegador, el recuento de `PermissionError` y la fecha.
- Tipo de prueba sugerida: revisión manual
- Severidad: Baja — afecta a la trazabilidad de una demostración.

#### VER-33: La documentación va en el commit de cada tarea
- Paso del plan: regla común 4 — "Un commit por tarea, que incluye la documentación de referencia que esa tarea deja desfasada" (README §5)
- Punto de fallo: la tabla de 16 filas de README §5 solo se inspecciona, y una sección se queda para «el final».
- Precondiciones: los commits de T-01 a T-21 y el de cierre, T-23.
- Cómo verificarlo: para cada fila de la tabla, `git show --stat <commit de la tarea>` y buscar la sección en el diff.
- Resultado esperado: 16 de 16 filas presentes en el commit de su tarea.
- Tipo de prueba sugerida: revisión manual
- Severidad: Media — la documentación describiría un estado que no es el del commit.

### Matriz de cobertura
| Requisito | CA | Validadores | Verificadores |
|-----------|----|-------------|---------------|
| R1 · RF-01 — dev server en 5173, `VITE_API_URL` | CA-01 | VAL-1 | VER-8 |
| R2 · RF-02 — tipos solo de `esquema.gen.ts` | CA-02 | SIN CUBRIR | VER-10 |
| R3 · RF-03 — toda petición desde el cliente, `GET` y `Accept` | CA-03 | SIN CUBRIR | VER-7, VER-12 |
| R4 · RF-04 — fallo con motivo y datos conservados | CA-04 | VAL-1, VAL-3 | VER-11 |
| R5 · RF-05 — sondeo a 10 s sin solapes | CA-05 | VAL-2 | VER-11 |
| R6 · RF-06 — pausa con pestaña oculta | CA-06 | VAL-5 | VER-11 |
| R7 · RF-07 — cancelación al cambiar de vista | CA-07 | VAL-4 | SIN CUBRIR |
| R8 · RF-08 — Inicio, una entrada por novela | CA-08 | SIN CUBRIR | SIN CUBRIR |
| R9 · RF-09 — «ruta no válida» sin peticiones | CA-09 | VAL-6 | SIN CUBRIR |
| R10 · RF-10 — estado en el hash | CA-10 | VAL-7 | SIN CUBRIR |
| R11 · RF-11 — orden `/novela-nueva` y copiar | CA-11 | VAL-8 | SIN CUBRIR |
| R12 · RF-12 — validación de campos | CA-12 | VAL-9 | SIN CUBRIR |
| R13 · RF-13 — slug existente | CA-13 | SIN CUBRIR | SIN CUBRIR |
| R14 · RF-14 — escapado de la idea | CA-14 | VAL-10 | VER-16 |
| R15 · RF-15 — órdenes de la sesión del harness | CA-15 | SIN CUBRIR | SIN CUBRIR |
| R16 · RF-16 — Lanzar no produce ficheros | CA-16 | SIN CUBRIR | VER-28 |
| R17 · RF-17 — resumen de Progreso | CA-17 | SIN CUBRIR | VER-26 |
| R18 · RF-18 — gráfica de tensión y tabla | CA-18 | VAL-11 | SIN CUBRIR |
| R19 · RF-19 — escaleta ausente sin error | CA-19 | VAL-12 | SIN CUBRIR |
| R20 · RF-20 — hilos abiertos | CA-20 | SIN CUBRIR | SIN CUBRIR |
| R21 · RF-21 — runs con «árbol sucio» | CA-21 | SIN CUBRIR | SIN CUBRIR |
| R22 · RF-22 — tramo de log a 3 s | CA-22 | VAL-13 | VER-26 |
| R23 · RF-23 — «sin actividad desde» | CA-23 | VAL-14 | SIN CUBRIR |
| R24 · RF-24 — un volumen por capítulo y tres estados | CA-24 | VAL-12, VAL-15 | VER-26 |
| R25 · RF-25 — lector sin frontmatter | CA-25 | VAL-16 | VER-24 |
| R26 · RF-26 — markdown hostil como texto | CA-26 | VAL-17 | VER-24 |
| R27 · RF-27 — no cerrado sin petición | CA-27 | VAL-7 | SIN CUBRIR |
| R28 · RF-28 — lista HTML y teclado | CA-28 | VAL-18 | SIN CUBRIR |
| R29 · RF-29 — sin WebGL | CA-29 | VAL-19 | SIN CUBRIR |
| R30 · RF-30 — cámara con reduced motion | CA-30 | SIN CUBRIR | SIN CUBRIR |
| R31 · RF-31 — liberación de la escena | CA-31 | VAL-20 | VER-22 |
| R32 · RF-32 — `GET …/config` | CA-32 | SIN CUBRIR | VER-2 |
| R33 · RF-33 — `GET …/escaleta` | CA-33 | SIN CUBRIR | VER-1, VER-2 |
| R34 · RF-34 — `GET …/checkpoint` | CA-34 | SIN CUBRIR | SIN CUBRIR |
| R35 · RF-35 — `GET …/runs` | CA-35 | SIN CUBRIR | VER-4 |
| R36 · RF-36 — `GET …/log`, tramo y tope | CA-36 | VAL-21 | VER-3, VER-4, VER-5 |
| R37 · RF-37 — códigos de borde del log | CA-37 | VAL-21 | VER-4, VER-5 |
| R38 · RF-38 — API sin escrituras | CA-38 | SIN CUBRIR | VER-6 |
| R39 · RF-39 — CI falla si `esquema.gen.ts` difiere | CA-39 | SIN CUBRIR | VER-10 |
| R40 · RF-40 — pasos de CI del frontend | CA-40 | SIN CUBRIR | VER-27, VER-30 |
| R41 · RF-41 — eslint en el pre-commit | CA-41 | VAL-22 | VER-9 |
| R42 · RF-42 — generador de e2e sin claves | CA-42 | VAL-23 | VER-25 |
| R43 · RF-43 — sin imports ni ficheros de fuera | CA-43 | VAL-24 | VER-7, VER-8 |
| R44 · RF-44 — dependencias exactas | CA-44 | SIN CUBRIR | SIN CUBRIR |
| R45 · RF-45 — documentación en el mismo commit | CA-45 | VAL-25 | VER-33 |
| R46 · RF-46 — tokens en un único fichero | CA-46 | VAL-26 | SIN CUBRIR |
| R47 · RF-47 — tonos vivos decorativos, pares AA | CA-47 | VAL-27 | VER-18 |
| R48 · RF-48 — barra lateral | CA-48 | VAL-28 | VER-13 |
| R49 · RF-49 — barra superior | CA-49 | VAL-3 | SIN CUBRIR |
| R50 · RF-50 — plegado | CA-50 | SIN CUBRIR | VER-13 |
| R51 · RF-51 — logo siempre redondeado | CA-51 | VAL-29 | VER-21 |
| R52 · RF-52 — CI comprueba logo y favicon | CA-52 | VAL-33 | VER-20, VER-21 |
| R53 · RF-53 — banner de la novela | CA-53 | VAL-30 | VER-17 |
| R54 · RF-54 — rejilla por ancho | CA-54 | VAL-31 | SIN CUBRIR |
| R55 · RF-55 — escena y gráfica leen los tokens | CA-55 | SIN CUBRIR | VER-19 |
| R56 · RF-56 — fuentes e iconos autoalojados | CA-56 | VAL-32 | SIN CUBRIR |
| R57 · RF-57 — estados de los componentes | CA-57 | SIN CUBRIR | VER-13, VER-31 |
| R58 · RF-58 — esqueleto, vacío y error | CA-58 | SIN CUBRIR | VER-31 |
| R59 · RF-59 — sin avatar, modo oscuro ni idioma | CA-59 | SIN CUBRIR | SIN CUBRIR |
| R60 · RF-60 — sin imágenes de personas reales | CA-60 | VAL-33 | SIN CUBRIR |
| R61 · RF-61 — favicon derivado | CA-61 | SIN CUBRIR | SIN CUBRIR |
| R62 · RNF-01 — JS inicial ≤ 100 KB | — | SIN CUBRIR | VER-15 |
| R63 · RNF-02 — chunk de Lectura ≤ 300 KB | — | SIN CUBRIR | VER-14 |
| R64 · RNF-03 — ≤ 5 draw calls | — | SIN CUBRIR | VER-23 |
| R65 · RNF-04 — ≥ 30 fps | — | SIN CUBRIR | VER-32 |
| R66 · RNF-05 — ≤ 60 peticiones/min; 0 oculta | — | VAL-2, VAL-5 | VER-11 |
| R67 · RNF-06 — 0 peticiones no `GET` | — | VAL-35 | VER-28 |
| R68 · RNF-07 — 0 elementos activos en el lector | — (CA-26) | VAL-17 | VER-24 |
| R69 · RNF-08 — 0 peticiones a otros orígenes | — | VAL-35 | VER-28 |
| R70 · RNF-09 — 0 datos en el navegador | — | SIN CUBRIR | SIN CUBRIR |
| R71 · RNF-10 — `/@fs/` responde 403 | — (CA-43) | VAL-24 | VER-8 |
| R72 · RNF-11 — 0 avisos `high` de `npm audit` | — | SIN CUBRIR | SIN CUBRIR |
| R73 · RNF-12 — 0 violaciones serias de axe | — | SIN CUBRIR | VER-29 |
| R74 · RNF-13 — 0 pasos con ratón | — | VAL-18 | SIN CUBRIR |
| R75 · RNF-14 — Chromium y Firefox | — | SIN CUBRIR | VER-30 |
| R76 · RNF-15 — recuperación en ≤ 1 ronda | — | VAL-34 | SIN CUBRIR |
| R77 · RNF-16 — 0 `console.error` y `pageerror` | — | VAL-19 | SIN CUBRIR |
| R78 · RNF-17 — log de 1 MiB < 200 ms | — | SIN CUBRIR | SIN CUBRIR |
| R79 · RNF-18 — 0 cambios en los cinco `GET` de la 0001 | — | SIN CUBRIR | VER-6 |
| R80 · RNF-19 — 0 pares bajo su umbral | — (CA-47) | VAL-27 | VER-18 |
| R81 · RNF-20 — WOFF2, CSS e imágenes de marca | — | SIN CUBRIR | VER-15 |
| R82 · RNF-21 — CLS ≤ 0,1 | — | SIN CUBRIR | SIN CUBRIR |
| R83 · RNF-22 — ≤ 0,1 % de píxeles distintos | — | SIN CUBRIR | VER-30, VER-31 |
| R84 · RNF-23 — 0 medidas distintas de su token | — | SIN CUBRIR | SIN CUBRIR |
| R85 · RNF-24 — foco visible de 2 px | — | SIN CUBRIR | VER-13 |

### Preguntas resueltas
Todas cerradas en la v5 de la spec. Se conservan con su resolución para que nadie las reproponga.
- Q1 — ¿`07`, ` 3` o `+3` son capítulos válidos, y se normalizan? **Resuelta (D41):** solo dígitos, sin ceros a la izquierda, sin signo ni espacios (`^[1-9][0-9]{0,2}$` para capítulos y para el de la ruta, `^[1-9][0-9]*$` para palabras); lo demás es error de validación, sin normalizar.
- Q2 — ¿Una idea con solo tabuladores o saltos de línea «solo tiene espacios»? **Resuelta (D42):** sí; cuenta como vacía la idea hecha solo de `\s`.
- Q3 — ¿Qué hace Lanzar si `GET /novelas` no ha respondido o ha fallado? **Resuelta (D43):** genera la orden sin comprobar el slug, con el aviso «no se ha podido comprobar si el slug ya existe».
- Q4 — ¿Se contempla pegar la orden en un bash interactivo, o en el prompt de Claude Code? **Resuelta (D44, que sustituye a D7):** la idea va entre comillas simples con cada `'` como `'\''`, inerte en bash interactivo y no interactivo; CA-14 corre además con `set -H`. El prompt de Claude Code queda fuera del alcance, como riesgo U.
- Q5 — ¿Una ronda con un recurso fallido cuenta como correcta, y cuándo desaparece el aviso? **Resuelta (D45):** correcta solo si todos sus recursos responden bien (el 404 de la escaleta y el 416 del log cuentan como bien); si no, se conserva la hora anterior y el aviso desaparece en la siguiente ronda correcta.
- Q6 — ¿Qué muestra la gráfica con todo `tension_real` a `null` o con más entradas que la curva objetivo? **Resuelta (D46):** el mismo estado que con `tension_real` vacío, con la curva objetivo dibujada; y el eje x hasta el mayor de los dos tamaños.
- Q7 — ¿Progreso cambia solo al run nuevo, y cómo se selecciona un run? **Resuelta (D38):** no hay selección; sigue siempre el de `run_id` mayor y cambia al aparecer uno nuevo, con `desde=0`.
- Q8 — ¿← en el 1 y → en el último dan la vuelta? **Resuelta (D47):** no hacen nada.
- Q9 — ¿Qué devuelve `…/log` con un `desde` a mitad de línea, y cuánto cuesta un log grande? **Resuelta (D48):** la API salta a `desde` sin leer desde el principio, lee como mucho 1 MiB y devuelve las líneas completas desde el primer límite de línea igual o posterior a `desde`, con el `desde` siguiente.
- Q10 — ¿Se devuelve el `\r` de `\r\n`? **Resuelta (D48):** no; las líneas van sin `\r\n` ni `\n` finales.
- Q11 — ¿Qué responde un run sin `harness.log` con `desde=5`? **Resuelta (D48):** 200 con el tramo vacío, `desde` y `hasta` iguales al pedido, para cualquier `desde` ≥ 0.
- Q12 — ¿`HEAD` y `OPTIONS` cuentan como métodos distintos de `GET`? **Resuelta (D49):** no; CA-38 comprueba que el OpenAPI no tiene operaciones distintas de `get` y que `POST`, `PUT`, `PATCH` y `DELETE` responden 405.
- Q13 — ¿El estado de la API de la barra lateral hace peticiones propias? **Resuelta (D50):** no; se deriva de las rondas de la vista, y en una ruta inválida muestra «sin datos».
- Q14 — ¿`transparent`, `currentColor` y los colores con nombre son colores literales? **Resuelta (D51):** `transparent`, `currentColor` e `inherit` se permiten; los colores con nombre, no.
- Q15 — ¿KB son 1 000 o 1 024 bytes? **Resuelta (D52):** 1 000 en todos los presupuestos.
- Q16 — ¿CA-32 compara el modelo validado o el YAML literal? **Resuelta (D53):** el modelo validado, con los valores por defecto.
- Q17 — ¿El commit de cierre actualiza `docs/validators.md` §3.6, §4.4, §4.7 y §4.9? **Resuelta (D37):** sí; RF-45 las incluye y T-23 las actualiza.
- Q18 — ¿Los errores de consola del navegador por un recurso fallido cuentan para RNF-16? **Resuelta (D54):** se excluyen solo los que provocan a propósito VAL-19, VAL-29 y VAL-32; cualquier otro cuenta.
- Q19 — ¿`TramoDeLog` lleva una línea en `docs/definitions.md`? **Resuelta (D34):** sí, en T-02.
- Q20 — ¿T-18 y T-22 se repiten? **Resuelta (D55):** T-22 cada vez que cambian `tokens.css`, `shared/ui/` o `shared/marca/`; T-18 una vez, al cerrar la spec. Ninguna entra en `docs/validators.md` §6.

### Al implementar
Qué pasa a `docs/validators.md` en el commit que cierra la spec (T-23), además de lo que RF-45 ya exige en cada tarea. Todo lo demás —D1 a D12, Q1 a Q20, VAL-1 a VAL-35 como lista y los verificadores de orden o de un solo uso (VER-9, VER-20, VER-32, VER-33)— se descarta con el plan.

**Métodos (§2 y §3–§4)**
- §2, tabla y párrafo de estado: las filas 1 y 2, activas sobre `frontend/` (`tsc --noEmit`, `eslint`); la fila 5, con Vitest y Playwright como herramientas; la fila 6, con la idea entre comillas simples (fast-check) y `cortar_tramo` como artefactos; la fila 8, «API ↔ frontend» activa con `tipos:comprobar`; la fila 16, con los jobs `frontend` y `frontend-e2e`.
- §3.1: VER-17, tablas exhaustivas sobre tipos generados comprobadas por `tsc`.
- §3.2: VER-7 (los fixtures de lint quedan fuera de `eslint .` y los prueba `lint.test.ts`), VER-12 (globales y propiedades de red), VER-24 (un único sumidero de HTML en `lector.ts`, con un único `eslint-disable-next-line` y sin excepción por fichero; el resto con `textContent`), VAL-26 (colores con nombre prohibidos salvo `transparent`, `currentColor` e `inherit`), y el patrón 1 ampliado con VER-4 (rutas `{slug:path}` solapadas) y VER-8 con VAL-24 (`/@fs/` con control positivo y variantes de ruta).
- §3.5: API con VER-1, VER-2, VER-5 y VER-6 (contexto de `Escaleta`, 404 por `WorkspaceInvalido`, carrera entre `stat` y lectura, solo lectura con escritura inyectada). Frontend con VER-11 (el reloj simulado controla el plazo), VER-13 (lo que jsdom no mide se cierra en e2e), VER-18 y VER-19 (pares con control conocido; lector de tokens igual en las dos implementaciones) y VER-22 (liberación comparada con `scene.traverse`). e2e con VER-23 y VER-28 (controles positivos: draw calls ≥ 1 y un espía que ve favicon y fuentes), VER-25 (el autouse no vacía CA-42), VER-26 y VER-27 (precondiciones e idempotencia del generador), VER-29 (etiquetas `wcag21a` y `wcag21aa`) y VER-31 (CI nunca con `--update-snapshots`). También VAL-23 como test de regresión junto al «Sink caído».
- §3.6: VER-3 (propiedad de `cortar_tramo` con `desde` > 0 y a mitad de línea, multibyte en el tope, líneas vacías y `\r\n`) y VER-16 (sin bash, el test falla en vez de saltarse), junto con VAL-10 como casos fijos, también con `set -H`.
- §3.8: VER-10 (`tipos:comprobar` también con el fichero sin seguimiento) y la parte OpenAPI de VER-6 (los cinco `GET` de la 0001 comparados por subárbol).
- §4.4 (D37): filas nuevas para `server.fs.allow` y `strictPort` con su control positivo y las variantes de ruta de VAL-24, el cliente único de `GET`, el único punto de inserción de HTML y la importación de `logo.png` reservada a `logo.ts`.
- §4.7: VER-14 y VER-15 (el presupuesto falla si falta el chunk de Lectura; la carga inicial incluye `modulepreload`; el logo se busca por su nombre con hash) y VER-30 (la versión de la imagen de Playwright igual a la del lockfile).
- §4.9: la amenaza 2 llevada al navegador, con el capítulo hostil de CA-26 ampliado con los vectores de VAL-17.

**Riesgos aceptados (§5)**
- 5.18 La calidad visual y la usabilidad de la escena solo tienen I y D. *Revisar si el operador deja de usar Lectura en favor de la lista HTML.*
- 5.19 CI renderiza WebGL por software: prueba los draw calls, no los fps. *Revisar si RNF-04 falla en T-18 o en la máquina de desarrollo.*
- 5.20 La API no autentica. *Aceptado mientras corra en `127.0.0.1`; revisar si se expone en red.*
- 5.21 La colisión entre las lecturas de la API y las escrituras atómicas en Windows no se reproduce en CI. *Revisar si `harness.log` registra un `PermissionError` con el panel abierto.*
- 5.22 El juicio estético solo tiene I (T-22). *Revisar si T-22 encuentra desviaciones que ninguna comprobación automática había detectado.*
- 5.23 La orden de Lanzar pegada en el prompt de Claude Code queda fuera del alcance: CA-14 garantiza la semántica de bash, no la del prompt (D44). *Revisar si una idea llega alterada a `novela nueva`.*
- 5.24 Una línea de `harness.log` de más de 1 MiB no llega al panel: el encadenado la salta (D48). *Revisar si el CLI empieza a escribir líneas de ese tamaño.*
- Q12 se resolvió sin riesgo nuevo: `HEAD` y `OPTIONS` no cuentan como métodos distintos de `GET` (D49), y el bash interactivo de Q4 queda cubierto por las comillas simples.

**Qué corre en cada punto (§6)**
- Fila «Pre-commit»: + `npm --prefix frontend run lint` si el índice tiene ficheros de `frontend/` (RF-41).
- Fila «CI del harness»: + job `frontend` (`npm ci`, `tipos:comprobar`, `lint`, `typecheck`, `test`, `build`, `presupuesto` y `npm audit --omit=dev --audit-level=high`) y job `frontend-e2e` (Playwright en Chromium y Firefox contra la API real y los workspaces sintéticos, axe, y marca y regresión visual en Chromium).
- Fila nueva «Commit que añade o cambia referencias visuales»: inspección de que solo muestran workspaces sintéticos (RF-60, CA-60) y aprobación frente a la captura (T-22) — clase I, coste humano.
- T-18 y T-22 no entran en §6, porque son manuales (D55): T-18 se hace una vez y T-22 se repite al cambiar `tokens.css`, `shared/ui/` o `shared/marca/`.

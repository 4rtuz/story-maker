# Decisiones — Spec 0015

## D1 — Dónde se genera la portada
- **Alternativas**: (a) el panel pide la imagen a Pollinations en cada carga; (b) el CLI la
  descarga una vez al workspace y la API la sirve.
- **Decisión**: (b).
- **Justificación**: con (a) el navegador enviaría datos de la novela a un tercero en cada visita,
  la primera carga tardaría lo que tarde la generación y sin red no habría portada. Con (b) la
  imagen es un artefacto más del workspace, escrito por el único que puede escribirlo.

## D2 — Servicio de generación
- **Alternativas**: Pollinations.ai; AI Horde; un modelo local.
- **Decisión**: Pollinations.ai.
- **Justificación**: código abierto, sin clave, una sola petición GET que devuelve la imagen. AI
  Horde exige cola asíncrona y sondeo; un modelo local exige GPU y dependencias nuevas.

## D3 — Qué entra en el prompt de la portada
- **Decisión**: subgénero y descripciones de escenarios del canon; nunca la idea, los personajes ni
  el brief.
- **Justificación**: la idea y los personajes de una novela de regalo pueden llevar datos
  personales, y la petición sale a un servicio externo (política RGPD de la organización).

## D4 — Métricas en disco, no en vivo
- **Alternativas**: (a) la API consulta Langfuse con caché; (b) el CLI guarda el informe y la API
  lo lee.
- **Decisión**: (b).
- **Justificación**: la descarga pagina miles de observaciones y pasa del plazo de 5 s del panel; la
  API seguiría sin tocar la red. La frescura que se pierde es de un capítulo, que es la granularidad
  que interesa.

## D5 — Novelas ocultas en el inicio
- **Decisión**: una lista fija en el frontend (`eval-*`, `humo-*`, `regalo-carmen`).
- **Justificación**: es una preferencia de presentación, no un dato de la novela; siguen accesibles
  por su ruta.

## D6 — Columnas del tablero
- **Decisión**: En proceso (`en_marcha`), En pausa (`detenido`), Bloqueada (`fallido`,
  `interrumpido`), Terminada (`terminado`).
- **Justificación**: la petición proponía tres; una detención pedida por el operador no es un
  bloqueo, y mezclarlas escondería cuál necesita una decisión.

## D7 — Retirada de la estantería 3D
- **Decisión**: se borran la escena, su disposición y la navegación por teclado de la lista, y la
  dependencia `three`.
- **Justificación**: la lectura se abre desde el índice y la ficha; la escena solo era otra forma de
  llegar al mismo capítulo.

## D8 — Descargar el PDF desde Lectura
- **Alternativas**: (a) servir `export/novela.pdf` si existe; (b) construir el PDF en memoria en
  `GET /novelas/{slug}/pdf`, como ya hace `download_novel` del MCP.
- **Decisión**: (b), con el título legible del panel.
- **Justificación**: con (a) el botón no funcionaría en una novela que nadie exportó. (b) no
  contradice el ADR 0003, que descarta sustituir el PDF por una web: el fichero es el mismo, lo
  compone el mismo `pdf.construir`, la API no escribe y sigue en `localhost`. La revisión humana que
  pide el ADR la hace quien lo descarga.

## D9 — Preferencias del lector sin almacenamiento
- **Decisión**: el tema de fondo y el tamaño de letra viven en memoria mientras dura la sesión del
  panel; no se guardan en `localStorage`.
- **Justificación**: RNF-09 de la spec 0004 exige que el panel no deje nada en el almacenamiento del
  navegador, y su e2e lo comprueba.

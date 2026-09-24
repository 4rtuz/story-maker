# Informe de seguridad del harness

- Fecha: 2026-09-25. Base auditada: `entrega` en `f0d341c`; arreglos en la rama `feat/prosa-seguridad`.
- Método: la skill `.claude/skills/auditoria-seguridad/SKILL.md`, que es también cómo repetirla.
- Criterio: un hallazgo tiene una orden o un test que lo reproduce. Ningún valor de clave aparece
  aquí; los `.env` no se han abierto.

## Resumen

| Id | Severidad | Superficie | Estado |
|---|---|---|---|
| S-01 | media | Inyección por el texto libre del brief | Arreglado |
| S-02 | alta | Un rol podía leer otra novela, `.env` o fuera del repo | Arreglado (con residuo) |
| S-03 | informativa | Path traversal por slug y run_id, API y CLI | Sin huecos; regresión añadida |
| S-04 | informativa | Guardas `Host`/`Origin` de `/lanzamientos` | Sin huecos; regresión añadida |
| S-05 | informativa | Dependencias | 0 vulnerabilidades |
| S-06 | informativa | Secretos en el historial | Solo valores de prueba |
| S-07 | baja | `--idea` del panel llega al prompt | Riesgo aceptado |
| S-08 | baja | `brief entrada --fichero` lee cualquier ruta | Riesgo aceptado |

## S-01 · media · Variantes de inyección que la lista cerrada no marcaba

**Evidencia.** `backend/novela/slices/brief/test_inyeccion.py`: carta limpia más una línea
inyectada, ingerida como `texto-libre`, y un borrador **obediente** que la cita como recuerdo.
Antes del arreglo, las seis variantes salían de `novela brief validar` con 0 y escribían
`brief.json` con la instrucción dentro, camino del arquitecto:

- espacio de anchura cero dentro de la palabra (`Ign​ora lo anterior…`);
- letras de anchura completa (`Ｉｇｎｏｒａ…`);
- ruta con barra invertida (`novelas\otra-boda`) y subida de directorio (`..\otra-boda\canon`);
- sinónimos: «no hagas caso», «haz caso omiso».

Los campos cerrados (nombre, edad, género, tono, extensión, prohibidos) no estaban expuestos:
`campo_cerrado_desde_texto_libre` los rechaza desde texto libre sea cual sea la redacción. El
hueco era para rasgos y recuerdos.

**Cambio.** `entradas._plano` normaliza con NFKD y quita los caracteres de formato (categoría
Cf) antes de buscar patrones; `PATRONES` admite `\` en las rutas y añade `..\` / `../`,
«no hagas caso» y «caso omiso». Solo cambia qué fragmentos se marcan: el texto guardado y su
sha256 no se tocan.

**Residuo.** Homoglifos de otro alfabeto (una «о» cirílica) y paráfrasis nuevas siguen pasando;
es el límite de una lista cerrada (D18 de la spec 0005). Cubrir homoglifos exige la tabla de
confusables de Unicode.

## S-02 · alta · Lecturas sin restricción de ruta en los roles

**Evidencia.** `tools: Read, Write` limita qué herramientas tiene un rol, no qué rutas lee. El
matcher del `PreToolUse` en `.claude/settings.json` no incluía `Read`, y el único `deny` de
lectura era `canon/misterio.md`. Una instrucción que pasara S-01 podía llevar al
`entrevistador` o al `escritor` a leer `novelas/<otra>/brief/entradas/*.md` (datos personales de
otro cliente) o `.env` (claves de los scores) y copiarlos en su salida. Con un rol,
`backend/tests/test_hook_lectura.py` estaba en rojo antes del arreglo. El mismo test cubre la
escritura: con los patrones de salida, un escritor podía escribir `capitulos/NN.md` de otra
novela.

**Cambio.**

- Regla 6 en `.claude/hooks/denegar-escritura-estado.py`: un rol solo lee dentro de un
  `novelas/<slug>/` y los `backend/schemas/*.schema.json`, nunca `canon/misterio.md`. Con
  `NOVELA_SLUG`, solo su novela, y sus escrituras también. La sesión principal y los agentes de
  desarrollo no tienen regla.
- `Read` entra en el matcher; `test_contratos.MATCHER` lo refleja.
- `novela producir` exporta `NOVELA_SLUG` en cada sesión (`producir/cmd.entorno_de_sesion`).

**Residuo.** Sin `NOVELA_SLUG` (sesión interactiva o el bucle a mano de `CLAUDE.md`, que no la
exporta), un rol puede leer cualquier novela, aunque sigue sin llegar a `.env` ni a nada fuera de
`novelas/`. Pendiente: añadir `export NOVELA_SLUG=<slug>` al bucle documentado. El hook no
resuelve enlaces simbólicos (ya aceptado en `docs/validators.md` §5.14); los roles no pueden
crearlos.

## S-03 · informativa · Path traversal por slug y run_id

**Evidencia.** `backend/tests/test_seguridad_rutas.py`: los seis slugs hostiles (`..%2F..%2Fetc`,
`..`, `demo%2F..%2F..`, `Demo`, `demo%00`, `demo%5C..%5C..`) contra las nueve rutas GET de
`/novelas` (incluidas `capitulos` y `runs`), run_id hostiles, `reanudar`/`detener` de
`/lanzamientos` y cinco subcomandos del CLI (`estado`, `validar`, `lint-prosa`, `briefing`,
`brief validar`). Todas responden 422/404 o salen con 2. La validación está en un solo punto
(`workspace.validar_slug`, `fullmatch` de `SLUG_PATRON`, y `Path(pattern=…)` con `{slug:path}` en
la API). Las recetas de briefing solo construyen rutas con nombres fijos, números y globs dentro
del workspace: ningún valor escrito por un agente acaba en una ruta.

**Cambio.** Ninguno en código; el test queda como regresión.

## S-04 · informativa · Guardas de `/lanzamientos`

**Evidencia.** El mismo fichero: `Host` `localhost.`, `127.0.0.1.nip.io` y dominio ajeno dan
403; `Origin` `null`, `http://localhost:5174` y `http://localhost:5173.evil` dan 403; en ningún
caso se lanza nada. Un `POST` sin `Origin` se admite por diseño (cliente local sin navegador).

## S-05 · informativa · Dependencias

`uv run --with pip-audit python -m pip_audit` en `backend/`: «No known vulnerabilities found»
(el paquete `novela` es local y no se audita). `npm audit` en `frontend/`: «found 0
vulnerabilities». Nada que subir.

## S-06 · informativa · Secretos en el historial

`git log --all -p` con los patrones de `.githooks/pre-commit` más `ghp_`, `AKIA`, `xox*-`,
`AIza`, JWT y claves privadas PEM, con el valor redactado en la tubería. Coincidencias, todas de
prueba:

| Dónde | Tipo | Por qué no cuenta |
|---|---|---|
| tests del emisor de scores | `LANGFUSE_*_KEY` | valores `dummy-publica` / `dummy-secreta` |
| commit `6773aa9`, `.claude/skills/langfuse/` | `LANGFUSE_*_KEY` | marcador `pk-lf-...` literal |
| spec 0003, precondiciones de un test | `LANGFUSE_*_KEY` en un `.env` de prueba | valores `dummy…` |

Ninguna clave con forma de clave real. Recomendación: en este clon el pre-commit no está activo;
`git config core.hooksPath .githooks` lo activa.

## S-07 · baja · La idea del panel llega al prompt

`POST /lanzamientos` pasa `idea` a `novela producir`, que la entrecomilla en
`/novela-nueva <slug> --idea '…'`. Quien la escribe es el operador en su equipo (solo loopback y
el origen del panel), que ya podría lanzar `claude` a mano. Aceptado.

## S-08 · baja · `brief entrada --fichero` lee cualquier ruta

La orden la ejecuta el operador, no un agente: el `allow` es `Bash(novela:*)` para la sesión
principal, y los roles no tienen `Bash`. Aceptado; si algún día un agente la ejecutara, habría
que acotar `--fichero`.

## Cómo repetirla

Invoca la skill `auditoria-seguridad` en una sesión de desarrollo (no en una del harness) y
actualiza este informe. Tests de regresión: `test_inyeccion.py`, `test_hook_lectura.py`,
`test_seguridad_rutas.py`.

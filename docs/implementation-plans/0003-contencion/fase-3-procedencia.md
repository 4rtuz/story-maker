# Fase 3 — Procedencia y correlación

**Objetivo.** Que el capítulo 1 se atribuya al canon y al plan que de verdad vio, que un prompt
sin commitear quede marcado en el manifiesto, y que cada línea de `harness.log` diga de qué sesión
de Claude Code viene. Y que el entorno se compruebe antes de lanzar nada caro.

**Al terminar existe**: `Manifest` con `fase`, `sucio` y `hashes_claude`; `run.abrir` que separa
el arranque y rechaza un `NOVELA_RUN_ID` de otra fase; `sesion=<uuid>` en el log;
`novela comprobar-entorno`; `api/openapi.json` regenerado.

**Cierra**: RF-11, RF-12, RF-21, RF-27, RF-28. CA-07, CA-08, CA-12, CA-16, CA-17. RNF-06.

Es la única fase de código de backend, y la única con TDD de principio a fin. No requiere las
fases 1 ni 2. Toca `novela/dominio/artefactos.py`, `novela/plataforma/run.py`,
`novela/slices/briefing/cmd.py`, `novela/cli.py` y `api/openapi.json`, y crea
`novela/slices/entorno/`.

---

## Orden y por qué

`fase` primero: es el defecto con evidencia (spec §2, hueco 4) y el único que rompe la
atribución de datos. `sucio`/`hashes_claude` después, en el mismo modelo. La sesión al final:
no toca el modelo, solo el log.

Las tres primeras tareas cambian `Manifest` o `Run`. Regenera el OpenAPI en la 3.1 y otra vez en
la 3.2; la 3.3 no lo necesita. `comprobar-entorno` va al final (3.4) porque reutiliza el `_sucio`
de la 3.2.

---

## 3.1 — Run de arranque

**Rojo**, dos tests:

1. `novela/plataforma/test_run.py::test_run_de_arranque`, sobre `run.abrir` con `ahora` fijo:
   - `abrir(ws, 1, fase="arranque", entorno={}, ahora=LAS_DIEZ)` dos veces → el mismo run, y su
     manifiesto dice `fase: "arranque"`;
   - `abrir(ws, 1, entorno={}, ahora=LAS_DIEZ_Y_CINCO)` → un run **distinto**, con
     `fase: "capitulo"`;
   - `abrir(ws, 1, entorno={}, ahora=LAS_DIEZ)` sin run de capítulo → `RunInvalido`: el minuto
     ya es del arranque. El mensaje dice «de otro capítulo o fase».

   Usa un workspace recién creado con `novela nueva`, sin checkpoint.
2. `novela/slices/briefing/test_briefing.py::test_arranque_no_contamina_el_capitulo_1` (CA-07),
   por CLI:
   1. `novela nueva` sobre un slug nuevo.
   2. `novela briefing <slug> 1 arquitecto` con `NOVELA_RUN_ID=r-20260101-0000`.
   3. Escribe canon y plan con `fabrica.canon` / `fabrica.plan` y `fabrica.escribir`.
   4. `novela briefing <slug> 1 trazador`, con el mismo `NOVELA_RUN_ID`. Los dos briefings están
      en `r-20260101-0000`, cuyo manifiesto dice `fase: "arranque"`.
   5. `novela briefing <slug> 1 escritor` **sin** `NOVELA_RUN_ID`: el run es otro, `fase` es
      `"capitulo"`, y `version_canon` y `version_plan` son la `huella()` del canon y el plan
      presentes, no `e3b0c442…`.

   El paso 5 no puede usar `fabrica.cli`, que siempre fija `NOVELA_RUN_ID`. Gana un parámetro
   opcional `entorno: dict[str, str] | None` que sustituye al suyo, y lo usarás otra vez en 3.3.
   El run del paso 5 sale del reloj y no choca con el del arranque, que está fijado.

**Verde**:

- `Manifest` gana `fase: Literal["arranque", "capitulo"] = "capitulo"`. `Modelo` es
  `extra="forbid"`, así que un manifiesto viejo sin el campo sigue validando por el valor por
  defecto (RNF-06), y uno con un campo desconocido no.
- `run.abrir(ws, capitulo, fase="capitulo", entorno=…, ahora=…)`. El nuevo parámetro va
  **antes** de `entorno` y `ahora` y con valor por defecto: `validar`, `aplicar-delta` y
  `checkpoint` no cambian.
- `_run_id` reutiliza solo manifiestos con el mismo `capitulo` **y** la misma `fase`. El resto de
  la lógica (reutilizar mientras no haya checkpoint del capítulo) no cambia, y sirve igual para el
  arranque: sin checkpoint, el arranque del capítulo 1 se reutiliza en cada reintento del
  `arquitecto`.
- `briefing/cmd.py`: `fase = "arranque" if agente in {Agente.ARQUITECTO, Agente.TRAZADOR} else "capitulo"`,
  pasado a `run.abrir`.

No cambian `run_id`, `RUN_ID_PATRON`, los nombres de briefing ni la API (spec §5.3).

**`NOVELA_RUN_ID` fijado a un run de otra fase o capítulo** (RF-27, CA-16). Tercer test,
`test_briefing.py::test_run_fijado_de_otra_fase`, por CLI:

- el run `r-20260101-0000` tiene un manifiesto con `fase: "arranque"`, que crea el briefing del
  `arquitecto` con esa variable;
- `novela briefing <slug> 1 escritor` con el mismo `NOVELA_RUN_ID` sale con 2, y
  `runs/r-20260101-0000/briefings/01-escritor.md` no existe;
- lo mismo con un run cuyo manifiesto es del capítulo 2.

Verde: en `_run_id`, la rama del valor fijado lee el manifiesto si existe y lanza `RunInvalido` si
`(capitulo, fase)` no coinciden. `RunInvalido` ya sale con 2. Son tres líneas, y cierran F-41: sin
ellas, la variable mezclaría arranque y capítulo por otra vía. `run.abrir` se llama antes de
escribir nada, así que abortar ahí deja el run intacto.

**Contratos**: `REGENERAR=1 uv run pytest tests/test_contratos.py` reescribe `api/openapi.json`
(`GET /runs/{run_id}` devuelve el campo). `Manifest` no tiene JSON Schema en `backend/schemas/`,
y `definitions.md` no lo describe: nada más que regenerar.

**Cierra**: RF-11, RF-27. CA-07, CA-16.

**Commit**: `feat(run): el arranque va a su propio run y el capítulo 1 registra su canon`

---

## 3.2 — Procedencia de `.claude/`

**Rojo**: `novela/plataforma/test_run.py::test_procedencia` (CA-08), sobre un repo git temporario.

- `git init` en `tmp_path`, `.claude/agents/escritor.md` y `.claude/commands/novela-nueva.md`
  con contenido, commit. Usa el `_git` de `tests/test_contratos.py` como modelo: fija
  `user.email` y `user.name` con `-c`, o el commit falla en CI.
- `run.procedencia(tmp_path)` → `(False, {".claude/agents/escritor.md": h1, ".claude/commands/novela-nueva.md": h2})`.
- Modifica `escritor.md` sin commitear → `(True, {…: h1', …})` con `h1' != h1`.
- Vuelve a limpio y modifica `CLAUDE.md` sin commitear → `True`, y la clave `CLAUDE.md` cambia de
  hash (F-05).
- `procedencia` con `git=None` (sin git) → `sucio` es `True`.

Y un segundo test, sin repo temporal: el manifiesto que crea `run.abrir` sobre el repo real
contiene las siete claves `.claude/agents/<rol>.md` (con la fase 1 hecha; si no, sáltalo con
`pytest.mark.skipif(not AGENTES_DIR.exists())` y quita el `skip` cuando exista).

**Verde**, en `run.py`:

```python
RAIZ_REPO = CONFIG_DIR.parent.parent
_VIGILADO = (".claude", "backend/config", "backend/novela", "CLAUDE.md", "AGENTS.md")
_HASHEADO = (".claude/agents/*.md", ".claude/commands/*.md", ".claude/hooks/*",
             ".claude/settings.json", "CLAUDE.md", "AGENTS.md")

def procedencia(raiz: Path = RAIZ_REPO, git: str | None = shutil.which("git")) -> tuple[bool, dict[str, str]]:
    hashes = {
        p.relative_to(raiz).as_posix(): sha256(p)
        for patron in _HASHEADO
        for p in sorted(raiz.glob(patron)) if p.is_file()
    }
    return _sucio(raiz, git), hashes
```

- `_sucio`: `git -C <raiz> status --porcelain -- <_VIGILADO>`, con el mismo patrón que
  `_sha_commit` (`timeout=5`, `check=False`). Salida no vacía → `True`. **Sin git o con error →
  `True`** (spec §5.3). El parámetro `git` es inyectable para el test de «sin git».
- No lleva `@cache`, a diferencia de `_sha_commit`: el test cambia el árbol entre llamadas, y
  solo se llama una vez por run creado.
- `settings.local.json` está en `.gitignore`, así que no ensucia.
- `Manifest` gana `sucio: bool = False` y `hashes_claude: dict[str, Sha256] = {}`. Pydantic copia
  el valor por defecto mutable, así que el `{}` literal es seguro.
- `abrir` rellena los dos campos al crear el manifiesto.

**Contratos**: regenera el OpenAPI otra vez.

**Cierra**: RF-12. CA-08.

**Commit**: `feat(run): el manifiesto registra si el árbol estaba sucio y el hash de cada prompt`

---

## 3.3 — Sesión en el log

**Rojo**: `novela/slices/validacion/test_validacion.py::test_sesion_en_el_log` (CA-12), por CLI
con el `entorno` de `fabrica.cli` de la tarea 3.1:

- con `NOVELA_SESSION_ID=<uuid4>`, la línea de `validar` en `harness.log` lleva
  `sesion=<uuid4>` **y** contiene la subcadena `validar NN -> ` seguida del código. Es la que
  cuenta el procedimiento: si el sufijo la partiera, la cuenta de intentos se rompería sin error
  (F-44);
- con `NOVELA_SESSION_ID=no-es-un-uuid`, la línea no lleva `sesion=` y el código de salida es el
  mismo que sin la variable.

**Verde**:

- `Run` gana `sesion: str | None = None`. Sigue siendo `frozen`.
- `abrir` la rellena con `entorno.get("NOVELA_SESSION_ID")` si casa
  `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$` (sin mayúsculas). Una expresión
  y no `uuid.UUID()`: este acepta llaves y `urn:`, y el valor acaba en una línea de log que el
  procedimiento lee, así que se admite solo la forma canónica. Un valor inválido se ignora: no
  aborta, a diferencia de `NOVELA_RUN_ID`, porque no se convierte en ruta.
- `registro` escribe `f"{marca} sesion={self.sesion} {orden} -> …"` cuando hay sesión (spec §5.3). Las
  subcadenas que cuenta `/novela-continuar` (`validar NN -> 1`) no cambian.

**Docs**, en este commit:

- `architecture.md` §12.2: se cierra. `sesion=` en `harness.log` enlaza cada paso con su traza.
- `architecture.md` §3.1, comentario de `manifest.json`: «sha de commit, recetas, canon, plan,
  fase y hashes de `.claude/`». Quita «sesión de Claude Code»: un capítulo reanudado tiene varias
  sesiones y un solo manifiesto, y por eso la sesión va al log.

**Cierra**: RF-21. CA-12.

**Commit**: `feat(run): sesión de Claude Code en cada línea de harness.log`

---

## 3.4 — `novela comprobar-entorno`

**Construye**: `novela/slices/entorno/{__init__.py,cmd.py,comprobaciones.py,test_entorno.py}` y
su registro en `novela/cli.py`.

Mismo reparto que los otros slices: `comprobaciones.py` es puro (recibe textos y resultados, no
abre nada) y `cmd.py` es la cáscara. No lleva slug, ni lock, ni run: no toca ningún workspace y
no escribe en `harness.log`.

**Rojo**: `novela/slices/entorno/test_entorno.py` (CA-17), sobre la función pura con entradas
fabricadas. Un test por hallazgo:

| Entrada | Hallazgo |
|---|---|
| `settings.json` que no es JSON | `settings.json no es JSON válido` |
| `settings.local.json` con `enabledPlugins` y `permissions` | `settings.local.json: clave no permitida: permissions` |
| el script del hook no existe | `falta .claude/hooks/denegar-escritura-estado.py` |
| `python` no resuelve | `python no resuelve: el hook fallaría abierto` |
| `python` resuelve bajo `…\Microsoft\WindowsApps\` | `python es el alias de la Microsoft Store: el hook fallaría abierto` |
| `limpio` y `sucio` a la vez | `cambios sin commitear en lo que atribuye el manifiesto` |
| todo correcto, sin `settings.local.json` | ninguno |

Y uno por CLI con `CliRunner`: con un hallazgo, sale con 1 e imprime una línea; sin ninguno, sale
con 0 y no imprime nada. La cáscara toma la raíz de la constante `RAIZ_REPO` de la 3.2, que el
test sustituye por un directorio temporal con `monkeypatch`.

**Verde**:

- `comprobaciones.entorno(settings, local, hook_existe, python, sucio, limpio) -> list[str]`,
  donde `settings` y `local` son textos o `None`, y `python` es el resultado de `which`.
- `cmd.comprobar_entorno(limpio: bool = False)`: lee los dos ficheros si existen, mira si existe
  el script, resuelve `shutil.which("python")` y, solo con `--limpio`, llama a `run.procedencia`.
  Así git no se ejecuta si no hace falta. Imprime un hallazgo por línea y sale con 1 si hay alguno.
- `WindowsApps` se compara como segmento de ruta y sin distinguir mayúsculas.

Que `novela` esté en el PATH no se comprueba aquí: lo prueba que la orden arranque (spec §5.3).

**Docs**, en este commit: `AGENTS.md` «CLI» y `architecture.md` §8 ganan una línea,
`novela comprobar-entorno [--limpio]   hook, python y settings.local.json antes de lanzar`.

**Cierra**: RF-28. CA-17.

**Commit**: `feat(entorno): novela comprobar-entorno antes del bucle y del canario`

---

## Al terminar la fase

- `uv run pytest` completo, `mypy --strict`, `ruff`. Mutmut no aplica: no se ha tocado
  `gates.py` ni `apply.py`.
- `test_openapi_al_dia` en verde sin `REGENERAR`.
- Filas CA-07, CA-08, CA-12, CA-16 y CA-17 en la trazabilidad de la spec.
- `validators.md` §4.17: F-04, F-05 y F-40 a F-45 pasan a `activo`, y F-22 en su parte de código.

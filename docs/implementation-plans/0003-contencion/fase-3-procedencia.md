# Fase 3 — Procedencia y correlación

**Objetivo.** Que el capítulo 1 se atribuya al canon y al plan que de verdad vio, que un prompt
sin commitear quede marcado en el manifiesto, y que cada línea de `harness.log` diga de qué sesión
de Claude Code viene.

**Al terminar existe**: `Manifest` con `fase`, `sucio` y `hashes_claude`; `run.abrir` que separa
el arranque; `sesion=<uuid>` en el log; `api/openapi.json` regenerado.

**Cierra**: RF-11, RF-12, RF-21. CA-07, CA-08, CA-12. RNF-06.

Es la única fase de código de backend, y la única con TDD de principio a fin. No requiere las
fases 1 ni 2. Toca cuatro ficheros: `novela/dominio/artefactos.py`, `novela/plataforma/run.py`,
`novela/slices/briefing/cmd.py` y `api/openapi.json`.

---

## Orden y por qué

`fase` primero: es el defecto con evidencia (spec §2, hueco 4) y el único que rompe la
atribución de datos. `sucio`/`hashes_claude` después, en el mismo modelo. La sesión al final:
no toca el modelo, solo el log.

Las tres tareas cambian `Manifest` o `Run`. Regenera el OpenAPI en la 3.1 y otra vez en la 3.2;
la 3.3 no lo necesita.

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

**Techo conocido**, como comentario en `_run_id`:

```python
# ponytail: con NOVELA_RUN_ID fijado no se mira `fase` ni `capitulo`; el bucle no lo fija. Si
# algún día lo hace, rechazar aquí un run cuyo manifiesto sea de otra fase.
```

**Contratos**: `REGENERAR=1 uv run pytest tests/test_contratos.py` reescribe `api/openapi.json`
(`GET /runs/{run_id}` devuelve el campo). `Manifest` no tiene JSON Schema en `backend/schemas/`,
y `definitions.md` no lo describe: nada más que regenerar.

**Cierra**: RF-11. CA-07.

**Commit**: `feat(run): el arranque va a su propio run y el capítulo 1 registra su canon`

---

## 3.2 — Procedencia de `.claude/`

**Rojo**: `novela/plataforma/test_run.py::test_procedencia` (CA-08), sobre un repo git temporario.

- `git init` en `tmp_path`, `.claude/agents/escritor.md` y `.claude/commands/novela-nueva.md`
  con contenido, commit. Usa el `_git` de `tests/test_contratos.py` como modelo: fija
  `user.email` y `user.name` con `-c`, o el commit falla en CI.
- `run.procedencia(tmp_path)` → `(False, {".claude/agents/escritor.md": h1, ".claude/commands/novela-nueva.md": h2})`.
- Modifica `escritor.md` sin commitear → `(True, {…: h1', …})` con `h1' != h1`.

Y un segundo test, sin repo temporal: el manifiesto que crea `run.abrir` sobre el repo real
contiene las siete claves `.claude/agents/<rol>.md` (con la fase 1 hecha; si no, sáltalo con
`pytest.mark.skipif(not AGENTES_DIR.exists())` y quita el `skip` cuando exista).

**Verde**, en `run.py`:

```python
RAIZ_REPO = CONFIG_DIR.parent.parent
_VIGILADO = (".claude", "backend/config", "backend/novela")

def procedencia(raiz: Path = RAIZ_REPO) -> tuple[bool, dict[str, str]]:
    hashes = {
        p.relative_to(raiz).as_posix(): sha256(p)
        for d in ("agents", "commands")
        for p in sorted((raiz / ".claude" / d).glob("*.md"))
    }
    return _sucio(raiz), hashes
```

- `_sucio`: `git -C <raiz> status --porcelain -- .claude backend/config backend/novela`, con el
  mismo patrón que `_sha_commit` (`shutil.which`, `timeout=5`, `check=False`). Salida no vacía →
  `True`. **Sin git o con error → `True`** (D-6).
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
  `sesion=<uuid4>`;
- con `NOVELA_SESSION_ID=no-es-un-uuid`, la línea no lleva `sesion=` y el código de salida es el
  mismo que sin la variable.

**Verde**:

- `Run` gana `sesion: str | None = None`. Sigue siendo `frozen`.
- `abrir` la rellena con `entorno.get("NOVELA_SESSION_ID")` si casa
  `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$` (sin mayúsculas). Una expresión
  y no `uuid.UUID()`: este acepta llaves y `urn:`, y el valor acaba en una línea de log que el
  procedimiento lee, así que se admite solo la forma canónica. Un valor inválido se ignora: no
  aborta, a diferencia de `NOVELA_RUN_ID`, porque no se convierte en ruta.
- `registro` escribe `f"{marca} sesion={self.sesion} {orden} -> …"` cuando hay sesión (D-5). Las
  subcadenas que cuenta `/novela-continuar` (`validar NN -> 1`) no cambian.

**Docs**, en este commit:

- `architecture.md` §12.2: se cierra. `sesion=` en `harness.log` enlaza cada paso con su traza.
- `architecture.md` §3.1, comentario de `manifest.json`: «sha de commit, recetas, canon, plan,
  fase y hashes de `.claude/`». Quita «sesión de Claude Code»: un capítulo reanudado tiene varias
  sesiones y un solo manifiesto, y por eso la sesión va al log.

**Cierra**: RF-21. CA-12.

**Commit**: `feat(run): sesión de Claude Code en cada línea de harness.log`

---

## Al terminar la fase

- `uv run pytest` completo, `mypy --strict`, `ruff`. Mutmut no aplica: no se ha tocado
  `gates.py` ni `apply.py`.
- `test_openapi_al_dia` en verde sin `REGENERAR`.
- Filas CA-07, CA-08 y CA-12 en la trazabilidad de la spec.

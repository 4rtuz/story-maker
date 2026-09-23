# Fase 2 — Las barreras

**Objetivo.** Que los invariantes 1 y 3 no dependan de que un agente obedezca su prompt, y que el
orquestador no pueda hacer el trabajo de un agente ni invocar uno que no sea de los siete.

**Al terminar existe**: `.claude/hooks/denegar-escritura-estado.py`, `.claude/settings.json` y
`backend/tests/test_hook.py`, más los tests de `settings.json` en `test_contratos.py`.

**Cierra**: RF-05 a RF-10, RF-20, RF-25, RF-26. CA-03 a CA-06, CA-11, CA-14, CA-15. RNF-01.

Requiere la fase 1: la tabla de salidas del hook se contrasta con `CONTRATO` de
`test_contratos.py`.

---

## Orden y por qué

Primero el esqueleto del hook que falla cerrado (2.1): es la propiedad de la que dependen todas
las demás, porque un hook que revienta con un código distinto de 2 **deja pasar** la acción.
Después las cinco reglas de la spec §5.2, en orden de gravedad:

| Tarea | Regla | Qué para |
|---|---|---|
| 2.2 | 1 | Escrituras bajo `estado/`, con las variantes de Win32 |
| 2.3 | 2 | Un rol que escribe fuera de sus salidas |
| 2.3b | 3 | La sesión principal escribiendo en el workspace |
| 2.4 | 4 | El misterio y `estado.db` en órdenes `Bash` y `PowerShell` |
| 2.4b | 5 | Un subagente que no es de los siete, en una sesión del harness |

El rendimiento (2.5) se mide con el hook ya completo. `settings.json` va al final (2.6), porque
registra un hook que ya existe y está probado.

---

## Forma del hook

Un solo fichero de la stdlib, sin importar `backend/` (spec §4). Tres piezas:

```python
MOTIVO = "denegar-escritura-estado:"  # prefijo de todo motivo; el canario lo busca en el transcript
ROLES = {"arquitecto", "trazador", "escritor", "continuista", "editor-estilo", "lector-suspense", "cronista"}
SALIDAS = {  # spec 0003 §5.1; test_hook comprueba que casa con CONTRATO de test_contratos
    "arquitecto": [r"canon/(premisa|mundo|estilo|misterio)\.md", r"canon/personajes/[^/]+\.md"],
    "trazador": [r"plan/escaleta\.md", r"plan/capitulos/\d{2,3}\.md"],
    ...
}

def decidir(entrada: dict, entorno: Mapping[str, str]) -> str | None:
    """None si se permite; el motivo si se deniega. Lanza ante lo que no entiende."""

if __name__ == "__main__":
    try:
        motivo = decidir(json.load(sys.stdin), os.environ)
    except Exception as exc:  # falla cerrado (RF-06)
        motivo = f"entrada no interpretable: {exc}"
    if motivo:
        print(f"{MOTIVO} {motivo}", file=sys.stderr)
        sys.exit(2)
```

`decidir` recibe el entorno como parámetro, igual que `run.abrir`. En los tests el entorno se fija
en el subproceso con `env=`.

### Normalización (regla 1, spec §5.2)

Es donde están los fallos. Cuatro pasos, en este orden:

```python
_PREFIJO_WIN32 = re.compile(r"^(\\\\|//)[?.][\\/]")   # \\?\  \\.\

def _normalizar(ruta: str, cwd: str) -> str:
    ruta = _PREFIJO_WIN32.sub("", ruta)
    sin_unidad = re.sub(r"^[a-zA-Z]:", "", ruta)
    if ":" in sin_unidad:
        raise RutaNoNormalizable(f"flujo alternativo: {ruta}")
    segmentos = re.split(r"[\\/]", ruta)
    if any(re.fullmatch(r"\.{3,}", s) for s in segmentos):
        raise RutaNoNormalizable(f"segmento de puntos: {ruta}")
    # Win32 quita puntos y espacios finales de cada segmento al escribir: estado./ es estado/
    segmentos = [s if s in (".", "..") else s.rstrip(". ") for s in segmentos]
    absoluta = os.path.normpath(os.path.join(cwd, "/".join(segmentos)))
    return absoluta.replace("\\", "/").casefold()      # D-3: siempre sin mayúsculas
```

`RutaNoNormalizable` se convierte en denegación, **no** en excepción no controlada: el motivo tiene
que decir por qué.

La localización del workspace va por segmento, no por prefijo. Así sirve con `NOVELAS_DIR`
apuntando fuera del repo, y en los tests:

```python
_WORKSPACE = re.compile(r"(?:^|/)novelas/[^/]+/(?P<rel>.+)$")
```

`rel` es la ruta relativa a `novelas/<slug>/`. Contra ella se comparan las reglas 1, 2 y 3, con
`re.fullmatch`.

**`os.path.normpath` no resuelve enlaces, uniones ni nombres 8.3**, y está bien: `realpath`
tocaría el disco en cada llamada (spec §15). Es el riesgo aceptado de `validators.md` §5.14.
Anótalo como `# ponytail:` en el código, con esa referencia.

---

## 2.1 — Esqueleto que falla cerrado

**Construye**: `.claude/hooks/denegar-escritura-estado.py` (mínimo), `backend/tests/test_hook.py`.

El test ejecuta el script **como subproceso**, igual que Claude Code (spec §13):

```python
HOOK = RAIZ_REPO / ".claude" / "hooks" / "denegar-escritura-estado.py"

def _hook(entrada: dict | str, cwd: Path, entorno: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    datos = entrada if isinstance(entrada, str) else json.dumps(entrada)
    env = {k: v for k, v in os.environ.items() if k != "NOVELA_SESSION_ID"} | (entorno or {})
    return subprocess.run([sys.executable, str(HOOK)], input=datos, capture_output=True,
                          text=True, cwd=cwd, env=env, timeout=10, check=False)
```

El entorno se limpia de `NOVELA_SESSION_ID` por defecto. Si el desarrollador corre la suite desde
una shell del bucle, la regla 5 no puede contaminar los tests de las otras cuatro.

**Rojo**: `test_hook.py::test_falla_cerrado` (CA-04). Tres entradas que deben salir con 2, y con
stderr que empieza por `denegar-escritura-estado:`:

- una cadena que no es JSON;
- `{"tool_name": "Write", "tool_input": {}}`, sin `file_path`;
- `{"tool_name": "Frobnicate", ...}`: una herramienta que el `matcher` de 2.6 no debería dejar
  llegar. Si llega, la configuración ha derivado, y el hook deniega.

Y una que sale con 0 y stdout vacío: un `Write` a `README.md` del repo con
`agent_type: "Explore"`.

**Verde**: el `__main__` de arriba y un `decidir` que solo sabe extraer el campo:

| `tool_name` | Campo |
|---|---|
| `Write`, `Edit`, `MultiEdit` | `tool_input.file_path` |
| `NotebookEdit` | `tool_input.notebook_path` (D-4) |
| `Bash`, `PowerShell` | `tool_input.command` |
| `Agent`, `Task` | `tool_input.subagent_type`, solo si la regla 5 está activa |
| cualquier otro | error → exit 2 |

**Solo esos campos, nunca `tool_input` entero** (spec §5.2, regla 7): en el experimento, una
regla sobre todo el `tool_input` bloqueó un `Agent` cuyo prompt mencionaba la ruta prohibida.

**Cierra**: RF-06. CA-04.

**Commit**: `feat(hook): esqueleto PreToolUse que falla cerrado`

---

## 2.2 — Regla 1: nada bajo `estado/` salvo el delta

**Rojo**: `test_hook.py::test_estado_denegado_salvo_delta` (CA-03). **Property-based**, con
Hypothesis. No es un gate de `validate.py`, pero es un guardarraíl, y los ejemplos no cubren las
variantes de ruta de Windows (spec §13).

**Todas las entradas llevan `agent_type: "Explore"`.** Así la propiedad aísla la regla 1. Sin
`agent_type`, aplicaría también la regla 3 y el delta saldría denegado por ella, que es lo que
prueba CA-14 en 2.3b.

La estrategia genera una ruta bajo `novelas/<slug>/estado/` y le aplica transformaciones:

- `slug`: reutiliza la estrategia de slugs de `tests/estrategias.py` si existe; si no, un
  `from_regex` de tres líneas;
- sufijo bajo `estado/`: `estado.db`, `estado.db-wal`, `state.lock`, `deltas/<n>.json` con `n` de
  1 o 4 dígitos (inválidos), `deltas/NN.json.tmp`, cualquier nombre;
- mayúsculas aleatorias por carácter;
- separador `/` o `\` por segmento;
- inyección de `x/..` en una posición;
- ruta absoluta (bajo `cwd`) o relativa;
- **prefijo `\\?\`** delante de la absoluta;
- **puntos y espacios finales** en cualquier segmento (`estado.`, `estado `, `estado. .`).

Propiedad: sale con 2 para todas, **salvo** `estado/deltas/NN.json` con `NN` de 2 o 3 dígitos,
que sale con 0 **también con las transformaciones** (un delta con `\\?\` delante sigue siendo el
delta).

Y dos casos de ejemplo en el mismo test, que no son propiedad sino frontera:

- `novelas/x/estado/estado.db:secreto` y `novelas/x/capitulos/01.md:x` → 2 (flujo alternativo,
  dentro o fuera de `estado/`);
- `novelas/x/.../estado.db` → 2 (segmento de puntos).

`@settings(max_examples=60, deadline=None)`: cada ejemplo es un proceso (~50-100 ms en Windows).
Son unos segundos por propiedad. Si la suite se vuelve lenta, baja a 30; no cambies a importar el
módulo, porque la spec pide ejecutarlo como lo ejecuta Claude Code.

**Verde**: la normalización de arriba y la regla, sobre `rel`:

```python
if rel.startswith("estado/") and not re.fullmatch(r"estado/deltas/\d{2,3}\.json", rel):
    return f"escritura bajo estado/ denegada: {rel}"
```

**Cierra**: RF-05. CA-03.

**Commit**: `feat(hook): nada escribe bajo estado/ salvo estado/deltas/NN.json`

---

## 2.3 — Regla 2: cada rol, solo en sus salidas

**Rojo**, dos tests:

1. `test_hook.py::test_salidas_por_rol` (CA-05), property-based. Para cada rol:
   - una ruta generada que casa una salida **de su fila** → 0;
   - una ruta generada que casa una salida **de otra fila y no de la suya** → 2. Cuidado con
     `capitulos/NN.md`, que es de `escritor` y de `editor-estilo`: no es «de otra fila» para
     ninguno de los dos;
   - una ruta fuera de `novelas/` (p. ej. `.claude/agents/escritor.md`, `backend/x.py`) → 2.

   Y sin rol: con `agent_type: "Explore"` y sin `agent_type`, una ruta del repo **fuera** de
   `novelas/` → 0.
2. `test_hook.py::test_salidas_casan_el_contrato` (D-2). Carga el hook con
   `importlib.util.spec_from_file_location` (el nombre lleva guiones y no se puede importar) y
   comprueba que las claves de `SALIDAS` son las de `CONTRATO` y que, para cada rol, cada patrón
   de `CONTRATO` (con `NN` → `07` y `*` → `x`) casa algún regex de `SALIDAS`, y viceversa por
   número de entradas. Importa `CONTRATO` de `test_contratos.py`. Comprueba también que
   `ROLES == set(CONTRATO)`: la regla 5 usa esa lista.

**Verde**: la regla, después de la regla 1:

```python
rol = entrada.get("agent_type")
if rol in ROLES:
    if not (ws := _WORKSPACE.search(ruta)) or not any(re.fullmatch(p, ws["rel"]) for p in SALIDAS[rol]):
        return f"{rol} solo escribe en sus salidas: {ruta}"
```

**Techo conocido** (spec §13, riesgos): la regla no sabe qué capítulo está en curso y permite
`capitulos/NN.md` para cualquier `NN`. Lo detecta el sello de 0001 RF-35.

**Cierra**: RF-07. CA-05.

**Commit**: `feat(hook): cada rol escribe solo en sus salidas de §5.1`

---

## 2.3b — Regla 3: la sesión principal no escribe en el workspace

**Rojo**: `test_hook.py::test_sesion_principal` (CA-14), de ejemplo. Sin `agent_type`:

| Ruta | Salida |
|---|---|
| `novelas/x/capitulos/07.md` | 2 |
| `novelas/x/qa/07-continuidad.json` | 2 |
| `novelas/x/estado/deltas/07.json` | 2 (la regla 1 lo permitiría; la 3, no) |
| `novelas/x/runs/r-20260101-0000/intervencion.md` | 0 |
| `novelas/x/runs/r-20260101-0000/manifest.json` | 2 |
| `README.md` | 0 |
| `docs/specs/0003-contencion-y-bucle-en-claude.md` | 0 |

**Verde**, después de la regla 2:

```python
if rol is None and (ws := _WORKSPACE.search(ruta)):
    if not re.fullmatch(r"runs/[^/]+/intervencion\.md", ws["rel"]):
        return f"la sesión principal solo escribe intervencion.md en el workspace: {ruta}"
```

La distinción «sin `agent_type` = sesión principal» es la de E-1. Si una actualización de Claude
Code dejara de mandar `agent_type` en los subagentes, todos pasarían a esta regla: los siete
roles dejarían de poder escribir sus salidas y el bucle no avanzaría. Es un fallo cerrado, no
abierto: lo detectan el freno del bucle y el control positivo del canario.

**Cierra**: RF-25. CA-14.

**Commit**: `feat(hook): la sesión principal solo escribe intervencion.md en el workspace`

---

## 2.4 — Regla 4: órdenes `Bash` y `PowerShell`

**Rojo**: `test_hook.py::test_ordenes` (CA-11), de ejemplo, porque es una regla de texto sin
variantes de ruta que normalizar:

| Herramienta | Orden | Salida |
|---|---|---|
| `Bash` | `cat novelas/x/canon/misterio.md` | 2 |
| `Bash` | `type novelas\x\CANON\Misterio.md` | 2 |
| `Bash` | `sqlite3 novelas/x/estado/estado.db` | 2 |
| `PowerShell` | `Get-Content novelas\x\CANON\Misterio.md` | 2 |
| `PowerShell` | `Remove-Item novelas/x/estado/estado.db` | 2 |
| `Bash` | `novela estado el-misterio-del-faro --breve` | 0 |
| `Bash` | `novela briefing el-misterio-del-faro 3 escritor` | 0 |

La sexta es la que justifica exigir la barra tras `canon`: un slug con «misterio» no dispara.

**Verde**: `re.search(r"canon[\\/].*misterio|estado\.db", orden, re.IGNORECASE)`, para los dos
`tool_name`.

**Riesgo aceptado** (spec §13): `cat canon/mis*` la esquiva. Solo la sesión principal tiene
órdenes, no es adversaria, y en el bucle el `allow` solo autoriza `novela`.

**Cierra**: RF-20. CA-11.

**Commit**: `feat(hook): regla de órdenes Bash y PowerShell para el misterio y estado.db`

---

## 2.4b — Regla 5: solo los siete, en una sesión del harness

**Rojo**: `test_hook.py::test_subagentes` (CA-15), de ejemplo:

| Entorno del subproceso | Entrada | Salida |
|---|---|---|
| `NOVELA_SESSION_ID=<uuid>` | `Agent`, `subagent_type: "general-purpose"` | 2 |
| `NOVELA_SESSION_ID=<uuid>` | `Task`, sin `subagent_type` | 2 |
| `NOVELA_SESSION_ID=<uuid>` | `Agent`, `subagent_type: "escritor"` | 0 |
| `NOVELA_SESSION_ID=<uuid>` | `Agent`, `subagent_type: "canario"` | 0 |
| sin la variable | `Agent`, `subagent_type: "general-purpose"` | 0 |
| sin la variable | `Agent`, sin `subagent_type` | 0 |

La última fija una decisión: sin la variable, el hook **no examina** `Agent` y no puede fallar
cerrado sobre él. Las sesiones de desarrollo no dependen de la forma de su entrada.

**Verde**:

```python
if tool in ("Agent", "Task"):
    if not entorno.get("NOVELA_SESSION_ID"):
        return None
    tipo = entrada["tool_input"].get("subagent_type")
    if tipo not in ROLES | {"canario"}:
        return f"subagente no permitido en una sesión del harness: {tipo!r}"
    return None
```

La regla mira que la variable exista, no que sea un UUID válido: el formato lo valida el CLI
(RF-21), y aquí basta con saber si la sesión es del harness.

**Riesgo abierto** (README, riesgo 4): este test fija el entorno del subproceso y no prueba que
Claude Code lo pase al hook. Eso lo prueba el quinto intento del canario (tarea 5.3).

**Cierra**: RF-26. CA-15 (la parte estática; la de verdad, con CA-09).

**Commit**: `feat(hook): en sesiones del harness, solo los siete roles y el canario`

---

## 2.5 — Rendimiento

**Rojo/verde**: `test_hook.py::test_rendimiento` (RNF-01). Diez invocaciones de una escritura
permitida; la mediana, por debajo de 300 ms. Mide con `time.perf_counter` alrededor de `_hook`.

Si falla, lo primero es el arranque del intérprete, no el hook: `python -X importtime` y quitar
imports. `re`, `json`, `os` y `sys` son todo lo que hace falta.

**Commit**: con 2.4b si pasa a la primera; si hubo que optimizar, `perf(hook): …`.

---

## 2.6 — `.claude/settings.json`

**Rojo**: `test_contratos.py::test_settings_de_claude` (CA-06). Parsea el fichero y falla si:

- no es JSON válido (en `-p`, un settings inválido se ignora **sin avisar**, y el `deny` del
  misterio desaparecería con él);
- tiene claves de primer nivel distintas de `permissions` y `hooks`;
- `permissions.allow` no es exactamente `["Agent", "Bash(novela:*)", "Edit(./novelas/**)"]`;
- falta alguno de los cuatro `deny`;
- la cadena `bypassPermissions` aparece en cualquier parte del fichero;
- el `matcher` de `hooks.PreToolUse`, partido por `|`, no es exactamente el conjunto
  `Write, Edit, MultiEdit, NotebookEdit, Bash, PowerShell, Agent, Task`;
- el script que nombra la orden del hook (lo que sigue a `$CLAUDE_PROJECT_DIR/`) no existe en
  el repo.

**Verde**:

```json
{
  "permissions": {
    "allow": ["Agent", "Bash(novela:*)", "Edit(./novelas/**)"],
    "deny": [
      "Read(./novelas/*/canon/misterio.md)",
      "Edit(./novelas/*/estado/estado.db*)",
      "Edit(./novelas/*/estado/state.lock)",
      "Bash(sqlite3:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell|Agent|Task",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/denegar-escritura-estado.py\""
          }
        ]
      }
    ]
  }
}
```

`python`, no `python3`: en esta máquina `python3` es el alias de la Microsoft Store (E-11). Que
`python` resuelva lo comprueba `novela comprobar-entorno` (tarea 3.4), y es crítico: si no
resuelve, el hook sale con un código distinto de 2 y **falla abierto**.

**Comprobación manual, sin modelo**: `claude --setting-sources project,local` en la raíz,
`/permissions` y `/hooks`. Los cuatro `deny` y el hook aparecen. Si el repo aún no tiene confianza
aceptada, el `allow` aparecerá como ignorado: es lo esperado hasta la fase 6.

**Cierra**: RF-08, RF-09, RF-10. CA-06.

**Commit**: `feat(claude): permisos y registro del hook en settings.json`

---

## 2.7 — Docs de referencia

En el commit de 2.6:

- `CLAUDE.md`, «Hooks»: «`PreToolUse` deniega cualquier escritura bajo `estado/` salvo
  `estado/deltas/NN.json`, a cada rol fuera de sus salidas, a la sesión principal en el
  workspace salvo `intervencion.md`, y en el bucle, cualquier subagente que no sea de los siete».
  Sustituye la línea actual; no añadas otra.
- `architecture.md` §7.1: las cinco reglas, con la excepción del `cronista`. §3.1: `hooks/` y
  `settings.json` en el árbol. §12.7: se cierra, el `deny` existe.
- `validators.md`:
  - §3.8: el tercer contrato, Harness ↔ Claude Code, corre en CI (CA-01, CA-02, CA-06), y
    desaparece el conflicto escrito del hook con el `cronista`;
  - §4.4: el guardarraíl real, hook + `deny`, con las cinco reglas;
  - §2: el hook corre;
  - §4.17: F-10 (su parte estática), F-13, F-14, F-16 a F-21 y F-24 pasan a `activo`.

---

## Al terminar la fase

- Suite completa, `mypy --strict`, `ruff`. El hook también pasa `ruff` y `mypy`: está fuera de
  `backend/`, así que ejecútalos explícitamente sobre él (`uv run ruff check ../.claude/hooks`,
  `uv run mypy --strict ../.claude/hooks/denegar-escritura-estado.py`). No lo metas en la
  configuración de `backend/` solo por esto.
- Filas CA-03 a CA-06, CA-11, CA-14 y CA-15 en la trazabilidad de la spec.

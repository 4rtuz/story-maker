# Fase 2 — Las barreras

**Objetivo.** Que los invariantes 1 y 3 no dependan de que un agente obedezca su prompt.

**Al terminar existe**: `.claude/hooks/denegar-escritura-estado.py`, `.claude/settings.json` y
`backend/tests/test_hook.py`, más los tests de `settings.json` en `test_contratos.py`.

**Cierra**: RF-05 a RF-10, RF-20. CA-03 a CA-06, CA-11. RNF-01.

Requiere la fase 1: la tabla de salidas del hook se contrasta con `CONTRATO` de
`test_contratos.py`.

---

## Orden y por qué

Primero el esqueleto del hook que falla cerrado (2.1): es la propiedad de la que dependen todas
las demás, porque un hook que revienta con un código distinto de 2 **deja pasar** la acción.
Después las tres reglas en orden de gravedad: `estado/` (2.2), salidas por rol (2.3) y `Bash`
(2.4). El rendimiento (2.5) se mide con el hook ya completo. `settings.json` va al final (2.6),
porque registra un hook que ya existe y está probado.

---

## Forma del hook

Un solo fichero de la stdlib, sin importar `backend/` (spec §4). Tres piezas:

```python
SALIDAS = {  # spec 0003 §5.1; test_hook comprueba que casa con CONTRATO de test_contratos
    "arquitecto": [r"canon/(premisa|mundo|estilo|misterio)\.md", r"canon/personajes/[^/]+\.md"],
    "trazador": [r"plan/escaleta\.md", r"plan/capitulos/\d{2,3}\.md"],
    ...
}

def decidir(entrada: dict) -> str | None:
    """None si se permite; el motivo si se deniega. Lanza ante lo que no entiende."""

if __name__ == "__main__":
    try:
        motivo = decidir(json.load(sys.stdin))
    except Exception as exc:  # falla cerrado (RF-06)
        motivo = f"entrada no interpretable: {exc}"
    if motivo:
        print(motivo, file=sys.stderr)
        sys.exit(2)
```

La normalización de rutas, que es donde están los fallos:

```python
def _normalizar(ruta: str, cwd: str) -> str:
    absoluta = os.path.normpath(os.path.join(cwd, ruta))  # colapsa .. y separadores
    return absoluta.replace("\\", "/").casefold()          # D-3: siempre sin mayúsculas
```

Y la localización del workspace, por segmento, no por prefijo. Así sirve con `NOVELAS_DIR`
apuntando fuera del repo, y en los tests:

```python
_WORKSPACE = re.compile(r"(?:^|/)novelas/[^/]+/(?P<rel>.+)$")
```

`rel` es la ruta relativa a `novelas/<slug>/`, que es contra lo que se comparan la regla 1 y las
salidas de la regla 2 (con `re.fullmatch`).

**`os.path.normpath` no resuelve enlaces simbólicos**, y está bien: `realpath` tocaría el disco en
cada llamada y un fichero que aún no existe no se resuelve igual en los dos sistemas. Un enlace
simbólico dentro de `novelas/` que apunte a `estado/` esquivaría la regla 1. No hay nadie que
cree enlaces en el workspace, y los triggers de `estado.db` siguen debajo. Anótalo como
`# ponytail:` en el código.

---

## 2.1 — Esqueleto que falla cerrado

**Construye**: `.claude/hooks/denegar-escritura-estado.py` (mínimo), `backend/tests/test_hook.py`.

El test ejecuta el script **como subproceso**, igual que Claude Code (spec §13):

```python
HOOK = RAIZ_REPO / ".claude" / "hooks" / "denegar-escritura-estado.py"

def _hook(entrada: dict | str, cwd: Path) -> subprocess.CompletedProcess[str]:
    datos = entrada if isinstance(entrada, str) else json.dumps(entrada)
    return subprocess.run([sys.executable, str(HOOK)], input=datos, capture_output=True,
                          text=True, cwd=cwd, timeout=10, check=False)
```

**Rojo**: `test_hook.py::test_falla_cerrado` (CA-04). Tres entradas que deben salir con 2:

- una cadena que no es JSON;
- `{"tool_name": "Write", "tool_input": {}}`, sin `file_path`;
- `{"tool_name": "Frobnicate", ...}`: una herramienta que el `matcher` de 2.6 no debería dejar
  llegar. Si llega, la configuración ha derivado, y el hook deniega.

Y una que sale con 0 y stdout vacío: un `Write` a `README.md` del repo sin `agent_type`.

**Verde**: el `__main__` de arriba y un `decidir` que solo sabe extraer la ruta:

| `tool_name` | Campo |
|---|---|
| `Write`, `Edit`, `MultiEdit` | `tool_input.file_path` |
| `NotebookEdit` | `tool_input.notebook_path` (D-4) |
| `Bash` | `tool_input.command` |
| cualquier otro | error → exit 2 |

**Solo esos campos, nunca `tool_input` entero** (spec §5.2, regla 5): en el experimento, una
regla sobre todo el `tool_input` bloqueó un `Agent` cuyo prompt mencionaba la ruta prohibida.

**Cierra**: RF-06. CA-04.

**Commit**: `feat(hook): esqueleto PreToolUse que falla cerrado`

---

## 2.2 — Regla 1: nada bajo `estado/` salvo el delta

**Rojo**: `test_hook.py::test_estado_denegado_salvo_delta` (CA-03). **Property-based**, con
Hypothesis. No es un gate de `validate.py`, pero es un guardarraíl, y los ejemplos no cubren las
variantes de ruta de Windows (spec §13).

La estrategia genera una ruta bajo `novelas/<slug>/estado/` y le aplica transformaciones:

- `slug`: reutiliza la estrategia de slugs de `tests/estrategias.py` si existe; si no, un
  `from_regex` de tres líneas;
- sufijo bajo `estado/`: `estado.db`, `estado.db-wal`, `state.lock`, `deltas/<n>.json` con `n` de
  1 o 4 dígitos (inválidos), `deltas/NN.json.tmp`, cualquier nombre;
- mayúsculas aleatorias por carácter;
- separador `/` o `\` por segmento;
- inyección de `x/..` en una posición;
- ruta absoluta (bajo `cwd`) o relativa.

Propiedad: sale con 2 para todas, **salvo** `estado/deltas/NN.json` con `NN` de 2 o 3 dígitos,
que sin `agent_type` sale con 0.

`@settings(max_examples=60, deadline=None)`: cada ejemplo es un proceso (~50-100 ms en Windows).
Son unos segundos por propiedad. Si la suite se vuelve lenta, baja a 30; no cambies a importar el
módulo, porque la spec pide ejecutarlo como lo ejecuta Claude Code.

**Verde**: la regla, sobre `rel`:

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

   Y sin rol: con `agent_type: "Explore"` y sin `agent_type`, una ruta del repo → 0.
2. `test_hook.py::test_salidas_casan_el_contrato` (D-2). Carga el hook con
   `importlib.util.spec_from_file_location` (el nombre lleva guiones y no se puede importar) y
   comprueba que las claves de `SALIDAS` son las de `CONTRATO` y que, para cada rol, cada patrón
   de `CONTRATO` (con `NN` → `07` y `*` → `x`) casa algún regex de `SALIDAS`, y viceversa por
   número de entradas. Importa `CONTRATO` de `test_contratos.py`.

**Verde**: la regla, después de la regla 1:

```python
rol = entrada.get("agent_type")
if rol in SALIDAS:
    if not (ws := _WORKSPACE.search(ruta)) or not any(re.fullmatch(p, ws["rel"]) for p in SALIDAS[rol]):
        return f"{rol} solo escribe en sus salidas: {ruta}"
```

Cualquier otro `agent_type` y la sesión principal solo tienen la regla 1: el desarrollo del
harness no se ve afectado.

**Techo conocido** (spec §13, riesgos): la regla no sabe qué capítulo está en curso y permite
`capitulos/NN.md` para cualquier `NN`. Lo detecta el sello de 0001 RF-35.

**Cierra**: RF-07. CA-05.

**Commit**: `feat(hook): cada rol escribe solo en sus salidas de §5.1`

---

## 2.4 — Regla 3: `Bash`

**Rojo**: `test_hook.py::test_bash` (CA-11), de ejemplo, porque es una regla de texto sin
variantes de ruta que normalizar:

| Orden | Salida |
|---|---|
| `cat novelas/x/canon/misterio.md` | 2 |
| `type novelas\x\CANON\Misterio.md` | 2 |
| `sqlite3 novelas/x/estado/estado.db` | 2 |
| `novela estado el-misterio-del-faro --breve` | 0 |
| `novela briefing el-misterio-del-faro 3 escritor` | 0 |

La cuarta es la que justifica exigir la barra tras `canon`: un slug con «misterio» no dispara.

**Verde**: `re.search(r"canon[\\/].*misterio|estado\.db", orden, re.IGNORECASE)`.

**Riesgo aceptado** (spec §13): `cat canon/mis*` la esquiva. Solo la sesión principal tiene
`Bash`, y no es adversaria.

**Cierra**: RF-20. CA-11.

**Commit**: `feat(hook): rama Bash para el misterio y estado.db`

---

## 2.5 — Rendimiento

**Rojo/verde**: `test_hook.py::test_rendimiento` (RNF-01). Diez invocaciones de una escritura
permitida; la mediana, por debajo de 300 ms. Mide con `time.perf_counter` alrededor de `_hook`.

Si falla, lo primero es el arranque del intérprete, no el hook: `python -X importtime` y quitar
imports. `re`, `json`, `os` y `sys` son todo lo que hace falta.

**Commit**: con 2.4 si pasa a la primera; si hubo que optimizar, `perf(hook): …`.

---

## 2.6 — `.claude/settings.json`

**Rojo**: `test_contratos.py::test_settings_de_claude` (CA-06). Parsea el fichero y falla si:

- no es JSON válido (en `-p`, un settings inválido se ignora **sin avisar**, y el `deny` del
  misterio desaparecería con él);
- tiene claves de primer nivel distintas de `permissions` y `hooks`;
- `permissions.allow` no es exactamente `["Agent", "Bash(novela:*)", "Edit(./novelas/**)"]`;
- falta alguno de los cuatro `deny`;
- la cadena `bypassPermissions` aparece en cualquier parte del fichero;
- `hooks.PreToolUse` no tiene un `matcher` que cubra `Write`, `Edit`, `MultiEdit`,
  `NotebookEdit` y `Bash`, o su orden no nombra el script del hook.

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
        "matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash",
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
`python` resuelva lo comprueba la fase 6, y es crítico: si no resuelve, el hook sale con un
código distinto de 2 y **falla abierto**.

**Comprobación manual, sin modelo**: `claude --setting-sources project,local` en la raíz, `/permissions`
y `/hooks`. Los cuatro `deny` y el hook aparecen. Si el repo aún no tiene confianza aceptada, el
`allow` aparecerá como ignorado: es lo esperado hasta la fase 6.

**Cierra**: RF-08, RF-09, RF-10. CA-06.

**Commit**: `feat(claude): permisos y registro del hook en settings.json`

---

## 2.7 — Docs de referencia

En el commit de 2.6:

- `CLAUDE.md`, «Hooks»: «`PreToolUse` deniega cualquier escritura bajo `estado/` salvo
  `estado/deltas/NN.json`, y a cada rol fuera de sus salidas». Sustituye la línea actual; no
  añadas otra.
- `architecture.md` §7.1: la misma regla, con la excepción del `cronista`. §3.1: `hooks/` y
  `settings.json` en el árbol. §12.7: se cierra, el `deny` existe.
- `validators.md` §3.8: el tercer contrato, Harness ↔ Claude Code, corre en CI (CA-01, CA-02,
  CA-06), y el conflicto escrito del hook con el `cronista` desaparece. §4.4: el guardarraíl
  real, hook + `deny`, con las tres ramas. §2: el hook corre.

---

## Al terminar la fase

- Suite completa, `mypy --strict`, `ruff`. El hook también pasa `ruff` y `mypy`: está fuera de
  `backend/`, así que ejecútalos explícitamente sobre él (`uv run ruff check ../.claude/hooks`,
  `uv run mypy --strict ../.claude/hooks/denegar-escritura-estado.py`). No lo metas en la
  configuración de `backend/` solo por esto.
- Filas CA-03 a CA-06 y CA-11 en la trazabilidad de la spec.

# Fase 1 — Los siete agentes y su contrato estático

**Objetivo.** Que `.claude/agents/` exista con los siete roles, y que CI falle si alguno deriva
de la tabla de la spec §5.1.

**Al terminar existe**: siete ficheros `.md` y `test_contratos.py::test_agentes_de_claude`.

**Cierra**: RF-01 a RF-04. CA-01, CA-02.

No requiere nada de otra fase. Antes de empezar, lee las convenciones del [README](README.md):
aquí conviven un test TDD (el contrato) y prosa sin TDD (los cuerpos).

---

## Orden y por qué

El test primero, en rojo contra un directorio que no existe. Después los ficheros, uno a uno,
hasta verde. Así el test ha fallado por cada rol antes de que el rol exista, y no hay un agente
que nunca haya estado en rojo.

---

## 1.1 — Test de contrato de los agentes

**Construye**: dos tests en `backend/tests/test_contratos.py`.

**Rojo**: `test_agentes_de_claude` (CA-01) y `test_agentes_nombran_sus_salidas` (CA-02).
Ejecútalos: fallan porque `.claude/agents/` no existe.

La tabla de la spec §5.1 entra en el test como literal. Es la fuente del contrato y, desde la
fase 2, también la referencia contra la que se compara el hook (D-2):

```python
AGENTES_DIR = RAIZ_REPO / ".claude" / "agents"

# spec 0003 §5.1. El hook (fase 2) lleva su propia copia de las salidas; test_hook compara.
CONTRATO = {
    "arquitecto": (["Read", "Write"], "opus", [
        "canon/premisa.md", "canon/mundo.md", "canon/estilo.md", "canon/misterio.md",
        "canon/personajes/*.md"]),
    "trazador": (["Read", "Write"], "opus", ["plan/escaleta.md", "plan/capitulos/NN.md"]),
    "escritor": (["Read", "Write"], "opus", ["capitulos/NN.md"]),
    "continuista": (["Read", "Write"], "sonnet", ["qa/NN-continuidad.json"]),
    "editor-estilo": (["Read", "Edit", "Write"], "sonnet", ["capitulos/NN.md", "qa/NN-estilo.json"]),
    "lector-suspense": (["Read", "Write"], "sonnet", ["qa/NN-suspense.json"]),
    "cronista": (["Read", "Write"], "haiku", ["estado/deltas/NN.json"]),
}
PROHIBIDAS = {"Glob", "Grep", "Bash", "Task", "Agent", "Skill", "WebFetch", "WebSearch"}
```

El primer test:

- lee `AGENTES_DIR.glob("*.md")` y compara el conjunto de `stem` con las claves de `CONTRATO`;
  falla si falta o sobra alguno;
- parsea el frontmatter con `yaml.safe_load` (ya es dependencia) y comprueba `name == stem`;
- parte `tools` por comas, quita espacios y lo compara **como lista** con la del contrato: el
  orden también es contrato, porque es lo que se lee en una revisión;
- comprueba que la intersección con `PROHIBIDAS` es vacía (redundante con la igualdad, pero nombra
  la herramienta en el mensaje de fallo el día que alguien «solo añade `Glob`»);
- compara `model`.

El segundo recorre las salidas de cada rol y comprueba que la cadena literal aparece en el cuerpo
(lo que va después del frontmatter). Una comprobación de subcadena y nada más: RF-04 es
«debería», y lo que protege es que un rol no se quede sin decir dónde escribe.

Extrae el parseo del frontmatter a un helper de tres líneas dentro del propio test. No lo
reutilices de `novela/dominio/frontmatter.py`: ese valida modelos de la novela, no ficheros del
harness, y acoplarlos haría que un cambio en uno rompa el otro.

**Cierra**: CA-01, CA-02 (en rojo; se cierran en 1.2).

**Commit**: ninguno todavía. El test en rojo se commitea con los agentes en 1.2.

---

## 1.2 — Los siete ficheros

**Construye**: `.claude/agents/{arquitecto,trazador,escritor,continuista,editor-estilo,lector-suspense,cronista}.md`.

**Verde**: los dos tests de 1.1.

### Frontmatter

Exactamente el de la tabla. `description` dice **cuándo** invocarlo, que es lo que lee el
orquestador para elegir. Una frase, dos como mucho:

```yaml
---
name: escritor
description: Escribe capitulos/NN.md a partir de su briefing. Invocar una vez por capítulo después de novela briefing <slug> <cap> escritor, y en cada reintento con las rutas de qa/ que lo motivan.
tools: Read, Write
model: opus
---
```

### Cuerpo

La misma plantilla para los siete, en este orden. Corta: se carga en cada invocación.

1. **Qué haces.** Una frase.
2. **Qué recibes.** El prompt de la invocación trae el slug, `NN`, la ruta del briefing, las
   rutas de salida y, en un reintento, rutas de `qa/`. Lees el briefing entero, y además solo:
   - las rutas de `qa/` que traiga el prompt;
   - el esquema de tu salida (D-1, abajo);
   - los ficheros de salida que ya existan, si el rol los corrige (`editor-estilo`, y cualquiera
     en un reintento).
3. **Qué escribes.** Las rutas de la columna «Salidas» de §5.1, relativas a `novelas/<slug>/`,
   escritas literalmente (`capitulos/NN.md`, no «el capítulo»): el test de 1.1 lo exige.
4. **Reglas** (de `architecture.md` §7.4), las cuatro, sin parafrasear:
   - Lee solo el briefing indicado y las rutas listadas en él.
   - Escribe solo en las rutas listadas como salida.
   - Devuelve a la sesión principal un informe de tres líneas como máximo.
   - Ante ambigüedad, falla explícitamente en lugar de inventar.
5. **Qué devuelves.** La columna «Retorno» de `architecture.md` §7.5, en tres líneas.

Una línea más para los cinco que escriben JSON o frontmatter validado: «Sin prosa alrededor ni
vallas de código» (`AGENTS.md`).

### Hueco: el briefing no trae el esquema de salida (D-1)

`assemble.py` incrusta canon, plan, estado y capítulos, pero no `backend/schemas/`. Y `AGENTS.md`
exige que la salida estructurada sea «JSON válido contra su esquema». Sin el esquema, el agente
adivina la forma, y la adivina mal en el primer capítulo.

Decisión: el cuerpo de cada agente nombra su esquema como entrada fija. La sesión corre en la
raíz del repo, así que la ruta es relativa a ella:

| Agente | Esquema |
|---|---|
| `arquitecto` | `backend/schemas/canon.schema.json` |
| `trazador` | `backend/schemas/escaleta.schema.json`, `backend/schemas/plan-capitulo.schema.json` |
| `escritor` | `backend/schemas/capitulo.schema.json` (frontmatter) |
| `continuista`, `editor-estilo`, `lector-suspense` | `backend/schemas/qa-informe.schema.json` |
| `cronista` | `backend/schemas/delta.schema.json` |

Cuesta una línea por agente y ningún cambio de backend. Si la novela de humo muestra que la
lectura del esquema gasta demasiado contexto, la alternativa es que la receta lo incruste: eso
sí es código y va por spec.

### Lo específico de cada rol

Lo que el cuerpo tiene que decir además de la plantilla. Viene de la spec §5.4 y de
`architecture.md` §7.5; no inventes nada más.

- **`arquitecto`.** Escribe los cinco tipos de fichero del canon. Hay una asimetría: el `deny`
  de la fase 2 le impide **leer** `canon/misterio.md`, aunque pueda escribirlo. Por eso, en un
  reintento (cuando el briefing del `trazador` rechaza el canon), reescribe los ficheros enteros
  con `Write` a partir del error que trae el prompt, sin intentar leer el misterio. Dilo en el
  cuerpo, o el primer reintento gastará un turno contra el `deny`.
- **`trazador`.** `plan/escaleta.md` y una ficha `plan/capitulos/NN.md` por capítulo, de 1 a
  `num_capitulos`, con el ancho de `NN` del workspace (dos dígitos, tres si pasa de 99).
- **`escritor`.** Un reintento no es una corrección: reescribe `capitulos/NN.md` entero, con el
  briefing de siempre y los hallazgos de las rutas de `qa/` del prompt. No tiene `Edit`, a
  propósito.
- **`continuista`** y **`lector-suspense`.** El campo `veredicto` es el que lee el gate del paso 6
  de `/novela-continuar`. Nómbralo.
- **`editor-estilo`.** El único con `Edit`. Corrige `capitulos/NN.md` en el sitio y escribe
  `qa/NN-estilo.json`. En un reintento (P-07) recibe el mismo briefing y `qa/NN-validacion.json`,
  y corrige solo los hallazgos mecánicos sobre el capítulo que hay en disco.
- **`cronista`.** Solo `estado/deltas/NN.json`. Nunca `estado.db`: lo aplica
  `novela aplicar-delta`. Si el delta se rechaza, el reintento trae la causa en el prompt.

**Comprobación manual antes de commitear**: los siete cuerpos juntos no pasan de ~150 líneas. Si
uno supera las 30, está explicando estilo, y el estilo no es de esta spec (§1, «fuera del
alcance»).

**Cierra**: RF-01 a RF-04. CA-01, CA-02.

**Commit**: `feat(agentes): los siete roles de .claude/agents con su contrato en CI`

---

## 1.3 — Docs de referencia

En el mismo commit que 1.2 si es pequeño; si no, en uno inmediatamente después, antes de la
fase 2.

- `architecture.md` §3.1: el árbol gana `.claude/agents/` con los siete ficheros.
- `architecture.md` §6.3 y §7.4: léelos y quita lo que hable del contrato como algo pendiente.
  Si ya están en presente, no se tocan.
- `architecture.md` §7.5: la columna «Entradas» gana el esquema de salida de cada rol (D-1).
- `validators.md` §2: el método 13 (`tools`) pasa a correr.

**Commit** (si va aparte): `docs(arquitectura): contrato de agente implementado`

---

## Al terminar la fase

- `uv run pytest` completo, `mypy --strict` y `ruff`, en verde.
- La trazabilidad de la spec §12 gana las filas de CA-01 y CA-02 con su test y estado `hecho`.
  Se rellena en la spec según se cierra cada CA, no al final.

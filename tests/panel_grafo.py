"""El grafo del panel contra el nucleo: que no haya un nodo huerfano.

El grafo de `panel/static/flowgraph.js` dibuja estados de `harness/state.py` y
subagentes de `.claude/agents/`. Si alguno de los dos lados se renombra, el nodo
deja de encenderse sin dar ningun error: la pagina se ve bien y miente. Esto es
lo unico que hay que comprobar, y se comprueba leyendo los identificadores de
los tres sitios.

Uso:  python tests/panel_grafo.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.state import STATES  # noqa: E402

ESTATICO = ROOT / "panel" / "static"
GRAFO = (ESTATICO / "flowgraph.js").read_text(encoding="utf-8")
APP = (ESTATICO / "app.js").read_text(encoding="utf-8")
HTML = (ESTATICO / "index.html").read_text(encoding="utf-8")

FALLOS: list[str] = []


def check(nombre: str, condicion: bool, detalle: str = "") -> None:
    FALLOS.append(nombre) if not condicion else None
    print(f"  [{'ok  ' if condicion else 'FALLO'}] {nombre}"
          + (f" — {detalle}" if detalle and not condicion else ""))


def bloque(fuente: str, nombre: str) -> str:
    ini = fuente.index(f"const {nombre} = [")
    return fuente[ini:fuente.index("\n];", ini)]


NODOS = re.findall(r"\['([\w-]+)',\s*'", bloque(GRAFO, "NODOS"))
ARISTAS = re.findall(r"\['([\w-]+)',\s*'([\w-]+)',", bloque(GRAFO, "ARISTAS"))
ALIAS = dict(re.findall(r"(\w+):\s*'(\w+)',", GRAFO[GRAFO.index("export const ALIAS"):
                                                    GRAFO.index("const R =")]))
AGENTES = sorted(p.stem for p in (ROOT / ".claude" / "agents").glob("*.md"))

print("— Grafo del panel —")

# 1. Todo estado del nucleo se ve: como nodo propio o redirigido por ALIAS.
sin_nodo = [e for e in STATES if e not in NODOS and e not in ALIAS]
check("Todo estado de §10 tiene nodo o alias en el grafo", not sin_nodo, str(sin_nodo))

# 2. Y al reves: ningun nodo de estado inventado.
ids = set(STATES) | set(AGENTES)
fantasma = [n for n in NODOS if n not in ids]
check("Ningun nodo del grafo es un identificador que el nucleo no emite",
      not fantasma, str(fantasma))

# 3. Los cinco subagentes estan, con el nombre exacto de `.claude/agents/`.
faltan = [a for a in AGENTES if a not in NODOS]
check(f"Los {len(AGENTES)} subagentes tienen nodo", not faltan, str(faltan))

# 4. Los alias apuntan a nodos que existen.
rotos = {k: v for k, v in ALIAS.items() if v not in NODOS}
check("Todos los alias apuntan a un nodo existente", not rotos, str(rotos))

# 5. Las aristas unen nodos declarados: una arista suelta revienta el montaje.
sueltas = [(a, b) for a, b in ARISTAS if a not in NODOS or b not in NODOS]
check("Todas las aristas unen nodos declarados", not sueltas, str(sueltas))

# 6. Un nodo sin arista no se enciende nunca con una animacion de delegacion.
tocados = {n for par in ARISTAS for n in par}
aislados = [n for n in NODOS if n not in tocados]
check("Ningun nodo queda aislado", not aislados, str(aislados))

# 7. El agente que `app.js` deduce del subpaso tiene que ser un nodo.
paso = re.search(r"const PASO_AGENTE = \{([^}]*)\}", APP).group(1)
deducidos = re.findall(r":\s*'([\w-]+)'", paso)
check("PASO_AGENTE solo nombra subagentes con nodo",
      all(a in NODOS for a in deducidos), str(deducidos))

# 8. BANDA (el «por donde ya se ha pasado») tambien son nodos.
banda = re.findall(r"'(\w+)'", bloque(APP, "BANDA"))
check("BANDA solo nombra nodos del grafo",
      all(e in NODOS for e in banda), str([e for e in banda if e not in NODOS]))

# 9. Los ids del DOM que `app.js` toca existen en la pagina. Un `$()` a la nada
#    devuelve null y revienta el pintado entero de la vista.
en_html = set(re.findall(r'id="([\w-]+)"', HTML))
# Los que crea `app.js` al pintar el interior de una burbuja no estan en el HTML.
GENERADOS = {"in-mensaje", "btn-responder", "puerta-arg"}
usados = set(re.findall(r"\$\('#([\w-]+)'\)", APP)) - GENERADOS
huerfanos = sorted(usados - en_html)
check("Todo `$('#id')` de app.js existe en index.html", not huerfanos, str(huerfanos))

print(f"\n{9 - len(FALLOS)} comprobaciones correctas, {len(FALLOS)} fallidas.")
sys.exit(1 if FALLOS else 0)

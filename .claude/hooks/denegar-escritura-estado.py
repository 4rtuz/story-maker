"""PreToolUse del harness (spec 0003 §5.2).

Deniega con exit 2 y el motivo en stderr; permite con exit 0 y sin salida. Falla cerrado: lo que
no entiende también sale con 2, porque cualquier otro código Claude Code lo trata como no
bloqueante y la acción seguiría adelante. Solo stdlib: corre en cada llamada de herramienta,
fuera del venv de backend/, y no puede importarlo. Cada denegación queda en un log JSONL
append-only (docs/guardrails.md).
"""

import json
import os
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

MOTIVO = "denegar-escritura-estado:"  # prefijo de todo motivo; el canario lo busca en el transcript
_NN = r"\d{2,3}"
_DELTA = rf"estado/deltas/{_NN}\.json"
_INTERVENCION = r"runs/[^/]+/intervencion\.md"
# spec 0003 §5.1 y 0005 §8.4, relativas a novelas/<slug>/. test_hook comprueba que casa con CONTRATO de
# test_contratos (D-2): el hook no puede importar backend/, así que es una copia vigilada.
SALIDAS = {
    # El misterio, al borrador: el deny de Read también deniega escribirlo, y lo promueve el CLI.
    "arquitecto": [
        r"canon/(premisa|mundo|estilo)\.md",
        r"canon/misterio\.borrador\.md",
        r"canon/personajes/[^/]+\.md",
    ],
    "trazador": [r"plan/escaleta\.md", rf"plan/capitulos/{_NN}\.md"],
    "escritor": [rf"capitulos/{_NN}\.md"],
    "continuista": [rf"qa/{_NN}-continuidad\.json"],
    "editor-estilo": [rf"capitulos/{_NN}\.md", rf"qa/{_NN}-estilo\.json"],
    "lector-suspense": [rf"qa/{_NN}-suspense\.json"],
    "cronista": [_DELTA],
    "entrevistador": [r"brief/borrador\.json"],
    "juez": [r"qa/juicio\.json"],
}
ROLES = frozenset(SALIDAS)
_PREFIJO_WIN32 = re.compile(r"^(\\\\|//)[?.][\\/]")  # \\?\  \\.\
_ORDEN_PROHIBIDA = re.compile(r"canon[\\/].*misterio|estado\.db", re.IGNORECASE)


class RutaNoNormalizable(ValueError):
    """Lo que Win32 resolvería de una forma que el hook no puede reproducir sin tocar el disco."""


def _normalizar(ruta: str, cwd: str) -> str:
    """Absoluta, con `/`, sin `..` y sin mayúsculas (D-3), deshaciendo lo que Win32 normaliza al
    escribir. ponytail: no resuelve enlaces, uniones ni nombres 8.3; eso exigiría tocar el disco
    en cada llamada (validators.md §5.14), y debajo quedan los triggers de estado.db."""
    ruta = _PREFIJO_WIN32.sub("", ruta)
    if re.match(r"[a-zA-Z]:(?![\\/])", ruta):
        raise RutaNoNormalizable(f"ruta relativa a una unidad: {ruta}")
    if ":" in re.sub(r"^[a-zA-Z]:", "", ruta):
        raise RutaNoNormalizable(f"flujo alternativo de NTFS: {ruta}")
    segmentos = re.split(r"[\\/]", ruta)
    limpios = [s if s in ("", ".", "..") else s.rstrip(". ") for s in segmentos]
    # Win32 quita puntos y espacios finales: `estado./` es `estado/`, pero `.. ` es `..` y `...`
    # no se sabe qué es. Un segmento que se queda sin nada no se interpreta.
    if "" in (limpio for s, limpio in zip(segmentos, limpios, strict=True) if s):
        raise RutaNoNormalizable(f"segmento de puntos o espacios: {ruta}")
    absoluta = os.path.normpath(os.path.join(cwd, "/".join(limpios)))
    return absoluta.replace("\\", "/").casefold()


def _relativas(ruta: str) -> list[str]:
    """La ruta relativa a cada `novelas/<slug>/` que contenga. Por segmento y no por prefijo, para
    que valga con NOVELAS_DIR fuera del repo. Todas, no la primera: un antecesor que se llame
    novelas/ no puede esconder el estado. ponytail: ese mismo antecesor hace que la sesión
    principal vea el repo entero como workspace; se mueve el repo si llega a pasar."""
    s = ruta.split("/")
    return ["/".join(s[i + 2 :]) for i in range(len(s) - 2) if s[i] == "novelas" and s[i + 1]]


_ESQUEMA = re.compile(r".*/backend/schemas/[^/]+\.schema\.json")
# Lo que un rol lee del repo fuera de su workspace, además de los esquemas.
_DEL_REPO = {"juez": re.compile(r".*/backend/config/rubrica\.yaml")}


def _ajena(ruta: str, entorno: Mapping[str, str]) -> bool:
    """Toca un `novelas/<slug>/` que no es el de `NOVELA_SLUG`. Sin la variable, ninguna lo es."""
    s = ruta.split("/")
    slugs = {s[i + 1] for i in range(len(s) - 2) if s[i] == "novelas" and s[i + 1]}
    propio = (entorno.get("NOVELA_SLUG") or "").casefold()
    return bool(propio) and bool(slugs - {propio})


def _lectura(ruta: str, rol: object, entorno: Mapping[str, str]) -> str | None:
    """Regla 6 (security-report.md S-02): un rol solo lee dentro de `novelas/<slug>/` y los
    esquemas de `backend/schemas/`, y nunca `canon/misterio.md`. Con `NOVELA_SLUG` (lo exporta
    `novela producir`), solo su novela: una instrucción inyectada en el brief no alcanza los
    datos de otra ni `.env`. La sesión principal y los agentes de desarrollo no tienen regla."""
    if rol not in ROLES or _ESQUEMA.fullmatch(ruta):
        return None
    if (propia := _DEL_REPO.get(str(rol))) and propia.fullmatch(ruta):
        return None
    relativas = _relativas(ruta)
    if not relativas or _ajena(ruta, entorno):
        return f"{rol} solo lee su workspace y sus esquemas: {ruta}"
    if "canon/misterio.md" in relativas:
        return f"{rol} no lee canon/misterio.md: {ruta}"
    return None


# Solo estos campos, nunca tool_input entero (regla 7): una regla sobre todo el tool_input
# bloqueó en el experimento un Agent cuyo prompt mencionaba la ruta prohibida.
_CAMPO = {
    "Write": "file_path",
    "Edit": "file_path",
    "MultiEdit": "file_path",
    "NotebookEdit": "notebook_path",  # D-4
    "Read": "file_path",  # regla 6
    "Bash": "command",
    "PowerShell": "command",
}


def decidir(entrada: dict[str, Any], entorno: Mapping[str, str]) -> str | None:
    """None si se permite; el motivo si se deniega. Lanza ante lo que no entiende."""
    tool = entrada["tool_name"]
    if tool in ("Agent", "Task"):
        # Regla 5. La variable solo la exportan el bucle y las sesiones del harness; basta con
        # que exista, su formato lo valida el CLI. Sin ella, las de desarrollo conservan Explore.
        if not entorno.get("NOVELA_SESSION_ID"):
            return None
        tipo = entrada["tool_input"].get("subagent_type")
        if tipo not in ROLES | {"canario"}:
            return f"subagente no permitido en una sesión del harness: {tipo!r}"
        return None
    valor = entrada["tool_input"][_CAMPO[tool]]
    if not isinstance(valor, str) or not valor:
        raise ValueError(f"{_CAMPO[tool]} vacío o no es texto")
    if _CAMPO[tool] == "command":
        # Regla 4. ponytail: texto sobre la orden, así que `cat canon/mis*` la esquiva; solo la
        # sesión principal tiene órdenes, no es adversaria, y en el bucle el allow es `novela`.
        if _ORDEN_PROHIBIDA.search(valor):
            return f"orden sobre el misterio o estado.db: {valor}"
        return None
    try:
        normalizada = _normalizar(valor, entrada.get("cwd") or os.getcwd())
    except RutaNoNormalizable as exc:
        return str(exc)
    if tool == "Read":
        return _lectura(normalizada, entrada.get("agent_type"), entorno)
    relativas = _relativas(normalizada)
    # Regla 1, para todos.
    if any(r.split("/")[0] == "estado" and not re.fullmatch(_DELTA, r) for r in relativas):
        return f"escritura bajo estado/ denegada: {valor}"
    # Regla 2: un rol, solo en sus salidas. Los agentes de desarrollo no son roles.
    # ponytail: no sabe qué capítulo está en curso; reescribir uno cerrado lo para el sello.
    rol = entrada.get("agent_type")
    if rol in ROLES and _ajena(normalizada, entorno):
        return f"{rol} solo escribe en su novela ({entorno['NOVELA_SLUG']}): {valor}"
    if rol in ROLES and not any(re.fullmatch(p, r) for p in SALIDAS[rol] for r in relativas):
        return f"{rol} solo escribe en sus salidas: {valor}"
    # Regla 3: sin agent_type es la sesión principal (E-1). Si Claude Code dejara de mandarlo en
    # los subagentes, esto los pararía a todos: falla cerrado, y lo ven el freno y el canario.
    if rol is None and relativas and not any(re.fullmatch(_INTERVENCION, r) for r in relativas):
        return f"la sesión principal solo escribe intervencion.md en el workspace: {valor}"
    return None


def _destino(entrada: Any, entorno: Mapping[str, str]) -> str:
    """El log del workspace si la ruta cae en un `novelas/<slug>/` que ya existe; si no (una
    orden, una entrada rota, un workspace inventado), el del proyecto. Nunca crea un workspace."""
    try:
        valor = entrada["tool_input"][_CAMPO[entrada["tool_name"]]]
        s = _normalizar(valor, entrada.get("cwd") or os.getcwd()).split("/")
        i = max(i for i in range(len(s) - 2) if s[i] == "novelas" and s[i + 1])
        if os.path.isdir("/".join(s[: i + 2])):
            return "/".join([*s[: i + 2], "auditoria", "policy.jsonl"])
    except Exception:  # noqa: S110 — sin workspace deducible, el del proyecto
        pass
    hooks = os.path.dirname(os.path.abspath(__file__))
    raiz = entorno.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(hooks))
    return os.path.join(raiz, ".claude", "logs", "policy.jsonl")


def _auditar(entrada: Any, motivo: str, entorno: Mapping[str, str]) -> None:
    """Una línea JSON por denegación, append-only (docs/guardrails.md). Nunca falla: un log que
    no se puede escribir no cambia la decisión."""
    try:
        es_dict = isinstance(entrada, dict)
        linea = {
            "momento": datetime.now(UTC).isoformat(timespec="seconds"),
            "decision": "denegar",
            "herramienta": entrada.get("tool_name") if es_dict else None,
            "agente": entrada.get("agent_type") if es_dict else None,
            "sesion": entorno.get("NOVELA_SESSION_ID"),
            "motivo": motivo,
        }
        ruta = _destino(entrada, entorno)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as log:
            log.write(json.dumps(linea, ensure_ascii=False) + "\n")
    except Exception:  # noqa: S110
        pass


def main() -> int:
    entrada: Any = None
    try:
        # Bytes y no sys.stdin: en Windows la página de códigos rompería una ruta con tildes.
        entrada = json.loads(sys.stdin.buffer.read())
        motivo = decidir(entrada, os.environ)
    except Exception as exc:  # falla cerrado (RF-06)
        motivo = f"entrada no interpretable: {exc!r}"
    if motivo is None:
        return 0
    _auditar(entrada, motivo, os.environ)
    sys.stderr.buffer.write(f"{MOTIVO} {motivo}\n".encode())
    return 2


if __name__ == "__main__":
    sys.exit(main())

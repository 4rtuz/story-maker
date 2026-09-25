"""Contratos transversales: esquemas, claves, clientes de modelo, OpenAPI."""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import jsonschema
import yaml
from typer.testing import CliRunner

from api.main import app as api
from novela.cli import app
from novela.dominio import esquemas
from novela.dominio.validadores import VALIDADORES
from novela.plataforma.workspace import WorkspaceRepository

RAIZ_REPO = Path(__file__).resolve().parents[2]
SCHEMAS = RAIZ_REPO / "backend" / "schemas"
# REGENERAR=1 uv run pytest tests/test_contratos.py reescribe los contratos commiteados; el diff del
# commit es la revisión del cambio.
REGENERAR = os.environ.get("REGENERAR") == "1"
GIT = shutil.which("git") or "git"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [GIT, "-C", str(repo), *args], capture_output=True, text=True, check=False
    )


def test_sin_claves_versionadas(tmp_path: Path) -> None:
    """CA-32: un fichero versionado con una clave hace fallar el pre-commit."""
    repo = tmp_path / "repo"
    (repo / ".githooks").mkdir(parents=True)
    shutil.copy(RAIZ_REPO / ".githooks" / "pre-commit", repo / ".githooks" / "pre-commit")
    _git(repo, "init", "-q")
    _git(repo, "config", "core.hooksPath", ".githooks")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")

    # Control: sin clave, el commit pasa. Si no pasara, el fallo de abajo no probaría nada.
    (repo / "limpio.md").write_text("Las claves van en `LANGFUSE_SECRET_KEY`, fuera de git.\n")
    _git(repo, "add", "-A")
    assert _git(repo, "commit", "-qm", "limpio").returncode == 0

    # Construida por partes para que este fichero no dispare el hook que lo prueba.
    clave = "LANGFUSE_SECRET_KEY" + "=" + "sk-lf-" + "dummy0000000000"
    (repo / "settings.env").write_text(clave + "\n")
    _git(repo, "add", "-A")
    resultado = _git(repo, "commit", "-qm", "con clave")
    assert resultado.returncode != 0
    assert "clave" in resultado.stderr


def test_pre_commit_frontend(tmp_path: Path) -> None:
    """CA-41 (RF-41): con ficheros de frontend/ en el índice, el pre-commit pasa eslint y aborta si
    falla; sin ellos, no invoca npm. El npm falso deja registro: sin comprobarlo, el test pasaría
    también con el npm real, que en el repositorio temporal falla igual (VER-9)."""
    repo = tmp_path / "repo"
    (repo / ".githooks").mkdir(parents=True)
    shutil.copy(RAIZ_REPO / ".githooks" / "pre-commit", repo / ".githooks" / "pre-commit")
    _git(repo, "init", "-q")
    _git(repo, "config", "core.hooksPath", ".githooks")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")
    falsos, registro = tmp_path / "bin", tmp_path / "npm.log"
    falsos.mkdir()
    npm = falsos / "npm"
    npm.write_text(f'#!/bin/sh\necho "$@" >> "{registro.as_posix()}"\nexit 1\n', newline="\n")
    npm.chmod(0o755)
    entorno = {**os.environ, "PATH": str(falsos) + os.pathsep + os.environ["PATH"]}

    def commit(mensaje: str) -> subprocess.CompletedProcess[str]:
        _git(repo, "add", "-A")
        return subprocess.run(  # noqa: S603
            [GIT, "-C", str(repo), "commit", "-qm", mensaje],
            capture_output=True,
            text=True,
            check=False,
            env=entorno,
        )

    (repo / "otro.md").write_text("sin frontend\n")
    assert commit("sin frontend").returncode == 0
    assert not registro.exists()

    (repo / "frontend").mkdir()
    (repo / "frontend" / "x.ts").write_text("export {};\n")
    assert commit("con frontend").returncode != 0
    assert registro.read_text().split() == ["--prefix", "frontend", "run", "lint"]


def test_state_schema_al_dia() -> None:
    """CA-06 y RF-26: el JSON Schema commiteado es el que genera Pydantic ahora mismo. Si cambias
    un modelo y no regeneras, esto se pone rojo."""
    generados = esquemas.generar()
    if REGENERAR:
        SCHEMAS.mkdir(exist_ok=True)
        for nombre, esquema in generados.items():
            texto = json.dumps(esquema, indent=2, ensure_ascii=False) + "\n"
            (SCHEMAS / nombre).write_bytes(texto.encode("utf-8"))
    commiteados = {p.name for p in SCHEMAS.glob("*.json")}
    assert commiteados == set(generados), "schemas/ tiene ficheros de más o de menos"
    for nombre, esquema in generados.items():
        assert json.loads((SCHEMAS / nombre).read_text(encoding="utf-8")) == esquema, nombre
        assert "schema_version" in esquema["properties"], nombre


def test_delta_schema_al_dia() -> None:
    """RF-02: el esquema que lee el cronista trae `hechos_usados`, opcional y con cita."""
    esquema = json.loads((SCHEMAS / "delta.schema.json").read_text(encoding="utf-8"))
    assert "hechos_usados" in esquema["properties"]
    assert "hechos_usados" not in esquema.get("required", [])
    assert set(esquema["$defs"]["UsoCitado"]["required"]) == {"hecho", "cita"}


def test_delta_trae_cronologia_opcional() -> None:
    """docs/formal/lean.md: la cronología del cronista es opcional (los deltas de antes siguen
    valiendo) y cada evento trae momento, lugar y personajes."""
    esquema = json.loads((SCHEMAS / "delta.schema.json").read_text(encoding="utf-8"))
    assert "cronologia" in esquema["properties"]
    assert "cronologia" not in esquema.get("required", [])
    assert set(esquema["$defs"]["EventoCronologia"]["required"]) == {"id", "momento", "lugar"}


def test_estado_json_valida_contra_el_esquema(
    novelas: Callable[[str], WorkspaceRepository],
) -> None:
    """CA-06, la otra mitad: lo que emite `novela estado --json` valida contra el commiteado."""
    novelas("demo-24")
    resultado = CliRunner().invoke(app, ["estado", "demo-24", "--json"])
    assert resultado.exit_code == 0, resultado.output
    esquema = json.loads((SCHEMAS / "state.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads(resultado.stdout), esquema)


BRIEF = RAIZ_REPO / "backend" / "tests" / "fixtures" / "brief"


def test_brief_valida_contra_el_esquema() -> None:
    """CA-28 (RF-28): las fixtures del brief validan contra los esquemas commiteados."""
    for fixture, esquema in (
        ("brief-completo.json", "brief.schema.json"),
        ("borrador-completo.json", "brief-borrador.schema.json"),
    ):
        datos = json.loads((BRIEF / fixture).read_text(encoding="utf-8"))
        jsonschema.validate(datos, json.loads((SCHEMAS / esquema).read_text(encoding="utf-8")))


# RNF-05: correo, teléfono de 9 dígitos, DNI/NIE y nombres propios fuera de los ficticios (§13).
_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_TELEFONO = re.compile(r"(?<!\w)\d{3}[ .-]?\d{3}[ .-]?\d{3}(?!\w)")
_DNI_NIE = re.compile(r"(?<!\w)[XYZxyz]?\d{7,8}[A-Za-z](?!\w)")
# Una palabra con mayúscula dentro de una línea, salvo tras fin de frase, dos puntos o título.
_NOMBRE = re.compile(r"(?<![.:?!…#\-])[ \t]([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)")
FICTICIOS = {"Aurora", "Ficticia", "Bruno", "Ficticio"}


def _datos_personales(texto: str) -> list[str]:
    hallados = [m[0] for p in (_CORREO, _TELEFONO, _DNI_NIE) for m in p.finditer(texto)]
    return hallados + [m[1] for m in _NOMBRE.finditer(texto) if m[1] not in FICTICIOS]


def test_fixtures_de_brief_sin_datos_personales() -> None:
    """RNF-05. El control positivo va primero: un escáner que no ve nada no prueba nada."""
    muestra = "Escribe a nadie@example.com o al 612 345 678, DNI 12345678Z, con Marta Gil."
    assert len(_datos_personales(muestra)) == 5
    for fichero in sorted(BRIEF.rglob("*")):
        if fichero.is_file():
            texto = fichero.read_bytes().decode("utf-8")
            assert _datos_personales(texto) == [], fichero.name


def _propiedades(esquema: dict[str, object], nodo: object, ruta: str = "") -> set[str]:
    """Rutas de todas las hojas del esquema, resolviendo $ref a $defs."""
    if not isinstance(nodo, dict):
        return set()
    if "$ref" in nodo:
        defs = esquema["$defs"]
        assert isinstance(defs, dict)
        return _propiedades(esquema, defs[nodo["$ref"].rsplit("/", 1)[1]], ruta)
    rutas: set[str] = set()
    for clave in ("items", "anyOf"):
        hijos = nodo.get(clave, [])
        for hijo in hijos if isinstance(hijos, list) else [hijos]:
            rutas |= _propiedades(esquema, hijo, ruta)
    for nombre, hijo in nodo.get("properties", {}).items():
        sub = f"{ruta}.{nombre}" if ruta else nombre
        rutas |= _propiedades(esquema, hijo, sub) or {sub}
    return rutas


def test_brief_minimiza_datos_personales() -> None:
    """RNF-06 (D19): lo único que el brief guarda de una persona es nombre, edad, rasgos y
    recuerdos. Todo lo demás son preferencias, procedencia o custodia."""
    esquema = json.loads((SCHEMAS / "brief.schema.json").read_text(encoding="utf-8"))
    raices = {r.split(".")[0] for r in _propiedades(esquema, esquema)}
    assert raices == {
        "schema_version",
        "ocasion",
        "destinatario",
        "recuerdos",
        "genero",
        "tono",
        "extension",
        "prohibidos",
        "entradas",
        "ficticio",
    }
    personales = {r.split(".")[1] for r in _propiedades(esquema, esquema) if r.startswith("dest")}
    assert personales == {"nombre", "edad", "rasgos"}


# Clientes de proveedores de modelos y gateways: AGENTS.md, «Nunca».
PROHIBIDOS = (
    "anthropic",
    "claude_agent_sdk",
    "openai",
    "google.generativeai",
    "google.genai",
    "mistralai",
    "cohere",
    "ollama",
    "litellm",
    "langchain",
    "openrouter",
)
RAICES = ("novela", "api")


def _prohibido(modulo: str) -> bool:
    return any(modulo == p or modulo.startswith(p + ".") for p in PROHIBIDOS)


def test_sin_clientes_de_modelo() -> None:
    """CA-28: ni un import directo (también los perezosos, dentro de funciones) ni uno transitivo
    de ningún cliente de modelo en el CLI ni en la API."""
    backend = RAIZ_REPO / "backend"
    directos = []
    for raiz in RAICES:
        for fichero in (backend / raiz).rglob("*.py"):
            for nodo in ast.walk(ast.parse(fichero.read_text(encoding="utf-8"))):
                if isinstance(nodo, ast.Import):
                    nombres = [a.name for a in nodo.names]
                elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                    nombres = [nodo.module]
                else:
                    continue
                directos += [f"{fichero.name}: {n}" for n in nombres if _prohibido(n)]
    assert directos == []

    assert [m for m in _cargados("novela.cli", "api.main") if _prohibido(m)] == []


def _cargados(*modulos: str) -> list[str]:
    """sys.modules tras importar `modulos` en un proceso limpio: en el de pytest hay módulos que
    no son del backend."""
    codigo = f"import sys, {', '.join(modulos)}; print(*sys.modules)"
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", codigo],
        capture_output=True,
        text=True,
        check=True,
        cwd=RAIZ_REPO / "backend",
    ).stdout.split()


def test_openapi_al_dia() -> None:
    """CA-29 (RNF-05): el OpenAPI commiteado es el que genera la app. De él salen los tipos del
    frontend, generados y no escritos a mano, así que no pueden derivar por su cuenta."""
    generado = api.openapi()
    ruta = RAIZ_REPO / "backend" / "api" / "openapi.json"
    if REGENERAR:
        texto = json.dumps(generado, indent=2, ensure_ascii=False) + "\n"
        ruta.write_bytes(texto.encode("utf-8"))
    assert json.loads(ruta.read_text(encoding="utf-8")) == generado


def test_api_no_importa_slices() -> None:
    """La API puede importar dominio/ y la lectura de plataforma/; slices/ es escritura. El
    montaje en solo lectura de test_api cubre el efecto; esto cubre la causa, y nombra el import
    el día que un router tire de delta/apply.py «solo para reutilizar la serialización»."""
    assert [m for m in _cargados("api.main") if m.startswith("novela.slices")] == []


# --- Harness ↔ Claude Code (validators.md §3.8, tercer contrato) -----------------------------

AGENTES_DIR = RAIZ_REPO / ".claude" / "agents"

# spec 0003 §5.1: tools, model y salidas relativas a novelas/<slug>/. El hook lleva su propia
# copia de las salidas (no puede importar backend/); test_hook comprueba que casan.
CONTRATO = {
    "arquitecto": (
        ["Read", "Write"],
        "opus",
        [
            "canon/premisa.md",
            "canon/mundo.md",
            "canon/estilo.md",
            # El deny de Read del misterio también deniega escribirlo: el gate promueve el
            # borrador (spec 0003 v0.5, F-28).
            "canon/misterio.borrador.md",
            "canon/personajes/*.md",
        ],
    ),
    "trazador": (["Read", "Write"], "haiku", ["plan/escaleta.md", "plan/capitulos/NN.md"]),
    "escritor": (["Read", "Write"], "opus", ["capitulos/NN.md"]),
    "continuista": (["Read", "Write"], "haiku", ["qa/NN-continuidad.json"]),
    "editor-estilo": (
        ["Read", "Edit", "Write"],
        "haiku",
        ["capitulos/NN.md", "qa/NN-estilo.json"],
    ),
    "lector-suspense": (["Read", "Write"], "haiku", ["qa/NN-suspense.json"]),
    "cronista": (["Read", "Write"], "sonnet", ["estado/deltas/NN.json"]),
    "entrevistador": (["Read", "Write"], "sonnet", ["brief/borrador.json"]),
    "juez": (["Read", "Write"], "sonnet", ["qa/juicio.json"]),
}
ESQUEMAS = {
    "arquitecto": ["backend/schemas/canon.schema.json"],
    "trazador": [
        "backend/schemas/escaleta.schema.json",
        "backend/schemas/plan-capitulo.schema.json",
    ],
    "escritor": ["backend/schemas/capitulo.schema.json"],
    "continuista": ["backend/schemas/qa-informe.schema.json"],
    "editor-estilo": ["backend/schemas/qa-informe.schema.json"],
    "lector-suspense": ["backend/schemas/qa-informe.schema.json"],
    "cronista": ["backend/schemas/delta.schema.json"],
    "entrevistador": ["backend/schemas/brief-borrador.schema.json"],
    "juez": ["backend/schemas/juicio.schema.json", "backend/config/rubrica.yaml"],
}
PROHIBIDAS = {"Glob", "Grep", "Bash", "Task", "Agent", "Skill", "WebFetch", "WebSearch"}


def _agente(rol: str) -> tuple[dict[str, str], str]:
    """Frontmatter y cuerpo. No reutiliza dominio/frontmatter.py: ese valida la novela, no el
    harness, y acoplarlos haría que un cambio en uno rompa el otro."""
    _, cabecera, cuerpo = (AGENTES_DIR / f"{rol}.md").read_text(encoding="utf-8").split("---", 2)
    meta: dict[str, str] = yaml.safe_load(cabecera)
    return meta, cuerpo


def test_agentes_de_claude() -> None:
    """CA-01 (RF-01 a RF-03): los roles de CONTRATO, con name, tools y model de la spec 0003 §5.1
    y de la 0005."""
    assert {p.stem for p in AGENTES_DIR.glob("*.md")} == set(CONTRATO)
    for rol, (tools, model, _) in CONTRATO.items():
        meta, _ = _agente(rol)
        assert meta["name"] == rol
        declaradas = [t.strip() for t in meta["tools"].split(",")]
        assert set(declaradas) & PROHIBIDAS == set(), f"{rol}: {set(declaradas) & PROHIBIDAS}"
        assert declaradas == tools, rol
        assert meta["model"] == model, rol


def test_agentes_nombran_sus_salidas() -> None:
    """CA-02 (RF-04, RF-24): cada cuerpo nombra sus salidas y su esquema, y todo esquema que se
    cita existe: uno renombrado rompe CI y no el primer capítulo (F-03)."""
    for rol, (_, _, salidas) in CONTRATO.items():
        _, cuerpo = _agente(rol)
        for ruta in salidas + ESQUEMAS[rol]:
            assert ruta in cuerpo, f"{rol} no nombra {ruta}"
        for citado in re.findall(r"backend/schemas/[\w.-]+\.json", cuerpo):
            assert (RAIZ_REPO / citado).is_file(), f"{rol} cita {citado}, que no existe"


SETTINGS = RAIZ_REPO / ".claude" / "settings.json"
DENY = {
    "Read(./novelas/*/canon/misterio.md)",
    "Edit(./novelas/*/estado/estado.db*)",
    "Edit(./novelas/*/estado/state.lock)",
    "Bash(sqlite3:*)",
}
MATCHER = {
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "Read",
    "Bash",
    "PowerShell",
    "Agent",
    "Task",
}


def test_settings_de_claude() -> None:
    """CA-06 (RF-08, RF-09, RF-10, RF-20). En -p, un settings.json inválido se ignora sin avisar, y
    con él desaparecerían el deny del misterio y el hook."""
    texto = SETTINGS.read_text(encoding="utf-8")
    settings = json.loads(texto)
    assert set(settings) <= {"permissions", "hooks"}, "ni claves, ni enabledPlugins, ni env"
    assert "bypassPermissions" not in texto
    assert settings["permissions"]["allow"] == ["Agent", "Bash(novela:*)", "Edit(./novelas/**)"]
    assert DENY <= set(settings["permissions"]["deny"])
    [registro] = settings["hooks"]["PreToolUse"]
    assert set(registro["matcher"].split("|")) == MATCHER
    [orden] = [h["command"] for h in registro["hooks"]]
    script = re.search(r"\$CLAUDE_PROJECT_DIR/([^\"\s]+)", orden)
    assert script and (RAIZ_REPO / script[1]).is_file(), orden  # F-10: la ruta existe
    assert orden.startswith("python "), "python3 es el alias de la Store en Windows (E-11)"


def _tabla_de_validadores(
    texto: str, titulo: str = "### 3.10 "
) -> list[tuple[str, tuple[str, ...]]]:
    """(nombre, puntos) de cada fila de docs/validators.md §3.10, y de nada más del documento."""
    seccion = texto.split(titulo, 1)[1].split("\n---", 1)[0]
    filas = [linea.split("|")[1:-1] for linea in seccion.splitlines() if linea.startswith("| `vp_")]
    return [
        (celdas[0].strip().strip("`"), tuple(re.findall(r"`([a-z]+)`", celdas[2])))
        for celdas in filas
    ]


def test_tabla_de_validadores() -> None:
    """CA-19 (spec 0009, RF-19): la tabla de §3.10 nombra los validadores del catálogo con sus
    puntos; con una fila borrada o un punto cambiado, deja de coincidir."""
    catalogo = [(v.nombre, v.puntos) for v in VALIDADORES]
    texto = (RAIZ_REPO / "docs" / "validators.md").read_text(encoding="utf-8")
    assert _tabla_de_validadores(texto) == catalogo
    sin_fila = re.sub(r"\n\| `vp_hilos` [^\n]*", "", texto)
    assert _tabla_de_validadores(sin_fila) != catalogo
    otro_punto = texto.replace(
        "| `vp_ids` | Los ids citados existen | `validar` |",
        "| `vp_ids` | Los ids citados existen | `auditar` |",
    )
    assert otro_punto != texto and _tabla_de_validadores(otro_punto) != catalogo


def test_hook_de_validacion_registrado() -> None:
    """CA-10 de la 0008 (RF-09, VER-17): el matcher literal, no como conjunto: un separador que
    Claude Code no interpreta dejaría el hook sin disparar."""
    [registro] = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PostToolUse"]
    assert registro["matcher"] == "Write|Edit|MultiEdit"
    [hook] = registro["hooks"]
    assert hook["command"] == 'python "$CLAUDE_PROJECT_DIR/.claude/hooks/validar-capitulo.py"'
    assert hook["timeout"] == 60 and hook["type"] == "command"
    assert (RAIZ_REPO / ".claude" / "hooks" / "validar-capitulo.py").is_file()


def test_adr_de_versiones() -> None:
    """CA-42 (RF-45): el ADR 0004 existe con su frontmatter y sus cinco secciones, y el
    invariante 7 de AGENTS.md admite versiones sin dejar de prohibir la reescritura en sitio."""
    _, cabecera, cuerpo = (
        (RAIZ_REPO / "docs" / "adr" / "0004-versiones-de-la-novela.md")
        .read_text(encoding="utf-8")
        .split("---", 2)
    )
    meta = yaml.safe_load(cabecera)
    assert (meta["adr"], meta["estado"], meta["specs"]) == (4, "aceptada", [7])
    for seccion in (
        "Contexto",
        "Decisión",
        "Alternativas descartadas",
        "Consecuencias",
        "Cuándo reabrirla",
    ):
        assert f"\n## {seccion}\n" in cuerpo, seccion
    [invariante] = [
        linea
        for linea in (RAIZ_REPO / "AGENTS.md").read_text(encoding="utf-8").splitlines()
        if linea.startswith("7. ")
    ]
    assert "versiones/" in invariante
    assert "novela cambio" in invariante


ADR_ENTREGA = RAIZ_REPO / "docs" / "adr" / "0003-entrega-del-libro-en-pdf.md"
SECCIONES_ADR = (
    "Contexto",
    "Opciones",
    "Criterios",
    "Decisión",
    "Alternativas descartadas",
    "Consecuencias",
    "Cuándo reabrirla",
)


def test_adr_de_entrega() -> None:
    """CA-31 (RF-31) y VAL-33: las opciones se buscan en su sección, no en todo el fichero."""
    texto = ADR_ENTREGA.read_text(encoding="utf-8")
    _, meta_texto, cuerpo = texto.split("---\n", 2)
    meta = yaml.safe_load(meta_texto)
    assert set(meta) == {"adr", "titulo", "estado", "fecha", "decide", "specs"}
    assert (meta["adr"], meta["estado"], meta["specs"]) == (3, "aceptada", [6])
    partes = re.split(r"^## (.+)$", cuerpo, flags=re.M)[1:]
    secciones = dict(zip(partes[::2], partes[1::2], strict=True))
    assert tuple(secciones) == SECCIONES_ADR
    for opcion in ("web servida por la API", "PDF", "epub"):
        assert opcion in secciones["Opciones"], opcion
    for consecuencia in ("revisión humana", "LGPL"):  # VER-1
        assert consecuencia.lower() in secciones["Consecuencias"].lower(), consecuencia


CONTINUAR = RAIZ_REPO / ".claude" / "commands" / "novela-continuar.md"
# La tabla de códigos de la spec 0003: la regeneración no añade ninguno (spec 0007, CA-31).
CODIGOS = """| Código | Qué haces |
|---|---|
| 0 | Sigues |
| 1 | Gate fallido: reintento según el paso, con la regla de lectura 1. Un 1 de `novela briefing` o de `novela checkpoint` no tiene reintento: `intervencion.md` y para |
| 2 | Uso incorrecto: el procedimiento está mal. Para sin `intervencion.md` |
| 3 | Lock ocupado: otro proceso trabaja en la novela. Para sin `intervencion.md` |
| 4 | Workspace inválido: `intervencion.md` y para. No es un gate y no se reintenta |
"""  # noqa: E501


def test_procedimiento_regeneracion() -> None:
    """CA-31 (spec 0007, RF-34): «Situación» pregunta al CLI qué toca, reaplica sin agentes y un 1
    de --reaplicar para con gate: regeneracion; la tabla de códigos no cambia."""
    texto = CONTINUAR.read_text(encoding="utf-8")
    situacion = texto.split("1. **Situación.**", 1)[1].split("\n2. ", 1)[0]
    for orden in (
        "novela cambio <slug> --siguiente",
        "aplicar-delta <slug> <cap> --reaplicar",
        "gate: regeneracion",
    ):
        assert orden in situacion, orden
    assert CODIGOS in texto


def test_agentes_nombran_el_cambio() -> None:
    """CA-32 (spec 0007, RF-35): el cronista nombra hechos_usados y la cita literal; los tres
    roles con capa cambio la nombran. tools y model los cubre test_agentes_de_claude."""
    _, cronista = _agente("cronista")
    assert "hechos_usados" in cronista
    assert re.search(r"`hechos_usados`[^\n]*\n?[^\n]*literal", cronista), "cita literal"
    for rol in ("cronista", "escritor", "continuista"):
        _, cuerpo = _agente(rol)
        assert "capa `cambio`" in cuerpo, rol

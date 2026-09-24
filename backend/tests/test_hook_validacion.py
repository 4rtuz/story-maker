"""El hook PostToolUse `.claude/hooks/validar-capitulo.py` (spec 0008), ejecutado como subproceso
contra el `novela` real del venv, igual que lo ejecuta Claude Code. Se importa con importlib solo
para los casos que un subproceso no provoca fácilmente (informe ilegible, excepciones, argv)."""

import ast
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from novela.dominio import frontmatter
from tests.fixtures import fabrica

RAIZ_REPO = Path(__file__).resolve().parents[2]
HOOK = RAIZ_REPO / ".claude" / "hooks" / "validar-capitulo.py"
RUN = "r-20260923-1000"
FALLO = "validar-capitulo: fallo del harness, no del capítulo"
FIN = "No reescribas el capítulo: termina e informa."
SIN_CAMPO = object()  # agent_type ausente, distinto de null


@pytest.fixture(autouse=True)
def _novela_en_el_path() -> None:
    """D5: sin `novela` el hook no se prueba; un skip dejaría la suite en verde (VER-8)."""
    assert shutil.which("novela"), "novela no resuelve en el PATH: ejecuta con `uv run pytest`"


@pytest.fixture
def ws(plantillas: Path, tmp_path: Path) -> Path:
    """demo-24 bajo un directorio con ñ (VAL-25): el hook solo actúa bajo `novelas/<slug>/`."""
    raiz = tmp_path / "año" / "novelas" / "demo-24"
    shutil.copytree(plantillas / "demo-24", raiz)
    return raiz


def _hook(
    entrada: object, cwd: Path, entorno: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Sin NOVELA_SESSION_ID heredado y con un NOVELAS_DIR que no es el del workspace: el hook
    tiene que sacarlo de la ruta (VAL-4)."""
    datos = entrada if isinstance(entrada, bytes) else json.dumps(entrada).encode()
    env = {k: v for k, v in os.environ.items() if k != "NOVELA_SESSION_ID"}
    env |= {"NOVELA_RUN_ID": RUN, "NOVELAS_DIR": str(cwd / "no-es-este")} | (entorno or {})
    return subprocess.run(  # noqa: S603
        [sys.executable, str(HOOK)],
        input=datos,
        capture_output=True,
        cwd=cwd,
        env=env,
        timeout=60,
        check=False,
    )


def _escritura(
    ruta: Path | str, cwd: Path, agente: object = "escritor", tool: str = "Write"
) -> dict[str, Any]:
    entrada: dict[str, Any] = {
        "tool_name": tool,
        "tool_input": {"file_path": str(ruta), "content": "x"},
        "tool_response": [1, None],  # tipos inesperados: no se lee (VAL-25)
        "cwd": str(cwd),
    }
    if agente is not SIN_CAMPO:
        entrada["agent_type"] = agente
    return entrada


def _valido(ws: Path) -> None:
    fabrica.escribir(ws, {"capitulos/08.md": fabrica.capitulo(fabrica.DEMO, 8)})


def _invalido(ws: Path, corto: bool = False) -> None:
    """El plan manda plantar pis-004 (CA-02); `corto` añade un hallazgo de longitud (VAL-6)."""
    meta, cuerpo = frontmatter.partir(fabrica.capitulo(fabrica.DEMO, 8))
    if corto:
        cuerpo = " ".join(cuerpo.split()[:30])
    texto = frontmatter.unir(meta | {"pistas_plantadas": []}, cuerpo)
    fabrica.escribir(ws, {"capitulos/08.md": texto})


def _log(ws: Path) -> list[str]:
    ruta = ws / "runs" / RUN / "harness.log"
    return ruta.read_text(encoding="utf-8").splitlines() if ruta.is_file() else []


def _ventanas(texto: str) -> set[str]:
    p = texto.split()
    return {" ".join(p[i : i + 8]) for i in range(len(p) - 7)}


def test_capitulo_valido(ws: Path, tmp_path: Path) -> None:
    """CA-01 (RF-01, RF-02, RF-06; VAL-4, VAL-5, VAL-25): aprobado en silencio, con el workspace de
    la ruta, la sesión del entorno y sin leer el contenido de la escritura."""
    _valido(ws)
    uuid = "11111111-1111-4111-8111-111111111111"
    entrada = _escritura(ws / "capitulos" / "08.md", tmp_path)
    entrada["tool_input"]["content"] = "x" * 2_000_000
    r = _hook(entrada, tmp_path, {"NOVELA_SESSION_ID": uuid})
    assert (r.returncode, r.stdout, r.stderr) == (0, b"", b"")
    log = _log(ws)
    assert "validar-hook 08 -> 0" in log[-1] and f"sesion={uuid}" in log[-1]
    assert not any("validar 08 -> " in linea for linea in log)
    informe = json.loads((ws / "qa" / "08-validacion.json").read_text(encoding="utf-8"))
    assert informe["veredicto"] == "aprobado"
    assert informe["capitulo_sha256"] == fabrica.sha256(ws / "capitulos" / "08.md")
    assert not (tmp_path / "no-es-este").exists()


@pytest.mark.parametrize("corto", [False, True])
def test_capitulo_invalido(ws: Path, tmp_path: Path, corto: bool) -> None:
    """CA-02 (RF-03, RNF-04; VAL-6, VAL-22): exit 2 con cada hallazgo y sus cuatro campos, sin
    prosa del capítulo ni del canon."""
    _invalido(ws, corto)
    r = _hook(_escritura(ws / "capitulos" / "08.md", tmp_path), tmp_path)
    assert r.returncode == 2
    texto = r.stderr.decode("utf-8")
    assert texto.startswith("validar-capitulo:") and len(texto) <= 4000
    assert "qa/08-validacion.json" in texto and "pis-004" in texto
    hallazgos = json.loads((ws / "qa" / "08-validacion.json").read_text("utf-8"))["hallazgos"]
    assert len(hallazgos) >= (2 if corto else 1)
    assert sum(linea.startswith("- ") for linea in texto.splitlines()) == len(hallazgos)
    for h in hallazgos:
        campos = (h["tipo"], h["gravedad"], h.get("ubicacion") or "sin ubicación", h["descripcion"])
        assert all(c in texto for c in campos), h
    _, cuerpo = frontmatter.partir((ws / "capitulos" / "08.md").read_text("utf-8"))
    secreto = (ws / "canon" / "misterio.md").read_text("utf-8")
    assert not any(v in texto for v in _ventanas(cuerpo) | _ventanas(secreto))
    assert "validar-hook 08 -> 1" in _log(ws)[-1]


def test_herramientas_y_roles_que_validan(ws: Path, tmp_path: Path) -> None:
    """CA-03 (RF-01, VAL-3): cada herramienta con cada rol que valida, y agent_type null o vacío
    como si no viniera (falla cerrado)."""
    _invalido(ws)
    ruta = ws / "capitulos" / "08.md"
    casos = [
        (tool, agente)
        for tool in ("Write", "Edit", "MultiEdit")
        for agente in ("escritor", "editor-estilo", SIN_CAMPO)
    ] + [("Write", None), ("Write", "")]
    for tool, agente in casos:
        antes = len(_log(ws))
        r = _hook(_escritura(ruta, tmp_path, agente, tool), tmp_path)
        assert r.returncode == 2, (tool, agente, r.stderr)
        nuevas = _log(ws)[antes:]
        assert len(nuevas) == 1 and "validar-hook 08 -> 1" in nuevas[0], (tool, agente)


def test_fuera_de_alcance(ws: Path, tmp_path: Path) -> None:
    """CA-04 (RF-05, RNF-01; VAL-12, VAL-19): exit 0 en silencio sin ejecutar novela, que no abre
    el run; mediana de 20 ejecuciones ≤ 300 ms."""
    _valido(ws)
    cap = ws / "capitulos"
    entradas = [
        _escritura(ws / "qa" / "08-estilo.json", tmp_path),
        _escritura(ws / "versiones" / "v1" / "capitulos" / "01.md", tmp_path),
        _escritura(cap / "08.md.tmp", tmp_path),
        _escritura(cap / "8.md", tmp_path),
        _escritura(cap / "0008.md", tmp_path),
        _escritura(tmp_path / "docs" / "capitulos" / "08.md", tmp_path),
        _escritura(cap / "08.md", tmp_path, "Explore"),
        _escritura(cap / "08.md", tmp_path, "general-purpose"),
        _escritura(cap / "08.md", tmp_path, tool="Read"),
    ]
    tiempos = []
    for i in range(20):
        inicio = time.perf_counter()
        r = _hook(entradas[i % len(entradas)], tmp_path)
        tiempos.append(time.perf_counter() - inicio)
        assert (r.returncode, r.stdout, r.stderr) == (0, b"", b""), entradas[i % len(entradas)]
    assert not (ws / "runs" / RUN).exists()
    assert statistics.median(tiempos) <= 0.3


def test_falla_cerrado(
    ws: Path, tmp_path: Path, lock_ajeno: Callable[[Path], AbstractContextManager[None]]
) -> None:
    """CA-05 (RF-04; VAL-8, VER-11, VER-12): cada causa sale con 2 y un mensaje de una línea que
    no es un rechazo del capítulo."""
    _valido(ws)
    ruta = ws / "capitulos" / "08.md"
    sin_novela = os.pathsep.join(
        e for e in os.environ["PATH"].split(os.pathsep) if not shutil.which("novela", path=e)
    )
    assert shutil.which("novela", path=sin_novela) is None
    casos: list[tuple[object, dict[str, str] | None, str | None]] = [
        (b"no es json", None, None),
        (b"", None, None),
        (b"\xff\xfe", None, None),
        ({"tool_name": "Write", "tool_input": {}}, None, None),
        ({"tool_name": "Write", "tool_input": {"file_path": 42}}, None, None),
        (_escritura(ruta, tmp_path), {"PATH": sin_novela}, "PATH"),
        (_escritura(ws.parent / "no-existe" / "capitulos" / "08.md", tmp_path), None, "4"),
        (_escritura(ws / "capitulos" / "99.md", tmp_path), None, "2"),
    ]

    def comprobar(entrada: object, entorno: dict[str, str] | None, causa: str | None) -> None:
        r = _hook(entrada, tmp_path, entorno)
        texto = r.stderr.decode("utf-8")
        assert r.returncode == 2, (entrada, texto)
        assert texto.startswith(FALLO) and texto.endswith(FIN), texto
        assert "\n" not in texto and "Traceback" not in texto
        assert causa is None or causa in texto, texto

    for entrada, entorno, causa in casos:
        comprobar(entrada, entorno, causa)
    with lock_ajeno(ws / "estado" / "state.lock"):
        comprobar(_escritura(ruta, tmp_path), None, "3")


def test_ancho_de_capitulo(ws: Path, tmp_path: Path) -> None:
    """CA-06 (RF-04, VAL-11): `008.md` en una novela de dos dígitos valida `08.md` (que no existe)
    y el informe que busca el hook, `qa/008-validacion.json`, no está."""
    fabrica.escribir(ws, {"capitulos/008.md": fabrica.capitulo(fabrica.DEMO, 8)})
    r = _hook(_escritura(ws / "capitulos" / "008.md", tmp_path), tmp_path)
    texto = r.stderr.decode("utf-8")
    assert r.returncode == 2 and texto.startswith(FALLO) and "qa/008-validacion.json" in texto


def _importados(fuente: str) -> set[str]:
    """Módulos de primer nivel: import, from, relativos (vacío) y los importados con literal."""
    modulos = set()
    for n in ast.walk(ast.parse(fuente)):
        if isinstance(n, ast.Import):
            modulos |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            modulos.add("" if n.level else (n.module or "").split(".")[0])
        elif isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant):
            nombre = getattr(n.func, "attr", getattr(n.func, "id", None))
            if nombre in ("import_module", "__import__"):
                modulos.add(str(n.args[0].value).split(".")[0])
    return modulos


def _foto(raiz: Path) -> dict[str, str]:
    return {
        p.relative_to(raiz).as_posix(): fabrica.sha256(p) for p in raiz.rglob("*") if p.is_file()
    }


def test_solo_stdlib_y_sin_estado(ws: Path, tmp_path: Path) -> None:
    """CA-09 (RF-08, RNF-03, RNF-05; VAL-15, VAL-21, VER-15): solo stdlib, y lo único que cambia
    en el workspace es lo que ya escribe `novela validar`."""
    assert _importados(HOOK.read_text(encoding="utf-8")) <= sys.stdlib_module_names
    assert not _importados("def f():\n    from yaml import safe_load\n") <= sys.stdlib_module_names
    assert "novela" in _importados("import importlib\nimportlib.import_module('novela.cli')\n")
    assert "" in _importados("from . import x\n")
    permitidos = {"qa/08-validacion.json", "estado/state.lock"}
    for preparar in (_valido, _invalido):
        preparar(ws)
        antes = _foto(ws)
        _hook(_escritura(ws / "capitulos" / "08.md", tmp_path), tmp_path)
        despues = _foto(ws)
        cambios = {r for r in antes.keys() | despues.keys() if antes.get(r) != despues.get(r)}
        assert {c for c in cambios if not c.startswith(f"runs/{RUN}/")} <= permitidos, cambios
        assert "estado/estado.db" in despues


def test_rendimiento(ws: Path, tmp_path: Path) -> None:
    """RNF-02 (VAL-20): mediana de 5 validaciones ≤ 3 s."""
    _valido(ws)
    tiempos = []
    for _ in range(5):
        inicio = time.perf_counter()
        assert _hook(_escritura(ws / "capitulos" / "08.md", tmp_path), tmp_path).returncode == 0
        tiempos.append(time.perf_counter() - inicio)
    assert statistics.median(tiempos) <= 3.0


def test_custodia_acepta_el_informe_del_hook(plantillas: Path, tmp_path: Path) -> None:
    """VAL-24 (spec §8.1): el informe del hook satisface la custodia de aplicar-delta sin que el
    orquestador valide; uno rechazado la rompe sin tocar el estado."""
    base = tmp_path / "novelas"
    shutil.copytree(plantillas / "demo-24", base / "demo-24")
    fabrica.preparar_capitulo(base, "demo-24", fabrica.DEMO, 8)
    raiz, run = base / "demo-24", fabrica.run_id(8)
    (raiz / "qa" / "08-validacion.json").unlink()
    db = raiz / "estado" / "estado.db"
    entrada = _escritura(raiz / "capitulos" / "08.md", tmp_path)
    _invalido(raiz)
    huella = fabrica.sha256(db)
    assert _hook(entrada, tmp_path, {"NOVELA_RUN_ID": run}).returncode == 2
    assert fabrica.cli(base, "aplicar-delta", "demo-24", "8", run=run).exit_code != 0
    assert fabrica.sha256(db) == huella
    _valido(raiz)
    assert _hook(entrada, tmp_path, {"NOVELA_RUN_ID": run}).returncode == 0
    resultado = fabrica.cli(base, "aplicar-delta", "demo-24", "8", run=run)
    assert resultado.exit_code == 0, resultado.output


# --- Unitarios, con el script importado ---------------------------------------------------------


@pytest.fixture
def hook() -> Iterator[ModuleType]:
    spec = importlib.util.spec_from_file_location("validar_capitulo", HOOK)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    yield modulo


def _entrada(ruta: str, cwd: str | None = "/r", agente: object = "escritor") -> dict[str, Any]:
    entrada = _escritura(ruta, Path(cwd or "."), agente)
    if cwd is None:
        del entrada["cwd"]
    return entrada


def test_ruta(hook: ModuleType, tmp_path: Path) -> None:
    """VAL-26, VER-6: normalización contra cwd, `\\` y mayúsculas, grafía original, última
    aparición, y nada que no sea exactamente `capitulos/<NN>.md`."""
    repo = tmp_path / "Repo"
    fuera = [
        "/r/novelas/demo-24/capitulos/08.md.tmp",
        "/r/novelas/demo-24/capitulos/٠٨.md",
        "/r/novelas/demo-24/versiones/v1/capitulos/01.md",
        "/r/novelas/demo-24/capitulos/1000.md",
    ]
    for ruta in fuera:
        assert hook.capitulo_de(_entrada(ruta)) is None, ruta
    for ruta in (r"Novelas\demo-24\Capitulos\08.md", "x/../Novelas/demo-24/capitulos/08.md"):
        novelas, slug, nn = hook.capitulo_de(_entrada(ruta, str(repo)))
        assert novelas.endswith("/Repo/Novelas") and (slug, nn) == ("demo-24", "08"), ruta
    anidada = "/r/novelas/a/capitulos/novelas/demo-24/capitulos/100.md"
    assert hook.capitulo_de(_entrada(anidada))[1:] == ("demo-24", "100")
    windows = hook.capitulo_de(_entrada(r"C:\R\NOVELAS\demo-24\CAPITULOS\08.md"))
    assert windows[0].endswith("/R/NOVELAS") and windows[1:] == ("demo-24", "08")
    assert hook.capitulo_de(_entrada("novelas/demo-24/capitulos/08.md", None)) is not None
    for agente in (SIN_CAMPO, None, "", "editor-estilo"):
        assert hook.capitulo_de(_entrada("/r/novelas/d/capitulos/08.md", agente=agente))
    assert hook.capitulo_de(_entrada("/r/novelas/d/capitulos/08.md", agente="Explore")) is None


def test_mensajes(hook: ModuleType) -> None:
    """VAL-27, VAL-7, VER-7: formato literal del rechazo y del fallo; truncado a 4.000 caracteres
    contando el `…`."""
    dos: list[dict[str, Any]] = [
        {"tipo": "pista_ausente", "gravedad": "alta", "ubicacion": "§2", "descripcion": "falta"},
        {"tipo": "id_inexistente", "gravedad": "media", "ubicacion": None, "descripcion": "→"},
    ]
    lineas = hook.mensaje_rechazo("08", dos).splitlines()
    assert lineas[0] == (
        "validar-capitulo: capitulos/08.md rechazado por novela validar (2 hallazgos en "
        "qa/08-validacion.json). Corrige el capítulo y vuelve a escribirlo:"
    )
    assert lineas[1:] == [
        "- pista_ausente (alta) §2: falta",
        "- id_inexistente (media) sin ubicación: →",
    ]
    largo = hook.mensaje_rechazo("08", [dos[0] | {"descripcion": "ñá" * 50}] * 200)
    assert len(largo) == 4000 and largo.endswith("…")
    fallo = hook.mensaje_fallo("novela validar\nsalió con 4")
    assert fallo == f"{FALLO}: novela validar salió con 4. {FIN}"


Llamadas = list[tuple[list[str], dict[str, Any]]]


def _falso(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch, codigo: int, informe: str | None
) -> Llamadas:
    """`novela` falso: registra la llamada y, si hay informe, lo escribe antes de salir."""
    llamadas: Llamadas = []

    def run(orden: list[str], **kw: Any) -> subprocess.CompletedProcess[bytes]:
        llamadas.append((orden, kw))
        if informe is not None:
            raiz = Path(kw["env"]["NOVELAS_DIR"], orden[2])
            fabrica.escribir(raiz, {"qa/08-validacion.json": informe})
        return subprocess.CompletedProcess(orden, codigo, b"", b"Traceback (most recent call last)")

    monkeypatch.setattr(hook.shutil, "which", lambda _: "/bin/novela")
    monkeypatch.setattr(hook.subprocess, "run", run)
    return llamadas


def test_invocacion(hook: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """VER-5, VAL-3: lista sin shell, NN como entero, entorno fusionado y NOVELAS_DIR de la ruta."""
    monkeypatch.setenv("NOVELA_RUN_ID", RUN)
    llamadas = _falso(hook, monkeypatch, 0, None)
    for ruta, slug, cap in (
        ("novelas/demo-24/capitulos/08.md", "demo-24", "8"),
        ("novelas/a;b/capitulos/008.md", "a;b", "8"),
        ("novelas/a&b/capitulos/100.md", "a&b", "100"),
    ):
        entrada = json.dumps(_entrada(ruta, str(tmp_path))).encode()
        assert hook.ejecutar(entrada) == (0, "")
        orden, kw = llamadas[-1]
        assert orden == ["/bin/novela", "validar", slug, cap, "--origen", "hook"]
        assert "shell" not in kw and kw["timeout"] == 45
        assert kw["env"]["NOVELA_RUN_ID"] == RUN
        assert kw["env"]["NOVELAS_DIR"] == (tmp_path / "novelas").as_posix()


def test_fuera_de_alcance_no_resuelve_novela(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VER-10: fuera de alcance sale antes de buscar `novela`."""

    def prohibido(_: str) -> str:
        raise AssertionError("resolvió novela")

    monkeypatch.setattr(hook.shutil, "which", prohibido)
    for entrada in (
        _entrada("/r/novelas/d/qa/08-estilo.json"),
        _entrada("/r/novelas/d/capitulos/08.md", agente="Explore"),
        _entrada("/r/novelas/d/capitulos/08.md") | {"tool_name": "Read"},
    ):
        assert hook.ejecutar(json.dumps(entrada).encode()) == (0, "")


@pytest.mark.parametrize(
    "informe",
    ["{", "[]", '{"hallazgos": "x"}', '{"hallazgos": [{"tipo": 1}]}', "OBSOLETO"],
)
def test_informe_ilegible(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch, ws: Path, tmp_path: Path, informe: str
) -> None:
    """VAL-28, VER-14, VAL-9: tras un 1, un informe que no se entiende, o que es de otra versión
    del capítulo (un traceback que dejó el anterior), es fallo del harness, no hallazgos."""
    _valido(ws)
    if informe == "OBSOLETO":
        informe = json.dumps(
            {
                "capitulo_sha256": "0" * 64,
                "hallazgos": [
                    {"tipo": "pista_ausente", "gravedad": "alta", "descripcion": "vieja"}
                ],
            }
        )
    _falso(hook, monkeypatch, 1, informe)
    codigo, texto = hook.ejecutar(
        json.dumps(_escritura(ws / "capitulos" / "08.md", tmp_path)).encode()
    )
    assert codigo == 2 and texto.startswith(FALLO) and "- pista_ausente" not in texto, texto


def test_excepciones(hook: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """VER-3: ni `which` a None, ni un OSError, ni el límite de 45 s salen con 1."""
    entrada = json.dumps(_entrada("novelas/d/capitulos/08.md", str(tmp_path))).encode()
    monkeypatch.setattr(hook.shutil, "which", lambda _: None)
    codigo, texto = hook.ejecutar(entrada)
    assert codigo == 2 and texto.startswith(FALLO) and "PATH" in texto
    monkeypatch.setattr(hook.shutil, "which", lambda _: "/bin/novela")
    for error in (OSError("x"), subprocess.TimeoutExpired("novela", 45)):

        def lanza(*_: object, error: Exception = error, **__: object) -> None:
            raise error

        monkeypatch.setattr(hook.subprocess, "run", lanza)
        codigo, texto = hook.ejecutar(entrada)
        assert codigo == 2 and texto.startswith(FALLO) and texto.endswith(FIN), texto

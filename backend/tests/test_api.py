"""API de solo lectura (spec 0001 §5.5): cinco GET, ningún verbo de escritura."""

import builtins
import io
import json
import os
import sqlite3
import stat
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import app
from novela.plataforma.workspace import WorkspaceRepository, huella
from tests.fixtures import fabrica

BACKEND = Path(__file__).resolve().parents[1]  # código y .venv
cliente = TestClient(app)


def test_app_arranca() -> None:
    assert cliente.get("/docs").status_code == 200


@pytest.mark.parametrize(
    "ruta",
    [
        "/novelas/..%2F..%2Fetc/estado",
        # spec 0004, CA-32 a CA-37: los GET nuevos pasan por la misma dependencia.
        "/novelas/..%2F..%2Fetc/config",
        "/novelas/..%2F..%2Fetc/escaleta",
        "/novelas/..%2F..%2Fetc/checkpoint",
    ],
)
def test_path_traversal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ruta: str) -> None:
    """CA-26: el slug se valida antes de construir ninguna ruta. «No toca el disco» se comprueba,
    no se supone: toda apertura, stat o conexión fuera del código durante la petición queda
    registrada. FastAPI lee el fuente del endpoint para el mensaje de error; eso no es disco."""
    respuesta, fuera = _pedir_espiando(monkeypatch, tmp_path, ruta)
    assert fuera == []
    assert respuesta.status_code == 422


def _pedir_espiando(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ruta: str
) -> tuple[Any, list[Any]]:
    """La respuesta y lo que la petición abrió, miró o conectó fuera de `backend/`."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    tocado: list[Any] = []

    def espia(original: Callable[..., Any]) -> Callable[..., Any]:
        def registrar(*args: Any, **kwargs: Any) -> Any:
            tocado.append(args[0] if args else kwargs)
            return original(*args, **kwargs)

        return registrar

    for modulo, nombre in (
        (builtins, "open"),
        (io, "open"),
        (os, "stat"),
        (os, "scandir"),
        (sqlite3, "connect"),
    ):
        monkeypatch.setattr(modulo, nombre, espia(getattr(modulo, nombre)))
    respuesta = cliente.get(ruta)
    monkeypatch.undo()
    return respuesta, [p for p in tocado if not str(p).startswith(str(BACKEND))]


@pytest.fixture
def solo_lectura(
    novelas: Callable[[str], WorkspaceRepository],
) -> Iterator[WorkspaceRepository]:
    """demo-24 en solo lectura mientras dura el test: si un endpoint intentara escribir, el sistema
    de ficheros lo impide. En Windows el atributo no protege directorios, así que además la huella
    del workspace tiene que salir igual que entró."""
    ws = novelas("demo-24")
    rutas = [ws.raiz, *ws.raiz.rglob("*")]
    antes = huella(ws.raiz)
    for ruta in rutas:
        ruta.chmod(stat.S_IREAD | (stat.S_IEXEC if ruta.is_dir() else 0))
    try:
        yield ws
    finally:
        for ruta in rutas:
            ruta.chmod(stat.S_IREAD | stat.S_IWRITE | (stat.S_IEXEC if ruta.is_dir() else 0))
    assert huella(ws.raiz) == antes


def test_cinco_get_en_solo_lectura(solo_lectura: WorkspaceRepository) -> None:
    """CA-25: los cinco GET sobre el fixture montado en solo lectura, y ningún verbo más."""
    ws = solo_lectura
    assert {m for ops in app.openapi()["paths"].values() for m in ops} == {"get"}

    novelas = cliente.get("/novelas")
    assert novelas.status_code == 200
    assert [(n["slug"], n["cursor"]["capitulo"]) for n in novelas.json()] == [("demo-24", 7)]

    estado = cliente.get("/novelas/demo-24/estado")
    assert estado.status_code == 200
    assert estado.json()["cursor"]["ultimo_paso"] == "aplicar-delta"

    indice = cliente.get("/novelas/demo-24/capitulos")
    assert indice.status_code == 200
    assert [c["capitulo"] for c in indice.json()] == list(range(1, 8))

    capitulo = cliente.get("/novelas/demo-24/capitulos/3")
    assert capitulo.status_code == 200
    assert capitulo.content == (ws.raiz / "capitulos" / "03.md").read_bytes()

    manifiesto = cliente.get(f"/novelas/demo-24/runs/{fabrica.run_id(7)}")
    assert manifiesto.status_code == 200
    assert manifiesto.json()["capitulo"] == 7

    for ruta in (
        "/novelas/no-existe/estado",
        "/novelas/no-existe/capitulos",
        "/novelas/demo-24/capitulos/8",  # dentro de rango, sin escribir
        "/novelas/demo-24/capitulos/25",  # fuera de rango
        "/novelas/demo-24/runs/r-20990101-0000",
    ):
        assert cliente.get(ruta).status_code == 404, ruta


# --- spec 0004: los GET del panel -------------------------------------------------------------


@pytest.fixture
def recien_creada(novelas: Callable[[str], WorkspaceRepository], tmp_path: Path) -> Path:
    """Solo `novela nueva`: sin plan, sin checkpoints y sin runs. `nueva` no abre run. Pide
    `novelas` por su NOVELAS_DIR en tmp_path."""
    resultado = fabrica.cli(
        tmp_path, "nueva", "recien-creada", "--idea", "Un faro apagado.", run=fabrica.run_id(1)
    )
    assert resultado.exit_code == 0, resultado.output
    return tmp_path / "recien-creada"


def test_config(novelas: Callable[[str], WorkspaceRepository]) -> None:
    """CA-32: el modelo validado, con sus valores por defecto, no el YAML literal (D53)."""
    ws = novelas("demo-24")
    respuesta = cliente.get("/novelas/demo-24/config")
    assert respuesta.status_code == 200
    assert respuesta.json() == ws.config().model_dump(mode="json")
    assert cliente.get("/novelas/no-existe/config").status_code == 404


def test_escaleta(novelas: Callable[[str], WorkspaceRepository], recien_creada: Path) -> None:
    """CA-33 y VER-1: 200 con la curva de la obra, aunque la respuesta pase por la validación de
    FastAPI, que no lleva el contexto de `num_capitulos`; sin plan, 404."""
    novelas("demo-24")
    respuesta = cliente.get("/novelas/demo-24/escaleta")
    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()["curva_tension_objetivo"]) == 24
    assert cliente.get("/novelas/recien-creada/escaleta").status_code == 404


def test_checkpoint(novelas: Callable[[str], WorkspaceRepository], recien_creada: Path) -> None:
    """CA-34: el `latest.json` tal cual, o `null` sin checkpoints."""
    ws = novelas("demo-24")
    respuesta = cliente.get("/novelas/demo-24/checkpoint")
    assert respuesta.status_code == 200
    assert respuesta.json()["capitulo"] == 7
    assert respuesta.json() == json.loads((ws.raiz / "checkpoints" / "latest.json").read_bytes())
    vacia = cliente.get("/novelas/recien-creada/checkpoint")
    assert vacia.status_code == 200
    assert vacia.json() is None


@pytest.mark.parametrize(
    ("fichero", "romper"),
    [
        # La curva de 23 valores no cuadra con num_capitulos 24.
        (
            "plan/escaleta.md",
            lambda t: t.replace("curva_tension_objetivo:\n- 2\n", "curva_tension_objetivo:\n", 1),
        ),
        ("plan/escaleta.md", lambda t: t.replace("\n---\n", "\n", 1)),  # frontmatter sin cerrar
        ("plan/escaleta.md", lambda t: t.replace("actos:", "actos: [", 1)),  # YAML roto
        ("config.yaml", lambda t: t.replace("parametros_obra:", "parametros_obra: [", 1)),
    ],
)
def test_ilegible_da_404(
    novelas: Callable[[str], WorkspaceRepository], fichero: str, romper: Callable[[str], str]
) -> None:
    """VER-2: un fichero que falta o no valida sale como 404 con su `detail`, nunca como 500."""
    ws = novelas("demo-24")
    ruta = ws.raiz / fichero
    texto = ruta.read_text(encoding="utf-8")
    assert romper(texto) != texto
    ruta.write_text(romper(texto), encoding="utf-8")
    recurso = "config" if fichero == "config.yaml" else "escaleta"
    respuesta = cliente.get(f"/novelas/demo-24/{recurso}")
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]


def test_runs(novelas: Callable[[str], WorkspaceRepository]) -> None:
    """CA-35: un Manifest por `runs/*/manifest.json`, por run_id ascendente."""
    ws = novelas("demo-24")
    respuesta = cliente.get("/novelas/demo-24/runs")
    assert respuesta.status_code == 200
    ids = [m["run_id"] for m in respuesta.json()]
    assert ids == sorted(ids) == [fabrica.run_id(n) for n in range(1, 8)]
    for manifiesto in respuesta.json():
        ruta = ws.raiz / "runs" / manifiesto["run_id"] / "manifest.json"
        assert manifiesto == json.loads(ruta.read_bytes())


def _log(ws: WorkspaceRepository, run_id: str = fabrica.run_id(7)) -> Path:
    return ws.raiz / "runs" / run_id / "harness.log"


def _run_propio(ws: WorkspaceRepository, run_id: str, log: bytes | None) -> Path:
    """Un run fabricado a mano: `run.abrir` siempre deja log tras el primer paso."""
    directorio = ws.raiz / "runs" / run_id
    directorio.mkdir()
    manifiesto = json.loads((ws.raiz / "runs" / fabrica.run_id(7) / "manifest.json").read_bytes())
    (directorio / "manifest.json").write_text(json.dumps(manifiesto | {"run_id": run_id}))
    if log is not None:
        (directorio / "harness.log").write_bytes(log)
    return directorio


def test_log_encadenado(novelas: Callable[[str], WorkspaceRepository]) -> None:
    """RF-36 contra la API: encadenar con cada `hasta` recorre el log entero, una sola vez."""
    ws = novelas("demo-24")
    ruta = f"/novelas/demo-24/runs/{fabrica.run_id(7)}/log"
    desde, lineas = 0, []
    while True:
        tramo = cliente.get(ruta, params={"desde": desde}).json()
        assert tramo["desde"] == desde and tramo["tamano"] == _log(ws).stat().st_size
        assert tramo["modificado"]
        if not tramo["lineas"]:
            break
        lineas += tramo["lineas"]
        desde = tramo["hasta"]
    assert lineas == _log(ws).read_text(encoding="utf-8").splitlines()
    assert desde == _log(ws).stat().st_size


def test_log_codigos(
    novelas: Callable[[str], WorkspaceRepository], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CA-37 y VAL-21, en el orden del criterio."""
    ws = novelas("demo-24")
    ruta = f"/novelas/demo-24/runs/{fabrica.run_id(7)}/log"
    sin_log = "/novelas/demo-24/runs/r-20990101-0000/log"
    tamano = _log(ws).stat().st_size
    _run_propio(ws, "r-20990101-0000", log=None)
    vacio: dict[str, Any] = {"tamano": 0, "modificado": None, "lineas": []}
    for pedida, codigo, cuerpo in (
        (f"{ruta}?desde=-1", 422, None),
        (f"{ruta}?desde=abc", 422, None),
        (f"{ruta}?desde={tamano + 1}", 416, None),
        ("/novelas/demo-24/runs/r-20990101-0001/log", 404, None),
        (f"{sin_log}?desde=0", 200, {"desde": 0, "hasta": 0} | vacio),
        (f"{sin_log}?desde=5", 200, {"desde": 5, "hasta": 5} | vacio),
    ):
        respuesta = cliente.get(pedida)
        assert respuesta.status_code == codigo, pedida
        if cuerpo is not None:
            assert respuesta.json() == cuerpo

    al_final = cliente.get(f"{ruta}?desde={tamano}").json()
    assert al_final["lineas"] == [] and al_final["hasta"] == al_final["tamano"] == tamano

    # A mitad de la línea 3: la primera devuelta es la 4, completa (VAL-21, D48).
    lineas = _log(ws).read_bytes().splitlines(keepends=True)
    mitad = len(b"".join(lineas[:2])) + len(lineas[2]) // 2
    tramo = cliente.get(f"{ruta}?desde={mitad}").json()
    assert tramo["lineas"][0] == lineas[3].decode().rstrip("\r\n")

    respuesta, fuera = _pedir_espiando(
        monkeypatch, tmp_path, "/novelas/demo-24/runs/..%2F..%2Fconfig.yaml/log"
    )
    assert respuesta.status_code != 200 and fuera == []


def test_rutas_de_runs_no_se_solapan(novelas: Callable[[str], WorkspaceRepository]) -> None:
    """VER-4: con `{slug:path}`, cada forma de ruta llega a su endpoint y a su modelo."""
    novelas("demo-24")
    run = fabrica.run_id(7)
    assert isinstance(cliente.get("/novelas/demo-24/runs").json(), list)
    assert cliente.get(f"/novelas/demo-24/runs/{run}").json()["run_id"] == run
    campos = {"desde", "hasta", "tamano", "modificado", "lineas"}
    assert set(cliente.get(f"/novelas/demo-24/runs/{run}/log").json()) == campos
    assert cliente.get(f"/novelas/demo-24/runs/{run}/log/extra").status_code == 404
    assert cliente.get("/novelas/runs/runs").status_code in (404, 422)


def test_log_con_escritura_entre_stat_y_lectura(
    novelas: Callable[[str], WorkspaceRepository], monkeypatch: pytest.MonkeyPatch
) -> None:
    """VER-5: si el CLI añade una línea entre el stat y la lectura, el tramo no pasa de `tamano`
    y la línea nueva llega en la petición siguiente."""
    ws = novelas("demo-24")
    ruta = f"/novelas/demo-24/runs/{fabrica.run_id(7)}/log"
    real = os.fstat

    def fstat_y_escribir(fd: int) -> os.stat_result:
        resultado = real(fd)
        with _log(ws).open("ab") as log:
            log.write(b"linea tardia\n")
        return resultado

    monkeypatch.setattr(os, "fstat", fstat_y_escribir)
    tramo = cliente.get(ruta).json()
    monkeypatch.setattr(os, "fstat", real)
    assert tramo["hasta"] <= tramo["tamano"]
    siguiente = cliente.get(ruta, params={"desde": tramo["hasta"]}).json()
    assert siguiente["lineas"][-1] == "linea tardia"


class _Contador:
    """Envuelve el fichero abierto y suma los bytes que se leen de él."""

    def __init__(self, fichero: Any, leidos: list[int]) -> None:
        self._fichero, self._leidos = fichero, leidos

    def read(self, *args: Any) -> bytes:
        datos: bytes = self._fichero.read(*args)
        self._leidos.append(len(datos))
        return datos

    def __enter__(self) -> "_Contador":
        return self

    def __exit__(self, *args: object) -> None:
        self._fichero.close()

    def __getattr__(self, nombre: str) -> Any:
        return getattr(self._fichero, nombre)


def test_log_rendimiento(
    novelas: Callable[[str], WorkspaceRepository], monkeypatch: pytest.MonkeyPatch
) -> None:
    """RNF-17: 1 MiB en menos de 200 ms, como mucho 65 536 bytes de líneas por respuesta, y nunca
    más de 1 MiB y el byte anterior leídos del log, tampoco cerca del final de uno de 8 MiB."""
    ws = novelas("demo-24")
    linea = b"x" * 63 + b"\n"
    _run_propio(ws, "r-20990101-0000", log=linea * (1_048_576 // len(linea)))
    grande = linea * (8 * 1_048_576 // len(linea))
    _run_propio(ws, "r-20990101-0001", log=grande)
    leidos: list[int] = []
    abrir = builtins.open

    def espia(fichero: Any, *args: Any, **kwargs: Any) -> Any:
        abierto = abrir(fichero, *args, **kwargs)
        return _Contador(abierto, leidos) if str(fichero).endswith("harness.log") else abierto

    monkeypatch.setattr(builtins, "open", espia)
    ruta = "/novelas/demo-24/runs/r-20990101-0000/log"
    cliente.get(ruta)  # calentamiento: la primera petición importa y compila
    leidos.clear()
    inicio = time.perf_counter()
    tramo = cliente.get(ruta).json()
    assert time.perf_counter() - inicio < 0.2
    assert sum(len(x.encode()) + 1 for x in tramo["lineas"]) <= 65_536
    assert 0 < sum(leidos) <= 1_048_576 + 1

    for desde in (len(grande) - 100, len(grande) - 1_048_576 - 7):
        leidos.clear()
        respuesta = cliente.get("/novelas/demo-24/runs/r-20990101-0001/log?desde=" + str(desde))
        assert respuesta.status_code == 200
        assert 0 < sum(leidos) <= 1_048_576 + 1


def test_get_del_panel_en_solo_lectura(solo_lectura: WorkspaceRepository) -> None:
    """CA-38 (RF-38): los diez GET de la spec 0004 §8.4 responden 200 sobre el workspace montado
    en solo lectura, sin cambiar su huella; POST, PUT, PATCH y DELETE, 405. Los HEAD y OPTIONS
    que Starlette y el CORS responden solos no cuentan (D49)."""
    run = fabrica.run_id(7)
    base = "/novelas/demo-24"
    rutas = [
        "/novelas",
        f"{base}/estado",
        f"{base}/capitulos",
        f"{base}/capitulos/3",
        f"{base}/runs/{run}",
        f"{base}/config",
        f"{base}/escaleta",
        f"{base}/checkpoint",
        f"{base}/runs",
        f"{base}/runs/{run}/log",
    ]
    assert {m for ops in app.openapi()["paths"].values() for m in ops} == {"get"}
    for ruta in rutas:
        assert cliente.get(ruta).status_code == 200, ruta
        for metodo in ("POST", "PUT", "PATCH", "DELETE"):
            assert cliente.request(metodo, ruta).status_code == 405, (metodo, ruta)


def test_estado_sin_tabla_apariciones(novelas: Callable[[str], WorkspaceRepository]) -> None:
    """CA-23 (RF-23) por la API: 200 y el mismo JSON con la tabla y sin ella."""
    ws = novelas("demo-24")
    con = cliente.get("/novelas/demo-24/estado")
    fabrica.quitar_apariciones(ws.raiz)
    sin = cliente.get("/novelas/demo-24/estado")
    assert (con.status_code, sin.status_code) == (200, 200)
    assert sin.json() == con.json()


def _rutas(rutas: list[Any], prefijo: str = "") -> list[str]:
    """Todas, también las que no salen en el OpenAPI (`include_in_schema=False`) y las montadas."""
    caminos = []
    for ruta in rutas:
        camino = prefijo + getattr(ruta, "path", "")
        caminos.append(camino)
        caminos += _rutas(getattr(ruta, "routes", []), camino)
    return caminos


def test_sin_rutas_de_libro() -> None:
    """CA-32 (RF-32), VAL-34: el libro de regalo no se sirve por la API (ADR 0003)."""
    prohibidas = ("libro", "pdf", "ficha", "portada", "apariciones")
    assert [c for c in _rutas(app.routes) if any(p in c for p in prohibidas)] == []

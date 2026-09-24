"""`/lanzamientos`: el panel lanza `novela producir` sin copiar ni pegar. Es la única superficie
de la API que ejecuta algo, así que cada guarda tiene su test: origen, host, cliente, cuerpo,
un lanzamiento a la vez y la raíz del harness. Ningún test lanza un proceso: `lanzar` es falso."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from filelock import FileLock

from api.main import app
from novela.plataforma import lanzador

LOCAL = ("127.0.0.1", 50000)
PANEL = "http://localhost:5173"


class Lanzados(list[list[str]]):
    pass


@pytest.fixture
def lanzados(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Lanzados]:
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    monkeypatch.setattr(lanzador, "raiz_del_harness", lambda: tmp_path)
    registro = Lanzados()
    monkeypatch.setattr(lanzador, "lanzar", registro.append)
    yield registro


def cliente(client: tuple[str, int] = LOCAL, base: str = "http://127.0.0.1:8000") -> TestClient:
    return TestClient(app, base_url=base, client=client)


def crear(c: TestClient | None = None, **cambios: Any) -> Any:
    cuerpo = {"slug": "demo", "idea": "un faro apagado", "capitulos": 3, **cambios}
    return (c or cliente()).post("/lanzamientos", json=cuerpo, headers={"Origin": PANEL})


def test_crear_lanza_producir_con_argumentos_en_lista(lanzados: Lanzados) -> None:
    r = crear()
    assert r.status_code == 202, r.text
    assert lanzados == [["producir", "demo", "--idea", "un faro apagado", "--capitulos", "3"]]
    assert crear(capitulos=None, palabras=80000).status_code == 202
    assert lanzados[1] == ["producir", "demo", "--idea", "un faro apagado", "--palabras", "80000"]


def test_sin_origin_se_admite(lanzados: Lanzados) -> None:
    """curl o un script local no mandan Origin; un navegador siempre lo manda en un POST."""
    assert cliente().post("/lanzamientos", json={"slug": "demo", "idea": "x"}).status_code == 202


@pytest.mark.parametrize(
    "cambios",
    [
        {"slug": "../etc"},
        {"slug": "Demo"},
        {"slug": ""},
        {"idea": ""},
        {"idea": "   \n"},
        {"idea": "a\x00b"},
        {"idea": "x" * 4001},
        {"capitulos": 0},
        {"capitulos": 1000},
        {"palabras": -1},
        {"comando": "rm -rf /"},
    ],
)
def test_cuerpo_invalido_no_lanza(lanzados: Lanzados, cambios: dict[str, Any]) -> None:
    assert crear(**cambios).status_code == 422
    assert lanzados == []


def test_cuerpo_que_no_es_json_no_lanza(lanzados: Lanzados) -> None:
    """Un formulario HTML de otra web no puede mandar JSON sin preflight."""
    r = cliente().post(
        "/lanzamientos",
        content='{"slug": "demo", "idea": "x"}',
        headers={"Content-Type": "text/plain", "Origin": PANEL},
    )
    assert r.status_code == 422
    assert lanzados == []


@pytest.mark.parametrize(
    ("client", "base", "origin"),
    [
        (LOCAL, "http://127.0.0.1:8000", "https://evil.example"),  # CSRF desde otra web
        (LOCAL, "http://127.0.0.1:8000", "null"),  # iframe con sandbox o file://
        (LOCAL, "http://evil.example:8000", PANEL),  # DNS rebinding
        (("192.168.1.20", 50000), "http://127.0.0.1:8000", PANEL),  # otra máquina
    ],
)
def test_guardas_de_origen(
    lanzados: Lanzados, client: tuple[str, int], base: str, origin: str
) -> None:
    c = cliente(client, base)
    cuerpo = {"slug": "demo", "idea": "x"}
    for ruta in ("/lanzamientos", "/lanzamientos/demo/reanudar", "/lanzamientos/demo/detener"):
        r = c.post(ruta, json=cuerpo, headers={"Origin": origin})
        assert r.status_code == 403, (ruta, r.text)
    assert lanzados == []


def test_slug_existente_es_409(lanzados: Lanzados, tmp_path: Path) -> None:
    (tmp_path / "demo").mkdir()
    assert crear().status_code == 409
    assert lanzados == []


def test_uno_a_la_vez(lanzados: Lanzados, tmp_path: Path) -> None:
    cerrojo = FileLock(lanzador.cerrojo())
    with cerrojo:
        r = crear()
        assert r.status_code == 409 and "en marcha" in r.json()["detail"]
    assert lanzados == []


def test_raiz_distinta_del_harness_es_409(
    lanzados: Lanzados, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """El harness trabaja en <repo>/novelas: con otra NOVELAS_DIR el panel lanzaría a ciegas."""
    monkeypatch.setattr(lanzador, "raiz_del_harness", lambda: tmp_path / "otra")
    r = crear()
    assert r.status_code == 409 and "NOVELAS_DIR" in r.json()["detail"]
    assert lanzados == []


def test_reanudar(lanzados: Lanzados, tmp_path: Path) -> None:
    c = cliente()
    assert c.post("/lanzamientos/demo/reanudar").status_code == 404
    (tmp_path / "demo").mkdir()
    assert c.post("/lanzamientos/demo/reanudar").status_code == 202
    assert lanzados == [["producir", "demo"]]


def test_detener_pide_parar_al_proceso_en_marcha(lanzados: Lanzados) -> None:
    c = cliente()
    assert c.post("/lanzamientos/demo/detener").status_code == 409  # nada en marcha
    lanzador.escribir(lanzador.nuevo("demo", "capitulo 02", "escribiendo"))
    with FileLock(lanzador.cerrojo()):
        assert c.post("/lanzamientos/demo/detener").status_code == 202
        assert c.get("/lanzamientos/demo").json()["detener_pedido"] is True


def test_consultar(lanzados: Lanzados) -> None:
    c = cliente()
    assert c.get("/lanzamientos/demo").status_code == 404
    assert c.get("/lanzamientos").json() == []
    lanzador.escribir(lanzador.nuevo("demo", "capitulo 01", "escribiendo"))
    lanzador.registro_de("demo").write_text("una\ndos\n", encoding="utf-8")
    with FileLock(lanzador.cerrojo()):
        r = c.get("/lanzamientos/demo").json()
        assert (r["estado"], r["paso"]) == ("en_marcha", "capitulo 01")
        assert r["registro"] == ["una", "dos"]
    # Sin nadie que sostenga el cerrojo, «en marcha» es mentira: el proceso murió a medias.
    assert c.get("/lanzamientos/demo").json()["estado"] == "interrumpido"
    assert [x["slug"] for x in c.get("/lanzamientos").json()] == ["demo"]


def test_consultar_slug_invalido_es_422(lanzados: Lanzados) -> None:
    assert cliente().get("/lanzamientos/..%2Fetc").status_code == 422


def test_novelas_ignora_el_directorio_del_lanzador(lanzados: Lanzados) -> None:
    lanzador.escribir(lanzador.nuevo("demo", "entorno", "comprobando"))
    assert cliente().get("/novelas").json() == []

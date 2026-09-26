"""`novela portada` (spec 0015 §5.1): la ilustración de Pollinations en `portada.jpg`. Sin red: el
descargador es falso y devuelve lo que se le pide."""

import json
import shutil
import urllib.parse
import zlib
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.dominio.brief import Brief
from novela.dominio.canon import Personaje
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.portada import cmd
from novela.slices.portada.nucleo import prompt, url

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
BRIEF = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "brief" / "brief-completo.json"
Novelas = Callable[[str], WorkspaceRepository]


class Descargador:
    def __init__(self, respuesta: bytes | Exception = JPEG) -> None:
        self.respuesta = respuesta
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


def _prompt_de(url: str) -> str:
    return urllib.parse.unquote(urllib.parse.urlsplit(url).path.removeprefix("/prompt/"))


def test_el_prompt_no_lleva_idea_personajes_ni_brief(novelas: Novelas) -> None:
    """RF-02: la petición sale a un tercero; una novela de regalo lleva datos personales en la
    idea, los personajes y el brief. Solo subgénero y escenarios."""
    ws = novelas("demo-regalo")
    (ws.raiz / "brief").mkdir(exist_ok=True)
    shutil.copy(BRIEF, ws.raiz / "brief" / "brief.json")
    pedir = Descargador()
    assert cmd.generar(ws, pedir=pedir)
    (url,) = pedir.urls
    texto = _prompt_de(url)

    assert ws.config().idea_semilla not in texto
    for ficha in (ws.raiz / "canon" / "personajes").glob("*.md"):
        identidad = ws.leer_md(ficha, Personaje).identidad
        for nombre in (identidad.nombre, *identidad.alias):
            assert all(parte not in texto for parte in nombre.split()), nombre
    brief = Brief.model_validate_json(BRIEF.read_bytes())
    datos = json.loads(BRIEF.read_text(encoding="utf-8"))
    assert brief.destinatario.nombre.valor not in texto
    assert all(r["cita"] not in texto for r in datos["recuerdos"])

    assert "no text" in texto.lower() and "suspense" in texto.lower()
    consulta = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert url.startswith("https://image.pollinations.ai/prompt/")
    assert consulta == {
        "width": ["768"],
        "height": ["1152"],
        "seed": [str(zlib.crc32(b"demo-regalo") & 0x7FFFFFFF)],
        "nologo": ["true"],
    }
    assert (ws.raiz / "portada.jpg").read_bytes() == JPEG


def test_el_prompt_quita_los_nombres_de_las_descripciones() -> None:
    texto = prompt(
        "noir", ["La casa de Elena Vidal, junto al puerto del norte."], ["Elena Vidal", "Nena"]
    )
    assert "Elena" not in texto and "Vidal" not in texto
    assert "puerto del norte" in texto and "noir" in texto


def _cli(
    ws: WorkspaceRepository, monkeypatch: pytest.MonkeyPatch, pedir: Descargador, *args: str
) -> Result:
    monkeypatch.setattr(cmd, "descargar", pedir)
    return CliRunner().invoke(app, ["portada", ws.slug, *args])


def test_solo_escribe_un_jpeg(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-01: una página de error o una red caída salen con 1 y no dejan fichero."""
    ws = novelas("demo-regalo")
    for respuesta in (b"<html>rate limited</html>", OSError("sin red")):
        r = _cli(ws, monkeypatch, Descargador(respuesta))
        assert r.exit_code == 1, r.output
        assert not (ws.raiz / "portada.jpg").exists()
        assert list(ws.raiz.glob("portada*")) == []


def test_sin_forzar_no_pide_nada(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-03: la portada existente se respeta; `--forzar` la sustituye."""
    ws = novelas("demo-regalo")
    (ws.raiz / "portada.jpg").write_bytes(b"\xff\xd8\xff vieja")
    pedir = Descargador()
    assert _cli(ws, monkeypatch, pedir).exit_code == 0
    assert pedir.urls == [] and (ws.raiz / "portada.jpg").read_bytes().endswith(b"vieja")
    assert _cli(ws, monkeypatch, pedir, "--forzar").exit_code == 0
    assert len(pedir.urls) == 1 and (ws.raiz / "portada.jpg").read_bytes() == JPEG


def test_la_semilla_cabe_en_un_entero_con_signo() -> None:
    """Pollinations rechaza semillas por encima de 2^31 - 1 (lo devolvió con un 500 en real para
    este slug, cuyo crc32 pasa de ahí)."""
    consulta = urllib.parse.parse_qs(urllib.parse.urlsplit(url("los-gritos-de-al-lado", "x")).query)
    assert zlib.crc32(b"los-gritos-de-al-lado") > 2**31 - 1
    assert int(consulta["seed"][0]) == zlib.crc32(b"los-gritos-de-al-lado") & 0x7FFFFFFF

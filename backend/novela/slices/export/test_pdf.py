"""Spec 0006: el libro en PDF, verificado siempre leyéndolo con pypdf: que exista no basta."""

import hashlib
import io
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
from pypdf.generic import Destination
from typer.testing import CliRunner, Result

from novela.cli import app
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.export import pdf
from novela.slices.export.ficha import EntradaFicha, Ficha
from tests.fixtures import fabrica

PROHIBIDAS = {"/URI", "/Launch", "/JavaScript", "/SubmitForm", "/GoToR"}


# --- lectura con pypdf, compartida con los tests de CLI -----------------------------------------


def lector(datos: bytes) -> PdfReader:
    return PdfReader(io.BytesIO(datos))


def catalogo(r: PdfReader) -> Any:
    return r.trailer["/Root"]


def marcadores(r: PdfReader) -> list[str]:
    return [o.title for o in r.outline if isinstance(o, Destination) and o.title]


def textos(r: PdfReader) -> list[str]:
    return [p.extract_text() for p in r.pages]


def enlaces(r: PdfReader, pagina: int) -> list[int]:
    """Destino (índice de página) de cada anotación Link de la página, en orden."""
    refs = [p.indirect_reference for p in r.pages]
    destinos = []
    for anotacion in r.pages[pagina].get("/Annots", []):
        a = anotacion.get_object()
        assert a["/Subtype"] == "/Link" and "/A" not in a, a  # solo GoTo interno
        destinos.append(refs.index(a["/Dest"][0]))
    return destinos


def acciones_prohibidas(r: PdfReader) -> list[str]:
    """VAL-38: todos los objetos del documento, no solo las anotaciones de página."""
    vistos: set[int] = set()
    halladas: list[str] = []

    def recorrer(o: Any) -> None:
        o = o.get_object() if hasattr(o, "get_object") else o
        if id(o) in vistos:
            return
        vistos.add(id(o))
        if isinstance(o, dict):
            if o.get("/S") in PROHIBIDAS:
                halladas.append(str(o["/S"]))
            for clave, valor in o.items():
                if clave != "/Parent":
                    recorrer(valor)
        elif isinstance(o, list):
            for valor in o:
                recorrer(valor)

    raiz = catalogo(r)
    recorrer(raiz)
    if isinstance(raiz.get("/OpenAction"), dict):  # un destino ([página /FitH]) no es una acción
        halladas.append("/OpenAction")
    if "/AA" in raiz:
        halladas.append("/AA")
    if "/Names" in raiz and "/JavaScript" in raiz["/Names"]:
        halladas.append("/Names/JavaScript")
    return halladas


def inicio_de(ts: list[str], prefijo: str) -> int:
    [pagina] = [i for i, t in enumerate(ts) if t.startswith(prefijo)]
    return pagina


# --- sobre un Libro en memoria ------------------------------------------------------------------

CREADO = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)


def libro(cuerpos: dict[int, str] | None = None, **cambios: Any) -> pdf.Libro:
    cuerpos = cuerpos or {n: f"# Capítulo {n}\n\nTexto del capítulo {n}.\n" for n in (1, 2, 3)}
    base = pdf.Libro(
        titulo="La luz del cabo",
        idioma="es",
        dedicatoria=None,
        capitulos=tuple(pdf.Capitulo(n, f"Noche {n}", c) for n, c in cuerpos.items()),
        ficha=Ficha(
            personajes=(EntradaFicha("per-a", "Elena Vidal", "la farera", (1, 3)),),
            lugares=(EntradaFicha("esc-a", "El faro", "Un faro en el cabo", (2,)),),
        ),
        creado=CREADO,
    )
    return pdf.Libro(**{**base.__dict__, **cambios})


def test_orden_y_enlaces_en_memoria() -> None:
    """RF-02, RF-03, RF-27: portada, índice, capítulos en página nueva y ficha; cada enlace va a
    la primera página de lo que nombra."""
    r = lector(pdf.construir(libro()))
    ts = textos(r)
    assert ts[0].startswith("La luz del cabo") and ts[1].startswith("Índice")
    paginas = [inicio_de(ts, f"Noche {n}") for n in (1, 2, 3)]
    ficha = inicio_de(ts, "Personajes y lugares")
    assert 1 < paginas[0] < paginas[1] < paginas[2] < ficha == len(ts) - 1
    assert enlaces(r, 1) == [*paginas, ficha]
    assert enlaces(r, ficha) == [paginas[0], paginas[2], paginas[1]]
    assert "Capítulo 1 — Noche 1" in ts[ficha] and "Capítulo 2 — Noche 2" in ts[ficha]


def test_marcadores_idioma_y_metadatos() -> None:
    """RF-04, RNF-08: capítulos + 2 marcadores, /Lang del libro y CreationDate fijada."""
    r = lector(pdf.construir(libro(idioma="en")))
    assert marcadores(r) == [
        "Índice",
        "Noche 1",
        "Noche 2",
        "Noche 3",
        "Personajes y lugares",
    ]
    assert catalogo(r)["/Lang"] == "en"
    assert r.metadata is not None and r.metadata.title == "La luz del cabo"
    assert r.metadata.creation_date == CREADO
    assert "�" not in "".join(textos(r))  # VAL-42: con ToUnicode, el texto se extrae


def test_markdown_inerte_en_memoria() -> None:
    """RF-05, RNF-03, VAL-6, VAL-38, VER-15: se ve el texto y no se crea ningún enlace."""
    cuerpo = (
        "[pulsa](https://ejemplo.invalid) y [x](javascript:alert(1)) y <https://otro.invalid>\n\n"
        "![foto](x.png) *cursiva* **negrita** ***las dos***\n\n"
        "<script>alert(1)</script>\n\n"
        "- uno\n\n> dos\n\n    tres\n\n```\ncuatro\n```\n\nlínea  \ncon salto duro\n\n***\n\nfin\n"
    )
    r = lector(pdf.construir(libro({1: cuerpo}, ficha=Ficha((), ()))))
    texto = "".join(textos(r))
    for visible in (
        "pulsa",
        "foto",
        "<script>alert(1)</script>",
        "cursiva",
        "negrita",
        "las dos",
        "uno",
        "dos",
        "tres",
        "cuatro",
        "con salto duro",
        "* * *",
        "otro.invalid",
    ):
        assert visible in texto, visible
    assert "javascript:" not in texto and "](" not in texto
    assert acciones_prohibidas(r) == []
    assert all(enlaces(r, p) == [] for p in range(2, len(r.pages) - 1))  # capítulos: ninguno


def test_determinista_en_memoria() -> None:
    """RF-07: misma entrada, mismos bytes."""
    assert pdf.construir(libro()) == pdf.construir(libro())


def test_indice_multipagina() -> None:
    """VER-16: con 99 capítulos el índice ocupa varias páginas y los enlaces no se desplazan."""
    cuerpos = {n: "Párrafo.\n" for n in range(1, 100)}
    r = lector(pdf.construir(libro(cuerpos, ficha=Ficha((), ()))))
    ts = textos(r)
    ficha = inicio_de(ts, "Personajes y lugares")
    indice = list(range(1, inicio_de(ts, "Noche 1\n")))
    assert len(indice) >= 2
    destinos = [d for p in indice for d in enlaces(r, p)]
    assert destinos == [inicio_de(ts, f"Noche {n}\n") for n in range(1, 100)] + [ficha]


@pytest.mark.parametrize(
    ("cambios", "seccion"),
    [
        ({"titulo": "Faro \U0001f56f"}, "portada"),
        ({"dedicatoria": "Para \U0001f56f"}, "portada"),
        ({"capitulos": (pdf.Capitulo(3, "Noche 3", "Luz \U0001f56f"),)}, "capítulo 3"),
        (
            {"ficha": Ficha((EntradaFicha("per-a", "Inés \U0001f56f Mar", None, (1,)),), ())},
            "ficha",
        ),
    ],
)
def test_glifo_ausente(cambios: dict[str, Any], seccion: str) -> None:
    """RF-09, VAL-10: nombra la sección y el código."""
    with pytest.raises(pdf.GlifoAusente) as exc:
        pdf.construir(libro(**cambios))
    assert (exc.value.seccion, exc.value.codigo) == (seccion, "U+1F56F")


def test_glifos_sin_falsos_positivos() -> None:
    """VER-17: saltos, tabuladores, espacio duro y «é» descompuesta no son glifos ausentes, y los
    textos fijos están en la fuente."""
    dedicatoria = "Para Aurora Ficticia,\nque siempre leyó primero el final."
    cuerpo = "Tab\taquí, duro aquí, y café.\n"
    r = lector(pdf.construir(libro({1: cuerpo}, dedicatoria=dedicatoria, ficha=Ficha((), ()))))
    assert "café" in textos(r)[2]
    cmap = pdf._cmap(pdf.FUENTES)
    assert {0x2014, 0x00CD, 0x00BF, 0x00AB, 0x00BB, 0x2026, 0x00A1} <= cmap
    assert 0x1F56F not in cmap  # VER-11: si la fuente lo tuviera, CA-09 no probaría nada


def test_dedicatoria_con_saltos_solo_en_portada() -> None:
    """RF-11, VAL-12: literal, con sus saltos de línea, y en ninguna otra página."""
    r = lector(
        pdf.construir(
            libro(dedicatoria="Para Aurora Ficticia,\nque siempre leyó primero el final.")
        )
    )
    ts = textos(r)
    lineas = ts[0].splitlines()
    i = lineas.index("Para Aurora Ficticia,")
    assert lineas[i + 1] == "que siempre leyó primero el final."
    assert all("Aurora" not in t for t in ts[1:])
    larga = "a" * 599 + "."
    ts = textos(lector(pdf.construir(libro(dedicatoria=larga))))
    assert re.sub(r"\s", "", ts[0]).endswith(larga) and ts[1].startswith("Índice")


def test_fuente_en_subconjunto() -> None:
    """RNF-02, VAL-37: cada fuente embebida lleva prefijo de subconjunto."""
    r = lector(pdf.construir(libro()))
    recursos: list[Any] = [p["/Resources"] for p in r.pages]
    fuentes = {f.get_object()["/BaseFont"] for rec in recursos for f in rec["/Font"].values()}
    assert fuentes and all(re.fullmatch(r"/[A-Z]{6}\+DejaVuSerif.*", f) for f in fuentes), fuentes


def sha(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


# --- novela exportar --formato pdf --------------------------------------------------------------

Novelas = Callable[[str], WorkspaceRepository]
SIN_BRIEF = "sin dedicatoria: el workspace no tiene brief/brief.json"
SECRETOS = (
    "apagó el faro a mano",
    "cofradía",
    "Vio luz en el cabo",
    "protagonista",
    "antagonista",
    "testigo",
    "el hermano",
    "olor a sal",
)


def exportar(ws: WorkspaceRepository, *extra: str, formato: str = "pdf") -> Result:
    return CliRunner().invoke(app, ["exportar", ws.slug, "--formato", formato, *extra])


def libro_de(ws: WorkspaceRepository) -> PdfReader:
    return lector((ws.raiz / "export" / "novela.pdf").read_bytes())


def sin_pdf(ws: WorkspaceRepository) -> bool:
    return not (ws.raiz / "export" / "novela.pdf").exists()


def cuerpo_extra(ws: WorkspaceRepository, n: int, texto: str) -> None:
    ruta = ws.raiz / "capitulos" / f"{n:02d}.md"
    ruta.write_text(ruta.read_text(encoding="utf-8") + texto, encoding="utf-8")


def aplicar_sin_cerrar(ws: WorkspaceRepository, n: int, cerrar: bool = False) -> None:
    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, n)
    for orden in ("aplicar-delta", "checkpoint")[: 2 if cerrar else 1]:
        resultado = fabrica.cli(ws.raiz.parent, orden, ws.slug, str(n), run=fabrica.run_id(n))
        assert resultado.exit_code == 0, resultado.output


def test_pdf_escrito(novelas: Novelas) -> None:
    """CA-01 (RF-01), VAL-1: 0, el resumen exacto, pypdf lo abre y no queda ningún .tmp."""
    ws = novelas("demo-regalo")
    resultado = exportar(ws)
    assert resultado.exit_code == 0, resultado.output
    assert resultado.stdout == f"{SIN_BRIEF}\nexportar: 3 capítulos en export/novela.pdf\n"
    assert len(libro_de(ws).pages) > 5
    assert [f.name for f in (ws.raiz / "export").iterdir()] == ["novela.pdf"]


def test_solo_capitulos_cerrados(novelas: Novelas) -> None:
    """VAL-1, VAL-27 (c), VAL-28: un capítulo aplicado y sin checkpoint no entra en el libro."""
    ws = novelas("demo-24")
    aplicar_sin_cerrar(ws, 8)
    resultado = exportar(ws)
    assert resultado.exit_code == 0, resultado.output
    assert "exportar: 7 capítulos" in resultado.stdout
    texto = "".join(textos(libro_de(ws)))
    assert (
        "La linterna, noche 7" in texto and "noche 8" not in texto and "Capítulo 8 —" not in texto
    )


def test_escritura_atomica(novelas: Novelas, monkeypatch: pytest.MonkeyPatch) -> None:
    """VAL-1: si el renombrado falla, ni PDF ni .tmp."""
    ws = novelas("demo-regalo")

    def falla(*_: object) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr(os, "replace", falla)
    assert exportar(ws).exit_code != 0
    assert list((ws.raiz / "export").glob("*")) == []


def test_lock_ocupado(
    novelas: Novelas, lock_ajeno: Callable[[Path], AbstractContextManager[None]]
) -> None:
    """VAL-2: con el lock tomado, 3 sin escribir."""
    ws = novelas("demo-regalo")
    with lock_ajeno(ws.lock):
        assert exportar(ws).exit_code == 3
    assert sin_pdf(ws)


def test_orden_de_secciones(novelas: Novelas) -> None:
    """CA-02 (RF-02), VAL-3."""
    ws = novelas("demo-regalo")
    assert exportar(ws).exit_code == 0
    ts = textos(libro_de(ws))
    assert ts[0].startswith("demo-regalo") and ts[1].startswith("Índice")
    paginas = [inicio_de(ts, f"La linterna, noche {n}") for n in (1, 2, 3)]
    assert 1 < paginas[0] < paginas[1] < paginas[2] < inicio_de(ts, "Personajes y lugares")
    assert ts[-1].startswith("Personajes y lugares") or "Personajes y lugares" not in ts[-1]


def test_indice_enlaza(novelas: Novelas) -> None:
    """CA-03 (RF-03), VAL-4: 4 enlaces, a los tres capítulos y a la ficha; el índice lleva el
    título del frontmatter, no el encabezado del cuerpo."""
    ws = novelas("demo-regalo")
    ruta = ws.raiz / "capitulos" / "02.md"
    texto = ruta.read_text(encoding="utf-8")
    ruta.write_text(texto.replace("titulo: La linterna, noche 2", "titulo: Marea baja"), "utf-8")
    assert exportar(ws).exit_code == 0
    r = libro_de(ws)
    ts = textos(r)
    capitulos = [
        inicio_de(ts, t) for t in ("La linterna, noche 1", "Marea baja", "La linterna, noche 3")
    ]
    assert enlaces(r, 1) == [*capitulos, inicio_de(ts, "Personajes y lugares")]
    assert "2. Marea baja" in ts[1]


def test_marcadores_e_idioma(novelas: Novelas) -> None:
    """CA-04 (RF-04), VAL-5: los marcadores y /Lang salen de config.yaml, no fijos en código."""
    ws = novelas("demo-regalo")
    assert exportar(ws).exit_code == 0
    r = libro_de(ws)
    titulos = [f"La linterna, noche {n}" for n in (1, 2, 3)]
    assert marcadores(r) == ["Índice", *titulos, "Personajes y lugares"]
    assert catalogo(r)["/Lang"] == "es"
    texto = ws.config_yaml.read_text(encoding="utf-8")
    assert "idioma: es" in texto
    ws.config_yaml.write_text(texto.replace("idioma: es", "idioma: en"), encoding="utf-8")
    assert exportar(ws).exit_code == 0
    assert catalogo(libro_de(ws))["/Lang"] == "en"


def test_markdown_inerte(novelas: Novelas) -> None:
    """CA-05 (RF-05), VAL-6, VAL-38."""
    ws = novelas("demo-regalo")
    cuerpo_extra(
        ws,
        2,
        "\n[pulsa](https://ejemplo.invalid) ![foto](x.png) *cursiva* [x](javascript:alert(1))"
        "\n\n<script>alert(1)</script>\n",
    )
    assert exportar(ws).exit_code == 0
    r = libro_de(ws)
    texto = "".join(textos(r))
    for visible in ("pulsa", "foto", "<script>alert(1)</script>", "cursiva"):
        assert visible in texto, visible
    assert "javascript:" not in texto
    assert acciones_prohibidas(r) == []


def test_sin_checkpoint(novelas: Novelas, tmp_path: Path) -> None:
    """CA-06 (RF-06), VAL-7: también con un --titulo válido."""
    novelas("demo-regalo")  # fija NOVELAS_DIR en tmp_path
    creada = fabrica.cli(tmp_path, "nueva", "recien", "--idea", "Un faro.", run=fabrica.run_id(1))
    assert creada.exit_code == 0, creada.output
    ws = WorkspaceRepository(tmp_path / "recien")
    for extra in ((), ("--titulo", "La luz del cabo")):
        resultado = exportar(ws, *extra)
        assert resultado.exit_code == 1
        assert "no hay capítulos cerrados que exportar" in resultado.output
        assert sin_pdf(ws)


def test_determinista(novelas: Novelas) -> None:
    """CA-07 (RF-07), VAL-8, VER-18: mismo sha256 en dos procesos con distinto PYTHONHASHSEED, y
    CreationDate es el `creado` del manifiesto del último checkpoint."""
    ws = novelas("demo-regalo")
    shas = []
    for semilla in ("1", "2"):
        entorno = os.environ | {"PYTHONHASHSEED": semilla, "NOVELAS_DIR": str(ws.raiz.parent)}
        orden = [sys.executable, "-c", "from novela.cli import app; app()", "exportar", ws.slug]
        proceso = subprocess.run(  # noqa: S603
            [*orden, "--formato", "pdf"], env=entorno, capture_output=True, check=False
        )
        assert proceso.returncode == 0, proceso.stderr
        shas.append(sha((ws.raiz / "export" / "novela.pdf").read_bytes()))
    assert shas[0] == shas[1]
    punto = ws.ultimo_checkpoint()
    assert punto is not None
    [manifiesto] = [m for m in ws.manifiestos() if m.run_id == punto.run_id]
    metadatos = libro_de(ws).metadata
    assert metadatos is not None
    assert metadatos.creation_date == datetime.fromisoformat(manifiesto.creado)


def test_sin_manifiesto(novelas: Novelas) -> None:
    """VER-18: sin el manifiesto del último checkpoint no hay fecha: 4 y sin PDF."""
    ws = novelas("demo-regalo")
    punto = ws.ultimo_checkpoint()
    assert punto is not None
    (ws.raiz / "runs" / punto.run_id / "manifest.json").unlink()
    assert exportar(ws).exit_code == 4
    assert sin_pdf(ws)


@pytest.mark.parametrize(
    ("titulo", "codigo", "portada"),
    [
        (None, 0, "demo-regalo"),
        ("La luz del cabo", 0, "La luz del cabo"),
        ("a" * 120, 0, "a" * 120),
        ("a" * 121, 2, None),
        ("   ", 2, None),
    ],
)
def test_titulo(novelas: Novelas, titulo: str | None, codigo: int, portada: str | None) -> None:
    """CA-08 (RF-08), VAL-9."""
    ws = novelas("demo-regalo")
    resultado = exportar(ws, *(() if titulo is None else ("--titulo", titulo)))
    assert resultado.exit_code == codigo, resultado.output
    if portada is None:
        assert sin_pdf(ws)
        return
    r = libro_de(ws)
    assert re.sub(r"\s", "", textos(r)[0]) == portada.replace(" ", "")
    assert r.metadata is not None and r.metadata.title == portada


def test_glifo_ausente_cli(novelas: Novelas) -> None:
    """CA-09 (RF-09), VAL-10: nombra la sección y el código, y no escribe."""
    ws = novelas("demo-regalo")
    cuerpo_extra(ws, 3, "\nUna vela \U0001f56f encendida.\n")
    resultado = exportar(ws)
    assert resultado.exit_code == 1
    assert "capítulo 3" in resultado.output and "U+1F56F" in resultado.output
    assert sin_pdf(ws)
    otra = novelas("demo-huerfana")
    resultado = exportar(otra, "--titulo", "Faro \U0001f56f")
    assert resultado.exit_code == 1 and "portada" in resultado.output
    assert sin_pdf(otra)


def test_md_y_epub_ignoran_titulo(novelas: Novelas) -> None:
    """VAL-11: --titulo solo afecta a pdf; con md y epub ni se valida."""
    ws = novelas("demo-huerfana")
    assert exportar(ws, "--titulo", "   ", formato="epub").exit_code == 0
    assert exportar(ws, "--titulo", "La luz del cabo", formato="md").exit_code == 0


def test_sin_brief(novelas: Novelas) -> None:
    """CA-12 (RF-12), VAL-13, RNF-01: demo-terminado sin brief/, en menos de 10 s."""
    ws = novelas("demo-terminado")
    inicio = time.perf_counter()
    resultado = exportar(ws)
    assert time.perf_counter() - inicio < 10
    assert resultado.exit_code == 0, resultado.output
    assert resultado.stdout.splitlines() == [
        SIN_BRIEF,
        "exportar: 24 capítulos en export/novela.pdf",
    ]
    assert textos(libro_de(ws))[0].strip() == "demo-terminado"


def test_enlaces_resuelven_a_escala(novelas: Novelas) -> None:
    """VAL-39: con 24 capítulos, cada enlace del índice y de la ficha va a la página cuyo texto
    empieza por el capítulo que nombra."""
    ws = novelas("demo-terminado")
    assert exportar(ws).exit_code == 0
    r = libro_de(ws)
    ts = textos(r)
    ficha = inicio_de(ts, "Personajes y lugares")
    for pagina in range(1, inicio_de(ts, "La linterna, noche 1\n")):
        for destino, n in zip(enlaces(r, pagina), range(1, 25), strict=False):
            assert ts[destino].startswith(f"La linterna, noche {n}\n"), (pagina, n)
    nombrados = [
        int(m[1]) for p in range(ficha, len(ts)) for m in re.finditer(r"Capítulo (\d+) —", ts[p])
    ]
    destinos = [d for p in range(ficha, len(ts)) for d in enlaces(r, p)]
    assert len(destinos) == len(nombrados) > 24
    for destino, n in zip(destinos, nombrados, strict=True):
        assert ts[destino].startswith(f"La linterna, noche {n}\n")


def test_tamano_y_tiempo_con_capitulos_largos(novelas: Novelas) -> None:
    """RNF-01, RNF-02: 1.500 palabras por capítulo, < 10 s y ≤ 5 MB."""
    ws = novelas("demo-terminado")
    for n in range(1, 25):
        cuerpo_extra(ws, n, "\n" + " ".join(["Elena miró el mar desde la linterna."] * 200) + "\n")
    inicio = time.perf_counter()
    assert exportar(ws).exit_code == 0
    assert time.perf_counter() - inicio < 10
    assert (ws.raiz / "export" / "novela.pdf").stat().st_size <= 5 * 1024 * 1024


def test_workspace_sin_apariciones(novelas: Novelas) -> None:
    """CA-25 (RF-25), VAL-27: capítulos cerrados sin filas, o sin tabla, dan 4 y los nombran; md
    sigue funcionando."""
    ws = novelas("demo-24")
    fabrica.quitar_apariciones(ws.raiz)
    resultado = exportar(ws)
    assert resultado.exit_code == 4 and "apariciones" in resultado.output
    aplicar_sin_cerrar(ws, 8, cerrar=True)
    resultado = exportar(ws)
    assert resultado.exit_code == 4
    assert "1, 2, 3, 4, 5, 6, 7" in resultado.output and "8" not in resultado.output.split(":")[-1]
    assert sin_pdf(ws)
    assert exportar(ws, formato="md").exit_code == 0  # VER-19: el lock no queda tomado


def test_ficha_desde_canon(novelas: Novelas) -> None:
    """CA-26 (RF-26), VAL-28: nombre y descripción de cada lugar; sin apariciones, no sale."""
    ws = novelas("demo-regalo")
    assert exportar(ws).exit_code == 0
    ts = textos(libro_de(ws))
    ficha = "".join(ts[inicio_de(ts, "Personajes y lugares") :])
    for nombre in ("Elena Vidal", "Tomás Reyes", "Inés Mar", "La casa del faro", "El puerto"):
        assert nombre in ficha, nombre
    assert "El archivo" in ficha and "El archivo en la novela sintética" in ficha
    otro = novelas("demo-huerfana")
    assert exportar(otro).exit_code == 0
    ts = textos(libro_de(otro))
    assert "El archivo" not in "".join(ts[inicio_de(ts, "Personajes y lugares") :])


def test_ficha_enlaces_resuelven(novelas: Novelas) -> None:
    """CA-27 (RF-27), VAL-29: 15 enlaces, «Capítulo N — título» sin ceros, ascendentes por
    entrada, cada uno a la primera página del capítulo N."""
    ws = novelas("demo-regalo")
    assert exportar(ws).exit_code == 0
    r = libro_de(ws)
    ts = textos(r)
    paginas = range(inicio_de(ts, "Personajes y lugares"), len(ts))
    lineas = [ln for p in paginas for ln in ts[p].splitlines() if ln.startswith("Capítulo")]
    destinos = [d for p in paginas for d in enlaces(r, p)]
    assert len(lineas) == len(destinos) == 15
    for linea, destino in zip(lineas, destinos, strict=True):
        m = re.fullmatch(r"Capítulo ([1-9][0-9]*) — La linterna, noche ([1-9][0-9]*)", linea)
        assert m and m[1] == m[2], linea
        assert ts[destino].startswith(f"La linterna, noche {m[1]}\n")


def test_sin_secreto(novelas: Novelas) -> None:
    """CA-28 (RF-28), VAL-30, VAL-40: no abre el misterio, el resultado no depende de él, y ni
    el texto, ni los metadatos ni los marcadores llevan nada del secreto."""
    ws = novelas("demo-regalo")
    abiertos: list[str] = []
    escuchando = [True]

    def auditar(evento: str, args: tuple[Any, ...]) -> None:
        if escuchando[0] and evento == "open" and args and isinstance(args[0], (str, Path)):
            abiertos.append(str(args[0]))

    sys.addaudithook(auditar)  # no se puede quitar: se apaga con la bandera
    try:
        assert exportar(ws).exit_code == 0
    finally:
        escuchando[0] = False
    assert not [a for a in abiertos if a.endswith("misterio.md")]
    primero = sha((ws.raiz / "export" / "novela.pdf").read_bytes())
    r = libro_de(ws)
    todo = "".join(textos(r)) + str(r.metadata) + "".join(marcadores(r))
    for secreto in SECRETOS:
        assert secreto not in todo, secreto
    (ws.raiz / "canon" / "misterio.md").rename(ws.raiz / "canon" / "misterio.oculto")
    assert exportar(ws).exit_code == 0
    assert sha((ws.raiz / "export" / "novela.pdf").read_bytes()) == primero


def test_entidad_sin_canon(novelas: Novelas) -> None:
    """CA-29 (RF-29), VER-14, VAL-21: nombra todos los ids sin canon, personajes o lugares."""
    ws = novelas("demo-regalo")
    for id_ in (fabrica.INES, fabrica.TOMAS):
        (ws.raiz / "canon" / "personajes" / f"{id_}.md").unlink()
    resultado = exportar(ws)
    assert resultado.exit_code == 4
    assert fabrica.INES in resultado.output and fabrica.TOMAS in resultado.output
    assert sin_pdf(ws)
    otro = novelas("demo-huerfana")
    mundo = otro.raiz / "canon" / "mundo.md"
    texto = mundo.read_text(encoding="utf-8")
    mundo.write_text(texto.replace(f"id: {fabrica.PUERTO}", "id: esc-otro-puerto"), "utf-8")
    resultado = exportar(otro)
    assert resultado.exit_code == 4 and fabrica.PUERTO in resultado.output
    assert sin_pdf(otro)

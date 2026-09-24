"""El libro de regalo en PDF con fpdf2 (spec 0006, ADR 0003): función pura, datos → bytes.

Portada, índice, un capítulo por página nueva y la ficha, con enlaces internos y marcadores. El
markdown se compone desde los tokens y nunca se crea un enlace desde el cuerpo: el libro no abre
nada fuera de sí mismo (RF-05, RNF-03). Es la única frontera con fpdf2.
"""

import functools
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import fpdf
from fontTools.ttLib import TTFont
from markdown_it import MarkdownIt
from markdown_it.token import Token

from novela.dominio.ficha import EntradaFicha, Ficha

FUENTES = Path(__file__).parent / "fuentes"
_VARIANTES = {"": "DejaVuSerif", "B": "DejaVuSerif-Bold", "I": "DejaVuSerif-Italic"}
_VARIANTES["BI"] = "DejaVuSerif-BoldItalic"
ALTO = 6.0  # interlineado del cuerpo, en mm
FIJOS = (
    "Novedades de la versión",
    "Índice",
    "Personajes y lugares",
    "Personajes",
    "Lugares",
    "Aparece en:",
    "Capítulo —",
)
SEPARADOR = "* * *"


@dataclass(frozen=True)
class Capitulo:
    numero: int
    titulo: str  # el del frontmatter
    cuerpo: str  # markdown sin frontmatter


@dataclass(frozen=True)
class Libro:
    titulo: str
    idioma: str
    dedicatoria: str | None
    capitulos: tuple[Capitulo, ...]
    ficha: Ficha
    creado: datetime  # CreationDate: el manifiesto del último checkpoint, para ser determinista
    version: int = 1  # spec 0007, RF-40: con novedades, página tras la portada
    novedades: tuple[int, ...] = ()  # capítulos cambiados respecto a la versión anterior


class GlifoAusente(ValueError):
    """Un carácter que la fuente embebida no tiene: saldría como una caja vacía. Salida 1."""

    def __init__(self, seccion: str, codigo: str) -> None:
        super().__init__(f"{seccion}: la fuente no tiene el carácter {codigo}")
        self.seccion, self.codigo = seccion, codigo


# --- markdown → bloques -------------------------------------------------------------------------

Tramo = tuple[str, str]  # (texto, estilo de fpdf: "", "B", "I" o "BI")


@dataclass(frozen=True)
class Bloque:
    tipo: Literal["encabezado", "parrafo", "separador"]
    tramos: tuple[Tramo, ...] = ()


def _md() -> MarkdownIt:
    md = MarkdownIt("commonmark")
    # Sin validar esquemas: un enlace `javascript:` se reconoce como enlace y se muestra su texto,
    # en vez de quedar como sintaxis cruda. Nunca se convierte en anotación.
    md.validateLink = lambda url: True  # type: ignore[method-assign]
    return md


def _tramos(hijos: Iterable[Token]) -> Iterator[Tramo]:
    negrita = cursiva = 0
    for t in hijos:
        estilo = ("B" if negrita else "") + ("I" if cursiva else "")
        if t.type in ("text", "code_inline", "html_inline", "image"):  # image: su texto alternativo
            yield t.content, estilo
        elif t.type in ("softbreak", "hardbreak"):
            yield (" " if t.type == "softbreak" else "\n"), estilo
        elif t.type in ("strong_open", "strong_close"):
            negrita += 1 if t.type == "strong_open" else -1
        elif t.type in ("em_open", "em_close"):
            cursiva += 1 if t.type == "em_open" else -1
        # link_open y link_close se ignoran: queda el texto, sin enlace


def bloques(cuerpo: str) -> list[Bloque]:
    """Lista blanca de lo que se compone; lo demás (listas, citas, código, HTML) pasa como párrafo
    con su texto literal: nada del capítulo se pierde."""
    resultado: list[Bloque] = []
    encabezado = False
    for t in _md().parse(cuerpo):
        if t.type == "heading_open":
            encabezado = True
        elif t.type == "inline":
            tipo: Literal["encabezado", "parrafo"] = "encabezado" if encabezado else "parrafo"
            resultado.append(Bloque(tipo, tuple(_tramos(t.children or []))))
            encabezado = False
        elif t.type == "hr":
            resultado.append(Bloque("separador"))
        elif t.type in ("fence", "code_block", "html_block"):
            resultado.append(Bloque("parrafo", ((t.content.rstrip("\n"), ""),)))
    return resultado


# --- glifos -------------------------------------------------------------------------------------


@functools.cache
def _cmap(fuentes: Path) -> frozenset[int]:
    """Lo que tienen las cuatro variantes: un carácter que falte en una sale en blanco en ella."""
    mapas = [set(TTFont(fuentes / f"{v}.ttf").getBestCmap()) for v in _VARIANTES.values()]
    return frozenset(set.intersection(*mapas))


def _comprobar(seccion: str, texto: str, cmap: frozenset[int]) -> None:
    for ch in texto:
        if ord(ch) not in cmap and unicodedata.category(ch)[0] != "C":  # controles: \n, \t
            raise GlifoAusente(seccion, f"U+{ord(ch):04X}")


def _entradas(ficha: Ficha) -> tuple[EntradaFicha, ...]:
    return (*ficha.personajes, *ficha.lugares)


def _nfc(libro: Libro) -> Libro:
    """Una «é» descompuesta (e + U+0301) es la misma letra; así la fuente la tiene entera."""

    def n(s: str) -> str:
        return unicodedata.normalize("NFC", s)

    def entrada(e: EntradaFicha) -> EntradaFicha:
        return EntradaFicha(
            e.id, n(e.nombre), None if e.detalle is None else n(e.detalle), e.capitulos
        )

    return Libro(
        titulo=n(libro.titulo),
        idioma=libro.idioma,
        dedicatoria=None if libro.dedicatoria is None else n(libro.dedicatoria),
        capitulos=tuple(Capitulo(c.numero, n(c.titulo), n(c.cuerpo)) for c in libro.capitulos),
        ficha=Ficha(
            tuple(entrada(e) for e in libro.ficha.personajes),
            tuple(entrada(e) for e in libro.ficha.lugares),
        ),
        creado=libro.creado,
        version=libro.version,
        novedades=libro.novedades,
    )


def comprobar_glifos(libro: Libro, fuentes: Path = FUENTES) -> None:
    """Antes de componer: RF-09 pide nombrar la sección y el código, y no escribir nada."""
    cmap = _cmap(fuentes)
    _comprobar("portada", libro.titulo + (libro.dedicatoria or ""), cmap)
    for c in libro.capitulos:
        _comprobar(f"capítulo {c.numero}", c.titulo + c.cuerpo, cmap)
    for e in _entradas(libro.ficha):
        _comprobar("ficha", e.nombre + (e.detalle or ""), cmap)
    _comprobar("ficha", "".join(FIJOS) + SEPARADOR, cmap)


# --- composición --------------------------------------------------------------------------------


def construir(libro: Libro, fuentes: Path = FUENTES) -> bytes:
    libro = _nfc(libro)
    comprobar_glifos(libro, fuentes)
    pdf = fpdf.FPDF(format=(148, 210))  # A5
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(True, margin=18)
    for estilo, nombre in _VARIANTES.items():
        pdf.add_font("serif", estilo, fuentes / f"{nombre}.ttf")
    pdf.set_lang(libro.idioma)
    pdf.set_title(libro.titulo)
    pdf.set_producer(f"novela, fpdf2 {fpdf.FPDF_VERSION}")
    pdf.set_creation_date(libro.creado)
    titulos = {c.numero: c.titulo for c in libro.capitulos}

    def texto(
        t: str,
        estilo: str = "",
        tam: float = 11,
        alto: float = ALTO,
        align: str = "L",
        link: int | None = None,
    ) -> None:
        pdf.set_font("serif", estilo, tam)
        if link is None:
            pdf.multi_cell(0, alto, t, align=align, new_x="LMARGIN", new_y="NEXT")
        else:  # write admite enlaces hacia delante; multi_cell exige ya la página de destino
            pdf.write(alto, t, link=link)
            pdf.ln(alto)

    # Portada. Los enlaces se crean después: fpdf2 les da la página en curso hasta set_link.
    pdf.add_page()
    enlaces = {c.numero: pdf.add_link() for c in libro.capitulos}
    enlace_ficha = pdf.add_link()
    pdf.set_y(60)
    texto(libro.titulo, "B", 20, 10, align="C")
    if libro.dedicatoria is not None:
        pdf.ln(12)
        texto(libro.dedicatoria, "I", 12, 7, align="C")

    if libro.novedades:
        pdf.add_page()
        cabecera = f"Novedades de la versión {libro.version}"
        pdf.start_section(cabecera)
        texto(cabecera, "B", 16, 10)
        pdf.ln(4)
        for n in libro.novedades:
            texto(f"Capítulo {n} — {titulos[n]}", link=enlaces[n])

    # Índice
    pdf.add_page()
    pdf.start_section("Índice")
    texto("Índice", "B", 16, 10)
    pdf.ln(4)
    for c in libro.capitulos:
        texto(f"{c.numero}. {c.titulo}", link=enlaces[c.numero])
    texto("Personajes y lugares", link=enlace_ficha)

    # Capítulos
    for c in libro.capitulos:
        pdf.add_page()
        pdf.set_link(enlaces[c.numero], page=pdf.page)
        pdf.start_section(c.titulo)
        texto(c.titulo, "B", 16, 10)
        pdf.ln(4)
        for b in bloques(c.cuerpo):
            if b.tipo == "separador":
                texto(SEPARADOR, align="C")
            else:
                for t, estilo in b.tramos:
                    b_estilo = "B" + estilo.replace("B", "") if b.tipo == "encabezado" else estilo
                    pdf.set_font("serif", b_estilo, 13 if b.tipo == "encabezado" else 11)
                    pdf.write(ALTO, t)
                pdf.ln(ALTO)
            pdf.ln(2)

    # Ficha
    pdf.add_page()
    pdf.set_link(enlace_ficha, page=pdf.page)
    pdf.start_section("Personajes y lugares")
    texto("Personajes y lugares", "B", 16, 10)
    for grupo, entradas in (
        ("Personajes", libro.ficha.personajes),
        ("Lugares", libro.ficha.lugares),
    ):
        if not entradas:
            continue
        pdf.ln(4)
        texto(grupo, "B", 13, 8)
        for e in entradas:
            pdf.ln(2)
            texto(e.nombre, "B")
            if e.detalle:
                texto(e.detalle, "I")
            texto("Aparece en:")
            for n in e.capitulos:
                texto(f"Capítulo {n} — {titulos[n]}", link=enlaces[n])
    return bytes(pdf.output())

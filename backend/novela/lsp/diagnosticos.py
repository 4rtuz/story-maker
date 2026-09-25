"""Diagnósticos LSP de un capítulo editado a mano (docs/lsp.md).

Solo lee: el workspace, `estado.db` con `mode=ro` y las listas del guardrail. Cada comprobación es
la de su gate (`buscar`, `gates.erratas`, la regla RF-33 de las citas y `lint-prosa`); aquí solo
se traducen sus hallazgos a rangos del documento, con el frontmatter incluido.
"""

import unicodedata
from pathlib import Path

from lsprotocol import types

from novela.dominio import frontmatter
from novela.dominio.prohibidas import buscar
from novela.dominio.texto import normalizar
from novela.plataforma import estado_db, policy_db
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.prosa import cmd as prosa
from novela.slices.prosa.reglas import analizar, parrafos
from novela.slices.validacion import cmd as validacion
from novela.slices.validacion import gates

_ERROR = types.DiagnosticSeverity.Error
_AVISO = types.DiagnosticSeverity.Warning
_INFO = types.DiagnosticSeverity.Information


def capitulo_de(ruta: Path) -> tuple[WorkspaceRepository, int] | None:
    """`<novelas>/<slug>/capitulos/NN.md` de un workspace existente; si no, None."""
    if ruta.parent.name != "capitulos" or not ruta.stem.isdigit() or ruta.suffix != ".md":
        return None
    ws = WorkspaceRepository(ruta.parent.parent)
    return (ws, int(ruta.stem)) if ws.existe() else None


def _diag(
    codigo: str,
    mensaje: str,
    severidad: types.DiagnosticSeverity,
    desde: tuple[int, int],
    hasta: tuple[int, int],
) -> types.Diagnostic:
    return types.Diagnostic(
        range=types.Range(types.Position(*desde), types.Position(*hasta)),
        message=mensaje,
        severity=severidad,
        code=codigo,
        source="novela",
    )


def _lineas_de_parrafos(cuerpo: str) -> list[int]:
    """Línea (desde 0) donde empieza cada párrafo de `parrafos`, en su orden."""
    inicios, pos = [], 0
    for bloque in parrafos(cuerpo):
        pos = cuerpo.find(bloque, pos)
        inicios.append(cuerpo.count("\n", 0, pos))
        pos += len(bloque)
    return inicios


def diagnosticar(ruta: Path, texto: str) -> list[types.Diagnostic]:
    """Los diagnósticos de `texto`, el contenido editado de `ruta`, que puede no estar guardado.

    ponytail: las columnas son las del texto en NFC y en unidades de Python; coinciden con las
    UTF-16 del protocolo para el español (plano básico) y un fichero ya en NFC. Si un editor manda
    NFD o emojis, habría que mapear offsets."""
    capitulo = capitulo_de(ruta)
    if capitulo is None:
        return []
    ws, n = capitulo
    try:
        cuerpo = frontmatter.partir(texto)[1]
    except ValueError:
        cuerpo = texto
    base = texto[: len(texto) - len(cuerpo)].count("\n")  # líneas del frontmatter

    diags = [
        _diag(
            "termino_prohibido",
            f"«{c.forma}» es el término prohibido «{c.termino.texto}» ({c.termino.nivel})",
            _ERROR,
            (base + c.linea - 1, c.columna),
            (base + c.fin[0] - 1, c.fin[1]),
        )
        for c in buscar(cuerpo, policy_db.prohibidos(ws))
    ]
    diags += [
        _diag(
            "nombre_mal_escrito",
            f"«{e.token}» no es la grafía de {e.referencia}: «{e.canonico}»",
            _ERROR,
            (base + e.linea - 1, e.columna),
            (base + e.linea - 1, e.columna + len(e.token)),
        )
        for e in gates.erratas(cuerpo, validacion.formas(ws))
    ]

    # RF-33: la cita de un hecho es literal del capítulo; si la edición la quita, cambia el hecho.
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        hechos = [h for h in estado_db.leer(conn).libro_de_hechos if h.capitulo == n]
    plano = normalizar(cuerpo)
    original = ws.raiz / "capitulos" / ruta.name
    en_disco = original.read_text(encoding="utf-8") if original.is_file() else ""
    lineas_disco = unicodedata.normalize("NFC", en_disco).splitlines()
    for h in hechos:
        if normalizar(h.cita) in plano:
            continue
        # Dónde estaba en el fichero guardado, para señalar el pasaje; si no, la primera línea.
        linea = next(
            (i for i, lin in enumerate(lineas_disco) if normalizar(h.cita)[:40] in normalizar(lin)),
            base,
        )
        diags.append(
            _diag(
                "hecho_cambiado",
                f"la edición cambia el hecho {h.id}: su cita «{h.cita}» ya no está en el texto. "
                "Publicarla exige `novela cambio` (docs/lsp.md)",
                _AVISO,
                (linea, 0),
                (linea, 0),
            )
        )

    inicios = _lineas_de_parrafos(cuerpo)
    for hallazgo in analizar(cuerpo, prosa.contexto(ws)).hallazgos:
        linea = base + (inicios[hallazgo.parrafo - 1] if hallazgo.parrafo else 0)
        diags.append(
            _diag(
                hallazgo.codigo,
                f"{hallazgo.regla}: {hallazgo.codigo} ({hallazgo.evidencia})",
                _INFO,
                (linea, 0),
                (linea, 0),
            )
        )
    return diags

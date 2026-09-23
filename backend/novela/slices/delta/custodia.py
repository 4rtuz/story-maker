"""Custodia del capítulo (RF-32): la cadena de hashes, como función pura.

Un modelo no calcula un sha256, así que lo registra el CLI por donde pasa el texto: `briefing` en
el frontmatter de cada briefing que incrusta el capítulo y `validar` en su informe. Aquí solo se
comparan. Es una precondición sobre datos, no un juicio sobre veredictos de modelo.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from novela.dominio.qa import InformeQA


@dataclass(frozen=True)
class Cadena:
    sha_disco: str | None  # capitulos/NN.md tal como está ahora
    sha_cronista: str | None  # el que leyó el cronista, de su briefing en el run
    validacion: InformeQA | None  # el último qa/NN-validacion.json
    shas_revision: Mapping[str, str | None]  # agente → hash de su briefing, los presentes en el run


def rotura(c: Cadena) -> list[str]:
    """Vacío si la cadena cierra; si no, por qué."""
    causas = []
    if c.sha_disco is None:
        causas.append("no existe el capítulo")
    if c.sha_cronista is None:
        causas.append("falta el briefing del cronista en el run, o no incrusta el capítulo")
    elif c.sha_cronista != c.sha_disco:
        causas.append("el capítulo en disco no es el que leyó el cronista")
    if c.validacion is None:
        causas.append("falta qa/NN-validacion.json: el capítulo no ha pasado validar")
    else:
        if c.validacion.hallazgos:
            causas.append("la última validación tiene hallazgos")
        if c.validacion.capitulo_sha256 != c.sha_disco:
            causas.append("el capítulo en disco no es el que pasó la última validación")
    if len(set(c.shas_revision.values())) > 1:
        # El del editor incluido: partió de la versión que revisaron los otros dos.
        detalle = ", ".join(
            f"{a}={(s or 'ninguno')[:8]}" for a, s in sorted(c.shas_revision.items())
        )
        causas.append(f"los briefings de revisión no llevan el mismo hash: {detalle}")
    return causas

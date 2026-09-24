"""Gates del borrador del `entrevistador` (spec 0005 §8.4): funciones puras.

El agente solo estructura y cita; estos gates deciden si el brief vale. Cada uno devuelve
hallazgos con códigos y rutas de campo, nunca valores: van al informe y, resumidos, al log.
"""

import re

from pydantic import ValidationError

from novela.dominio.brief import BorradorBrief, Hallazgo
from novela.dominio.texto import normalizar

EDAD_MINIMA = 12  # D7: decisión de producto, no norma
GENEROS_ADULTOS = ("noir", "thriller_psicologico")


def comparable(texto: str) -> str:
    """Lo que se compara en el brief: `normalizar` y además minúsculas."""
    return normalizar(texto).lower()


def _ruta(loc: tuple[int | str, ...]) -> str | None:
    """El campo del borrador al que apunta un `loc` de Pydantic: `tono`, `destinatario.edad`,
    `recuerdos[3]`. Lo que va por debajo (`valor`, `fuente.cita`) no cambia qué pedir."""
    if not loc:
        return None
    ruta, resto = str(loc[0]), list(loc[1:])
    if ruta == "destinatario" and resto and isinstance(resto[0], str):
        ruta += f".{resto.pop(0)}"
    if resto and isinstance(resto[0], int):
        ruta += f"[{resto[0]}]"
    return ruta


def esquema(crudo: bytes | None) -> tuple[BorradorBrief | None, list[Hallazgo]]:
    if crudo is None:
        return None, [Hallazgo(tipo="esquema", codigo="borrador_ausente")]
    try:
        return BorradorBrief.model_validate_json(crudo), []
    except ValidationError as exc:
        rutas = list(dict.fromkeys(_ruta(e["loc"]) for e in exc.errors()))
        return None, [
            Hallazgo(tipo="esquema", codigo="esquema_invalido", campos=[r] if r else [])
            for r in rutas
        ]


def faltantes(b: BorradorBrief) -> list[Hallazgo]:
    """Cada obligatorio a `null` y las listas vacías. `prohibidos` con `terminos: []` está."""
    d = b.destinatario
    ausentes = [
        ("destinatario.nombre", d.nombre is None),
        ("destinatario.edad", d.edad is None),
        ("destinatario.rasgos", not d.rasgos),
        ("recuerdos", not b.recuerdos),
        ("genero", b.genero is None),
        ("tono", b.tono is None),
        ("extension", b.extension is None),
        ("prohibidos", b.prohibidos is None),
    ]
    return [
        Hallazgo(tipo="faltante", codigo="falta_campo", campos=[campo])
        for campo, falta in ausentes
        if falta
    ]


def contradicciones(b: BorradorBrief) -> list[Hallazgo]:
    """C-01 y C-02 solo con los dos campos presentes; C-03 por palabra completa."""
    hallazgos = []
    edad = b.destinatario.edad
    if edad is not None and edad.valor < EDAD_MINIMA:
        if b.genero is not None and b.genero.valor in GENEROS_ADULTOS:
            campos = ["destinatario.edad", "genero"]
            hallazgos.append(Hallazgo(tipo="contradiccion", codigo="edad_genero", campos=campos))
        if b.tono is not None and b.tono.valor == "oscuro":
            campos = ["destinatario.edad", "tono"]
            hallazgos.append(Hallazgo(tipo="contradiccion", codigo="edad_tono", campos=campos))
    if b.prohibidos is not None and b.prohibidos.terminos:
        vetos = [
            re.compile(rf"(?<!\w){re.escape(comparable(t))}(?!\w)") for t in b.prohibidos.terminos
        ]
        textos = [(f"recuerdos[{i}]", r.cita) for i, r in enumerate(b.recuerdos)]
        textos += [
            (f"destinatario.rasgos[{i}]", r.valor) for i, r in enumerate(b.destinatario.rasgos)
        ]
        hallazgos += [
            Hallazgo(tipo="contradiccion", codigo="prohibido_en_texto", campos=[campo])
            for campo, texto in textos
            if any(v.search(comparable(texto)) for v in vetos)
        ]
    return hallazgos

"""Lo que el esquema del delta no puede expresar: función pura (validators.md §3.4).

Recibe el estado vigente, el delta, el cuerpo del capítulo sin frontmatter y el frontmatter, y
devuelve las causas de rechazo. Vacío: el delta se puede aplicar.
"""

import re
import unicodedata
from collections import Counter

from novela.dominio.artefactos import FrontmatterCapitulo
from novela.dominio.estado import Delta, Estado

_ESPACIOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    """NFC y cada secuencia de espacios en blanco a un espacio. Nada más: ni comillas ni
    mayúsculas, porque una cita que solo casa aflojando la comparación ya no es una cita."""
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", texto))


def _ids(delta: Delta) -> list[str]:
    """Todo id que el delta define, de todas sus colecciones: ninguno puede repetirse."""
    ids = [h.id for h in delta.libro_de_hechos]
    ids += [e.escena for e in delta.linea_temporal]
    ids += [h.id for h in delta.hilos]
    ids += [o.id for o in delta.objetos]
    ids += [f"{r.de}→{r.a}" for r in delta.relaciones]
    return ids


def _duplicados(delta: Delta) -> list[str]:
    return [f"id repetido en el delta: {i}" for i, n in Counter(_ids(delta)).items() if n > 1]


def _reescrituras(estado: Estado, delta: Delta) -> list[str]:
    """Un alta append-only con un id que ya existe tiene que ser la misma entrada: si lo es, es
    reanudar; si no, es reescribir la historia."""
    hechos = {h.id: h for h in estado.libro_de_hechos}
    escenas = {e.escena: e for e in estado.linea_temporal}
    causas = [
        f"{h.id} ya está en libro_de_hechos con otro contenido"
        for h in delta.libro_de_hechos
        if h.id in hechos and hechos[h.id] != h
    ]
    causas += [
        f"{e.escena} ya está en linea_temporal con otro contenido"
        for e in delta.linea_temporal
        if e.escena in escenas and escenas[e.escena] != e
    ]
    return causas


def _cursor(estado: Estado, delta: Delta, fm: FrontmatterCapitulo) -> list[str]:
    causas = []
    if delta.capitulo < estado.cursor.capitulo:
        causas.append(
            f"cursor decreciente: el delta es del capítulo {delta.capitulo} y el estado ya va "
            f"por el {estado.cursor.capitulo}"
        )
    if delta.capitulo != fm.capitulo:
        causas.append(f"el delta es del capítulo {delta.capitulo} y el capítulo, del {fm.capitulo}")
    return causas


def _citas(delta: Delta, cuerpo: str) -> list[str]:
    """RF-33: toda cita presente, de las cuatro colecciones que la llevan, es literal del cuerpo."""
    texto = normalizar(cuerpo)
    citadas: list[tuple[str, str | None]] = [(h.id, h.cita) for h in delta.libro_de_hechos]
    citadas += [(e.escena, e.cita) for e in delta.linea_temporal]
    citadas += [(e.hecho, e.cita) for e in delta.conocimiento_lector]
    citadas += [(e.hecho, e.cita) for es in delta.conocimiento.values() for e in es]
    return [
        f"la cita de {origen} no es literal del capítulo"
        for origen, cita in citadas
        if cita is not None and normalizar(cita) not in texto
    ]


def _hilos(delta: Delta, fm: FrontmatterCapitulo) -> list[str]:
    """RF-34: delta y frontmatter describen el mismo texto. Si difieren, uno de los dos se
    equivoca, y no hace falta saber cuál para no aplicar."""
    n = delta.capitulo
    abiertos = {h.id for h in delta.hilos if h.abierto_en == n}
    cerrados = {h.id for h in delta.hilos if h.cerrado_en == n}
    causas = []
    for nombre, del_delta, del_fm in (
        ("abre", abiertos, set(fm.hilos_abiertos)),
        ("cierra", cerrados, set(fm.hilos_cerrados)),
    ):
        if del_delta != del_fm:
            diferencia = ", ".join(sorted(del_delta ^ del_fm))
            causas.append(
                f"el delta y el frontmatter no coinciden en qué hilos {nombre}: {diferencia}"
            )
    return causas


def violaciones(estado: Estado, delta: Delta, cuerpo: str, fm: FrontmatterCapitulo) -> list[str]:
    return (
        _duplicados(delta)
        + _reescrituras(estado, delta)
        + _cursor(estado, delta, fm)
        + _citas(delta, cuerpo)
        + _hilos(delta, fm)
    )

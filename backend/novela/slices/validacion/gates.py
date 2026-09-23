"""Los cinco gates de `novela validar`: funciones puras, en el orden de la spec §5.3.

De más barato a más caro y de más común a más raro. Deciden si se gastan tres llamadas a modelo,
así que nada aquí abre ficheros: lo recibe todo.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from novela.dominio.artefactos import FrontmatterCapitulo, contar_palabras
from novela.dominio.config import PalabrasPorCapitulo
from novela.dominio.plan import FichaCapitulo
from novela.dominio.qa import Hallazgo


@dataclass(frozen=True)  # pragma: no mutate
class Contexto:
    capitulo: int
    palabras: PalabrasPorCapitulo
    ficha: FichaCapitulo
    personajes: frozenset[str]  # ids con ficha en canon/personajes/
    pistas: frozenset[str]  # ids de canon.misterio.pistas
    hilos_abiertos: frozenset[str]  # abiertos en el estado antes de este capítulo


def _frontmatter(meta: Mapping[str, Any] | None, capitulo: int) -> FrontmatterCapitulo | Hallazgo:
    try:
        fm = FrontmatterCapitulo.model_validate(meta)
    except ValidationError as exc:
        errores = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return Hallazgo(tipo="frontmatter_invalido", gravedad="alta", descripcion=errores)
    if fm.capitulo != capitulo:
        return Hallazgo(
            tipo="frontmatter_invalido",
            gravedad="alta",
            descripcion=f"el frontmatter dice capítulo {fm.capitulo} y el fichero es el {capitulo}",
        )
    return fm


def _longitud(cuerpo: str, rango: PalabrasPorCapitulo) -> list[Hallazgo]:
    # Contra min y max, nunca contra objetivo: exigir un número exacto degrada la prosa.
    n = contar_palabras(cuerpo)
    if rango.min <= n <= rango.max:
        return []
    return [
        Hallazgo(
            tipo="longitud_fuera_de_rango",
            gravedad="alta",
            descripcion=f"{n} palabras; el rango es {rango.min}..{rango.max}",
        )
    ]


def _pistas(fm: FrontmatterCapitulo, ficha: FichaCapitulo) -> list[Hallazgo]:
    faltan = [("plantar", p) for p in ficha.pistas_a_plantar if p not in fm.pistas_plantadas]
    faltan += [("pagar", p) for p in ficha.pistas_a_pagar if p not in fm.pistas_pagadas]
    return [
        Hallazgo(
            tipo="pista_ausente",
            gravedad="alta",
            referencia=pista,
            descripcion=f"el plan manda {accion} {pista} y el frontmatter no la declara",
        )
        for accion, pista in faltan
    ]


def _hilos(fm: FrontmatterCapitulo, abiertos: frozenset[str]) -> list[Hallazgo]:
    return [
        Hallazgo(
            tipo="hilo_cerrado_sin_abrir",
            gravedad="alta",
            referencia=hilo,
            descripcion=f"{hilo} se cierra y no estaba abierto ni se abre en este capítulo",
        )
        for hilo in fm.hilos_cerrados
        if hilo not in abiertos and hilo not in fm.hilos_abiertos
    ]


def _ids(fm: FrontmatterCapitulo, ctx: Contexto) -> list[Hallazgo]:
    escenas = frozenset(e.id for e in ctx.ficha.escenas)
    citados = [("personaje", fm.pov, ctx.personajes)]
    citados += [("escena", e, escenas) for e in fm.escenas]
    citados += [("pista", p, ctx.pistas) for p in fm.pistas_plantadas + fm.pistas_pagadas]
    return [
        Hallazgo(
            tipo="id_inexistente",
            gravedad="alta",
            referencia=id_,
            descripcion=f"{id_} no existe como {clase} en el canon ni en el plan",
        )
        for clase, id_, existentes in citados
        if id_ not in existentes
    ]


def validar(meta: Mapping[str, Any] | None, cuerpo: str, ctx: Contexto) -> list[Hallazgo]:
    """Vacío si el capítulo pasa. Con el frontmatter roto no se puede mirar lo que depende de
    él, así que ese hallazgo va solo."""
    fm = _frontmatter(meta, ctx.capitulo)
    if isinstance(fm, Hallazgo):
        return [fm]
    return (
        _longitud(cuerpo, ctx.palabras)
        + _pistas(fm, ctx.ficha)
        + _hilos(fm, ctx.hilos_abiertos)
        + _ids(fm, ctx)
    )

"""Los gates de `novela validar`, en el orden de la spec §5.3, y los de la spec 0009 que corren
en otros puntos. Funciones puras.

De más barato a más caro y de más común a más raro. Deciden si se gastan tres llamadas a modelo,
así que nada aquí abre ficheros: lo recibe todo.
"""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from novela.dominio.artefactos import FrontmatterCapitulo, contar_palabras
from novela.dominio.config import PalabrasPorCapitulo
from novela.dominio.plan import FichaCapitulo
from novela.dominio.qa import Hallazgo

_BRIEF = "brief/brief.json"
_LETRAS = re.compile(r"[^\W\d_]+")


@dataclass(frozen=True)  # pragma: no mutate
class FormaCanonica:
    referencia: str  # per-… o "destinatario"
    texto: str  # nombre o alias
    origen: str  # canon/personajes/<id>.md o brief/brief.json


@dataclass(frozen=True)  # pragma: no mutate
class Contexto:
    capitulo: int
    palabras: PalabrasPorCapitulo
    ficha: FichaCapitulo
    personajes: frozenset[str]  # ids con ficha en canon/personajes/
    pistas: frozenset[str]  # ids de canon.misterio.pistas
    hilos_abiertos: frozenset[str]  # abiertos en el estado antes de este capítulo
    formas: tuple[FormaCanonica, ...] = ()  # personajes por id y, al final, el destinatario


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


def plegar(texto: str) -> str:
    """Sin marcas combinantes y sin caja: «Vídal», «VIDAL» y «vidal» pliegan igual."""
    sin_marcas = (c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c))
    return "".join(sin_marcas).casefold()


def _canonicos(forma: FormaCanonica) -> list[str]:
    # Tres letras o más y mayúscula inicial: «Li» o «la jefa» no se comprueban (spec §9).
    tokens = _LETRAS.findall(unicodedata.normalize("NFC", forma.texto))
    return [t for t in tokens if len(t) >= 3 and t[0].isupper()]


def _no_grito(token: str) -> bool:
    return token[0].isupper() and not token.isupper()


def nombres(cuerpo: str, formas: Sequence[FormaCanonica]) -> list[Hallazgo]:
    """vp_nombres (spec 0009 D4): una forma del cuerpo que pliega como un nombre canónico sin
    serlo, empieza por mayúscula y no está gritada. Antes, el canon contra el brief (D5)."""
    exactos = {t for f in formas for t in _canonicos(f)}
    canon: dict[str, tuple[str, str]] = {}  # plegado → (token, referencia); gana la primera
    for forma in formas:
        for token in _canonicos(forma):
            canon.setdefault(plegar(token), (token, forma.referencia))
    del_brief = {plegar(t): t for f in formas if f.origen == _BRIEF for t in _canonicos(f)}
    hallazgos = {
        (forma.referencia, token): Hallazgo(
            tipo="nombre_mal_escrito",
            gravedad="alta",
            referencia=forma.referencia,
            ubicacion=forma.origen,
            descripcion=f"«{token}» no es la grafía de destinatario: «{del_brief[plegar(token)]}»",
        )
        for forma in formas
        if forma.origen != _BRIEF
        for token in _canonicos(forma)
        if del_brief.get(plegar(token), token) != token and _no_grito(token)
    }
    lineas: dict[str, list[int]] = {}
    for n, linea in enumerate(unicodedata.normalize("NFC", cuerpo).splitlines(), 1):
        for token in _LETRAS.findall(linea):
            if token not in exactos and plegar(token) in canon and _no_grito(token):
                lineas.setdefault(token, []).append(n)
    return list(hallazgos.values()) + [
        Hallazgo(
            tipo="nombre_mal_escrito",
            gravedad="alta",
            referencia=canon[plegar(token)][1],
            ubicacion="línea " + ", ".join(map(str, dict.fromkeys(ns))),
            descripcion=f"«{token}» no es la grafía de {canon[plegar(token)][1]}: "
            f"«{canon[plegar(token)][0]}»",
        )
        for token, ns in lineas.items()
    ]


def esquemas(
    documentos: Mapping[str, tuple[type[BaseModel], object | None, bool]],
    contexto: Mapping[str, Any] | None = None,
) -> list[Hallazgo]:
    """vp_schema (spec 0009 D2): ruta → (modelo, datos ya leídos o None si no existe, obligatorio).
    Un hallazgo por documento, con las rutas de campo y los tipos de error: nunca los valores,
    que acaban en stderr y en harness.log. `contexto` es el de la validación (la escaleta)."""
    hallazgos = []
    for ruta, (modelo, datos, obligatorio) in documentos.items():
        if datos is None:
            if obligatorio:
                hallazgos.append(
                    Hallazgo(
                        tipo="esquema_invalido",
                        gravedad="alta",
                        referencia=ruta,
                        ubicacion="(ausente)",
                        descripcion="falta el artefacto",
                    )
                )
            continue
        try:
            modelo.model_validate(datos, context=contexto)
        except ValidationError as exc:
            errores = exc.errors()  # solo se leen loc y type: nunca input ni msg
            hallazgos.append(
                Hallazgo(
                    tipo="esquema_invalido",
                    gravedad="alta",
                    referencia=ruta,
                    ubicacion=", ".join(".".join(map(str, e["loc"])) or "(raíz)" for e in errores),
                    descripcion=", ".join(dict.fromkeys(e["type"] for e in errores)),
                )
            )
    return hallazgos


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
        + nombres(cuerpo, ctx.formas)
    )

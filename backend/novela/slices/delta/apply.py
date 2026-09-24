"""`aplicar(estado, delta) -> estado`: función pura e idempotente (RF-19, validators.md §3.6).

Reanudar repite el paso entero, así que aplicar dos veces el mismo delta deja el mismo estado.
Las altas append-only que ya están no se repiten; las mutables se sustituyen por id. `pistas`,
`metricas` y `tension_real` no vienen en el delta: llegan como `Derivados` desde la cáscara.
"""

from collections.abc import Callable, Hashable, Iterable, Mapping
from dataclasses import dataclass

from novela.dominio.artefactos import FrontmatterCapitulo
from novela.dominio.base import ColeccionAppendOnly
from novela.dominio.estado import (
    Cursor,
    Delta,
    Estado,
    EstadoPista,
    Metricas,
    UsoDeHecho,
    Via,
)


@dataclass(frozen=True)  # pragma: no mutate
class Derivados:
    frontmatter: FrontmatterCapitulo  # pistas plantadas y pagadas en el capítulo
    pago_previsto: Mapping[str, int | None]  # canon.misterio.pistas: id → capitulo_pagado
    tension: int | None  # qa/NN-suspense.json; None es un hueco
    palabras_totales: int  # contadas en los capítulos 1..N
    palabras_objetivo: int  # palabras_por_capitulo.objetivo × N


def _altas[T](coleccion: ColeccionAppendOnly[T], nuevas: Iterable[T]) -> ColeccionAppendOnly[T]:
    for entrada in nuevas:
        if entrada not in coleccion.entradas:
            coleccion = coleccion.añadir(entrada)
    return coleccion


def _sustituir[T](
    actuales: list[T], nuevos: Iterable[T], clave: Callable[[T], Hashable]
) -> list[T]:
    """Mismo orden que antes; lo tocado se sustituye en su sitio y lo nuevo va al final."""
    por_clave = {clave(n): n for n in nuevos}
    resultado = [por_clave.pop(clave(a), a) for a in actuales]
    return resultado + list(por_clave.values())


def _pistas(estado: Estado, capitulo: int, d: Derivados) -> dict[str, EstadoPista]:
    pistas = dict(estado.pistas)
    ids = [*d.pago_previsto, *d.frontmatter.pistas_plantadas, *d.frontmatter.pistas_pagadas]
    for pista in dict.fromkeys(ids):
        antes = pistas.get(pista)
        plantada = antes.plantada_en if antes else None
        pagada = antes.pagada_en if antes else None
        if pista in d.frontmatter.pistas_plantadas:
            plantada = plantada or capitulo
        if pista in d.frontmatter.pistas_pagadas:
            pagada = pagada or capitulo
        previsto = d.pago_previsto.get(pista)
        if pagada is not None:
            valor = "pagada"
        elif plantada is None:
            valor = "pendiente"
        elif previsto is None or previsto <= capitulo:
            valor = "huerfana"  # plantada y sin capítulo que la pague por delante
        else:
            valor = "plantada"
        pistas[pista] = EstadoPista(estado=valor, plantada_en=plantada, pagada_en=pagada)
    return pistas


def _tension(estado: Estado, capitulo: int, valor: int | None) -> ColeccionAppendOnly[int | None]:
    """Una entrada por capítulo: el índice es el capítulo. Los que faltan son huecos."""
    tension = estado.tension_real
    while len(tension) < capitulo - 1:
        tension = tension.añadir(None)
    return tension.añadir(valor) if len(tension) < capitulo else tension


def usos(delta: Delta) -> tuple[UsoDeHecho, ...]:
    """Spec 0007 RF-03: qué hechos usa el capítulo y por qué vía, sin repetir. El capítulo del uso
    es el del delta, no el `desde_capitulo` de la entrada."""
    n = delta.capitulo
    filas: list[tuple[str, Via]] = [(h.id, "origen") for h in delta.libro_de_hechos]
    filas += [(e.hecho, "conocimiento") for es in delta.conocimiento.values() for e in es]
    filas += [(e.hecho, "lector") for e in delta.conocimiento_lector]
    filas += [(u.hecho, "cita") for u in delta.hechos_usados]
    return tuple(UsoDeHecho(hecho=h, capitulo=n, via=v) for h, v in dict.fromkeys(filas))


def aplicar(estado: Estado, delta: Delta, d: Derivados) -> Estado:
    n = delta.capitulo
    mismo_capitulo = estado.cursor.capitulo == n
    conocimiento = dict(estado.conocimiento)
    for personaje, entradas in delta.conocimiento.items():
        sabe = _altas(conocimiento.get(personaje, ColeccionAppendOnly()), entradas)
        if len(sabe):  # model_copy no valida: sin esto quedaría {per-x: []}, que la base no guarda
            conocimiento[personaje] = sabe
    objetivo = d.palabras_objetivo
    return estado.model_copy(
        update={
            "cursor": Cursor(
                capitulo=n,
                fase="registro",
                ultimo_paso="aplicar-delta",
                intento=estado.cursor.intento if mismo_capitulo else 1,
            ),
            "linea_temporal": _altas(estado.linea_temporal, delta.linea_temporal),
            "personajes": {**estado.personajes, **delta.personajes},
            "conocimiento": conocimiento,
            "relaciones": _sustituir(estado.relaciones, delta.relaciones, lambda r: (r.de, r.a)),
            "objetos": _sustituir(estado.objetos, delta.objetos, lambda o: o.id),
            "libro_de_hechos": _altas(estado.libro_de_hechos, delta.libro_de_hechos),
            "hilos": _sustituir(estado.hilos, delta.hilos, lambda h: h.id),
            "pistas": _pistas(estado, n, d),
            "conocimiento_lector": _altas(estado.conocimiento_lector, delta.conocimiento_lector),
            "tension_real": _tension(estado, n, d.tension),
            "metricas": Metricas(
                palabras_totales=d.palabras_totales,
                desviacion_vs_plan=round(d.palabras_totales / objetivo - 1, 4) if objetivo else 0.0,
            ),
        }
    )

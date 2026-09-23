"""Ensamblado del briefing: función pura. Recibe receta y datos ya leídos, devuelve el texto.

No abre ficheros ni mira el reloj: esa frontera es la que permite el property-based de
validators.md §3.6. Incrusta contenido, nunca rutas: un agente sin Glob ni Grep solo alcanza lo
que su briefing le da.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any

import yaml

from novela.dominio import frontmatter
from novela.dominio.artefactos import FrontmatterBriefing, Memoria
from novela.dominio.canon import Misterio, Personaje
from novela.dominio.estado import Estado
from novela.dominio.ids import Agente
from novela.dominio.plan import FichaCapitulo
from novela.slices.briefing import recipes
from novela.slices.briefing.recipes import Receta

# architecture.md §6.5: 3,5 caracteres por token para español, tratado como cota superior.
CARACTERES_POR_TOKEN = 3.5


class FuenteAusente(Exception):
    """La receta nombra algo que el workspace no tiene."""


@dataclass(frozen=True)
class Fuentes:
    """Todo lo que el ensamblado puede incrustar, leído por la cáscara."""

    agente: Agente
    capitulo: int
    run_id: str
    ficheros: Mapping[str, str]  # ruta relativa → texto: config.yaml, canon/*.md, plan/escaleta.md
    ficha: FichaCapitulo | None
    ficha_texto: str | None
    misterio: Misterio | None
    misterio_texto: str | None
    personajes: Mapping[str, tuple[Personaje, str]]  # id → (ficha, texto)
    estado: Estado  # ya filtrado por la cáscara con consulta indexada
    capitulo_anterior: str | None
    capitulo_actual: str | None
    sha_actual: str | None  # sha256 de capitulos/NN.md en disco
    resumenes: Mapping[int, Memoria]  # capítulos anteriores


@dataclass(frozen=True)
class Briefing:
    meta: FrontmatterBriefing
    cuerpo: str

    @property
    def texto(self) -> str:
        return frontmatter.unir(self.meta.model_dump(mode="json", exclude_none=True), self.cuerpo)


@dataclass(frozen=True)
class _Ajuste:
    """Cuánto se ha degradado (architecture.md §6.5, pasos 1 a 3)."""

    remotas_recortadas: int = 0
    reciente_a_linea: bool = False
    solo_con_dialogo: bool = False


def estimar_tokens(texto: str) -> int:
    return math.ceil(len(texto) / CARACTERES_POR_TOKEN)


def _md(ruta: str) -> str:
    nombre = ruta.rsplit("/", 1)[-1]
    return ruta if "." in nombre or nombre == "*" else ruta + ".md"


def _rutas(patrones: list[str], disponibles: Mapping[str, str], excluir: list[str]) -> list[str]:
    fuera = {_md(e) for e in excluir}
    elegidas: list[str] = []
    for patron in map(_md, patrones):
        if patron.endswith("/*"):
            base = patron[:-1]
            hallados = sorted(
                r
                for r in disponibles
                if fnmatchcase(r, base + "*.md") and "/" not in r[len(base) :]
            )
        elif patron in disponibles:
            hallados = [patron]
        else:
            raise FuenteAusente(f"la receta pide {patron} y el workspace no lo tiene")
        elegidas += [r for r in hallados if r not in fuera and r not in elegidas]
    return elegidas


def _seccion(titulo: str, contenido: str) -> str:
    return f"## {titulo}\n\n{contenido.strip()}\n"


def _yaml(datos: Any) -> str:
    return "```yaml\n" + yaml.safe_dump(datos, allow_unicode=True, sort_keys=False) + "```"


def _presentes(f: Fuentes) -> list[str]:
    if f.ficha is None:
        return sorted(f.personajes)
    vistos = dict.fromkeys(p for e in f.ficha.escenas for p in e.personajes)
    return list(vistos)


def _con_dialogo(f: Fuentes) -> set[str]:
    return {p for e in f.ficha.escenas for p in e.dialogo} if f.ficha else set(f.personajes)


def _estado(selector: str, f: Fuentes) -> Any:
    e = f.estado.model_dump(mode="json")
    if selector == "hilos_abiertos":
        return [h for h in e["hilos"] if h["estado"] == "abierto"]
    if selector == "coartadas":
        return {
            id_: [m.model_dump(mode="json") for m in ficha.coartada_y_cronologia_privada]
            for id_, (ficha, _) in sorted(f.personajes.items())
        }
    return e[selector]


def _pistas_del_capitulo(f: Fuentes) -> str:
    if f.ficha is None or f.misterio is None:
        return ""
    por_id = {p.id: p for p in f.misterio.pistas}
    lineas = []
    for accion, ids in (("plantar", f.ficha.pistas_a_plantar), ("pagar", f.ficha.pistas_a_pagar)):
        for id_ in ids:
            if id_ not in por_id:
                raise FuenteAusente(f"la ficha pide {accion} {id_} y el misterio no la tiene")
            lineas.append(f"- {id_} · {accion} · {por_id[id_].contenido}")
    return "\n\n### Pistas de este capítulo\n\n" + "\n".join(lineas) if lineas else ""


def _resumenes(f: Fuentes, capitulos: range, granularidad: str) -> str:
    faltan = [c for c in capitulos if c not in f.resumenes]
    if faltan:
        raise FuenteAusente(f"faltan resúmenes de memoria/ de los capítulos {faltan}")
    if granularidad == "una_linea":
        return "\n".join(f"- {c:02d}: {f.resumenes[c].linea}" for c in capitulos)
    return "\n\n".join(f"### Capítulo {c:02d}\n\n{f.resumenes[c].parrafo}" for c in capitulos)


def _capas(receta: Receta, f: Fuentes, ajuste: _Ajuste) -> list[str]:
    n = f.capitulo
    secciones: list[str] = []
    reciente = next((c.reciente for c in receta.capas if isinstance(c, recipes.Reciente)), None)
    for capa in receta.capas:
        match capa:
            case recipes.Permanente(permanente=patrones):
                for ruta in _rutas(patrones, f.ficheros, receta.excluir):
                    secciones.append(_seccion(f"permanente · {ruta}", f.ficheros[ruta]))
            case recipes.Personajes(personajes=cuales):
                ids = _presentes(f) if cuales == "presentes_en_escena" else sorted(f.personajes)
                if ajuste.solo_con_dialogo:
                    ids = [p for p in ids if p in _con_dialogo(f)]
                for id_ in ids:
                    if id_ not in f.personajes:
                        raise FuenteAusente(f"falta la ficha canon/personajes/{id_}.md")
                    secciones.append(_seccion(f"personajes · {id_}", f.personajes[id_][1]))
            case recipes.EstadoFiltrado(estado=selectores):
                for selector in selectores:
                    secciones.append(_seccion(f"estado · {selector}", _yaml(_estado(selector, f))))
            case recipes.Inmediata():
                if n > 1:
                    if f.capitulo_anterior is None:
                        raise FuenteAusente(f"falta capitulos/{n - 1:02d}.md")
                    secciones.append(
                        _seccion(f"inmediata · capítulo {n - 1:02d}", f.capitulo_anterior)
                    )
            case recipes.Reciente(reciente=r):
                capitulos = range(max(1, n - r.n), n)
                gran = "una_linea" if ajuste.reciente_a_linea else r.granularidad
                if capitulos:
                    secciones.append(_seccion(f"reciente · {gran}", _resumenes(f, capitulos, gran)))
            case recipes.Remota(remota=r):
                hasta = n - (reciente.n if reciente else 0)
                capitulos = range(max(r.desde, 1) + ajuste.remotas_recortadas, max(1, hasta))
                if capitulos:
                    secciones.append(
                        _seccion(
                            f"remota · {r.granularidad}", _resumenes(f, capitulos, r.granularidad)
                        )
                    )
            case recipes.Plan():
                if f.ficha_texto is None:
                    raise FuenteAusente(f"falta plan/capitulos/{n:02d}.md")
                secciones.append(
                    _seccion(f"plan · capítulo {n:02d}", f.ficha_texto + _pistas_del_capitulo(f))
                )
            case recipes.Variacion():
                if f.ficha is None:
                    raise FuenteAusente(f"falta plan/capitulos/{n:02d}.md")
                secciones.append(
                    _seccion("variacion · restricción de apertura", f.ficha.restriccion_de_apertura)
                )
            case recipes.Objetivo():
                if f.capitulo_actual is None:
                    raise FuenteAusente(f"falta capitulos/{n:02d}.md")
                secciones.append(_seccion(f"objetivo · capítulo {n:02d}", f.capitulo_actual))
    return secciones


def ensamblar(receta: Receta, f: Fuentes) -> Briefing:
    cuerpo = "\n".join(_capas(receta, f, _Ajuste()))
    incrusta_capitulo = any(isinstance(c, recipes.Objetivo) for c in receta.capas)
    meta = FrontmatterBriefing(
        agente=f.agente,
        capitulo=f.capitulo,
        run_id=f.run_id,
        presupuesto_tokens=receta.presupuesto_tokens,
        tokens_estimados=estimar_tokens(cuerpo),
        capitulo_sha256=f.sha_actual if incrusta_capitulo else None,
    )
    return Briefing(meta=meta, cuerpo=cuerpo)

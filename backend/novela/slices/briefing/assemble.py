"""Ensamblado del briefing: función pura. Recibe receta y datos ya leídos, devuelve el texto.

No abre ficheros ni mira el reloj: esa frontera es la que permite el property-based de
validators.md §3.6. Incrusta contenido, nunca rutas: un agente sin Glob ni Grep solo alcanza lo
que su briefing le da.
"""

import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, replace
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

# ponytail: el guardarraíl compara texto, hoja a hoja y frase a frase, desde 20 caracteres. No ve
# la paráfrasis (spec 0001 §13); eso es de las sondas ciegas de la spec 0002.
MIN_FRAGMENTO = 20
_ID = re.compile(r"[a-z]{1,3}-[a-z0-9-]+")
_CORTE_DE_FRASE = re.compile(r"(?<=[.!?…])\s+|\n+")


class FuenteAusente(Exception):
    """La receta nombra algo que el workspace no tiene."""


class FugaDelSecreto(Exception):
    """El briefing de un agente que excluye canon/misterio contiene texto de ese fichero."""


class PresupuestoExcedido(Exception):
    """No cabe ni degradado: paso 4 de §6.5, se para y se pide intervención. Nunca se trunca."""


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
    digitos: int = 2  # 3 si la novela pasa de 99 capítulos, en todo el workspace

    def nn(self, capitulo: int) -> str:
        return f"{capitulo:0{self.digitos}d}"


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


# --- capas -----------------------------------------------------------------------------------


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
    return list(dict.fromkeys(p for e in f.ficha.escenas for p in e.personajes))


def _con_dialogo(f: Fuentes) -> set[str]:
    return {p for e in f.ficha.escenas for p in e.dialogo} if f.ficha else set(f.personajes)


def _estado(selector: str, f: Fuentes) -> Any:
    if selector == "coartadas":
        return {
            id_: [m.model_dump(mode="json") for m in ficha.coartada_y_cronologia_privada]
            for id_, (ficha, _) in sorted(f.personajes.items())
        }
    e = f.estado.model_dump(mode="json")
    if selector == "hilos_abiertos":
        return [h for h in e["hilos"] if h["estado"] == "abierto"]
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
        return "\n".join(f"- {f.nn(c)}: {f.resumenes[c].linea}" for c in capitulos)
    return "\n\n".join(f"### Capítulo {f.nn(c)}\n\n{f.resumenes[c].parrafo}" for c in capitulos)


def _capas(receta: Receta, f: Fuentes, ajuste: _Ajuste) -> list[str]:
    n = f.capitulo
    secciones: list[str] = []
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
                        raise FuenteAusente(f"falta capitulos/{f.nn(n - 1)}.md")
                    titulo = f"inmediata · capítulo {f.nn(n - 1)}"
                    secciones.append(_seccion(titulo, f.capitulo_anterior))
            case recipes.Reciente(reciente=r):
                capitulos = range(max(1, n - r.n), n)
                gran = "una_linea" if ajuste.reciente_a_linea else r.granularidad
                if capitulos:
                    secciones.append(_seccion(f"reciente · {gran}", _resumenes(f, capitulos, gran)))
            case recipes.Remota(remota=r):
                capitulos = _remotas(receta, f, ajuste)
                if capitulos:
                    texto = _resumenes(f, capitulos, r.granularidad)
                    secciones.append(_seccion(f"remota · {r.granularidad}", texto))
            case recipes.Plan():
                if f.ficha_texto is None:
                    raise FuenteAusente(f"falta plan/capitulos/{f.nn(n)}.md")
                texto = f.ficha_texto + _pistas_del_capitulo(f)
                secciones.append(_seccion(f"plan · capítulo {f.nn(n)}", texto))
            case recipes.Variacion():
                if f.ficha is None:
                    raise FuenteAusente(f"falta plan/capitulos/{f.nn(n)}.md")
                apertura = f.ficha.restriccion_de_apertura
                secciones.append(_seccion("variacion · restricción de apertura", apertura))
            case recipes.Objetivo():
                if f.capitulo_actual is None:
                    raise FuenteAusente(f"falta capitulos/{f.nn(n)}.md")
                secciones.append(_seccion(f"objetivo · capítulo {f.nn(n)}", f.capitulo_actual))
    return secciones


# --- guardarraíl del secreto (invariante 3) --------------------------------------------------


def _hojas(valor: object) -> Iterator[str]:
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for v in valor.values():
            yield from _hojas(v)
    elif isinstance(valor, list):
        for v in valor:
            yield from _hojas(v)


def _permitidos(f: Fuentes, misterio: Misterio) -> set[str]:
    """Lo del misterio que este capítulo puede tener delante: las pistas ya plantadas o que su
    ficha manda plantar o pagar, y lo ya revelado. Todo eso está, o va a estar, en el texto."""
    n, ficha = f.capitulo, f.ficha
    de_la_ficha = set(ficha.pistas_a_plantar + ficha.pistas_a_pagar) if ficha else set()
    permitidos = {
        p.contenido for p in misterio.pistas if p.capitulo_plantado <= n or p.id in de_la_ficha
    }
    for rev in misterio.revelaciones:
        if rev.capitulo_previsto < n:
            permitidos.add(rev.contenido)
    for giro in misterio.giros:
        if giro.capitulo_previsto < n:
            permitidos |= {giro.contenido, giro.que_creia_el_lector_antes}
    return permitidos


def _fragmentos(f: Fuentes, misterio: Misterio, permitidos: set[str]) -> set[str]:
    cuerpo = frontmatter.partir(f.misterio_texto)[1] if f.misterio_texto else ""
    fragmentos: set[str] = set()
    for hoja in (*_hojas(misterio.model_dump(mode="json")), cuerpo):
        if hoja in permitidos or _ID.fullmatch(hoja):
            continue
        for trozo in (hoja, *_CORTE_DE_FRASE.split(hoja)):
            trozo = trozo.strip()
            if len(trozo) >= MIN_FRAGMENTO and trozo not in permitidos:
                fragmentos.add(trozo)
    return fragmentos


def _vigilar_el_secreto(receta: Receta, f: Fuentes, secciones: list[str]) -> None:
    """Se mira el ensamblado completo, antes de degradar: una fuga en una capa que luego se
    recorta sigue siendo una fuga del workspace."""
    excluye = "canon/misterio" in {e.removesuffix(".md") for e in receta.excluir}
    if not excluye or f.misterio is None:
        return
    permitidos = _permitidos(f, f.misterio)
    fragmentos = _fragmentos(f, f.misterio, permitidos)
    por_longitud = sorted(permitidos, key=len, reverse=True)
    for seccion in secciones:
        resto = seccion
        for texto in por_longitud:
            resto = resto.replace(texto, " ")
        if any(fragmento in resto for fragmento in fragmentos):
            # El mensaje llega al orquestador: nombra la capa, nunca el texto filtrado.
            titulo = seccion.splitlines()[0].removeprefix("## ")
            raise FugaDelSecreto(
                f"el briefing de {f.agente} trae texto de canon/misterio.md en «{titulo}»"
            )


# --- sello de capítulos cerrados (RF-35) -----------------------------------------------------


def capitulos_alterados(
    sellados: Mapping[int, str], actuales: Mapping[int, str | None]
) -> list[int]:
    """Los capítulos cerrados cuyo hash ya no es el del checkpoint, o que han desaparecido. Los
    hashes los calcula la cáscara; esto solo compara."""
    return sorted(c for c, sha in sellados.items() if actuales.get(c) != sha)


# --- ensamblado ------------------------------------------------------------------------------


def _remotas(receta: Receta, f: Fuentes, ajuste: _Ajuste) -> range:
    remota = next((c.remota for c in receta.capas if isinstance(c, recipes.Remota)), None)
    if remota is None:
        return range(0)
    reciente = next((c.reciente for c in receta.capas if isinstance(c, recipes.Reciente)), None)
    hasta = f.capitulo - (reciente.n if reciente else 0)
    return range(max(remota.desde, 1) + ajuste.remotas_recortadas, max(1, hasta))


def _degradar(receta: Receta, f: Fuentes, ajuste: _Ajuste) -> _Ajuste | None:
    """El siguiente paso de §6.5, de menos a más doloroso. canon/ y el estado filtrado no se
    degradan nunca: su ausencia produce contradicción, no imprecisión."""
    if _remotas(receta, f, ajuste):
        return replace(ajuste, remotas_recortadas=ajuste.remotas_recortadas + 1)
    reciente = next((c.reciente for c in receta.capas if isinstance(c, recipes.Reciente)), None)
    if reciente and reciente.granularidad == "parrafo" and f.capitulo > 1:
        if not ajuste.reciente_a_linea:
            return replace(ajuste, reciente_a_linea=True)
    hay_personajes = any(isinstance(c, recipes.Personajes) for c in receta.capas)
    if hay_personajes and not ajuste.solo_con_dialogo and set(_presentes(f)) - _con_dialogo(f):
        return replace(ajuste, solo_con_dialogo=True)
    return None


def _pasos(ajuste: _Ajuste) -> list[str]:
    pasos = []
    if ajuste.remotas_recortadas:
        pasos.append(
            f"1 resúmenes a una línea más antiguos recortados: {ajuste.remotas_recortadas}"
        )
    if ajuste.reciente_a_linea:
        pasos.append("2 resúmenes a párrafo bajados a una línea")
    if ajuste.solo_con_dialogo:
        pasos.append("3 personajes reducidos a los que tienen diálogo")
    return pasos


def ensamblar(receta: Receta, f: Fuentes) -> Briefing:
    ajuste = _Ajuste()
    secciones = _capas(receta, f, ajuste)
    _vigilar_el_secreto(receta, f, secciones)
    cuerpo = "\n".join(secciones)
    while (tokens := estimar_tokens(cuerpo)) > receta.presupuesto_tokens:
        siguiente = _degradar(receta, f, ajuste)
        if siguiente is None:
            raise PresupuestoExcedido(
                f"el briefing de {f.agente} estima {tokens} tokens y su presupuesto es "
                f"{receta.presupuesto_tokens}; no cabe ni degradado: hace falta intervención"
            )
        ajuste = siguiente
        cuerpo = "\n".join(_capas(receta, f, ajuste))
    incrusta_capitulo = any(isinstance(c, recipes.Objetivo) for c in receta.capas)
    meta = FrontmatterBriefing(
        agente=f.agente,
        capitulo=f.capitulo,
        run_id=f.run_id,
        presupuesto_tokens=receta.presupuesto_tokens,
        tokens_estimados=tokens,
        degradacion=_pasos(ajuste),
        capitulo_sha256=f.sha_actual if incrusta_capitulo else None,
    )
    return Briefing(meta=meta, cuerpo=cuerpo)

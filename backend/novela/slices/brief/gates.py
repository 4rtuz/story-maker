"""Gates del borrador del `entrevistador` (spec 0005 §8.4): funciones puras.

El agente solo estructura y cita; estos gates deciden si el brief vale. Cada uno devuelve
hallazgos con códigos y rutas de campo, nunca valores: van al informe y, resumidos, al log.
"""

import re

from pydantic import ValidationError

from novela.dominio.brief import BorradorBrief, CodigoHallazgo, Fuente, Hallazgo
from novela.dominio.texto import normalizar
from novela.slices.brief import entradas
from novela.slices.brief.assemble import Entrada

EDAD_MINIMA = 12  # D7: decisión de producto, no norma
GENEROS_ADULTOS = ("noir", "thriller_psicologico")


def comparable(texto: str) -> str:
    """Lo que se compara en el brief: `normalizar`, sin espacios en los bordes y en minúsculas,
    carácter a carácter, igual que el lado de la entrada en `normalizar_con_mapa`."""
    return entradas.normalizar_con_mapa(normalizar(texto).strip())[0]


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


CERRADOS = ("destinatario.nombre", "destinatario.edad", "genero", "tono", "extension", "prohibidos")


def _fuentes(b: BorradorBrief) -> list[tuple[str, Fuente, list[str]]]:
    """Cada fuente del borrador con su ruta y los valores que tienen que salir de su cita."""
    d = b.destinatario
    fuentes: list[tuple[str, Fuente, list[str]]] = []
    if d.nombre is not None:
        fuentes.append(("destinatario.nombre", d.nombre.fuente, [d.nombre.valor]))
    if d.edad is not None:
        fuentes.append(("destinatario.edad", d.edad.fuente, []))
    fuentes += [(f"destinatario.rasgos[{i}]", r.fuente, [r.valor]) for i, r in enumerate(d.rasgos)]
    fuentes += [(f"recuerdos[{i}]", r, []) for i, r in enumerate(b.recuerdos)]
    for campo, valor in (("genero", b.genero), ("tono", b.tono), ("extension", b.extension)):
        if valor is not None:
            fuentes.append((campo, valor.fuente, []))
    if b.prohibidos is not None:
        fuentes.append(("prohibidos", b.prohibidos.fuente, list(b.prohibidos.terminos)))
    return fuentes


def _apariciones(texto: str, cita: str) -> list[int]:
    if not cita:
        return []
    posiciones, desde = [], texto.find(cita)
    while desde != -1:
        posiciones.append(desde)
        desde = texto.find(cita, desde + 1)
    return posiciones


def procedencia(b: BorradorBrief, lista: list[Entrada]) -> list[Hallazgo]:
    """RF-19 a RF-21. La cita se busca en el texto normalizado y cada aparición se traduce a un
    intervalo del original, para ver si toca un fragmento marcado: basta con que una lo toque."""
    por_id = {e.meta.id: e for e in lista}
    mapas = {e.meta.id: entradas.normalizar_con_mapa(e.texto) for e in lista}
    marcados = {
        e.meta.id: [(f.inicio, f.fin) for f in entradas.marcar(e.texto)]
        for e in lista
        if e.meta.tipo == "texto_libre"
    }
    hallazgos = []

    def hallazgo(codigo: CodigoHallazgo, campo: str, fuente: Fuente) -> None:
        hallazgos.append(
            Hallazgo(tipo="procedencia", codigo=codigo, campos=[campo], entrada=fuente.entrada)
        )

    for campo, fuente, valores in _fuentes(b):
        entrada = por_id.get(fuente.entrada)
        if entrada is None:
            hallazgo("entrada_inexistente", campo, fuente)
            continue
        texto, mapa = mapas[fuente.entrada]
        cita = comparable(fuente.cita)
        posiciones = _apariciones(texto, cita)
        if not posiciones:
            hallazgo("cita_no_literal", campo, fuente)
        if any(comparable(v) not in cita for v in valores):
            hallazgo("valor_fuera_de_cita", campo, fuente)
        if campo in CERRADOS and entrada.meta.tipo != "respuesta":
            hallazgo("campo_cerrado_desde_texto_libre", campo, fuente)
        intervalos = [(mapa[p], mapa[p + len(cita) - 1] + 1) for p in posiciones]
        if any(
            a < fin and inicio < z
            for a, z in intervalos
            for inicio, fin in marcados.get(fuente.entrada, [])
        ):
            hallazgo("cita_en_fragmento_marcado", campo, fuente)
    return hallazgos

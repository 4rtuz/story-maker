"""Estrategias de Hypothesis para los modelos del dominio.

Los tipos con patrón no se pueden inferir de las anotaciones: `st.builds` generaría cadenas
cualesquiera y el modelo las rechazaría. Cada id sale de su regex.
"""

import string
from typing import Any

from hypothesis import strategies as st

from novela.dominio.artefactos import FrontmatterCapitulo
from novela.dominio.canon import (
    Estilo,
    Giro,
    Misterio,
    MotivoMedioOportunidad,
    Pista,
    PistaFalsa,
    Reloj,
    Revelacion,
    Ritmo,
)
from novela.dominio.estado import (
    FASES,
    PASOS,
    Cursor,
    Delta,
    EntradaConocimiento,
    EntradaTemporal,
    Estado,
    EstadoPersonaje,
    EstadoPista,
    Hecho,
    Hilo,
    Metricas,
    Objeto,
    Relacion,
    Resumen,
    UsoCitado,
)
from novela.dominio.plan import FichaCapitulo
from novela.slices.validacion.gates import plegar

LETRAS = string.ascii_letters + "áéíóúñÁÉÍÓÚÑ"
# Texto de prosa: letras, espacios y puntuación; sin caracteres de control.
texto = st.text(alphabet=LETRAS + " ,;¿?¡!", min_size=1, max_size=60).map(str.strip).filter(bool)
frase = st.lists(texto, min_size=1, max_size=4).map(lambda ps: ". ".join(ps) + ".")
capitulo = st.integers(min_value=1, max_value=30)


def id_(prefijo: str) -> st.SearchStrategy[str]:
    return st.integers(min_value=0, max_value=999).map(lambda n: f"{prefijo}-{n:03d}")


personaje_id = st.from_regex(r"per-[a-z][a-z0-9]{0,8}", fullmatch=True)


def _unicos(estrategia: st.SearchStrategy[Any], clave: str, maximo: int = 5) -> Any:
    return st.lists(estrategia, max_size=maximo, unique_by=lambda x: getattr(x, clave))


pistas = _unicos(
    st.builds(
        Pista,
        id=id_("pis"),
        contenido=frase,
        capitulo_plantado=capitulo,
        capitulo_pagado=st.none() | capitulo,
        quien_la_percibe=st.lists(st.just("lector") | personaje_id, max_size=2),
        es_fair_play=st.booleans(),
    ),
    "id",
)


@st.composite
def misterios(draw: st.DrawFn) -> Misterio:
    lista = draw(pistas.filter(bool))
    ids_pista = [p.id for p in lista]
    pagadas = st.lists(st.sampled_from(ids_pista), min_size=1, max_size=3, unique=True)
    campos: dict[str, Any] = {
        "id": id_("rev"),
        "contenido": frase,
        "pistas_que_la_pagan": pagadas,
        "capitulo_previsto": capitulo,
        "quien_la_recibe": st.sampled_from(["lector", "personaje", "ambos"]),
        "impacto": st.sampled_from(["alta", "media", "baja"]),
    }
    revelaciones = draw(_unicos(st.builds(Revelacion, **campos), "id", 3))
    usados = {r.id for r in revelaciones}
    giros = draw(
        _unicos(
            st.builds(Giro, **campos, que_creia_el_lector_antes=frase).filter(
                lambda g: g.id not in usados
            ),
            "id",
            2,
        )
    )
    return Misterio(
        verdad_oculta=draw(st.lists(frase, min_size=1, max_size=3)),
        culpable_o_amenaza=draw(personaje_id),
        motivo_medio_oportunidad=MotivoMedioOportunidad(
            motivo=draw(frase), medio=draw(frase), oportunidad=draw(frase)
        ),
        pistas=lista,
        pistas_falsas=draw(
            _unicos(
                st.builds(
                    PistaFalsa,
                    id=id_("pfa"),
                    contenido=frase,
                    a_quien_apunta=personaje_id,
                    cuando_se_desmonta=st.none() | capitulo,
                ),
                "id",
                3,
            )
        ),
        revelaciones=revelaciones,
        giros=giros,
        reloj=Reloj(descripcion=draw(frase), limite=draw(texto)),
    )


estilos = st.builds(
    Estilo,
    guia_de_voz_narrativa=frase,
    ritmo=st.just(
        Ritmo(
            longitud_media_frase=14.0,
            proporcion_dialogo=0.3,
            proporcion_accion=0.4,
            proporcion_interioridad=0.3,
        )
    ),
    prohibiciones=st.lists(texto, max_size=5),
    parrafos_canonicos=st.lists(frase, min_size=1, max_size=2),
    convenciones_formato=st.just({}),
)


# --- Rama 4 ----------------------------------------------------------------------------------

escenario_id = st.from_regex(r"esc-[a-z][a-z0-9-]{0,10}", fullmatch=True)
escena_id = st.builds(lambda c, n: f"esc-{c:02d}-{n}", capitulo, st.integers(1, 9))
cita = st.none() | frase

cursores = st.builds(
    Cursor,
    capitulo=capitulo,
    fase=st.sampled_from(FASES),
    ultimo_paso=st.none() | st.sampled_from(PASOS),
    intento=st.integers(1, 3),
)
entradas_temporales = st.builds(
    EntradaTemporal,
    escena=escena_id,
    capitulo=capitulo,
    inicio=texto,
    duracion_min=st.integers(0, 600),
    cita=cita,
)
estados_personaje = st.builds(
    EstadoPersonaje,
    ubicacion=st.none() | escenario_id,
    estado_fisico=texto,
    estado_emocional=texto,
    condicion=st.sampled_from(["viva", "muerta", "desaparecida"]),
    objetivo_activo=texto,
    ultima_aparicion=capitulo,
)
entradas_conocimiento = st.builds(
    EntradaConocimiento, hecho=id_("hec"), desde_capitulo=capitulo, cita=cita
)
relaciones = st.builds(
    Relacion,
    de=personaje_id,
    a=personaje_id,
    tipo=texto,
    intensidad=st.floats(0, 1),
    desde=capitulo,
)
objetos = st.builds(
    Objeto,
    id=id_("obj"),
    poseedor=st.none() | personaje_id,
    ubicacion=st.none() | escenario_id,
    capitulo_intro=capitulo,
    relevancia=st.sampled_from(["alta", "media", "baja"]),
)
hechos = st.builds(Hecho, id=id_("hec"), texto=frase, capitulo=capitulo, cita=frase)


@st.composite
def hilos(draw: st.DrawFn) -> Hilo:
    abierto_en = draw(capitulo)
    cerrado_en = draw(st.none() | st.integers(abierto_en, 30))
    return Hilo(
        id=draw(id_("hil")),
        estado="abierto" if cerrado_en is None else "cerrado",
        abierto_en=abierto_en,
        cerrado_en=cerrado_en,
        descripcion=draw(frase),
    )


estados_pista = st.builds(
    EstadoPista,
    estado=st.sampled_from(["plantada", "pagada", "pendiente", "huerfana"]),
    plantada_en=st.none() | capitulo,
    pagada_en=st.none() | capitulo,
)

estados = st.builds(
    Estado,
    cursor=cursores,
    linea_temporal=st.lists(entradas_temporales, max_size=4, unique_by=lambda e: e.escena),
    personajes=st.dictionaries(personaje_id, estados_personaje, max_size=3),
    conocimiento=st.dictionaries(personaje_id, st.lists(entradas_conocimiento, max_size=3)),
    relaciones=st.lists(relaciones, max_size=3, unique_by=lambda r: (r.de, r.a)),
    objetos=st.lists(objetos, max_size=3, unique_by=lambda o: o.id),
    libro_de_hechos=st.lists(hechos, max_size=4, unique_by=lambda h: h.id),
    hilos=st.lists(hilos(), max_size=3, unique_by=lambda h: h.id),
    pistas=st.dictionaries(id_("pis"), estados_pista, max_size=3),
    conocimiento_lector=st.lists(entradas_conocimiento, max_size=3),
    tension_real=st.lists(st.none() | st.integers(1, 10), max_size=5),
    metricas=st.builds(
        Metricas,
        palabras_totales=st.integers(0, 10**6),
        desviacion_vs_plan=st.floats(-1, 10, allow_nan=False),
    ),
)


# --- Delta del cronista ------------------------------------------------------------------------


@st.composite
def deltas(draw: st.DrawFn, capitulo: int | None = None) -> Delta:
    """Deltas coherentes consigo mismos. Las citas no se garantizan literales de ningún cuerpo:
    quien lo necesite construye el cuerpo desde ellas (`cuerpo_con_citas`)."""
    n = capitulo if capitulo is not None else draw(st.integers(1, 30))
    escena = st.integers(1, 9).map(lambda k: f"esc-{n:02d}-{k}")
    hilo_ids = draw(st.lists(id_("hil"), max_size=3, unique=True))
    hilos_delta = []
    for h in hilo_ids:
        abre = draw(st.sampled_from([n, max(1, n - 1)]))
        cierra = draw(st.none() | st.just(n)) if abre == n else n
        hilos_delta.append(
            Hilo(
                id=h,
                estado="abierto" if cierra is None else "cerrado",
                abierto_en=abre,
                cerrado_en=cierra,
                descripcion=draw(frase),
            )
        )
    hechos_delta = draw(
        st.lists(
            st.builds(Hecho, id=id_("hec"), texto=frase, capitulo=st.just(n), cita=frase),
            max_size=3,
            unique_by=lambda h: h.id,
        )
    )
    # Usos de los hechos del propio delta: existen sin depender de ningún estado.
    usados = (
        draw(
            st.lists(
                st.builds(
                    UsoCitado, hecho=st.sampled_from([h.id for h in hechos_delta]), cita=frase
                ),
                max_size=2,
            )
        )
        if hechos_delta
        else []
    )
    return Delta(
        capitulo=n,
        linea_temporal=draw(
            st.lists(
                st.builds(
                    EntradaTemporal,
                    escena=escena,
                    capitulo=st.just(n),
                    inicio=texto,
                    duracion_min=st.integers(0, 600),
                    cita=cita,
                ),
                max_size=3,
                unique_by=lambda e: e.escena,
            )
        ),
        personajes=draw(st.dictionaries(personaje_id, estados_personaje, max_size=2)),
        conocimiento=draw(
            st.dictionaries(personaje_id, st.lists(entradas_conocimiento, max_size=2), max_size=2)
        ),
        conocimiento_lector=draw(st.lists(entradas_conocimiento, max_size=2)),
        relaciones=draw(st.lists(relaciones, max_size=2, unique_by=lambda r: (r.de, r.a))),
        objetos=draw(st.lists(objetos, max_size=2, unique_by=lambda o: o.id)),
        libro_de_hechos=hechos_delta,
        hechos_usados=usados,
        hilos=hilos_delta,
        resumen=Resumen(
            linea=draw(frase),
            parrafo=draw(frase),
            escena={f"esc-{n:02d}-1": draw(frase)},
        ),
    )


def citas(delta: Delta) -> list[str]:
    todas = [h.cita for h in delta.libro_de_hechos]
    todas += [e.cita for e in delta.linea_temporal if e.cita]
    todas += [e.cita for e in delta.conocimiento_lector if e.cita]
    todas += [e.cita for es in delta.conocimiento.values() for e in es if e.cita]
    todas += [u.cita for u in delta.hechos_usados]
    return todas


def cuerpo_con_citas(delta: Delta) -> str:
    return "# Capítulo\n\n" + "\n\n".join(["Relleno inicial.", *citas(delta), "Relleno final."])


def frontmatter_de(delta: Delta) -> FrontmatterCapitulo:
    n = delta.capitulo
    return FrontmatterCapitulo(
        capitulo=n,
        titulo="t",
        pov="per-a",
        palabras=0,
        escenas=[f"esc-{n:02d}-1"],
        hilos_abiertos=sorted(h.id for h in delta.hilos if h.abierto_en == n),
        hilos_cerrados=sorted(h.id for h in delta.hilos if h.cerrado_en == n),
        version_canon=1,
        version_plan=1,
        run_id="r-20260101-0900",
    )


# --- vp_nombres (spec 0009, CA-06) -------------------------------------------------------------

MAYUSCULAS = string.ascii_uppercase + "ÁÉÍÓÚÑ"
MINUSCULAS = string.ascii_lowercase + "áéíóúñ"
token_nombre = st.builds(
    str.__add__, st.sampled_from(MAYUSCULAS), st.text(MINUSCULAS, min_size=2, max_size=11)
)


@st.composite
def nombres_en_cuerpo(draw: st.DrawFn) -> tuple[list[tuple[str, str]], list[list[str]]]:
    """Formas `(referencia, texto)` de uno o dos tokens, sin dos tokens que plieguen igual, y las
    líneas de un cuerpo con esos tokens exactos y relleno en minúscula. Al menos una ocurrencia."""
    tokens = draw(st.lists(token_nombre, min_size=1, max_size=8, unique_by=plegar))
    formas: list[tuple[str, str]] = []
    while len(tokens) > sum(len(t.split()) for _, t in formas):
        i = sum(len(t.split()) for _, t in formas)
        k = draw(st.integers(1, 2))
        formas.append((f"per-f{len(formas)}", " ".join(tokens[i : i + k])))
    plegados = {plegar(t) for t in tokens}
    relleno = st.text(MINUSCULAS, min_size=1, max_size=8).filter(
        lambda w: plegar(w) not in plegados
    )
    palabra = st.sampled_from(tokens) | relleno
    lineas = draw(st.lists(st.lists(palabra, min_size=1, max_size=8), min_size=1, max_size=6))
    lineas[draw(st.integers(0, len(lineas) - 1))].append(draw(st.sampled_from(tokens)))
    return formas, lineas


# --- Ficha de plan coherente con un capítulo ----------------------------------------------------


@st.composite
def fichas_de(draw: st.DrawFn, capitulo: int) -> FichaCapitulo:
    """Fichas del capítulo con escenas `esc-NN-1..9`; unas las declara el frontmatter y otras no."""
    escenas = []
    for k in draw(st.lists(st.integers(1, 9), min_size=1, max_size=4, unique=True)):
        presentes = draw(st.lists(personaje_id, min_size=1, max_size=3, unique=True))
        escenas.append(
            {
                "id": f"esc-{capitulo:02d}-{k}",
                "lugar": draw(escenario_id),
                "tiempo_diegetico": "dia 1",
                "personajes": presentes,
                "dialogo": draw(st.lists(st.sampled_from(presentes), unique=True)),
                "beat": "b",
                "conflicto": "c",
            }
        )
    return FichaCapitulo.model_validate(
        {
            "capitulo": capitulo,
            "pov": draw(personaje_id),
            "objetivo_dramatico": "o",
            "escenas": escenas,
            "gancho_final": "amenaza",
            "restriccion_de_apertura": "r",
        }
    )

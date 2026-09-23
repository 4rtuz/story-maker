"""Estrategias de Hypothesis para los modelos del dominio.

Los tipos con patrón no se pueden inferir de las anotaciones: `st.builds` generaría cadenas
cualesquiera y el modelo las rechazaría. Cada id sale de su regex.
"""

import string
from typing import Any

from hypothesis import strategies as st

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

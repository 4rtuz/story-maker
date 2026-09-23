from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from novela.dominio import frontmatter
from novela.dominio.base import ColeccionAppendOnly
from novela.dominio.canon import Estilo, Misterio, Personaje
from tests import estrategias

FICHA = """---
identidad:
  id: per-elena-vidal
  nombre: Elena Vidal
  alias: [la farera]
  edad: 41
  rol_narrativo: protagonista
fisico:
  ojos: grises
  cicatriz: ceja izquierda
voz:
  idiolecto: frases cortas, nunca tutea
  muletillas: ["a ver"]
  registro: seco
  dialogo_canonico:
    - "No le pregunté. Le dije que se fuera."
psicologia:
  deseo: saber qué pasó en el faro
  necesidad: perdonarse
  miedo: el agua de noche
  herida: la muerte de su hermano
secreto:
  que_oculta: estuvo en el faro la noche del apagón
  a_quien: [per-tomas-reyes, lector]
coartada_y_cronologia_privada:
  - momento: "dia 1, 23:10"
    ubicacion: esc-casa-del-faro
    detalle: sube a la linterna y encuentra la puerta forzada
---
Elena volvió al pueblo después de nueve años.
"""


def test_ficha_personaje_estructurada() -> None:
    """CA-40: secreto y coartada son campos, la ficha hace round-trip y rechaza lo desconocido."""
    meta, cuerpo = frontmatter.partir(FICHA)
    ficha = Personaje.model_validate(meta)
    assert ficha.secreto is not None
    assert ficha.secreto.que_oculta == "estuvo en el faro la noche del apagón"
    assert ficha.coartada_y_cronologia_privada[0].ubicacion == "esc-casa-del-faro"

    texto = frontmatter.unir(ficha.model_dump(mode="json"), cuerpo)
    meta2, cuerpo2 = frontmatter.partir(texto)
    assert (Personaje.model_validate(meta2), cuerpo2) == (ficha, cuerpo)

    with pytest.raises(ValidationError, match="coartada"):
        Personaje.model_validate({**meta, "coartada": "estaba en casa"})


@given(misterio=estrategias.misterios())
def test_revelacion_sin_pista_no_se_escribe(misterio: Misterio) -> None:
    """Fair play como guardarraíl: pistas_que_la_pagan lleva mínimo una referencia existente."""
    base = misterio.model_dump(mode="json")
    rev = {
        "id": "rev-900",
        "contenido": "x",
        "pistas_que_la_pagan": [],
        "capitulo_previsto": 3,
        "quien_la_recibe": "lector",
        "impacto": "alta",
    }
    with pytest.raises(ValidationError):
        Misterio.model_validate({**base, "revelaciones": [rev]})
    usados = {p.id for p in misterio.pistas}
    ausente = next(f"pis-{n:03d}" for n in range(1000) if f"pis-{n:03d}" not in usados)
    with pytest.raises(ValidationError, match=ausente):
        revelacion = {**rev, "pistas_que_la_pagan": [ausente]}
        Misterio.model_validate({**base, "revelaciones": [revelacion]})


@given(misterio=estrategias.misterios(), estilo=estrategias.estilos, nueva=st.text())
def test_append_only_sin_trigger(misterio: Misterio, estilo: Estilo, nueva: str) -> None:
    """CA-30: ningún método público de las seis colecciones reduce su longitud ni altera una
    entrada existente. No porque falle en runtime: porque el tipo no expone el método."""
    colecciones: list[ColeccionAppendOnly[Any]] = [
        misterio.verdad_oculta,
        misterio.pistas,
        misterio.pistas_falsas,
        misterio.revelaciones,
        misterio.giros,
        estilo.prohibiciones,
    ]
    for coleccion in colecciones:
        assert {n for n in dir(coleccion) if not n.startswith("_")} == {"añadir", "entradas"}
        for mutador in ("__setitem__", "__delitem__", "__iadd__"):
            assert not hasattr(coleccion, mutador)
        antes = coleccion.entradas
        assert isinstance(antes, tuple)
        despues = coleccion.añadir(antes[0] if antes else nueva)
        assert len(despues) == len(antes) + 1
        assert despues.entradas[: len(antes)] == antes
        assert coleccion.entradas == antes

    with pytest.raises(ValidationError):
        misterio.pistas = misterio.pistas.añadir(misterio.pistas.entradas[0])  # type: ignore[misc]

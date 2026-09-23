import unicodedata

from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.base import ColeccionAppendOnly
from novela.dominio.estado import Cursor, Delta, Estado, Hecho
from novela.slices.delta import violaciones
from tests import estrategias


def _estado(capitulo: int) -> Estado:
    return Estado(cursor=Cursor(capitulo=capitulo, fase="registro", ultimo_paso=None, intento=1))


def _comprobar(delta: Delta, estado: Estado | None = None, cuerpo: str | None = None) -> list[str]:
    return violaciones.violaciones(
        estado or _estado(delta.capitulo),
        delta,
        estrategias.cuerpo_con_citas(delta) if cuerpo is None else cuerpo,
        estrategias.frontmatter_de(delta),
    )


@given(estrategias.deltas(), st.sampled_from(["hecho", "escena", "hilo", "cursor", "reescribe"]))
def test_ids_y_cursor_property(delta: Delta, defecto: str) -> None:
    """CA-18: ids duplicados y cursor decreciente se rechazan; el delta sin defecto pasa."""
    assert _comprobar(delta) == []
    estado = _estado(delta.capitulo)
    if defecto == "hecho" and delta.libro_de_hechos:
        delta = delta.model_copy(
            update={"libro_de_hechos": [*delta.libro_de_hechos, delta.libro_de_hechos[0]]}
        )
    elif defecto == "escena" and delta.linea_temporal:
        delta = delta.model_copy(
            update={"linea_temporal": [*delta.linea_temporal, delta.linea_temporal[0]]}
        )
    elif defecto == "hilo" and delta.hilos:
        delta = delta.model_copy(update={"hilos": [*delta.hilos, delta.hilos[0]]})
    elif defecto == "cursor" and delta.capitulo < 30:
        estado = _estado(delta.capitulo + 1)
    elif defecto == "reescribe" and delta.libro_de_hechos:
        viejo = delta.libro_de_hechos[0]
        otro = Hecho(id=viejo.id, texto=viejo.texto + " (otra versión)", capitulo=1, cita="c")
        estado = estado.model_copy(update={"libro_de_hechos": estado.libro_de_hechos.añadir(otro)})
    else:
        return
    assert _comprobar(delta, estado) != []


@given(estrategias.deltas())
def test_reaplicar_lo_mismo_no_es_duplicar(delta: Delta) -> None:
    """Las altas que ya están, idénticas, no son ids duplicados: reanudar repite el paso."""
    ya = ColeccionAppendOnly(delta.libro_de_hechos)
    estado = _estado(delta.capitulo).model_copy(update={"libro_de_hechos": ya})
    assert _comprobar(delta, estado) == []


@given(estrategias.deltas(), st.data())
def test_citas_property(delta: Delta, datos: st.DataObject) -> None:
    """CA-37: una cita que no es subcadena del cuerpo se rechaza; una que solo difiere en espacios
    o en forma de normalización Unicode se acepta; un delta sin citas opcionales aplica."""
    cuerpo = estrategias.cuerpo_con_citas(delta)
    assert _comprobar(delta, cuerpo=cuerpo) == []

    # Mismo texto con otros espacios y en NFD: sigue siendo la misma cita.
    otra_forma = unicodedata.normalize("NFD", cuerpo).replace(" ", " \n\t ")
    assert _comprobar(delta, cuerpo=otra_forma) == []

    sin_opcionales = delta.model_copy(
        update={
            "linea_temporal": [e.model_copy(update={"cita": None}) for e in delta.linea_temporal],
            "conocimiento_lector": [],
            "conocimiento": {},
        }
    )
    assert _comprobar(sin_opcionales) == []

    if delta.libro_de_hechos:
        inventada = datos.draw(estrategias.frase.filter(lambda c: c not in cuerpo))
        hecho = delta.libro_de_hechos[0].model_copy(update={"cita": inventada + " inventada"})
        falsa = delta.model_copy(update={"libro_de_hechos": [hecho, *delta.libro_de_hechos[1:]]})
        assert any("cita" in v for v in _comprobar(falsa, cuerpo=cuerpo))


def test_hilos_contra_frontmatter() -> None:
    """CA-38: un delta que cierra un hilo que el frontmatter no cierra, o al revés, se rechaza."""
    base = {
        "capitulo": 5,
        "hilos": [
            {
                "id": "hil-001",
                "estado": "cerrado",
                "abierto_en": 2,
                "cerrado_en": 5,
                "descripcion": "d",
            }
        ],
        "resumen": {"linea": "l", "parrafo": "p", "escena": {"esc-05-1": "e"}},
    }
    delta = Delta.model_validate(base)
    fm = estrategias.frontmatter_de(delta)
    assert violaciones.violaciones(_estado(5), delta, "", fm) == []

    no_lo_cierra = fm.model_copy(update={"hilos_cerrados": []})
    assert any("hil-001" in v for v in violaciones.violaciones(_estado(5), delta, "", no_lo_cierra))

    sin_hilos = delta.model_copy(update={"hilos": []})
    assert any("hil-001" in v for v in violaciones.violaciones(_estado(5), sin_hilos, "", fm))

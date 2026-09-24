import unicodedata
from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from novela.dominio.base import ColeccionAppendOnly
from novela.dominio.estado import (
    Cursor,
    Delta,
    EntradaConocimiento,
    Estado,
    Hecho,
    Hilo,
    UsoCitado,
)
from novela.dominio.version import PeticionDeCambio, PlanDeRegeneracion
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


@settings(max_examples=200)
@given(estrategias.deltas(), estrategias.hechos, st.data())
def test_hechos_usados_property(delta: Delta, previo: Hecho, datos: st.DataObject) -> None:
    """RF-02: cada uso cita literal del cuerpo un hecho que existe en el estado vigente o en el
    propio delta; si no, `cita no literal` o `hecho inexistente`."""
    if previo.id in {h.id for h in delta.libro_de_hechos}:
        return
    estado = _estado(delta.capitulo).model_copy(
        update={"libro_de_hechos": ColeccionAppendOnly([previo])}
    )
    cuerpo = estrategias.cuerpo_con_citas(delta) + "\n\n" + previo.cita
    del_estado = delta.model_copy(
        update={
            "hechos_usados": [*delta.hechos_usados, UsoCitado(hecho=previo.id, cita=previo.cita)]
        }
    )
    assert _comprobar(del_estado, estado, cuerpo) == []

    fuera = datos.draw(
        estrategias.id_("hec").filter(
            lambda h: h != previo.id and h not in {x.id for x in delta.libro_de_hechos}
        )
    )
    inexistente = del_estado.model_copy(
        update={
            "hechos_usados": [*del_estado.hechos_usados, UsoCitado(hecho=fuera, cita=previo.cita)]
        }
    )
    assert _comprobar(inexistente, estado, cuerpo) == [f"hecho inexistente: {fuera}"]

    inventada = datos.draw(estrategias.frase.filter(lambda c: c not in cuerpo)) + " inventada"
    no_literal = del_estado.model_copy(
        update={
            "hechos_usados": [*del_estado.hechos_usados, UsoCitado(hecho=previo.id, cita=inventada)]
        }
    )
    assert _comprobar(no_literal, estado, cuerpo) == [
        f"la cita de {previo.id} no es literal del capítulo"
    ]


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


@settings(max_examples=200)
@given(estrategias.deltas(), st.lists(estrategias.hilos(), max_size=3), st.data())
def test_hilos_sin_abrir_property(delta: Delta, previos: list[Hilo], datos: st.DataObject) -> None:
    """P2 (CA-25): en --reaplicar, un hilo que el delta cierra sin abrirlo en el capítulo tiene
    que estar abierto en el estado vigente. Si y solo si no lo está, hay causa."""
    n = delta.capitulo
    hilos = {h.id: h for h in previos}
    for id_ in datos.draw(
        st.sets(st.sampled_from([h.id for h in delta.hilos])) if delta.hilos else st.just(set())
    ):
        hilos[id_] = Hilo(id=id_, estado="abierto", abierto_en=1, descripcion="abierto antes")
    estado = _estado(n).model_copy(update={"hilos": list(hilos.values())})
    # Cerrado ya en este capítulo: es repetir el --reaplicar tras un corte.
    abiertos = {h.id for h in hilos.values() if h.estado == "abierto" or h.cerrado_en == n}
    esperados = {
        h.id
        for h in delta.hilos
        if h.cerrado_en == n and h.abierto_en != n and h.id not in abiertos
    }
    causas = violaciones.hilos_sin_abrir(estado, delta)
    assert len(causas) == len(esperados)
    assert all(any(id_ in c for c in causas) for id_ in esperados)


H, NUEVO, T = "hec-002", "hec-103", "La puerta estaba intacta."
ANTERIORES = ["hec-002", "hec-004", "hec-102", "obj-001", "obj-002"]


@settings(max_examples=200)
@given(st.data())
def test_de_regeneracion_property(datos: st.DataObject) -> None:
    """CA-28 (RF-32): hay causa `regeneracion:` si y solo si el delta del capítulo de origen
    omite el id reservado o cambia su texto, referencia H, omite o altera un requerido, o
    introduce un id de hecho u objeto de la versión anterior que no es requerido."""
    requerido = Hecho(id="hec-102", texto="La colilla.", capitulo=2, cita="c")
    anterior = _estado(6).model_copy(
        update={
            "libro_de_hechos": ColeccionAppendOnly(
                [Hecho(id=i, texto=f"texto de {i}", capitulo=2, cita="c") for i in ANTERIORES[:2]]
                + [requerido]
            ),
            "objetos": [
                o.model_copy(update={"id": i})
                for i, o in zip(
                    ANTERIORES[3:],
                    datos.draw(st.lists(estrategias.objetos, min_size=2, max_size=2)),
                    strict=True,
                )
            ],
        }
    )
    vigente_obj = datos.draw(st.sets(st.sampled_from(ANTERIORES[3:])))
    vigente = _estado(1).model_copy(
        update={"objetos": [o for o in anterior.objetos if o.id in vigente_obj]}
    )
    plan = PlanDeRegeneracion(
        regenerar=[2, 4], reaplicar=[1, 3], origen=2, requeridos={2: ["hec-102"]}
    )
    peticion = PeticionDeCambio(
        id="cam-001",
        hecho=H,
        texto_anterior="texto de hec-002",
        texto=T,
        hecho_nuevo=NUEVO,
        version_base=1,
        version_nueva=2,
        plan=plan,
        estado="en_curso",
        creado=datetime(2026, 9, 24, tzinfo=UTC),
    )
    nuevo_texto = datos.draw(st.sampled_from([T, "  La puerta  estaba intacta. ", "Otra cosa."]))
    hechos = []
    if datos.draw(st.booleans()):
        hechos.append(Hecho(id=NUEVO, texto=nuevo_texto, capitulo=2, cita="c"))
    req = datos.draw(st.sampled_from(["igual", "otro", "sin"]))
    if req != "sin":
        texto = requerido.texto if req == "igual" else "Otra colilla."
        hechos.append(requerido.model_copy(update={"texto": texto}))
    extra = datos.draw(st.sampled_from([None, "hec-004", "hec-150", H]))
    if extra:
        hechos.append(Hecho(id=extra, texto="x", capitulo=2, cita="c"))
    objetos = [
        o.model_copy(update={"id": i})
        for i, o in zip(
            datos.draw(st.lists(st.sampled_from(["obj-001", "obj-002", "obj-009"]), unique=True)),
            datos.draw(st.lists(estrategias.objetos, min_size=3, max_size=3)),
            strict=False,
        )
    ]
    en_lector = datos.draw(st.booleans())
    lector = [EntradaConocimiento(hecho=H, desde_capitulo=2)] if en_lector else []
    usado = datos.draw(st.booleans())
    usos = [UsoCitado(hecho=H, cita="c")] if usado else []
    n = datos.draw(st.sampled_from([2, 4]))
    delta = datos.draw(estrategias.deltas(capitulo=n)).model_copy(
        update={
            "libro_de_hechos": hechos,
            "objetos": objetos,
            "conocimiento": {},
            "conocimiento_lector": lector,
            "hechos_usados": usos,
        }
    )
    ids_nuevo = [h for h in hechos if h.id == NUEVO]
    a = n == 2 and not any(" ".join(h.texto.split()) == T for h in ids_nuevo)
    b = extra == H or en_lector or usado
    c = n == 2 and req != "igual"
    introducidos = {x.id for x in hechos} | ({o.id for o in objetos} - vigente_obj)
    d = bool(introducidos & (set(ANTERIORES) - ({"hec-102"} if n == 2 else set())))
    causas = violaciones.de_regeneracion(delta, peticion, anterior, vigente)
    assert bool(causas) == (a or b or c or d), (a, b, c, d, causas)
    assert all(c.startswith("regeneracion: ") for c in causas)

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from novela.dominio.estado import UsoDeHecho
from novela.dominio.version import PlanDeRegeneracion
from novela.slices.cambio import plan

VIAS = ("origen", "conocimiento", "lector", "cita")


@st.composite
def _usos_y_hecho(draw: st.DrawFn) -> tuple[list[UsoDeHecho], str, int]:
    num = draw(st.integers(1, 30))
    hechos = [f"hec-{i:03d}" for i in range(1, draw(st.integers(1, 40)) + 1)]
    usos = draw(
        st.lists(
            st.builds(
                UsoDeHecho,
                hecho=st.sampled_from(hechos),
                capitulo=st.integers(1, num),
                via=st.sampled_from(VIAS),
            ),
            max_size=120,
        )
    )
    h = draw(st.sampled_from(hechos))
    # H existe en libro_de_hechos: al menos su origen está en usos (RF-03).
    usos.append(UsoDeHecho(hecho=h, capitulo=draw(st.integers(1, num)), via="origen"))
    return draw(st.permutations(usos)), h, num


@settings(max_examples=200)
@given(_usos_y_hecho())
def test_plan_de_regeneracion_property(caso: tuple[list[UsoDeHecho], str, int]) -> None:
    """CA-13 (RF-13, RF-14): regenerar = capítulos con algún uso de H; regenerar y reaplicar
    parten 1..num_capitulos; cada requerido de a nace en a, no es H y se usa después de a."""
    usos, h, num = caso
    resultado = plan.plan_de_regeneracion(usos, h, num)
    assert isinstance(resultado, PlanDeRegeneracion)
    assert set(resultado.regenerar) == {u.capitulo for u in usos if u.hecho == h}
    assert resultado.regenerar == sorted(resultado.regenerar)
    assert resultado.reaplicar == sorted(resultado.reaplicar)
    assert not set(resultado.regenerar) & set(resultado.reaplicar)
    assert set(resultado.regenerar) | set(resultado.reaplicar) == set(range(1, num + 1))
    assert resultado.origen in resultado.regenerar
    assert (h, resultado.origen, "origen") in {(u.hecho, u.capitulo, u.via) for u in usos}
    esperados = {
        a: sorted(
            {
                u.hecho
                for u in usos
                if u.capitulo == a
                and u.via == "origen"
                and u.hecho != h
                and any(o.hecho == u.hecho and o.capitulo > a for o in usos)
            }
        )
        for a in resultado.regenerar
    }
    assert resultado.requeridos == {a: r for a, r in esperados.items() if r}


def test_plan_de_demo_cambio() -> None:
    """El plan de spec §7: hec-002 se usa en 2, 4 y 6; hec-102 nace en el 2 y lo cita el 5."""
    usos = [
        UsoDeHecho(hecho=h, capitulo=c, via=v)
        for h, c, v in (
            ("hec-002", 2, "origen"),
            ("hec-002", 2, "conocimiento"),
            ("hec-102", 2, "origen"),
            ("hec-002", 4, "cita"),
            ("hec-102", 5, "cita"),
            ("hec-002", 6, "cita"),
        )
    ]
    resultado = plan.plan_de_regeneracion(usos, "hec-002", 6)
    assert resultado == PlanDeRegeneracion(
        regenerar=[2, 4, 6], reaplicar=[1, 3, 5], origen=2, requeridos={2: ["hec-102"]}
    )


def test_id_reservado() -> None:
    """CA-14 (RF-15): el mayor número más uno, con tres dígitos; con hec-999, sin ids libres."""
    assert plan.id_reservado(["hec-001", "hec-007", "hec-102"]) == "hec-103"
    assert plan.id_reservado(["hec-009"]) == "hec-010"
    assert plan.id_reservado([]) == "hec-001"
    with pytest.raises(plan.SinIdsLibres, match="no quedan ids de hecho"):
        plan.id_reservado(["hec-001", "hec-999"])


def test_siguiente_paso() -> None:
    """RF-24: el capítulo checkpoint + 1 con el ancho del workspace, o completo."""
    p = PlanDeRegeneracion(regenerar=[2, 4, 6], reaplicar=[1, 3, 5], origen=2, requeridos={})
    assert plan.siguiente_paso(p, 0, 6) == "01 reaplicar"
    assert plan.siguiente_paso(p, 1, 6) == "02 regenerar"
    assert plan.siguiente_paso(p, 5, 6) == "06 regenerar"
    assert plan.siguiente_paso(p, 6, 6) == "completo"
    ancho = PlanDeRegeneracion(regenerar=[100], reaplicar=[], origen=100, requeridos={})
    assert plan.siguiente_paso(ancho, 99, 120) == "100 regenerar"
    assert plan.siguiente_paso(ancho, 0, 120) == "001 reaplicar"

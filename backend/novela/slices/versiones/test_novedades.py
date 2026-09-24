from hypothesis import given, settings
from hypothesis import strategies as st

from novela.slices.versiones import novedades

_shas = st.dictionaries(st.integers(1, 30), st.sampled_from(["a" * 64, "b" * 64, "c" * 64]))


@settings(max_examples=200)
@given(_shas, _shas)
def test_novedades_property(anterior: dict[int, str], actual: dict[int, str]) -> None:
    """CA-34 (RF-37): exactamente los capítulos cerrados en la versión nueva cuyo hash difiere o
    no existe en la anterior, en orden ascendente."""
    resultado = novedades.calcular(anterior, actual)
    assert resultado == sorted(resultado)
    assert set(resultado) == {c for c in actual if anterior.get(c) != actual[c]}

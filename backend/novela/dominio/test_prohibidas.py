from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.prohibidas import Termino, buscar

GLOBAL = Termino("cabrón", "global")


def _formas(cuerpo: str, *terminos: Termino) -> list[tuple[str, str, int]]:
    return [(c.termino.texto, c.forma, c.linea) for c in buscar(cuerpo, terminos)]


def test_variantes_de_caja_acento_plural_y_genero() -> None:
    cuerpo = "Era un CABRON.\nDos cabrones y una Cabrona.\nY el cabroncete no cuenta."
    assert _formas(cuerpo, GLOBAL) == [
        ("cabrón", "CABRON", 1),
        ("cabrón", "cabrones", 2),
        ("cabrón", "Cabrona", 2),
    ]


def test_diminutivo_y_plural_en_es() -> None:
    tonto = Termino("tonto", "cliente")
    assert _formas("Qué tontitas. Tontos todos.", tonto) == [
        ("tonto", "tontitas", 1),
        ("tonto", "Tontos", 1),
    ]


def test_palabra_completa() -> None:
    """«puta» no salta dentro de «disputa» ni de «computadora»."""
    assert _formas("Una disputa por la computadora.", Termino("puta", "global")) == []


def test_frase_de_varias_palabras_aunque_cruce_linea() -> None:
    frase = Termino("Casa del Faro", "novela")
    assert _formas("Volvió a la casa\ndel faro.", frase) == [("Casa del Faro", "casa del faro", 1)]
    assert _formas("La casa y el faro.", frase) == []


def test_la_enie_no_se_pliega() -> None:
    """«año» no es «ano»: plegar la tilde de la ñ inventaría insultos."""
    assert _formas("Un año entero.", Termino("ano", "global")) == []


sufijos = st.sampled_from(["", "s", "a", "as", "ito", "itas"])


@given(
    st.sampled_from(["bastardo", "imbécil", "gilipollas", "mierda", "zorra", "maricón"]),
    st.sampled_from([str.upper, str.lower, str.title, lambda s: s]),
    st.booleans(),
)
def test_toda_variante_simple_casa(base: str, caja: object, sin_tildes: bool) -> None:
    """La misma palabra en otra caja o sin tildes siempre casa con su término."""
    forma = base.translate(str.maketrans("áéíóú", "aeiou")) if sin_tildes else base
    forma = caja(forma)  # type: ignore[operator]
    [c] = buscar(f"Le dijo: {forma}, y se fue.", [Termino(base, "global")])
    assert (c.forma, c.linea) == (forma, 1)


@given(st.sampled_from(["bastard", "tont", "cabr"]), sufijos, sufijos)
def test_las_variantes_de_una_raiz_casan_entre_si(raiz: str, uno: str, otro: str) -> None:
    """Término y texto en variantes distintas (plural, género, diminutivo) de la misma raíz."""
    termino = raiz + "o" + uno if not uno.startswith(("a", "i")) else raiz + uno
    forma = raiz + "o" + otro if not otro.startswith(("a", "i")) else raiz + otro
    assert [c.forma for c in buscar(f"¡{forma}!", [Termino(termino, "global")])] == [forma]


@given(st.text(alphabet="bcdfghjklmnpqrstvwxyz ", max_size=40))
def test_sin_vocales_no_hay_falsos_positivos(texto: str) -> None:
    assert buscar(texto, [GLOBAL, Termino("tonto", "global")]) == []

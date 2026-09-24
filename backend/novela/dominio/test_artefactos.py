"""`cortar_tramo`: el encadenado de tramos de `harness.log` desde cualquier `desde` (spec 0004)."""

from hypothesis import given
from hypothesis import strategies as st

from novela.dominio.artefactos import TOPE_LECTURA_BYTES, cortar_tramo

_TEXTO = st.text(st.characters(exclude_characters="\r\n", exclude_categories=["Cs"]), max_size=40)
_LINEA = st.tuples(_TEXTO, st.sampled_from(["\n", "\r\n"]))


def _tramo(log: bytes, desde: int, tope: int) -> tuple[list[str], int]:
    """Lo que hace el repositorio: la ventana desde `desde` y si `desde` es límite de línea."""
    ventana = log[desde : desde + TOPE_LECTURA_BYTES]
    return cortar_tramo(
        ventana,
        desde,
        tope,
        en_limite=desde == 0 or log[desde - 1 : desde] == b"\n",
        hasta_el_final=desde + len(ventana) >= len(log),
    )


def _limites(log: bytes) -> list[int]:
    return [0, *(i + 1 for i, b in enumerate(log) if b == ord("\n"))]


@given(
    lineas=st.lists(_LINEA, max_size=30),
    final=_TEXTO,  # la línea incompleta del final, que no se devuelve
    tope=st.integers(1, 64),
    datos=st.data(),
)
def test_cortar_tramo_property(
    lineas: list[tuple[str, str]], final: str, tope: int, datos: st.DataObject
) -> None:
    """CA-36: desde un `desde` arbitrario —también a mitad de línea o de un carácter multibyte—,
    encadenar con cada `hasta` devuelve exactamente las líneas completas desde el primer límite
    igual o posterior, sin `\\r\\n` ni `\\n`, sin pasar del tope salvo una línea sola mayor."""
    log = "".join(t + fin for t, fin in lineas).encode() + final.encode()
    desde = datos.draw(st.integers(0, len(log)), label="desde")
    limites = _limites(log)
    primero = next((b for b in limites if b >= desde), None)
    esperadas = [
        t
        for (t, _), b in zip(lineas, limites, strict=False)
        if primero is not None and b >= primero
    ]

    vistas: list[str] = []
    while True:
        devueltas, hasta = _tramo(log, desde, tope)
        assert desde <= hasta <= len(log)
        assert all("\n" not in linea for linea in devueltas)
        if not devueltas:
            break
        assert hasta > desde  # avanza: un `hasta` relativo daría vueltas sin fin
        assert hasta in limites
        inicio = next(b for b in limites if b >= desde)
        assert hasta - inicio <= tope or len(devueltas) == 1
        vistas += devueltas
        desde = hasta
    assert vistas == esperadas


def test_linea_de_mas_de_una_lectura() -> None:
    """Una línea de más de 1 MiB da un tramo vacío con `hasta` = `desde` + 1 MiB, y el siguiente
    empieza en la línea posterior: el encadenado la salta en vez de bloquearse (D48)."""
    log = b"a" * (TOPE_LECTURA_BYTES + 10) + b"\nsiguiente\r\n"
    assert _tramo(log, 0, 65_536) == ([], TOPE_LECTURA_BYTES)
    assert _tramo(log, TOPE_LECTURA_BYTES, 65_536) == (["siguiente"], len(log))

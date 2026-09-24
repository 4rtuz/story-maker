"""Concatenación a markdown. Transporte, no edición: los cuerpos pasan tal cual."""

from collections.abc import Callable


def concatenar(cuerpos: list[str]) -> str:
    return "\n\n".join(c.strip("\n") for c in cuerpos) + "\n"


def con_novedades(
    capitulos: list[tuple[str, str]], version: int, cambiados: list[int], nn: Callable[[int], str]
) -> str:
    """RF-38: `capitulos` son pares (título, cuerpo), en orden. Delante, las novedades; un ancla
    delante de cada capítulo, y la marca bajo el encabezado de los cambiados, o al principio si
    el cuerpo no empieza por uno (plan 0007, P9)."""
    marca = f"*Modificado en la versión {version}.*"
    enlaces = [f"- [Capítulo {n} — {capitulos[n - 1][0]}](#capitulo-{nn(n)})" for n in cambiados]
    partes = [f"# Novedades de la versión {version}\n\n" + "\n".join(enlaces)]
    for n, (_, cuerpo) in enumerate(capitulos, 1):
        cuerpo = cuerpo.strip("\n")
        if n in cambiados:
            primera, _, resto = cuerpo.partition("\n")
            if primera.startswith("#"):
                cuerpo = f"{primera}\n\n{marca}\n{resto}"
            else:
                cuerpo = f"{marca}\n\n{cuerpo}"
        partes.append(f'<a id="capitulo-{nn(n)}"></a>\n\n{cuerpo}')
    return concatenar(partes)

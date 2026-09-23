"""Concatenación a markdown. Transporte, no edición: los cuerpos pasan tal cual."""


def concatenar(cuerpos: list[str]) -> str:
    return "\n\n".join(c.strip("\n") for c in cuerpos) + "\n"

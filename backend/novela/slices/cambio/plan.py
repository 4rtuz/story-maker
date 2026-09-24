"""Plan de regeneración de un cambio: funciones puras (spec 0007, D13 a D15)."""

from collections.abc import Iterable

from novela.dominio.estado import UsoDeHecho
from novela.dominio.ids import nn
from novela.dominio.version import PlanDeRegeneracion


class SinIdsLibres(ValueError):
    """Ya existe `hec-999`: el hecho nuevo no tiene id (RF-12). Salida 4."""


def plan_de_regeneracion(
    usos: Iterable[UsoDeHecho], hecho: str, num_capitulos: int
) -> PlanDeRegeneracion:
    """Regenerar = capítulos con algún uso de `hecho`, sin cascada (RF-13). Requeridos de `a` =
    los otros hechos que nacen en `a` y se usan en un capítulo posterior (RF-14)."""
    todos = list(usos)
    regenerar = sorted({u.capitulo for u in todos if u.hecho == hecho})
    origenes = sorted(u.capitulo for u in todos if u.hecho == hecho and u.via == "origen")
    ultimo_uso: dict[str, int] = {}
    for u in todos:
        ultimo_uso[u.hecho] = max(u.capitulo, ultimo_uso.get(u.hecho, 0))
    requeridos: dict[int, list[str]] = {}
    for a in regenerar:
        nacen = {u.hecho for u in todos if u.capitulo == a and u.via == "origen"} - {hecho}
        if lista := sorted(x for x in nacen if ultimo_uso[x] > a):
            requeridos[a] = lista
    return PlanDeRegeneracion(
        regenerar=regenerar,
        reaplicar=[c for c in range(1, num_capitulos + 1) if c not in regenerar],
        # Sin fila de origen (usos parciales, P12) el primer uso hace de origen.
        origen=origenes[0] if origenes else regenerar[0],
        requeridos=requeridos,
    )


def id_reservado(ids: Iterable[str]) -> str:
    """`hec-` y el mayor número más uno, con tres dígitos (RF-15)."""
    siguiente = max((int(i[-3:]) for i in ids), default=0) + 1
    if siguiente > 999:
        raise SinIdsLibres("no quedan ids de hecho: ya existe hec-999")
    return f"hec-{siguiente:03d}"


def siguiente_paso(plan: PlanDeRegeneracion, cerrados: int, num_capitulos: int) -> str:
    """`NN reaplicar`, `NN regenerar` o `completo`, para el capítulo `cerrados + 1` (RF-24)."""
    if cerrados >= num_capitulos:
        return "completo"
    capitulo = cerrados + 1
    que = "regenerar" if capitulo in plan.regenerar else "reaplicar"
    return f"{nn(capitulo, num_capitulos)} {que}"

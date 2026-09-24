"""`/lanzamientos`: el panel lanza, reanuda y detiene `novela producir`, y consulta por dónde va.

Es la única superficie de la API que ejecuta algo, y ejecuta `claude` sin preguntar. Por eso
cada `POST` pasa por `_solo_el_panel` antes de leer el cuerpo:

- **Cliente de loopback.** Nadie de la red llega aunque uvicorn escuche en 0.0.0.0.
- **Host local.** Un dominio que resuelve a 127.0.0.1 (DNS rebinding) no pasa.
- **Origin del panel, o ninguno.** Un navegador siempre manda Origin en un POST entre orígenes;
  una web cualquiera abierta en el mismo equipo no puede lanzar nada. Sin Origin, es un cliente
  local sin navegador (curl), que ya podría ejecutar `novela` por su cuenta.
- **Cuerpo JSON validado.** Un formulario HTML no manda JSON sin preflight, y el preflight solo
  lo admite el CORS del panel. Slug por la misma regex que el CLI, sin campos de más.

Lo que se lanza es siempre `python -m novela producir` con argumentos en lista: ni shell ni
órdenes libres. Uno a la vez en toda la máquina (`lanzador.en_marcha`).
"""

import threading
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from novela.dominio.ids import SLUG_PATRON
from novela.dominio.lanzamiento import Lanzamiento, PeticionDeLanzamiento
from novela.plataforma import lanzador
from novela.plataforma.workspace import raiz_de_novelas

ORIGENES = {"http://localhost:5173", "http://127.0.0.1:5173"}
LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_decidir = threading.Lock()  # comprobar y lanzar, sin que dos POST se crucen


def _solo_el_panel(request: Request) -> None:
    host = (request.headers.get("host") or "").rsplit(":", 1)[0].strip("[]")
    origen = request.headers.get("origin")
    if request.client is None or request.client.host not in LOOPBACK:
        raise HTTPException(403, "solo se lanza desde este equipo")
    if host not in LOOPBACK:
        raise HTTPException(403, f"host no admitido: {host!r}")
    if origen is not None and origen not in ORIGENES:
        raise HTTPException(403, f"origen no admitido: {origen!r}")


SoloElPanel = Depends(_solo_el_panel)
SlugPath = Annotated[str, Path(pattern=SLUG_PATRON)]
SLUG = "/{slug:path}"  # como en novelas.py: `%2F` no esquiva la validación

router = APIRouter(prefix="/lanzamientos", tags=["lanzamientos"])


def _lanzar(argumentos: list[str], comprobar: str) -> Lanzamiento:
    with _decidir:
        if error := lanzador.raiz_correcta():
            raise HTTPException(409, error)
        if lanzador.en_marcha():
            raise HTTPException(409, "ya hay un lanzamiento en marcha: espera o detenlo")
        existe = (raiz_de_novelas() / argumentos[1]).exists()
        if comprobar == "nueva" and existe:
            raise HTTPException(409, f"ya existe una novela {argumentos[1]}: usa reanudar")
        if comprobar == "reanudar" and not existe:
            raise HTTPException(404, f"no existe la novela {argumentos[1]}")
        inicial = lanzador.nuevo(argumentos[1], "entorno", "arrancando")
        lanzador.escribir(inicial)
        lanzador.lanzar(argumentos)
        return inicial


@router.post("", status_code=202, dependencies=[SoloElPanel])
def crear(peticion: PeticionDeLanzamiento) -> Lanzamiento:
    argumentos = ["producir", peticion.slug, "--idea", peticion.idea]
    if peticion.capitulos:
        argumentos += ["--capitulos", str(peticion.capitulos)]
    if peticion.palabras:
        argumentos += ["--palabras", str(peticion.palabras)]
    return _lanzar(argumentos, "nueva")


@router.post(SLUG + "/reanudar", status_code=202, dependencies=[SoloElPanel])
def reanudar(slug: SlugPath) -> Lanzamiento:
    return _lanzar(["producir", slug], "reanudar")


@router.post(SLUG + "/detener", status_code=202, dependencies=[SoloElPanel])
def detener(slug: SlugPath) -> Lanzamiento:
    """Para tras el capítulo en curso: matar una sesión a medias dejaría el capítulo sin cerrar."""
    actual = lanzador.leer(slug)
    if actual is None or actual.estado != "en_marcha":
        raise HTTPException(409, f"{slug} no está en marcha")
    lanzador.pedir_detener(slug)
    return actual.model_copy(update={"detener_pedido": True})


@router.get("")
def lanzamientos() -> list[Lanzamiento]:
    return lanzador.listar()


@router.get(SLUG)
def lanzamiento(slug: SlugPath) -> Lanzamiento:
    actual = lanzador.leer(slug)
    if actual is None:
        raise HTTPException(404, f"{slug} no se ha lanzado desde el panel")
    return actual

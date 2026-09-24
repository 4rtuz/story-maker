"""Generador cronología → `Cronologia.lean` y su compilación contra `formal/lean/`.

Lean trabaja con ids numéricos: comparar `Nat` es barato para `decide`, comparar `String` no. La
`Tabla` es la correspondencia, en los dos sentidos: numera al generar y traduce el informe de
vuelta. Los nombres quedan en comentarios del fichero, para quien lo lea.
"""

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from novela.dominio.estado import EventoCronologia

PROYECTO = Path(__file__).resolve().parents[4] / "formal" / "lean"
_BIBLIOTECA = PROYECTO / ".lake" / "build" / "lib" / "lean"
_INVARIANTES = PROYECTO / "StoryMaker" / "Invariantes.lean"
_OLEAN = _BIBLIOTECA / "StoryMaker" / "Invariantes.olean"
TIMEOUT_S = 600

Invariante = Literal["orden", "edad", "ubicuidad", "exclusion"]
# Nombre del teorema del fichero generado → checker de StoryMaker.Invariantes, su lema y su Prop.
INVARIANTES: dict[Invariante, tuple[str, str, str]] = {
    "orden": ("respetaOrden", "respetaOrden_correcto", "RespetaOrden"),
    "edad": ("edadesCoherentes", "edadesCoherentes_correcto", "EdadesCoherentes"),
    "ubicuidad": ("sinUbicuidad", "sinUbicuidad_correcto", "SinUbicuidad"),
    "exclusion": ("respetaExclusiones", "respetaExclusiones_correcto", "RespetaExclusiones"),
}


class LeanAusente(RuntimeError):
    """No hay `lean` en el PATH ni en ~/.elan/bin: el gate falla, no se salta."""


@dataclass(frozen=True)
class Tabla:
    eventos: tuple[str, ...]
    personajes: tuple[str, ...]
    lugares: tuple[str, ...]

    @classmethod
    def de(cls, eventos: Sequence[EventoCronologia], edades: Mapping[str, int]) -> "Tabla":
        ids = [e.id for e in eventos]
        # Un `tras` a un evento que no existe también lleva número: el invariante (a) lo caza.
        ids += sorted({t for e in eventos for t in e.tras} - set(ids))
        personajes = {p for e in eventos for p in (*e.personajes, *e.excluye)} | set(edades)
        return cls(tuple(ids), tuple(sorted(personajes)), tuple(sorted({e.lugar for e in eventos})))


@dataclass(frozen=True)
class Violacion:
    invariante: Invariante
    evento: str
    personaje: str | None
    otro: str  # el evento con el que choca, o la edad declarada


def _lista(valores: Sequence[object]) -> str:
    return "[" + ", ".join(str(v) for v in valores) + "]"


def generar(slug: str, eventos: Sequence[EventoCronologia], edades: Mapping[str, int]) -> str:
    t = Tabla.de(eventos, edades)
    per, lug, evt = (
        {n: i for i, n in enumerate(xs)} for xs in (t.personajes, t.lugares, t.eventos)
    )
    lineas = [
        f"-- Generado por `novela verificar-lean {slug}`. No editar: se regenera desde el estado.",
        "import StoryMaker.Invariantes",
        "open StoryMaker",
        "",
        *(f"-- personaje {i}: {n}" for i, n in enumerate(t.personajes)),
        *(f"-- lugar {i}: {n}" for i, n in enumerate(t.lugares)),
        "",
        "def cronologia : Cronologia where",
        "  eventos := [",
    ]
    for i, e in enumerate(eventos):
        edades_e = [f"({per[p]}, {a})" for p, a in sorted(e.edades.items())]
        coma = "," if i < len(eventos) - 1 else ""
        lineas += [
            f"    -- {i}: {e.id}",
            f"    {{ id := {i}, momento := {e.momento}, duracion := {e.duracion_min}, "
            f"lugar := {lug[e.lugar]},",
            f"      presentes := {_lista([per[p] for p in e.personajes])}, "
            f"excluidos := {_lista([per[p] for p in e.excluye])},",
            f"      edades := {_lista(edades_e)}, "
            f"tras := {_lista([evt[x] for x in e.tras])} }}{coma}",
        ]
    lineas += [
        "  ]",
        f"  edadAlInicio := {_lista([f'({per[p]}, {a})' for p, a in sorted(edades.items())])}",
        "",
        "#eval informe cronologia",
        "",
    ]
    for nombre, (checker, lema, prop) in INVARIANTES.items():
        lineas += [
            f"theorem {nombre} : {checker} cronologia = true := by decide +kernel",
            f"example : {prop} cronologia := {lema} _ {nombre}",
        ]
    return "\n".join(lineas) + "\n"


def violaciones(salida: str, tabla: Tabla) -> list[Violacion]:
    """Traduce las líneas `VIOLACION|inv|evento|personaje|otro` que imprime `informe`."""
    resultado = []
    for linea in salida.splitlines():
        partes = linea.strip().split("|")
        if len(partes) != 5 or partes[0] != "VIOLACION" or partes[1] not in INVARIANTES:
            continue
        _, inv, evento, personaje, otro = partes
        resultado.append(
            Violacion(
                invariante=cast(Invariante, inv),
                evento=tabla.eventos[int(evento)],
                personaje=tabla.personajes[int(personaje)] if personaje else None,
                otro=otro if inv == "edad" else tabla.eventos[int(otro)],
            )
        )
    return resultado


def buscar_lean() -> str | None:
    if encontrado := shutil.which("lean"):
        return encontrado
    elan = Path.home() / ".elan" / "bin" / ("lean.exe" if os.name == "nt" else "lean")
    return str(elan) if elan.is_file() else None


def _lean(binario: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — binario y argumentos los fija el harness
        [binario, *args],
        cwd=PROYECTO,
        env={**os.environ, "LEAN_PATH": str(_BIBLIOTECA)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_S,
        check=False,
    )


def compilar(fichero: Path) -> tuple[int, str]:
    """Compila `StoryMaker.Invariantes` si hace falta y después `fichero`. Devuelve el código de
    salida de Lean y su salida entera. Sin `lake`: hay máquinas donde Device Guard lo bloquea, y
    `lean` con `LEAN_PATH` basta para un proyecto sin dependencias."""
    binario = buscar_lean()
    if binario is None:
        raise LeanAusente("lean no está instalado: ni en el PATH ni en ~/.elan/bin")
    # ponytail: sin lock; dos verificaciones a la vez con el olean caducado lo compilan dos veces.
    if not _OLEAN.is_file() or _OLEAN.stat().st_mtime < _INVARIANTES.stat().st_mtime:
        _OLEAN.parent.mkdir(parents=True, exist_ok=True)
        r = _lean(binario, str(_INVARIANTES), "-o", str(_OLEAN))
        if r.returncode:
            return r.returncode, f"StoryMaker/Invariantes.lean no compila:\n{r.stdout}{r.stderr}"
    r = _lean(binario, str(fichero))
    return r.returncode, r.stdout + r.stderr

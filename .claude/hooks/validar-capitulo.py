"""PostToolUse del harness (spec 0008): `novela validar --origen hook` en cuanto el `escritor` o el
`editor-estilo` escriben `novelas/<slug>/capitulos/NN.md`.

Aprueba con exit 0 y sin salida; con hallazgos, o ante cualquier cosa que no entiende, sale con 2
y el motivo en stderr, que Claude Code entrega al agente. La escritura ya está hecha: el 2 no la
deshace. Falla cerrado porque cualquier otro código Claude Code lo trata como no bloqueante. Solo
stdlib: corre fuera del venv de backend/ y no puede importarlo. No escribe nada; lo que se escribe
lo escribe `novela validar`.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PREFIJO = "validar-capitulo:"
LIMITE = 4000  # caracteres de feedback, RNF-04
TIEMPO = 45  # s: antes de los 60 del registro, para que el fallo sea nuestro y cerrado (D13)
_HERRAMIENTAS = frozenset({"Write", "Edit", "MultiEdit"})
_ROLES = frozenset({"escritor", "editor-estilo"})
# Al final de la ruta y con el slug de un solo segmento: `versiones/vN/capitulos/` no casa.
_CAPITULO = re.compile(r"/(novelas)/([^/]+)/capitulos/(\d{2,3})\.md\Z", re.IGNORECASE | re.ASCII)


def capitulo_de(entrada: dict[str, Any]) -> tuple[str, str, str] | None:
    """(directorio novelas, slug, NN tal como se escribió), o None si está fuera de alcance. Lee
    solo tool_name, tool_input.file_path, cwd y agent_type. Lanza ante lo que no entiende."""
    if entrada["tool_name"] not in _HERRAMIENTAS:
        return None
    # null o "" cuentan como «no viene»: se valida, que es fallar cerrado (validators Q1).
    rol = entrada.get("agent_type") or None
    if rol is not None and rol not in _ROLES:
        return None
    ruta = entrada["tool_input"]["file_path"]
    if not isinstance(ruta, str) or not ruta:
        raise ValueError("tool_input.file_path vacío o no es texto")
    cwd = entrada.get("cwd") or os.getcwd()
    normal = os.path.normpath(os.path.join(cwd, ruta.replace("\\", "/"))).replace("\\", "/")
    m = _CAPITULO.search(normal)
    if m is None:
        return None
    return normal[: m.end(1)], m[2], m[3]


def leer_hallazgos(raiz: Path, nn: str) -> list[dict[str, Any]]:
    """Los hallazgos de `qa/NN-validacion.json`, si es el informe del capítulo que hay en disco.
    Un traceback también sale con 1: sin el sha, se reenviarían los de una validación anterior."""
    informe = raiz / "qa" / f"{nn}-validacion.json"
    if not informe.is_file():
        raise ValueError(f"no existe qa/{nn}-validacion.json")
    datos = json.loads(informe.read_bytes())
    sha = hashlib.sha256((raiz / "capitulos" / f"{nn}.md").read_bytes()).hexdigest()
    if not isinstance(datos, dict) or datos.get("capitulo_sha256") != sha:
        raise ValueError(f"qa/{nn}-validacion.json no es el informe del capítulo en disco")
    hallazgos = datos.get("hallazgos")
    if not isinstance(hallazgos, list) or not hallazgos:
        raise ValueError(f"qa/{nn}-validacion.json sin hallazgos tras un rechazo")
    for h in hallazgos:
        if not (
            isinstance(h, dict)
            and all(isinstance(h.get(c), str) for c in ("tipo", "gravedad", "descripcion"))
            and isinstance(h.get("ubicacion"), str | None)
        ):
            raise ValueError(f"qa/{nn}-validacion.json con un hallazgo ilegible")
    return hallazgos


def mensaje_rechazo(nn: str, hallazgos: list[dict[str, Any]]) -> str:
    cabecera = (
        f"{PREFIJO} capitulos/{nn}.md rechazado por novela validar ({len(hallazgos)} hallazgos en "
        f"qa/{nn}-validacion.json). Corrige el capítulo y vuelve a escribirlo:"
    )
    lineas = [
        f"- {h['tipo']} ({h['gravedad']}) {h.get('ubicacion') or 'sin ubicación'}: "
        + " ".join(h["descripcion"].split())
        for h in hallazgos
    ]
    texto = "\n".join([cabecera, *lineas])
    return texto if len(texto) <= LIMITE else texto[: LIMITE - 1] + "…"


def mensaje_fallo(causa: str) -> str:
    causa = " ".join(causa.split())[:300]
    fin = "No reescribas el capítulo: termina e informa."
    return f"{PREFIJO} fallo del harness, no del capítulo: {causa}. {fin}"


def ejecutar(datos: bytes) -> tuple[int, str]:
    """(código de salida, stderr). Nunca lanza: cualquier excepción es fallo del harness."""
    try:
        destino = capitulo_de(json.loads(datos.decode("utf-8")))
        if destino is None:
            return 0, ""
        novelas, slug, nn = destino
        novela = shutil.which("novela")
        if novela is None:
            return 2, mensaje_fallo("novela no resuelve en el PATH")
        try:
            # Lista y sin shell: el slug sale de un nombre de directorio. Solo se reenvía texto
            # propio, nunca la salida del CLI (D7). ponytail: en Windows el timeout mata el
            # lanzador .exe; el Python hijo cae con él por el job object del lanzador de uv.
            r = subprocess.run(  # noqa: S603
                [novela, "validar", slug, str(int(nn)), "--origen", "hook"],
                env=os.environ | {"NOVELAS_DIR": novelas},
                capture_output=True,
                timeout=TIEMPO,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return 2, mensaje_fallo(f"novela validar no terminó en {TIEMPO} s")
        if r.returncode == 0:
            return 0, ""
        if r.returncode != 1:
            return 2, mensaje_fallo(f"novela validar salió con {r.returncode}")
        return 2, mensaje_rechazo(nn, leer_hallazgos(Path(novelas, slug), nn))
    except Exception as exc:  # noqa: BLE001 — falla cerrado (RF-04)
        return 2, mensaje_fallo(f"{type(exc).__name__}: {exc}")


def main() -> int:
    # Bytes en las dos direcciones: en Windows la página de códigos rompería tildes y el `…`.
    codigo, mensaje = ejecutar(sys.stdin.buffer.read())
    sys.stderr.buffer.write(mensaje.encode("utf-8"))
    return codigo


if __name__ == "__main__":
    sys.exit(main())

"""Versiones de la novela (spec 0007): edición vigente, cambio en curso e instantáneas.

Una versión nueva no reescribe la anterior: la guarda entera en `versiones/vN/`, verificada, y
empieza en la raíz con una base vacía (ADR 0004). La preparación sigue el orden de RF-19 con
`cambios/cam-NNN.json` en `preparando` como diario: repetirla tras un corte la completa (RF-20).
"""

import os
import shutil
import sqlite3
from collections.abc import Callable
from pathlib import Path

from novela.dominio.base import ColeccionAppendOnly
from novela.dominio.estado import Cursor, Estado
from novela.dominio.version import (
    PeticionDeCambio,
    RegistroDeVersiones,
    Version,
    VersionRegistrada,
)
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceInvalido, WorkspaceRepository, sha256

# Lo que entra en la instantánea además de la base (RF-17). canon/ no: pondría misterio.md en
# una ruta que el deny de lectura no cubre (spec 0007, D8).
COPIADOS = ("capitulos", "estado/deltas", "memoria", "qa", "checkpoints")
BASE = "estado/estado.db"


class VersionInexplicada(WorkspaceInvalido):
    """`versiones/vN/` existe sin un cambio en `preparando` que lo explique (RF-21). Salida 4."""


class InstantaneaInvalida(WorkspaceInvalido):
    """La copia no casa con la raíz: un sha256, `quick_check` o `leer` distintos. Salida 4."""


def _meta(conn: sqlite3.Connection, clave: str) -> str | None:
    fila = conn.execute("SELECT valor FROM meta WHERE clave = ?", (clave,)).fetchone()
    return None if fila is None else str(fila[0])


def version_vigente(conn: sqlite3.Connection) -> int:
    """`meta.version`, o la 1 si la base no la tiene (RF-16)."""
    return int(_meta(conn, "version") or 1)


def _ruta_cambio(ws: WorkspaceRepository, cambio: str) -> Path:
    return ws.raiz / "cambios" / f"{cambio}.json"


def ultimo_cambio(ws: WorkspaceRepository) -> PeticionDeCambio | None:
    """El último `cam-NNN.json`, en el estado que esté."""
    rutas = sorted((ws.raiz / "cambios").glob("cam-*.json"))
    return ws.leer_json(rutas[-1], PeticionDeCambio) if rutas else None


def cambio_en_curso(ws: WorkspaceRepository) -> PeticionDeCambio | None:
    """El último cambio si está `en_curso` y la raíz no tiene aún el checkpoint del último
    capítulo: con él, el cambio está completo, y eso se deriva, no se escribe (spec 0007, D12)."""
    cambio = ultimo_cambio(ws)
    if cambio is None or cambio.estado != "en_curso":
        return None
    punto = ws.ultimo_checkpoint()
    completo = punto is not None and punto.capitulo >= ws.config().parametros_obra.num_capitulos
    return None if completo else cambio


def _sin_corte(punto: str) -> None:
    """Los cortes de CA-18 se inyectan aquí (D6)."""


def registrar_peticion(ws: WorkspaceRepository, peticion: PeticionDeCambio) -> None:
    """Paso 1 de RF-19: `cam-NNN.json` en `preparando`. Antes, el rechazo de RF-21."""
    destino = ws.raiz / "versiones" / f"v{peticion.version_base}"
    previo = ultimo_cambio(ws)
    explicado = previo is not None and previo.id == peticion.id and previo.estado == "preparando"
    if destino.exists() and not explicado:
        raise VersionInexplicada(f"{destino}: existe sin un cambio en preparando que la explique")
    preparando = peticion.model_copy(update={"estado": "preparando"})
    ws.escribir(_ruta_cambio(ws, peticion.id), preparando.model_dump_json(indent=2))


def _copiar(
    ws: WorkspaceRepository, tmp: Path, peticion: PeticionDeCambio, corte: Callable[[str], None]
) -> None:
    """Pasos 2 y 3: copia a `vN.tmp/`, verificación y `version.json`."""
    for i, directorio in enumerate(COPIADOS):
        if (ws.raiz / directorio).is_dir():
            ignorar = shutil.ignore_patterns("*.tmp")
            shutil.copytree(ws.raiz / directorio, tmp / directorio, ignore=ignorar)
        if i == len(COPIADOS) // 2:
            corte("mitad_copia")
    copia = tmp / BASE
    copia.parent.mkdir(parents=True, exist_ok=True)
    with estado_db.abrir(ws.estado_db) as conn:
        # D5: sin WAL pendiente en la raíz, y la copia en modo DELETE, que se lee en solo lectura
        # sin crear -wal ni -shm dentro de una versión que ya no se escribe.
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        vigente, cambio = estado_db.leer(conn), _meta(conn, "cambio")
        destino = sqlite3.connect(copia)
        try:
            conn.backup(destino)
            destino.execute("PRAGMA journal_mode = DELETE")
            # Una tabla o un índice ocupa al menos una página: con 1 KiB en vez de 4, la copia
            # de una novela pequeña no pesa el triple de sus datos (RNF-08).
            destino.execute("PRAGMA page_size = 1024")
            destino.execute("VACUUM")
        finally:
            destino.close()

    ficheros: dict[str, str] = {}
    for directorio in COPIADOS:
        for original in sorted((ws.raiz / directorio).rglob("*")):
            if not original.is_file() or original.suffix == ".tmp":
                continue
            relativa = original.relative_to(ws.raiz).as_posix()
            copiado = tmp / relativa
            if not copiado.is_file() or sha256(copiado) != sha256(original):
                raise InstantaneaInvalida(f"{copiado}: la copia no casa con {original}")
            ficheros[relativa] = sha256(copiado)
    with estado_db.abrir(copia, solo_lectura=True) as conn:
        if conn.execute("PRAGMA quick_check").fetchone() != ("ok",) or estado_db.leer(conn) != (
            vigente
        ):
            raise InstantaneaInvalida(f"{copia}: la base copiada no lee igual que la vigente")
    ficheros[BASE] = sha256(copia)
    punto = ws.ultimo_checkpoint()
    version = Version(
        numero=peticion.version_base,
        creada=peticion.creado,
        cambio=cambio,
        capitulos_sha256=punto.capitulos_sha256 if punto else {},
        ficheros=ficheros,
    )
    ws.escribir(tmp / "version.json", version.model_dump_json(indent=2))


def _registrar_version(ws: WorkspaceRepository, peticion: PeticionDeCambio) -> None:
    """Paso 5: la versión nueva en `versiones/versiones.json`, una sola vez."""
    ruta = ws.raiz / "versiones" / "versiones.json"
    if ruta.exists():
        registro = ws.leer_json(ruta, RegistroDeVersiones)
    else:
        original = VersionRegistrada(numero=1, cambio=None, creada=peticion.creado)
        registro = RegistroDeVersiones(versiones=ColeccionAppendOnly([original]))
    if len(registro.versiones) >= peticion.version_nueva:
        return
    nueva = VersionRegistrada(
        numero=peticion.version_nueva, cambio=peticion.id, creada=peticion.creado
    )
    registro = RegistroDeVersiones(versiones=registro.versiones.añadir(nueva))
    ws.escribir(ruta, registro.model_dump_json(indent=2))


def _vaciar(ws: WorkspaceRepository, corte: Callable[[str], None]) -> None:
    """Paso 6. El árbol queda como lo deja `novela nueva`."""
    for directorio in COPIADOS:
        ruta = ws.raiz / directorio
        if ruta.exists():
            shutil.rmtree(ruta)
        ruta.mkdir(parents=True)
        if directorio == "capitulos":
            corte("capitulos_vaciados")
    (ws.raiz / "memoria" / "resumenes").mkdir()


def _base_nueva(ws: WorkspaceRepository, peticion: PeticionDeCambio) -> None:
    """Paso 7 (D5): la base se crea aparte y se instala sin -wal ni -shm viejos al lado."""
    ruta = ws.estado_db
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.unlink(missing_ok=True)
    estado_db.crear(tmp, version=peticion.version_nueva, cambio=peticion.id)
    with estado_db.abrir(tmp) as conn, estado_db.transaccion(conn):
        inicial = Cursor(capitulo=1, fase="escritura", ultimo_paso=None, intento=1)
        estado_db.guardar(conn, Estado(cursor=inicial))
    for sufijo in ("-wal", "-shm"):
        ruta.with_name(ruta.name + sufijo).unlink(missing_ok=True)
    os.replace(tmp, ruta)


def preparar(
    ws: WorkspaceRepository,
    peticion: PeticionDeCambio,
    corte: Callable[[str], None] = _sin_corte,
) -> None:
    """Pasos 2 a 8 de RF-19, tras `registrar_peticion` y con el lock tomado. Con `vN.tmp/` de un
    corte, se borra y se copia de nuevo; con `vN/` ya renombrado, se sigue desde el paso 5."""
    versiones = ws.raiz / "versiones"
    destino = versiones / f"v{peticion.version_base}"
    if not destino.exists():
        tmp = versiones / f"v{peticion.version_base}.tmp"
        if tmp.exists():
            shutil.rmtree(tmp)
        _copiar(ws, tmp, peticion, corte)
        os.replace(tmp, destino)  # punto de confirmación: desde aquí vN/ no se toca
        corte("renombrado")
    _registrar_version(ws, peticion)
    _vaciar(ws, corte)
    _base_nueva(ws, peticion)
    en_curso = peticion.model_copy(update={"estado": "en_curso"})
    ws.escribir(_ruta_cambio(ws, peticion.id), en_curso.model_dump_json(indent=2))

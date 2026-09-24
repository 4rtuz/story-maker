import shutil
import sqlite3
import time
from collections.abc import Callable
from contextlib import AbstractContextManager, closing
from pathlib import Path

import pytest
from typer.testing import Result

from novela.dominio.version import PeticionDeCambio
from novela.plataforma import estado_db, versiones
from novela.plataforma.workspace import WorkspaceRepository, huella
from tests.fixtures import fabrica

Novelas = Callable[[str], WorkspaceRepository]
TEXTO = "La puerta de la linterna estaba intacta en la noche 2."
PETICION = ("--hecho", "hec-002", "--texto", TEXTO)


def _cambio(ws: WorkspaceRepository, *args: str) -> Result:
    # Sin NOVELA_RUN_ID: el run de `novela cambio` sale del reloj, como en una sesión real.
    return fabrica.cli(
        ws.raiz.parent,
        "cambio",
        ws.slug,
        *args,
        run="",
        entorno={"NOVELAS_DIR": str(ws.raiz.parent)},
    )


def _huella(ws: WorkspaceRepository) -> str:
    """Sin los -wal y -shm de SQLite, que son efímeros: en Windows, abrir la base en solo
    lectura los crea o los toca, y no son parte de lo que el subcomando escribe."""
    copia = ws.raiz.parent / "huella"
    shutil.rmtree(copia, ignore_errors=True)
    shutil.copytree(ws.raiz, copia, ignore=shutil.ignore_patterns("*-wal", "*-shm"))
    try:
        return huella(copia)
    finally:
        shutil.rmtree(copia)


def test_simular(novelas: Novelas) -> None:
    """CA-08 (RF-08): el plan y el id reservado, sin escribir nada."""
    ws = novelas("demo-cambio")
    antes = _huella(ws)
    resultado = _cambio(ws, *PETICION, "--simular")
    assert resultado.exit_code == 0, resultado.output
    for esperado in ("hec-103", "regenerar 02, 04, 06", "requeridos 02: hec-102"):
        assert esperado in resultado.output
    assert "reaplicar 01, 03, 05" in resultado.output
    assert _huella(ws) == antes


def test_peticion_registrada(novelas: Novelas) -> None:
    """CA-09 (RF-09) y la línea de RF-44."""
    ws = novelas("demo-cambio")
    resultado = _cambio(ws, *PETICION, "--motivo", "petición del lector")
    assert resultado.exit_code == 0, resultado.output
    assert resultado.output.strip() == (
        "cambio cam-001: hec-002 → hec-103 · versión 2 · regenerar 02, 04, 06 · "
        "reaplicar 3 capítulos"
    )
    peticion = ws.leer_json(ws.raiz / "cambios" / "cam-001.json", PeticionDeCambio)
    assert peticion.estado == "en_curso" and peticion.motivo == "petición del lector"
    assert (peticion.hecho_nuevo, peticion.version_base, peticion.version_nueva) == (
        "hec-103",
        1,
        2,
    )
    assert not [f for f in ws.raiz.rglob("*") if f.name.endswith(".tmp")]
    logs = [p.read_text(encoding="utf-8") for p in (ws.raiz / "runs").glob("*/harness.log")]
    assert sum("cambio cam-001 -> 0" in log for log in logs) == 1


def test_precondiciones(novelas: Novelas, tmp_path: Path) -> None:
    """CA-10 (RF-10): sin terminar, con un cambio en curso o con una intervención viva, 1 sin
    escribir nada."""
    ws = novelas("demo-cambio")
    base = tmp_path / "copias"

    def copia(nombre: str) -> WorkspaceRepository:
        otra = WorkspaceRepository(base / nombre / ws.slug)
        shutil.copytree(ws.raiz, otra.raiz)
        return otra

    a_medias = copia("a-medias")
    cuatro = (a_medias.raiz / "checkpoints" / "04.json").read_bytes()
    (a_medias.raiz / "checkpoints" / "latest.json").write_bytes(cuatro)
    en_curso = copia("en-curso")
    assert _cambio(en_curso, *PETICION).exit_code == 0
    intervenida = copia("intervenida")
    (intervenida.raiz / "runs" / fabrica.run_id(6) / "intervencion.md").write_text(
        "gate: continuidad\nintentos: 3\n", encoding="utf-8"
    )
    for otra, causa in (
        (a_medias, "novela sin terminar"),
        (en_curso, "cambio en curso: cam-001"),
        (intervenida, "intervención sin resolver"),
    ):
        antes = _huella(otra)
        resultado = _cambio(otra, *PETICION)
        assert resultado.exit_code == 1, (causa, resultado.output)
        assert causa in resultado.output
        assert _huella(otra) == antes

    resuelta = copia("resuelta")
    (resuelta.raiz / "runs" / fabrica.run_id(6) / "intervencion.md").write_text(
        "gate: continuidad\nresuelto: arreglado a mano\n", encoding="utf-8"
    )
    assert _cambio(resuelta, *PETICION, "--simular").exit_code == 0


def test_argumentos_invalidos(novelas: Novelas) -> None:
    """CA-11 (RF-11) y la exclusión de --siguiente: 2 sin escribir nada."""
    ws = novelas("demo-cambio")
    vigente = "La puerta de la linterna estaba forzada en la noche 2."
    antes = _huella(ws)
    for args in (
        ("--hecho", "hec-2", "--texto", TEXTO),
        ("--hecho", "hec-900", "--texto", TEXTO),
        ("--hecho", "hec-002", "--texto", "   "),
        ("--hecho", "hec-002", "--texto", "x" * 501),
        ("--hecho", "hec-002", "--texto", vigente.replace(" ", "  ")),
        ("--hecho", "hec-002", "--texto", TEXTO, "--motivo", "m" * 501),
        ("--hecho", "hec-002"),
        ("--siguiente", *PETICION),
        ("--siguiente", "--simular"),
    ):
        resultado = _cambio(ws, *args)
        assert resultado.exit_code == 2, (args, resultado.output)
    assert _huella(ws) == antes


def test_workspace_sin_tabla_o_sin_ids(novelas: Novelas, tmp_path: Path) -> None:
    """CA-12 (RF-12): sin la tabla de usos o con hec-999, 4 sin escribir nada."""
    sin_tabla = novelas("demo-cambio")
    sin_ids = WorkspaceRepository(tmp_path / "otra" / sin_tabla.slug)
    shutil.copytree(sin_tabla.raiz, sin_ids.raiz)
    # closing: el with de sqlite3 confirma pero no cierra, y un cierre tardío reescribiría la base.
    with closing(sqlite3.connect(sin_tabla.estado_db)) as conn, conn:
        conn.execute("DROP TABLE usos_de_hecho")
    with closing(sqlite3.connect(sin_ids.estado_db)) as conn, conn:
        conn.execute("INSERT INTO libro_de_hechos VALUES ('hec-999', 'Otro hecho.', 6, 'x')")
    for ws, causa in ((sin_tabla, "sin tabla usos_de_hecho"), (sin_ids, "no quedan ids de hecho")):
        antes = _huella(ws)
        resultado = _cambio(ws, *PETICION)
        assert resultado.exit_code == 4, resultado.output
        assert causa in resultado.output
        assert _huella(ws) == antes


def test_version_inexplicada(novelas: Novelas) -> None:
    """CA-19, la parte de RF-21 por el CLI: 4 sin escribir nada."""
    ws = novelas("demo-cambio")
    (ws.raiz / "versiones" / "v1").mkdir(parents=True)
    antes = _huella(ws)
    resultado = _cambio(ws, *PETICION)
    assert resultado.exit_code == 4, resultado.output
    assert _huella(ws) == antes


def test_numero_de_version(novelas: Novelas) -> None:
    """CA-15 (RF-16): antes, sin clave y edición 1; después, version = 2 y cambio = cam-001."""
    ws = novelas("demo-cambio")

    def meta() -> tuple[dict[str, str], int]:
        with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
            return dict(conn.execute("SELECT clave, valor FROM meta")), versiones.version_vigente(
                conn
            )

    claves, vigente = meta()
    assert "version" not in claves and "cambio" not in claves and vigente == 1
    assert _cambio(ws, *PETICION).exit_code == 0
    claves, vigente = meta()
    assert (claves["version"], claves["cambio"], vigente) == ("2", "cam-001", 2)


def test_siguiente(novelas: Novelas) -> None:
    """CA-22 (RF-24): sin cambio, tras pedirlo, tras cerrar el 1 y con el 6 cerrado. El cierre
    se simula con los checkpoints de la versión 1: --reaplicar es de otra tarea."""
    ws = novelas("demo-cambio")
    antes = _huella(ws)
    assert _cambio(ws, "--siguiente").output == "sin cambio\n"
    assert _huella(ws) == antes
    assert _cambio(ws, *PETICION).exit_code == 0
    salidas = [_cambio(ws, "--siguiente").output]
    v1 = ws.raiz / "versiones" / "v1" / "checkpoints"
    for n in (1, 6):
        shutil.copyfile(v1 / f"{n:02d}.json", ws.raiz / "checkpoints" / "latest.json")
        salidas.append(_cambio(ws, "--siguiente").output)
    assert salidas == ["01 reaplicar\n", "02 regenerar\n", "completo\n"]


def test_reanuda_tras_corte(novelas: Novelas) -> None:
    """RF-20 por el CLI: con el cambio en preparando, repetir la misma petición lo completa, y
    otra petición sale con 1."""
    ws = novelas("demo-cambio")
    assert _cambio(ws, *PETICION, "--simular").exit_code == 0

    def cortar(punto: str) -> None:
        if punto == "capitulos_vaciados":
            raise RuntimeError(punto)

    real = versiones.preparar
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(versiones, "preparar", lambda ws_, p: real(ws_, p, cortar))
        assert _cambio(ws, *PETICION).exit_code != 0
    otra = _cambio(ws, "--hecho", "hec-002", "--texto", "Otra cosa distinta.")
    assert otra.exit_code == 1 and "cambio en curso: cam-001" in otra.output
    resultado = _cambio(ws, *PETICION)
    assert resultado.exit_code == 0, resultado.output
    assert "cambio cam-001: hec-002 → hec-103" in resultado.output
    peticion = versiones.cambio_en_curso(ws)
    assert peticion is not None and peticion.estado == "en_curso"


def test_lock_ocupado(
    novelas: Novelas, lock_ajeno: Callable[[Path], AbstractContextManager[None]]
) -> None:
    ws = novelas("demo-cambio")
    antes = _huella(ws)
    with lock_ajeno(ws.lock):
        assert _cambio(ws, *PETICION).exit_code == 3
    assert _huella(ws) == antes


def test_rendimiento(novelas: Novelas) -> None:
    """RNF-02 (R48): novela cambio sobre demo-terminado en menos de 10 s."""
    ws = novelas("demo-terminado")
    inicio = time.perf_counter()
    resultado = _cambio(ws, *PETICION)
    assert resultado.exit_code == 0, resultado.output
    assert time.perf_counter() - inicio < 10

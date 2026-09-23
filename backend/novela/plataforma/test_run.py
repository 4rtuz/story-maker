import hashlib
from collections.abc import Callable
from datetime import datetime

import pytest

from novela.dominio.artefactos import Manifest
from novela.plataforma import run
from novela.plataforma.workspace import CONFIG_DIR, WorkspaceRepository

Novelas = Callable[[str], WorkspaceRepository]
LAS_DIEZ = datetime(2026, 9, 23, 10, 0)


def test_manifiesto_y_log(novelas: Novelas) -> None:
    """CA-13: sin run abierto se crea runs/<run_id>/ con manifest.json (sha y recetas), y la línea
    de harness.log está en disco al salir del bloque, no al cerrar el proceso."""
    ws = novelas("demo-24")
    abierto = run.abrir(ws, 8, entorno={}, ahora=LAS_DIEZ)
    assert abierto.id == "r-20260923-1000"
    manifiesto = Manifest.model_validate_json((abierto.dir / "manifest.json").read_bytes())
    assert manifiesto.capitulo == 8
    assert len(manifiesto.sha_commit) == 40
    recetas = hashlib.sha256((CONFIG_DIR / "recipes.yaml").read_bytes()).hexdigest()
    assert manifiesto.version_recetas == recetas

    with abierto.registro("briefing", "08", "escritor"):
        pass
    with open(abierto.dir / "harness.log", encoding="utf-8") as otro_descriptor:
        assert "briefing 08 escritor -> 0" in otro_descriptor.read()

    # El capítulo sigue abierto: un minuto después se reutiliza el mismo run.
    assert run.abrir(ws, 8, entorno={}, ahora=datetime(2026, 9, 23, 10, 7)).id == abierto.id


def test_registro_anota_la_causa_del_fallo(novelas: Novelas) -> None:
    abierto = run.abrir(novelas("demo-24"), 8, entorno={}, ahora=LAS_DIEZ)
    with pytest.raises(ValueError, match="custodia"):
        with abierto.registro("aplicar-delta", "08") as causas:
            causas.append("custodia: el capítulo cambió")
            raise ValueError("custodia rota")
    log = (abierto.dir / "harness.log").read_text(encoding="utf-8")
    assert "aplicar-delta 08 -> error · custodia: el capítulo cambió" in log


def test_run_id_de_entorno(novelas: Novelas) -> None:
    """CA-33: con NOVELA_RUN_ID se usa ese run; con un valor que no casa el formato, se aborta
    sin crear directorio."""
    ws = novelas("demo-24")
    fijado = run.abrir(ws, 8, entorno={"NOVELA_RUN_ID": "r-20260101-0101"}, ahora=LAS_DIEZ)
    assert fijado.dir == ws.raiz / "runs" / "r-20260101-0101"
    antes = sorted((ws.raiz / "runs").iterdir())
    for malo in ("../fuera", "r-2026-01", "r-20260101-0101\n"):
        with pytest.raises(run.RunInvalido):
            run.abrir(ws, 8, entorno={"NOVELA_RUN_ID": malo}, ahora=LAS_DIEZ)
    assert sorted((ws.raiz / "runs").iterdir()) == antes
    assert not (ws.raiz / "fuera").exists()

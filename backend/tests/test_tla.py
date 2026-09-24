"""Los modelos TLA+ de formal/tla/ (docs/formal/tla.md): el del harness pasa y cada mutante da su
contraejemplo. Solo corre con java y tla2tools.jar en la máquina; si no, se salta."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

TLA = Path(__file__).resolve().parents[2] / "formal" / "tla"
JAVA = os.environ.get("JAVA", "C:/Users/arturo.soto/tools/jdk-21.0.12.1+1-jre/bin/java.exe")
TLA2TOOLS = os.environ.get("TLA2TOOLS", "C:/Users/arturo.soto/tools/tla2tools.jar")
BASH = shutil.which("bash")


@pytest.mark.skipif(
    not (BASH and shutil.which(JAVA) and Path(TLA2TOOLS).is_file()),
    reason="sin bash, java o tla2tools.jar",
)
def test_modelos_tla(tmp_path: Path) -> None:
    entorno = os.environ | {"JAVA": JAVA, "TLA2TOOLS": TLA2TOOLS, "SALIDA": str(tmp_path)}
    assert BASH is not None
    hecho = subprocess.run(  # noqa: S603 (argumentos fijos)
        [BASH, str(TLA / "tlc.sh")], env=entorno, capture_output=True, text=True, timeout=900
    )
    assert hecho.returncode == 0, hecho.stdout + hecho.stderr

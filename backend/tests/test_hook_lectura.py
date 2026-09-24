"""Regla 6 del hook PreToolUse (docs/security-report.md S-02): un rol solo lee su workspace y
sus esquemas. Sin ella, una instrucción inyectada en el brief podía llevar a un agente a leer
los datos de otra novela, o `.env`, y copiarlos en su salida."""

from pathlib import Path

import pytest

from tests.test_hook import MOTIVO, _hook

REPO = "/r"


def _lectura(ruta: str, agente: str | None) -> dict[str, object]:
    entrada: dict[str, object] = {
        "tool_name": "Read",
        "tool_input": {"file_path": ruta},
        "cwd": REPO,
    }
    if agente is not None:
        entrada["agent_type"] = agente
    return entrada


@pytest.mark.parametrize(
    "ruta",
    [
        "/r/novelas/boda-ana/runs/r-20260924-1200/briefings/01-escritor.md",
        "novelas/boda-ana/capitulos/01.md",
        "/r/backend/schemas/capitulo.schema.json",
    ],
)
def test_rol_lee_su_workspace_y_sus_esquemas(tmp_path: Path, ruta: str) -> None:
    r = _hook(_lectura(ruta, "escritor"), tmp_path, {"NOVELA_SLUG": "boda-ana"})
    assert (r.returncode, r.stderr) == (0, "")


@pytest.mark.parametrize(
    "ruta",
    [
        "/r/novelas/boda-otra/brief/entradas/ent-01.md",  # otra novela
        "/r/novelas/boda-ana/../boda-otra/brief/brief.json",  # subida de directorio
        "/r/.env",  # claves de los scores
        "/r/backend/novela/plataforma/langfuse.py",
        "C:/Users/x/.ssh/id_rsa",
        "/r/novelas/boda-ana/canon/misterio.md",  # secreto aunque sea el suyo
    ],
)
def test_rol_no_lee_fuera(tmp_path: Path, ruta: str) -> None:
    r = _hook(_lectura(ruta, "entrevistador"), tmp_path, {"NOVELA_SLUG": "boda-ana"})
    assert r.returncode == 2 and r.stderr.startswith(MOTIVO)


def test_sin_slug_cualquier_workspace_pero_nada_fuera(tmp_path: Path) -> None:
    """Sesión interactiva sin NOVELA_SLUG: no sabe qué novela es la suya, pero `.env` sigue
    fuera."""
    r = _hook(_lectura("/r/novelas/boda-otra/capitulos/01.md", "escritor"), tmp_path)
    assert r.returncode == 0
    assert _hook(_lectura("/r/.env", "escritor"), tmp_path).returncode == 2


@pytest.mark.parametrize("agente", [None, "Explore"])
def test_la_sesion_principal_y_los_de_desarrollo_leen_sin_regla(
    tmp_path: Path, agente: str | None
) -> None:
    r = _hook(_lectura("/r/novelas/boda-otra/estado/estado.db", agente), tmp_path)
    assert (r.returncode, r.stderr) == (0, "")


def test_rol_no_escribe_en_otra_novela(tmp_path: Path) -> None:
    """S-02 también para escribir: con NOVELA_SLUG, sus salidas solo en su novela."""
    entrada = {
        "tool_name": "Write",
        "tool_input": {"file_path": "/r/novelas/boda-otra/capitulos/01.md", "content": "x"},
        "cwd": REPO,
        "agent_type": "escritor",
    }
    assert _hook(entrada, tmp_path).returncode == 0
    r = _hook(entrada, tmp_path, {"NOVELA_SLUG": "boda-ana"})
    assert r.returncode == 2 and r.stderr.startswith(MOTIVO)


def test_el_juez_lee_su_rubrica_y_nadie_mas_lee_config(tmp_path: Path) -> None:
    """juez.md lee `backend/config/rubrica.yaml`; el resto de `backend/config/` sigue fuera."""
    entorno = {"NOVELA_SLUG": "boda-ana"}
    rubrica = "/r/backend/config/rubrica.yaml"
    assert _hook(_lectura(rubrica, "juez"), tmp_path, entorno).returncode == 0
    assert _hook(_lectura(rubrica, "escritor"), tmp_path, entorno).returncode != 0
    otro = "/r/backend/config/recipes.yaml"
    assert _hook(_lectura(otro, "juez"), tmp_path, entorno).returncode != 0


def test_escritor_no_lee_un_informe_que_copia_el_misterio(tmp_path: Path) -> None:
    """eval-b3-inyeccion: el continuista copió en qa/01-continuidad.json la nota de la pista, y
    ese informe va al escritor en el reintento (invariante 3). Ocho palabras seguidas bastan."""
    raiz = tmp_path / "novelas" / "boda-ana"
    (raiz / "canon").mkdir(parents=True)
    (raiz / "qa").mkdir()
    secreto = "La nota decía que el atlas guardaba la llave del depósito desde 1952."
    (raiz / "canon" / "misterio.md").write_text(f"---\nx: 1\n---\n{secreto}\n", encoding="utf-8")
    fuga = raiz / "qa" / "01-continuidad.json"
    fuga.write_text(f'{{"hallazgos": ["{secreto[:60]}"]}}', encoding="utf-8")
    limpio = raiz / "qa" / "01-suspense.json"
    limpio.write_text('{"hallazgos": ["falta plantar pis-006 en el capítulo"]}', encoding="utf-8")
    entorno = {"NOVELA_SLUG": "boda-ana"}
    r = _hook(_lectura(str(fuga), "escritor"), tmp_path, entorno)
    assert r.returncode != 0 and "misterio" in r.stderr
    assert _hook(_lectura(str(limpio), "escritor"), tmp_path, entorno).returncode == 0
    assert _hook(_lectura(str(fuga), "continuista"), tmp_path, entorno).returncode == 0

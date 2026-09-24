"""`novela producir`: la novela de principio a fin con sesiones falsas. Ningún test llama a un
modelo: cada sesión es una función que deja en disco lo que dejaría la de verdad."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from filelock import FileLock
from typer.testing import CliRunner

from novela.cli import app
from novela.plataforma import lanzador
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.producir.flujo import Puertos, orden_nueva, producir

NUM = 3


class Harness:
    """Un harness falso sobre tmp_path. `efectos` decide qué deja cada sesión."""

    def __init__(self, raiz: Path, efectos: Callable[["Harness", str], int] | None = None) -> None:
        self.ws = WorkspaceRepository(raiz / "demo")
        self.sesiones: list[str] = []
        self.pasos: list[str] = []
        self.hallazgos: str | None = None
        self.detener = False
        self.cerrados = 0
        self.efectos = efectos or Harness.bien

    def bien(self, prompt: str) -> int:
        if prompt.startswith("/novela-nueva"):
            (self.ws.raiz / "plan").mkdir(parents=True)
            (self.ws.raiz / "plan" / "escaleta.md").write_text("escaleta", encoding="utf-8")
        elif prompt.startswith("/novela-continuar"):
            self.cerrados += 1
            (self.ws.raiz / "checkpoints").mkdir(exist_ok=True)
            latest = self.ws.raiz / "checkpoints" / "latest.json"
            latest.write_text(f'{{"capitulo": {self.cerrados}}}', encoding="utf-8")
        elif prompt.startswith("/novela-auditar"):
            (self.ws.raiz / "export").mkdir(exist_ok=True)
            (self.ws.raiz / "export" / "demo.epub").write_bytes(b"epub")
        return 0

    def puertos(self) -> Puertos:
        def sesion(prompt: str) -> int:
            self.sesiones.append(prompt)
            return self.efectos(self, prompt)

        return Puertos(
            sesion=sesion,
            entorno=lambda: self.hallazgos,
            pendiente=lambda: self.cerrados < NUM,
            detener=lambda: self.detener,
            informar=lambda paso, _detalle: self.pasos.append(paso),
        )

    def producir(self, nueva: str | None = "/novela-nueva demo --idea 'x'") -> tuple[str, str]:
        return producir(self.ws, nueva, self.puertos())


def test_de_principio_a_fin(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    estado, detalle = h.producir()
    assert estado == "terminado", detalle
    assert h.sesiones == [
        "/novela-nueva demo --idea 'x'",
        *["/novela-continuar demo --capitulos 1"] * NUM,
        "/novela-auditar demo",
    ]
    assert h.pasos == ["entorno", "nueva", "capitulo 01", "capitulo 02", "capitulo 03", "auditoria"]


def test_entorno_con_hallazgos_no_lanza_nada(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.hallazgos = "falta settings.local.json"
    assert h.producir() == ("fallido", "falta settings.local.json")
    assert h.sesiones == []


def test_sesion_que_no_avanza_el_checkpoint_para(tmp_path: Path) -> None:
    """La última línea del bucle desatendido: sin avance, no se insiste."""

    def atascada(h: Harness, prompt: str) -> int:
        return 0 if prompt.startswith("/novela-continuar") else Harness.bien(h, prompt)

    h = Harness(tmp_path, atascada)
    estado, detalle = h.producir()
    assert estado == "fallido" and "checkpoint" in detalle
    assert h.sesiones.count("/novela-continuar demo --capitulos 1") == 1


def test_codigo_distinto_de_cero_para(tmp_path: Path) -> None:
    h = Harness(tmp_path, lambda h, p: 1 if p.startswith("/novela-continuar") else h.bien(p))
    estado, detalle = h.producir()
    assert estado == "fallido" and "salió con 1" in detalle
    assert h.sesiones[-1].startswith("/novela-continuar")


def test_intervencion_viva_para_y_resuelta_no(tmp_path: Path) -> None:
    def con_intervencion(texto: str) -> Callable[[Harness, str], int]:
        def efectos(h: Harness, prompt: str) -> int:
            rc = Harness.bien(h, prompt)
            if prompt.startswith("/novela-continuar") and h.cerrados == 1:
                run = h.ws.raiz / "runs" / "r-20260924-0001"
                run.mkdir(parents=True, exist_ok=True)
                (run / "intervencion.md").write_text(texto, encoding="utf-8")
            return rc

        return efectos

    viva = Harness(tmp_path / "a", con_intervencion("gate: continuidad\n"))
    estado, detalle = viva.producir()
    assert estado == "fallido" and "intervencion.md" in detalle
    assert len(viva.sesiones) == 2

    resuelta = Harness(tmp_path / "b", con_intervencion("gate: x\nresuelto: abc123\n"))
    assert resuelta.producir()[0] == "terminado"


def test_reanudar_con_intervencion_viva_no_lanza(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.bien("/novela-nueva")
    run = h.ws.raiz / "runs" / "r-20260924-0001"
    run.mkdir(parents=True)
    (run / "intervencion.md").write_text("gate: suspense\n", encoding="utf-8")
    assert h.producir(None)[0] == "fallido"
    assert h.sesiones == []


def test_detener_para_antes_del_siguiente_capitulo(tmp_path: Path) -> None:
    def detiene(h: Harness, prompt: str) -> int:
        rc = Harness.bien(h, prompt)
        h.detener = prompt.startswith("/novela-continuar")
        return rc

    h = Harness(tmp_path, detiene)
    estado, detalle = h.producir()
    assert estado == "detenido" and "02" in detalle
    assert h.sesiones.count("/novela-continuar demo --capitulos 1") == 1


def test_reanudar_no_repite_novela_nueva(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.bien("/novela-nueva")
    assert h.producir(None)[0] == "terminado"
    assert not any(s.startswith("/novela-nueva") for s in h.sesiones)


def test_sin_workspace_y_sin_idea_falla(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    assert h.producir(None)[0] == "fallido"
    assert h.sesiones == []


def test_workspace_sin_plan_no_se_reanuda(tmp_path: Path) -> None:
    """`/novela-nueva` sale con 1 si el workspace existe: no hay forma de reanudarla."""
    h = Harness(tmp_path)
    h.ws.raiz.mkdir()
    estado, detalle = h.producir(None)
    assert estado == "fallido" and "escaleta" in detalle
    assert h.sesiones == []


def test_nueva_sin_escaleta_falla(tmp_path: Path) -> None:
    def sin_plan(h: Harness, _: str) -> int:
        h.ws.raiz.mkdir()
        return 0

    h = Harness(tmp_path, sin_plan)
    estado, detalle = h.producir()
    assert estado == "fallido" and "escaleta" in detalle


def test_auditoria_sin_exportar_falla(tmp_path: Path) -> None:
    h = Harness(tmp_path, lambda h, p: 0 if p.startswith("/novela-auditar") else h.bien(p))
    estado, detalle = h.producir()
    assert estado == "fallido" and "export" in detalle


def test_orden_nueva_entrecomilla_como_el_panel() -> None:
    """La misma regla que `entrecomillar` de frontend/src/features/lanzar/orden.ts (D44)."""
    assert orden_nueva("demo", "it's $HOME", 3, None) == (
        "/novela-nueva demo --idea 'it'\\''s $HOME' --capitulos 3"
    )
    assert orden_nueva("demo", "x", None, 80000) == "/novela-nueva demo --idea 'x' --palabras 80000"


def test_cascara_deja_el_estado_final_y_respeta_el_cerrojo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sin `claude` en el PATH no se lanza ninguna sesión, y el panel lo lee en el estado final.
    Con otro `producir` en marcha, sale con 3 sin tocar nada."""
    monkeypatch.setenv("NOVELAS_DIR", str(tmp_path))
    monkeypatch.setattr(shutil, "which", lambda _: None)
    r = CliRunner().invoke(app, ["producir", "demo", "--idea", "x"])
    assert r.exit_code == 1, r.output
    final = lanzador.leer("demo")
    assert final is not None and final.estado == "fallido" and "claude" in final.detalle
    with FileLock(lanzador.cerrojo()):
        assert CliRunner().invoke(app, ["producir", "demo", "--idea", "x"]).exit_code == 3

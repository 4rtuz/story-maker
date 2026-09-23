"""Model checking del bucle por capítulo (validators.md §4.10) y su integración de principio a fin.

La máquina es la que el procedimiento *debería* seguir; `.claude/commands/novela-continuar.md` la
implementa en prosa y ningún test la ejecuta (§5.8). Por eso, además de enumerarla, se comprueba
que el CLI rechaza de verdad las transiciones que la máquina prohíbe y que el bucle completo corre
con agentes falsos.
"""

from collections import deque
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from pathlib import Path

from typer.testing import CliRunner

from novela.cli import app
from novela.dominio.estado import FASES, PASOS
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceRepository
from tests.fixtures import fabrica

# El procedimiento: los nueve pasos del bucle, con validar repetido tras el editor-estilo, que
# reescribe el capítulo (validators.md §3.9.3). La custodia de aplicar-delta lo exige.
SECUENCIA = (
    "briefing",
    "escritor",
    "validar",
    "continuista",
    "editor-estilo",
    "lector-suspense",
    "validar",
    "cronista",
    "aplicar-delta",
    "checkpoint",
)
FASE_DE = {
    "briefing": "escritura",
    "escritor": "escritura",
    "validar": "revision",
    "continuista": "revision",
    "editor-estilo": "revision",
    "lector-suspense": "revision",
    "cronista": "registro",
    "aplicar-delta": "registro",
    "checkpoint": "cerrado",
}
GATES = {"validar", "continuista", "lector-suspense"}  # el editor-estilo no es gate: se aplica
MAX_INTENTOS = 3


@dataclass(frozen=True)
class Punto:
    indice: int  # posición en SECUENCIA del último paso dado; -1 antes del primero
    intento: int
    validado: bool  # validar pasó sobre la versión actual del capítulo
    parado: bool  # intervencion.md escrito

    @property
    def ultimo_paso(self) -> str | None:
        return SECUENCIA[self.indice] if self.indice >= 0 else None

    @property
    def fase(self) -> str:
        return FASE_DE[self.ultimo_paso] if self.ultimo_paso else "escritura"


def _siguientes(p: Punto) -> list[tuple[str, bool, Punto]]:
    """(paso, pasa, punto siguiente). Un gate puede pasar o fallar; el resto siempre avanza."""
    if p.parado or p.ultimo_paso == "checkpoint":
        return []
    i = p.indice + 1
    paso = SECUENCIA[i]
    avance = replace(p, indice=i)
    if paso == "escritor" or paso == "editor-estilo":
        avance = replace(avance, validado=False)  # reescriben el capítulo
    if paso not in GATES:
        return [(paso, True, avance)]
    pasa = replace(avance, validado=True) if paso == "validar" else avance
    if p.intento == MAX_INTENTOS:
        falla = replace(p, indice=i, parado=True)
    else:  # el reintento repite todos los gates desde validar: vuelve al escritor
        falla = Punto(indice=0, intento=p.intento + 1, validado=False, parado=False)
    return [(paso, True, pasa), (paso, False, falla)]


def test_maquina_del_bucle_y_sus_invariantes() -> None:
    inicio = Punto(indice=-1, intento=1, validado=False, parado=False)
    vistos, cola = {inicio}, deque([inicio])
    transiciones = 0
    while cola:
        p = cola.popleft()
        # Los valores son los de los enums del dominio: si no cuadrasen, estarían mal cerrados.
        assert p.fase in FASES and (p.ultimo_paso is None or p.ultimo_paso in PASOS)
        for paso, pasa, q in _siguientes(p):
            transiciones += 1
            # 1. Nunca aplicar-delta sin que validar haya pasado sobre esa misma versión.
            if paso == "aplicar-delta":
                assert p.validado
            # 2. Nunca checkpoint antes de aplicar-delta.
            if paso == "checkpoint":
                assert p.ultimo_paso == "aplicar-delta"
            # 4. Los intentos son 1, 2 y 3; el fallo del tercero para y no hay un 4.
            assert 1 <= q.intento <= MAX_INTENTOS
            if not pasa and p.intento == MAX_INTENTOS:
                assert q.parado and not _siguientes(q)
            # Tras un reintento no queda nada validado: se repiten todos los gates.
            if not pasa and not q.parado:
                assert (q.ultimo_paso, q.validado) == ("briefing", False)
            if q not in vistos:
                vistos.add(q)
                cola.append(q)
    finales = [p for p in vistos if not _siguientes(p)]
    # 5. El capítulo siguiente solo empieza desde un checkpoint; si no, se ha parado.
    assert all(p.ultimo_paso == "checkpoint" or p.parado for p in finales)
    assert any(p.ultimo_paso == "checkpoint" for p in finales)
    assert 10 < len(vistos) < 200, "decenas de estados, no millones: TLA+ sería ceremonia"
    assert transiciones > len(vistos) - 1


Novelas = Callable[[str], WorkspaceRepository]


def _cli(ws: WorkspaceRepository, *orden: str) -> int:
    return fabrica.cli(ws.raiz.parent, *orden, run=fabrica.run_id(8)).exit_code


def test_la_cli_rechaza_lo_que_la_maquina_prohibe(
    novelas: Novelas, lock_ajeno: Callable[[Path], AbstractContextManager[None]]
) -> None:
    """Los invariantes que dependen de código, contra el CLI real y no contra el modelo."""
    ws = novelas("demo-24")
    assert _cli(ws, "checkpoint", ws.slug, "8") == 1  # 2: sin aplicar-delta
    assert _cli(ws, "briefing", ws.slug, "9", "escritor") == 1  # 5: el 8 sin checkpoint
    with lock_ajeno(ws.lock):  # 3: nunca dos procesos
        assert _cli(ws, "briefing", ws.slug, "8", "escritor") == 3

    fabrica.preparar_capitulo(ws.raiz.parent, ws.slug, fabrica.DEMO, 8)
    # El editor-estilo reescribe después de validar: sin validar otra vez, no se aplica (1).
    capitulo = ws.raiz / "capitulos" / "08.md"
    # Una frase de relleno, que ninguna cita del delta usa.
    capitulo.write_bytes(capitulo.read_bytes().replace(b"el mar sigui", b"el mar segu", 1))
    assert _cli(ws, "aplicar-delta", ws.slug, "8") == 1
    assert _cli(ws, "validar", ws.slug, "8") == 0
    assert _cli(ws, "aplicar-delta", ws.slug, "8") == 1  # el cronista leyó la versión anterior
    for agente in ("continuista", "editor-estilo", "lector-suspense", "cronista"):
        assert _cli(ws, "briefing", ws.slug, "8", agente) == 0
    assert _cli(ws, "aplicar-delta", ws.slug, "8") == 0
    assert _cli(ws, "checkpoint", ws.slug, "8") == 0


def test_bucle_completo_con_agente_falso(tmp_path: Path) -> None:
    """validators.md §3.5: la novela entera, de `nueva` a `pendiente`, sin una llamada a modelo."""
    raiz = fabrica.construir(tmp_path, "humo", fabrica.HUERFANA, cerrados=3)
    ws = WorkspaceRepository(raiz)
    resultado = CliRunner().invoke(app, ["pendiente", "humo"], env={"NOVELAS_DIR": str(tmp_path)})
    assert (resultado.exit_code, resultado.stdout) == (1, "")
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        estado = estado_db.leer(conn)
    assert (estado.cursor.capitulo, estado.cursor.ultimo_paso) == (3, "aplicar-delta")
    assert len(estado.tension_real) == 3 and None not in estado.tension_real.entradas
    assert [h.estado for h in estado.hilos] == ["cerrado"]
    assert estado.pistas["pis-002"].estado == "huerfana"
    assert sorted(p.name for p in (raiz / "memoria" / "resumenes").iterdir()) == [
        "01.md",
        "02.md",
        "03.md",
    ]
    punto = ws.ultimo_checkpoint()
    assert punto is not None and sorted(punto.capitulos_sha256) == [1, 2, 3]

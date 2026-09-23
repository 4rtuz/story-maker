"""`novela auditar <slug>`: pistas huérfanas, hilos sin cerrar, pistas falsas sin desmontar y
revelaciones sin pista previa. Lee estado, canon y checkpoint; solo escribe `qa/auditoria.json`,
con el mismo modelo que el informe de `validar`.
"""

import typer

from novela.dominio.canon import Misterio
from novela.dominio.qa import InformeQA
from novela.plataforma import estado_db
from novela.plataforma.workspace import WorkspaceRepository
from novela.slices.auditoria.comprobaciones import auditar as comprobar


def auditar(slug: str) -> None:
    """Sale con 1 si hay hallazgos. El detalle queda en qa/auditoria.json."""
    ws = WorkspaceRepository.resolver(slug).exigir()
    with ws.bloquear():
        with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
            estado = estado_db.leer(conn)
        misterio = ws.leer_md(ws.raiz / "canon" / "misterio.md", Misterio)
        punto = ws.ultimo_checkpoint()
        hallazgos = comprobar(estado, misterio, punto.capitulo if punto else 0)
        informe = InformeQA(
            capitulo=estado.cursor.capitulo,
            agente="auditar",
            veredicto="rechazado" if hallazgos else "aprobado",
            hallazgos=hallazgos,
        )
        ws.escribir(ws.raiz / "qa" / "auditoria.json", informe.model_dump_json(indent=2))
    if not hallazgos:
        typer.echo("auditar: sin hallazgos")
        return
    tipos = sorted({h.tipo for h in hallazgos})
    typer.echo(f"auditar: {len(hallazgos)} hallazgos ({', '.join(tipos)}) en qa/auditoria.json")
    raise typer.Exit(1)

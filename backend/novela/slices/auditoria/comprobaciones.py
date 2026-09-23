"""Las cuatro comprobaciones de cierre (RF-22): función pura sobre estado y misterio.

Las tres primeras son la auditoría final de `definitions.md` §10; la cuarta es el fair play del
invariante 4. Reporta lo que no está resuelto *ahora*: a mitad de novela, un hilo que se cierra
más adelante también sale. Está pensada para el cierre; el parcial por acto es de la spec 0002.
"""

from novela.dominio.canon import Misterio
from novela.dominio.estado import Estado
from novela.dominio.qa import Hallazgo


def auditar(estado: Estado, misterio: Misterio, cerrados: int) -> list[Hallazgo]:
    hallazgos = [
        Hallazgo(
            tipo="pista_huerfana",
            gravedad="alta",
            referencia=pista,
            descripcion=f"plantada en el capítulo {e.plantada_en} y nunca pagada",
        )
        for pista, e in sorted(estado.pistas.items())
        if e.estado == "huerfana"
    ]
    hallazgos += [
        Hallazgo(
            tipo="hilo_sin_cerrar",
            gravedad="media",
            referencia=h.id,
            descripcion=f"abierto en el capítulo {h.abierto_en} y nunca cerrado",
        )
        for h in sorted(estado.hilos, key=lambda h: h.id)
        if h.estado == "abierto"
    ]
    # El estado no registra pistas falsas: desmontada es que su capítulo ya está cerrado.
    hallazgos += [
        Hallazgo(
            tipo="pista_falsa_sin_desmontar",
            gravedad="media",
            referencia=pf.id,
            descripcion=f"se desmonta en el capítulo {pf.cuando_se_desmonta}"
            if pf.cuando_se_desmonta
            else "no tiene capítulo en que se desmonte",
        )
        for pf in misterio.pistas_falsas
        if pf.cuando_se_desmonta is None or pf.cuando_se_desmonta > cerrados
    ]
    for rev in (*misterio.revelaciones, *misterio.giros):
        plantadas = [
            p
            for p in rev.pistas_que_la_pagan
            if (e := estado.pistas.get(p))
            and e.plantada_en is not None
            and e.plantada_en < rev.capitulo_previsto
        ]
        if not plantadas:
            hallazgos.append(
                Hallazgo(
                    tipo="revelacion_sin_pista",
                    gravedad="alta",
                    referencia=rev.id,
                    descripcion=f"ninguna de {', '.join(rev.pistas_que_la_pagan)} está plantada "
                    f"antes del capítulo {rev.capitulo_previsto}",
                )
            )
    return hallazgos

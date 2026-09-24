"""Tablas `cronologia` y `cronologia_personajes`: escritura desde el delta y lectura para Lean.

Las escribe `aplicar-delta` dentro de su transacción; son append-only e idempotentes como
`apariciones`. Sobre una base anterior, `asegurar` las crea desde su bloque de `esquema.sql`.
"""

import json
import re
import sqlite3
from collections.abc import Iterable, Mapping
from importlib import resources

from novela.dominio.estado import Delta, EntradaTemporal, EventoCronologia
from novela.dominio.plan import EscenaPlan


def asegurar(conn: sqlite3.Connection) -> None:
    """Sentencia a sentencia: `executescript` haría COMMIT de la transacción de quien llama."""
    ddl = resources.files("novela.plataforma").joinpath("esquema.sql").read_text("utf-8")
    bloque = ddl.split("-- cronologia: inicio")[1].split("-- cronologia: fin")[0]
    sentencia = ""
    for linea in bloque.splitlines(keepends=True):
        sentencia += linea
        if sqlite3.complete_statement(sentencia):
            conn.execute(sentencia)
            sentencia = ""


def registrar(conn: sqlite3.Connection, delta: Delta) -> None:
    """Va dentro de la transacción de quien llama. Repetir un capítulo no duplica ni borra."""
    for e in delta.cronologia:
        conn.execute(
            "INSERT OR IGNORE INTO cronologia VALUES (?, ?, ?, ?, ?, ?, ?)",
            (e.id, delta.capitulo, e.momento, e.duracion_min, e.lugar, json.dumps(e.tras), e.cita),
        )
        filas = [(e.id, p, "presente", e.edades.get(p)) for p in e.personajes]
        filas += [(e.id, p, "excluido", None) for p in e.excluye]
        conn.executemany("INSERT OR IGNORE INTO cronologia_personajes VALUES (?, ?, ?, ?)", filas)


def leer(conn: sqlite3.Connection) -> list[EventoCronologia]:
    """En orden de inserción. Una base sin las tablas no tiene cronología: lista vacía."""
    try:
        eventos = conn.execute(
            "SELECT evento, momento, duracion_min, lugar, tras, cita FROM cronologia ORDER BY rowid"
        ).fetchall()
        personajes = conn.execute(
            "SELECT evento, personaje, papel, edad FROM cronologia_personajes ORDER BY rowid"
        ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        return []
    resultado = []
    for evento, momento, duracion, lugar, tras, cita in eventos:
        suyos = [(p, papel, edad) for ev, p, papel, edad in personajes if ev == evento]
        resultado.append(
            EventoCronologia(
                id=evento,
                momento=momento,
                duracion_min=duracion,
                lugar=lugar,
                personajes=[p for p, papel, _ in suyos if papel == "presente"],
                excluye=[p for p, papel, _ in suyos if papel == "excluido"],
                edades={p: edad for p, papel, edad in suyos if edad is not None},
                tras=json.loads(tras),
                cita=cita,
            )
        )
    return resultado


_MOMENTO = re.compile(r"d[ií]a\s+(\d+)\D+?(\d{1,2}):(\d{2})", re.IGNORECASE)


def momento(texto: str) -> int | None:
    """«dia 3, 23:00» → minutos desde el día 1 a las 00:00; None si no sigue ese formato."""
    casa = _MOMENTO.search(texto)
    if casa is None:
        return None
    dia, hora, minuto = (int(g) for g in casa.groups())
    return (dia - 1) * 1440 + hora * 60 + minuto if dia >= 1 else None


def derivar(
    lineas: Iterable[EntradaTemporal], escenas: Mapping[str, EscenaPlan]
) -> tuple[list[EventoCronologia], list[str]]:
    """Para una novela sin cronología: un evento por escena de `linea_temporal`, con el lugar y
    los personajes de su ficha de plan. Devuelve también las escenas que no se pudieron datar o
    no tienen ficha. Sin exclusiones, edades ni `tras`: la base antigua no los registra."""
    eventos, omitidas = [], []
    for entrada in lineas:
        plan = escenas.get(entrada.escena)
        cuando = momento(entrada.inicio)
        if plan is None or cuando is None:
            omitidas.append(entrada.escena)
            continue
        eventos.append(
            EventoCronologia(
                id="evt-" + entrada.escena.removeprefix("esc-"),
                momento=cuando,
                duracion_min=entrada.duracion_min,
                lugar=plan.lugar,
                personajes=plan.personajes,
                cita=entrada.cita,
            )
        )
    return eventos, omitidas

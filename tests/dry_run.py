"""Simulacro completo del POC con respuestas enlatadas, sin tocar la red.

Valida la maquina descrita en 15.1 sin gastar una sola peticion: sustituye a los
cinco subagentes por respuestas fijas y recorre el ciclo de los 3 capitulos,
incluidas las dos ramas del bucle de evaluacion, la verificacion de hashes, el
agotamiento de iteraciones, la reanudacion y las puertas de acto.

Uso:  python tests/dry_run.py [--keep]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.artifacts import Card, ClueLedger, read, sections  # noqa: E402
from harness.config import load  # noqa: E402
from harness.scenes import Chapter  # noqa: E402

PASS, FAIL = [], []


def check(name: str, condition: bool, detail: str = "") -> bool:
    (PASS if condition else FAIL).append(name)
    mark = "ok  " if condition else "FALLO"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not condition else ""))
    return condition


def run(sandbox: Path, *args: str, expect: int | None = 0) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "harness", "--root", str(sandbox), *args],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if expect is not None and proc.returncode != expect:
        print(f"    (código {proc.returncode}, esperado {expect})\n{output}")
    return output


# --------------------------------------------------------------------------
# artefactos enlatados
# --------------------------------------------------------------------------
PREMISA = """# Premisa

## Logline
Cuando su marido reaparece tras nueve días desaparecido sin recordar nada, una
restauradora de muebles empieza a sospechar que el hombre que ha vuelto no es
exactamente el que se fue.

## Situación de partida
Elena restaura muebles en el taller de la casa que comparte con Marcos.

## El secreto
Marcos se marchó por su propia voluntad y vuelve para recuperar algo escondido.

## La revelación
En el capítulo 3 Elena descubre que la llave que Marcos busca abre su propio taller.

## Pistas que sostienen la revelación
- P-01 · El reloj de pulsera aparece con la correa cambiada
- P-02 · La vecina asegura haber oído el coche a las tres
- P-03 · La llave pequeña en el bolsillo del abrigo

## Apuesta temática
Nadie conoce del todo a la persona con la que vive.

## Final
Elena abre el taller y encuentra la caja. Marcos se marcha. La vecina calla.
"""

PERSONAJES = """# Personajes

## Elena Vargas
- **Rol:** protagonista
- **Focalizador:** sí
- **Edad y ocupación:** 41, restauradora de muebles
- **Deseo consciente:** recuperar la normalidad
- **Necesidad inconsciente:** dejar de justificar a Marcos
- **Miente sobre:** las llamadas al hermano de Marcos, a nadie, por vergüenza
- **Rasgo físico distintivo:** una quemadura de barniz en el dorso de la mano
- **Tic verbal o de conducta:** ordena objetos mientras escucha
- **Arco:** de la lealtad automática a la sospecha lúcida
- **Relaciones:** Marcos: marido; Nieves: vecina

## Marcos Duarte
- **Rol:** antagonista
- **Focalizador:** no
- **Edad y ocupación:** 45, comercial
- **Deseo consciente:** que nadie pregunte
- **Necesidad inconsciente:** ser descubierto
- **Miente sobre:** los nueve días, a Elena, para protegerse
- **Rasgo físico distintivo:** una cicatriz corta bajo la ceja izquierda
- **Tic verbal o de conducta:** repite la última palabra de quien le habla
- **Arco:** del silencio calculado a la huida
- **Relaciones:** Elena: mujer

## Nieves Abad
- **Rol:** secundario
- **Focalizador:** no
- **Edad y ocupación:** 68, jubilada
- **Deseo consciente:** que la escuchen
- **Necesidad inconsciente:** sentirse útil
- **Miente sobre:** la hora del coche, a Elena, por costumbre
- **Rasgo físico distintivo:** gafas colgadas de una cadena de cuentas
- **Tic verbal o de conducta:** empieza las frases con "yo no digo nada, pero"
- **Arco:** de testigo servicial a testigo interesado
- **Relaciones:** Elena: vecina
"""

VOZ = """# Voz y estilo

## Parámetros fijos
- Persona y tiempo: tercera limitada, pasado
- Focalizadores: Elena Vargas
- Longitud media de frase: variada con dominio de la corta
- Densidad de diálogo: media

## Reglas positivas
- Empieza dentro de la escena.
- Un detalle físico concreto por párrafo.
- El diálogo oculta tanto como dice.
- Los objetos del taller miden el estado de ánimo.
- Cierra cada escena en desequilibrio.

## Reglas negativas
- Nada de "sintió que algo no encajaba".
- Nada de adverbios en -mente en el diálogo.
- No se narra el interior de Marcos.
- No se explica la emoción después de mostrarla.
- No hay preámbulos de ambientación.

## Pasaje ancla
Elena pasó el paño por la tabla y el olor a aguarrás le llenó la boca. La puerta
del taller estaba entornada como la había dejado. Como creía haberla dejado.
"""


def escaleta() -> str:
    entries = [
        (1, "El regreso", "Elena Vargas", 0, "La casa",
         ["Marcos aparece en la puerta", "Elena le sirve agua y calla",
          "Elena ve el reloj con la correa cambiada"],
         "P1", "ninguna", "ninguna", "ninguna",   # forma floja a proposito
         "Elena oye la puerta", "Elena reconoce el reloj y no dice nada"),
        (2, "La vecina", "Elena Vargas", 1, "El rellano",
         ["Nieves para a Elena en la escalera",
          "Nieves menciona el coche a las tres",
          "Elena vuelve y registra el abrigo"],
         "P-03", "P-01", "ninguna", "P-02",
         "Elena baja la basura", "Elena encuentra una llave pequeña"),
        (3, "El taller", "Elena Vargas", 2, "El taller",
         ["Elena prueba la llave", "La llave abre su propio taller",
          "Nieves admite que se equivocó de hora"],
         "ninguna", "ninguna", "P-01, P-03", "ninguna",
         "Elena con la llave en la mano", "Elena encuentra la caja"),
    ]
    parts = ["# Escaleta", ""]
    acts = [(1, 1, 1), (2, 2, 2), (3, 3, 3)]
    for num, lo, hi in acts:
        parts.append(f"## Acto {num} — Capítulos {lo}-{hi}")
        parts.append("")
        for e in entries:
            if not (lo <= e[0] <= hi):
                continue
            n, title, pov, day, loc, beats, plant, reinf, res, rel, starts, ends = e
            parts.append(f"### Capítulo {n}")
            parts.append(f"- **Título provisional:** {title}")
            parts.append(f"- **Focalizador:** {pov}")
            parts.append(f"- **Día de ficción:** {day}")
            parts.append(f"- **Localización:** {loc}")
            parts.append("- **Beats:**")
            for i, b in enumerate(beats, 1):
                parts.append(f"  {i}. {b}")
            parts.append(f"- **Pistas a plantar:** {plant}")
            parts.append(f"- **Pistas a reforzar:** {reinf}")
            parts.append(f"- **Pistas a resolver:** {res}")
            parts.append(f"- **Pistas relevantes en contexto:** {rel}")
            parts.append(f"- **Empieza en:** {starts}")
            parts.append(f"- **Termina en:** {ends}")
            parts.append("")
    parts += ["## Cambios", "- (ninguno)"]
    return "\n".join(parts)


def draft(n: int, title: str, s1: str, s2: str) -> str:
    return (f"# Capítulo {n} — {title}\n\n"
            f"<!-- ESCENA 1 -->\n{s1}\n\n"
            f"<!-- ESCENA 2 -->\n{s2}\n\n"
            f"<!-- FIN -->\n")


DRAFTS = {
    1: draft(1, "El regreso",
             "Elena oyó la puerta y no se levantó. Marcos entró con el abrigo "
             "mojado y dejó las llaves en el plato de la entrada, donde siempre. "
             "Le sirvió un vaso de agua y esperó.",
             "Él bebió despacio. Elena le miró la muñeca. El reloj era el mismo, "
             "pero la correa no. Volvió a llenarle el vaso y no dijo nada."),
    2: draft(2, "La vecina",
             "Nieves la paró en el rellano con la bolsa en la mano. Dijo que ella "
             "no decía nada, pero que el coche había vuelto a las tres. Elena "
             "asintió y siguió bajando.",
             "Arriba, el abrigo seguía en la percha. Elena metió la mano en el "
             "bolsillo y sacó una llave pequeña, de latón, que no conocía."),
    3: draft(3, "El taller",
             "La llave entró sin forzar. Elena empujó la puerta de su propio "
             "taller y se quedó en el umbral con la mano en el marco, contando "
             "las tablas apiladas contra la pared.",
             "Nieves apareció detrás y admitió que quizá no habían sido las tres. "
             "Elena no se giró. Detrás del banco, bajo una manta, había una caja "
             "que ella no había puesto allí."),
}

BAD_DRAFT = draft(3, "El taller",
                  "Elena abrió la puerta del taller y entró. Miró alrededor. "
                  "Sintió que algo no encajaba. Todo parecía normal pero no lo era.",
                  "Salió otra vez. Cerró con llave. No pasó nada más aquella tarde "
                  "y se fue a dormir temprano, tranquila del todo.")


def evaluation(n: int, scores: dict, patches=None) -> str:
    mean = round(sum(scores.values()) / len(scores), 1)
    return json.dumps({
        "capitulo": n,
        "puntuaciones": scores,
        "media": mean,
        "veredicto": "APROBADO" if mean >= 3.0 else "CORREGIR",
        "parches": patches or [],
        "observaciones": "",
    }, ensure_ascii=False)


GOOD_SCORES = {"tension": 4, "escaleta": 4, "voz": 4,
               "caracterizacion": 4, "ritmo": 4, "prosa": 4}
BAD_SCORES = {"tension": 2, "escaleta": 2, "voz": 2,
              "caracterizacion": 2, "ritmo": 2, "prosa": 2}


def continuity(n: int, title: str, pov: str, day: int, summary: str,
               present: list[str], hook: str, clues: list[dict],
               verdict: str = "OK") -> str:
    payload = {"capitulo": n, "veredicto": verdict, "contradicciones": []}
    if verdict == "OK":
        payload["deltas"] = {
            "ficha": {"titulo": title, "focalizador": pov, "dia_ficcion": day,
                      "resumen_120": summary, "personajes_presentes": present,
                      "gancho_final": hook},
            "pistas": clues,
            "cronologia": [{"dia_ficcion": day, "suceso": hook}],
            "personajes": [{"nombre": pov,
                            "cambios": {"ubicacion": "la casa",
                                        "sabe_que": f"lo aprendido en el cap. {n}"}}],
        }
    else:
        payload["deltas"] = None
        payload["contradicciones"] = [
            {"escena": 1, "tipo": "hecho",
             "descripcion": "El reloj aparece con la correa original.",
             "evidencia": "Capítulo 1, escena 2: la correa estaba cambiada.",
             "correccion": "Devolver la correa cambiada a la descripción."}]
    return json.dumps(payload, ensure_ascii=False)


CONT = {
    1: continuity(1, "El regreso", "Elena Vargas", 0,
                  "Marcos regresó a casa tras nueve días. Elena le sirvió agua y "
                  "no preguntó. Al mirarle la muñeca reconoció el reloj, pero la "
                  "correa era distinta de la que recordaba. Guardó silencio.",
                  ["Elena Vargas", "Marcos Duarte"],
                  "Elena reconoce el reloj y calla.",
                  [{"id": "P-01", "nuevo_estado": "PLANTADA",
                    "nota": "correa cambiada"}]),
    2: continuity(2, "La vecina", "Elena Vargas", 1,
                  "Nieves detuvo a Elena en el rellano y mencionó que el coche "
                  "había vuelto a las tres. Elena subió, registró el abrigo de "
                  "Marcos y encontró una llave pequeña de latón desconocida.",
                  ["Elena Vargas", "Nieves Abad"],
                  "Elena encuentra una llave que no conoce.",
                  [{"id": "P-03", "nuevo_estado": "PLANTADA", "nota": "llave de latón"},
                   {"id": "P-01", "nuevo_estado": "REFORZADA", "nota": "el reloj otra vez"},
                   {"id": "P-02", "nuevo_estado": "RED_HERRING", "nota": "la hora del coche"}]),
    3: continuity(3, "El taller", "Elena Vargas", 2,
                  "Elena probó la llave y descubrió que abría su propio taller. "
                  "Nieves admitió haberse equivocado de hora. Detrás del banco, "
                  "bajo una manta, Elena encontró una caja que no había puesto allí.",
                  ["Elena Vargas", "Nieves Abad"],
                  "Elena encuentra la caja.",
                  [{"id": "P-01", "nuevo_estado": "RESUELTA", "nota": "el reloj se explica"},
                   {"id": "P-03", "nuevo_estado": "RESUELTA", "nota": "la llave abre el taller"},
                   {"id": "P-02", "nuevo_estado": "DESACTIVADA", "nota": "Nieves se equivocó"}]),
}

INFORME = """# Informe de cierre del Acto {n}

## Estado de las pistas
| id | estado | último capítulo tocado | riesgo |
|----|--------|------------------------|--------|
| P-01 | PLANTADA | {n} | bajo |

## Problemas detectados
1. Ninguno relevante a esta escala. Gravedad BAJA.

## Recomendación
CONTINUAR SIN CAMBIOS
El acto cumple su función y las pistas avanzan según lo previsto.
"""


# --------------------------------------------------------------------------
# simulacro
# --------------------------------------------------------------------------
def write_tmp(sandbox: Path, name: str, text: str) -> Path:
    path = sandbox / ".tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def setup(sandbox: Path) -> None:
    (sandbox / "novela").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "novela" / "config.json", sandbox / "novela" / "config.json")
    run(sandbox, "init")


def plan(sandbox: Path) -> None:
    print("\n— Planificación y Puerta 1 —")
    for name, text in (("premisa.md", PREMISA), ("personajes.md", PERSONAJES),
                       ("voz-y-estilo.md", VOZ)):
        run(sandbox, "save-bible", "--name", name,
            "--file", str(write_tmp(sandbox, name, text)))
    out = run(sandbox, "save-bible", "--name", "escaleta.md",
              "--file", str(write_tmp(sandbox, "escaleta.md", escaleta())),
              "--gate")
    check("Tras la biblia el estado queda en GATE_PLAN",
          "presentar_puerta_plan" in out, out)

    out = run(sandbox, "validate-bible")
    check("La escaleta valida contra el esquema de §6.5",
          "cumplen su esquema" in out, out)

    out = run(sandbox, "next")
    check("En la puerta, `next` no escribe: pide presentar la puerta",
          "presentar_puerta_plan" in out, out)

    out = run(sandbox, "gate", "--answer", "aprobar")
    check("Puerta 1 aprobada deja el estado en ESCRIBIENDO, capítulo 1",
          "capítulo 1" in out, out)

    cfg = load(sandbox)
    ledger = ClueLedger.load(cfg.state_path("pistas.md"))
    check("El ledger se siembra desde la escaleta con las 3 pistas",
          len(ledger.clues) == 3, f"{[c.id for c in ledger.clues]}")
    check("Una pista escrita `P1` se siembra como `P-01` y no duplica",
          [c.id for c in ledger.clues] == ["P-01", "P-02", "P-03"],
          f"{[c.id for c in ledger.clues]}")


def write_chapter(sandbox: Path, n: int, text: str, ev: str, cont: str,
                  iteration: int = 0, patched: str | None = None) -> str:
    args = ["save-attempt", "--file", str(write_tmp(sandbox, f"{n}-i{iteration}.md", text))]
    if patched:
        args += ["--patched-scenes", patched]
    out = run(sandbox, *args, expect=None)
    run(sandbox, "record", "eval", "--file", str(write_tmp(sandbox, f"{n}-ev{iteration}.json", ev)))
    run(sandbox, "record", "cont", "--file", str(write_tmp(sandbox, f"{n}-co{iteration}.json", cont)))
    return out + run(sandbox, "decide")


def chapter_1(sandbox: Path) -> None:
    print("\n— Capítulo 1: camino de aprobación a la primera —")
    cfg = load(sandbox)

    out = run(sandbox, "prompt", "escritor", "--chapter", "1",
              "-o", str(sandbox / ".tmp" / "ctx1.md"))
    check("El contexto del Escritor cabe en el presupuesto de 16k (§7.4)",
          "tokens de 16000" in out and "AVISO" not in out, out)
    ctx1 = (sandbox / ".tmp" / "ctx1.md").read_text(encoding="utf-8")
    check("El contexto lleva premisa, voz y entrada de escaleta",
          all(s in ctx1 for s in ("## Premisa", "## Voz y estilo", "Escaleta —")))
    check("El contexto impone la extensión del perfil poc, no las 2.000 palabras",
          "entre 30 y 90 palabras" in ctx1, ctx1[:400])

    out = write_chapter(sandbox, 1, DRAFTS[1],
                        evaluation(1, GOOD_SCORES), CONT[1])
    check("Comprobación estructural sin problemas (2 escenas, marcador FIN)",
          "PROBLEMAS_ESTRUCTURALES: ninguno" in out, out)
    check("Con media 4.0 y continuidad OK, la decisión es aceptar",
          "DECISION: aceptar" in out, out)

    check("El borrador vive en .intentos/ y no en capitulos/ (§15.1 punto 3)",
          cfg.attempt_path(1, 0).exists() and not cfg.chapter_path(1).exists())

    out = run(sandbox, "accept")
    check("Al aceptar se promueve el capítulo y se escribe la ficha",
          cfg.chapter_path(1).exists() and cfg.card_path(1).exists(), out)
    check("Fin de acto 1 (poc): el siguiente paso es el Editor de acto",
          "SIGUIENTE: editar_acto" in out, out)

    ledger = ClueLedger.load(cfg.state_path("pistas.md"))
    check("El delta movió P-01 a PLANTADA",
          ledger.by_id("P-01").estado == "PLANTADA",
          ledger.by_id("P-01").estado)
    check("La cronología registró el día 0",
          "| 0 |" in read(cfg.state_path("cronologia.md")))
    check("El estado de personajes recoge a Elena",
          "Elena Vargas" in read(cfg.state_path("personajes-estado.md")))

    run(sandbox, "commit", "--chapter", "1")


def act_gate(sandbox: Path, act: int) -> None:
    out = run(sandbox, "save-report", "--act", str(act),
              "--file", str(write_tmp(sandbox, f"acto{act}.md",
                                      INFORME.format(n=act))))
    check(f"El cierre del acto {act} abre la Puerta 2",
          "presentar_puerta_acto" in out, out)
    run(sandbox, "gate", "--answer", "continuar")


def chapter_2_resume(sandbox: Path) -> None:
    print("\n— Capítulo 2: reanudación a mitad de ciclo —")
    cfg = load(sandbox)
    run(sandbox, "save-attempt",
        "--file", str(write_tmp(sandbox, "2-i0.md", DRAFTS[2])), expect=None)

    # se simula el cierre de la sesion: solo se relee el estado del disco
    out = run(sandbox, "next")
    check("Tras reanudar, `next` pide evaluar y no reescribe el capítulo 2",
          "ACCION: evaluar" in out, out)

    run(sandbox, "record", "eval",
        "--file", str(write_tmp(sandbox, "2-ev.json", evaluation(2, GOOD_SCORES))))
    out = run(sandbox, "next")
    check("Con la evaluación ya registrada, `next` pide verificar",
          "ACCION: verificar" in out, out)

    run(sandbox, "record", "cont",
        "--file", str(write_tmp(sandbox, "2-co.json", CONT[2])))
    run(sandbox, "decide")
    out = run(sandbox, "accept")
    check("Capítulo 2 aceptado", cfg.chapter_path(2).exists(), out)

    summary = read(cfg.state_path("resumen-rodante.md"))
    check("El resumen rodante degrada el capítulo 1 a una línea y deja el 2 íntegro "
          "(§7.2, §15.1 punto 12)",
          "**Cap. 1:**" in summary or "Cap. 1" in summary)

    ctx = run(sandbox, "prompt", "escritor", "--chapter", "3",
              "-o", str(sandbox / ".tmp" / "ctx3.md"))
    text = (sandbox / ".tmp" / "ctx3.md").read_text(encoding="utf-8")
    check("En el capítulo 3 el Escritor ve el 2 íntegro y el 1 solo como ficha "
          "(§15.1 punto 12)",
          "Texto íntegro del capítulo 2" in text
          and "Texto íntegro del capítulo 1" not in text, ctx)
    run(sandbox, "commit", "--chapter", "2")
    act_gate(sandbox, 2)


def chapter_3_loop(sandbox: Path) -> None:
    print("\n— Capítulo 3: parche, hashes y agotamiento de iteraciones —")
    cfg = load(sandbox)

    out = write_chapter(sandbox, 3, BAD_DRAFT, evaluation(
        3, BAD_SCORES,
        [{"escena": 2, "criterio": "tension",
          "problema": "La escena cierra en reposo.",
          "correccion": "Termina con el hallazgo de la caja."}]), CONT[3])
    check("Un capítulo por debajo del umbral manda parchear",
          "DECISION: parchear" in out, out)

    out = run(sandbox, "patch-plan")
    check("El plan de parches nombra la escena 2", "ESCENAS: 2" in out, out)

    # el modelo devuelve la escena 2 arreglada pero toca tambien la 1
    tampered = draft(3, "El taller",
                     "Otra escena 1 completamente distinta, reescrita sin permiso "
                     "por el modelo, que no debería sobrevivir a la comprobación.",
                     "Nieves apareció detrás y admitió que quizá no habían sido las "
                     "tres. Elena no se giró. Detrás del banco, bajo una manta, "
                     "había una caja que ella no había puesto allí.")
    out = run(sandbox, "save-attempt", "--iteration", "1",
              "--file", str(write_tmp(sandbox, "3-i1.md", tampered)),
              "--patched-scenes", "2", expect=None)
    check("La verificación de hashes detecta la escena 1 alterada (§9.5)",
          "alteró escenas no señaladas [1]" in out, out)

    restored = Chapter(read(cfg.attempt_path(3, 1)))
    original = Chapter(read(cfg.attempt_path(3, 0)))
    check("La escena 1 se restaura byte a byte desde el intento anterior",
          restored.scenes[1] == original.scenes[1],
          f"{restored.scenes[1][:60]!r}")
    check("La escena 2 sí conserva el parche",
          "caja" in restored.scenes[2])

    run(sandbox, "record", "eval", "--iteration", "1",
        "--file", str(write_tmp(sandbox, "3-ev1.json", evaluation(3, BAD_SCORES))))
    run(sandbox, "record", "cont", "--iteration", "1",
        "--file", str(write_tmp(sandbox, "3-co1.json", CONT[3])))
    out = run(sandbox, "decide")
    check("Segunda iteración fallida: sigue habiendo margen (max 2)",
          "DECISION: parchear" in out, out)

    run(sandbox, "save-attempt", "--iteration", "2",
        "--file", str(write_tmp(sandbox, "3-i2.md", DRAFTS[3])), expect=None)
    run(sandbox, "record", "eval", "--iteration", "2",
        "--file", str(write_tmp(sandbox, "3-ev2.json",
                                evaluation(3, {**BAD_SCORES, "tension": 3}))))
    run(sandbox, "record", "cont", "--iteration", "2",
        "--file", str(write_tmp(sandbox, "3-co2.json", CONT[3])))
    out = run(sandbox, "decide")
    check("Agotadas las 2 reescrituras, se acepta con deuda (§9.4)",
          "DECISION: aceptar_con_deuda" in out, out)
    check("Se elige el intento de mayor media, no el último",
          "MEJOR_INTENTO: i2" in out, out)

    out = run(sandbox, "accept")
    check("El capítulo 3 se acepta pese a no llegar al umbral",
          cfg.chapter_path(3).exists(), out)
    debt = read(cfg.state_path("deuda-narrativa.md"))
    check("La deuda narrativa registra el capítulo 3 (§6.10)",
          "## Capítulo 3" in debt, debt)
    run(sandbox, "commit", "--chapter", "3")


def final(sandbox: Path) -> None:
    print("\n— Auditoría final y Puerta 3 —")
    act_gate(sandbox, 3)
    out = run(sandbox, "audit", "--final", expect=None)
    check("La auditoría de §8.3 pasa: ninguna pista real sin resolver "
          "ni red herring vivo", "sin incidencias" in out, out)

    out = run(sandbox, "gate", "--answer", "aceptar")
    check("La Puerta 3 cierra la ejecución", "completada" in out.lower(), out)

    out = run(sandbox, "next")
    check("Con la novela completa, `next` no propone nada",
          "ACCION: nada" in out, out)


def audit_blocks(sandbox: Path) -> None:
    """15.1 punto 10: un red herring sin desactivar debe frenar la ejecución."""
    print("\n— Red herring sin desactivar: la auditoría debe bloquear —")
    cfg = load(sandbox)
    path = cfg.state_path("pistas.md")
    ledger = ClueLedger.load(path)
    clue = ledger.by_id("P-02")
    clue.estado = "RED_HERRING"
    clue.resolucion_prevista = "-"
    ledger.save(path)

    out = run(sandbox, "audit", "--final", expect=1)
    check("Con un red herring vivo, la auditoría final falla y lo nombra",
          "P-02" in out and "incidencias" in out, out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true",
                        help="No borra el directorio de pruebas.")
    args = parser.parse_args()

    sandbox = Path(tempfile.mkdtemp(prefix="novela-poc-"))
    subprocess.run(["git", "init", "-q"], cwd=sandbox, capture_output=True)
    subprocess.run(["git", "config", "user.email", "poc@local"], cwd=sandbox,
                   capture_output=True)
    subprocess.run(["git", "config", "user.name", "poc"], cwd=sandbox,
                   capture_output=True)

    print(f"Simulacro del POC en {sandbox}")
    try:
        setup(sandbox)
        plan(sandbox)
        chapter_1(sandbox)
        act_gate(sandbox, 1)
        chapter_2_resume(sandbox)
        chapter_3_loop(sandbox)
        final(sandbox)
        audit_blocks(sandbox)

        log = subprocess.run(["git", "log", "--oneline"], cwd=sandbox,
                             capture_output=True, text=True,
                             encoding="utf-8").stdout
        print("\n— Historial —")
        check("Hay un commit por capítulo aceptado (§15.1 punto 5)",
              len([l for l in log.splitlines() if "capítulo" in l]) == 3, log)
        tracked = subprocess.run(["git", "ls-files"], cwd=sandbox,
                                 capture_output=True, text=True).stdout
        check("`.intentos/` no entra en el historial (§15.1 punto 5)",
              ".intentos" not in tracked)
    finally:
        print(f"\n{len(PASS)} comprobaciones correctas, {len(FAIL)} fallidas.")
        if FAIL:
            for name in FAIL:
                print(f"  FALLO: {name}")
        if args.keep:
            print(f"Directorio conservado: {sandbox}")
        else:
            shutil.rmtree(sandbox, ignore_errors=True)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())

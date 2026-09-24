"""Fábrica de workspaces sintéticos: el agente falso de validators.md §3.5.

Genera de forma determinista lo que escribirían el arquitecto, el trazador, el escritor, los
revisores y el cronista. La prosa es mala a propósito: se prueba el mecanismo, no el texto.
Ningún fixture se genera llamando a un modelo.
"""

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from typer.testing import CliRunner, Result

from novela.cli import app
from novela.dominio import frontmatter
from novela.dominio.artefactos import Memoria
from novela.dominio.estado import Estado
from novela.dominio.version import PeticionDeCambio
from novela.plataforma import estado_db
from novela.plataforma.workspace import huella as huella_de

ELENA, TOMAS, INES = "per-elena-vidal", "per-tomas-reyes", "per-ines-mar"
FARO, PUERTO, ARCHIVO = "esc-casa-del-faro", "esc-puerto", "esc-archivo"
PALABRAS_POR_CAPITULO = 300
GANCHOS = ("pregunta_abierta", "amenaza", "revelacion", "decision_pendiente", "calma_inquietante")
APERTURAS = (
    "una línea de diálogo",
    "un objeto en primer plano",
    "una frase de menos de 6 palabras",
)


@dataclass(frozen=True)
class Novela:
    num_capitulos: int
    pistas: tuple[tuple[int, int | None], ...]  # (capítulo en que se planta, en que se paga)
    hilos: tuple[tuple[int, int], ...]  # (capítulo en que se abre, en que se cierra)
    # Spec 0007: hechos además del hec-00n de cada capítulo, y los que un capítulo cita en
    # hechos_usados.
    hechos_extra: tuple[tuple[str, int], ...] = ()  # (id, capítulo que lo introduce)
    usados: tuple[tuple[int, str], ...] = ()  # (capítulo, hecho que cita)

    def pistas_de(self, n: int) -> tuple[list[str], list[str]]:
        plantar = [f"pis-{i:03d}" for i, (p, _) in enumerate(self.pistas, 1) if p == n]
        pagar = [f"pis-{i:03d}" for i, (_, q) in enumerate(self.pistas, 1) if q == n]
        return plantar, pagar

    def hilos_de(self, n: int) -> tuple[list[str], list[str]]:
        abre = [f"hil-{j:03d}" for j, (a, _) in enumerate(self.hilos, 1) if a == n]
        cierra = [f"hil-{j:03d}" for j, (_, c) in enumerate(self.hilos, 1) if c == n]
        return abre, cierra


DEMO = Novela(24, pistas=((2, 20), (3, 6), (5, 22), (8, 23)), hilos=((1, 10), (4, 24), (7, 15)))
# Una pista plantada en el 1 que nadie paga: el hallazgo de CA-23.
HUERFANA = Novela(3, pistas=((1, 3), (1, None)), hilos=((1, 3),))
# demo-cambio (spec 0007 §7): hec-102 nace en el 2 y lo cita el 5; hec-002 lo citan el 4 y el 6.
# El 2, afectado, planta una pista, cierra hil-003 y abre hil-002, que cierra el 3, reaplicable:
# es lo que miran CA-25 y CA-27.
CAMBIO = Novela(
    6,
    pistas=((2, 5), (3, 6)),
    hilos=((1, 6), (2, 3), (1, 2)),
    hechos_extra=(("hec-102", 2),),
    usados=((4, "hec-002"), (5, "hec-102"), (6, "hec-002")),
)


def _md(meta: dict[str, Any], cuerpo: str) -> str:
    return frontmatter.unir(meta, cuerpo)


def nn(n: int) -> str:
    return f"{n:02d}"


def run_id(n: int) -> str:
    return f"r-202601{n:02d}-0900"


def run_v2(n: int) -> str:
    """Los runs de la versión 2: los de la 1 son anteriores al cambio y no se reutilizan (P1)."""
    return f"r-202602{n:02d}-0900"


# La petición ficticia de spec 0007 §7.
TEXTO_CAMBIO = "La puerta de la linterna estaba intacta en la noche 2."


# --- Canon: lo que escribiría el arquitecto --------------------------------------------------


def _ficha(id_: str, nombre: str, rol: str, habla: str, secreto: str | None) -> str:
    meta: dict[str, Any] = {
        "identidad": {"id": id_, "nombre": nombre, "alias": [], "edad": 40, "rol_narrativo": rol},
        "fisico": {"pelo": "gris"},
        "voz": {"idiolecto": "seco", "registro": "llano", "dialogo_canonico": [habla]},
        "psicologia": {
            "deseo": f"{nombre} quiere irse",
            "necesidad": "quedarse",
            "miedo": "el agua",
            "herida": "el hermano",
        },
        "coartada_y_cronologia_privada": [
            {"momento": "dia 1, 23:10", "ubicacion": FARO, "detalle": f"{nombre} sube al faro"}
        ],
    }
    if secreto:
        meta["secreto"] = {"que_oculta": secreto, "a_quien": [ELENA]}
    return _md(meta, f"{nombre} es personaje de la novela sintética.\n")


def canon(novela: Novela) -> dict[str, str]:
    pistas = [
        {
            "id": f"pis-{i:03d}",
            "contenido": f"El reloj de la linterna marca las {i} y cuarto en la pista {i}.",
            "capitulo_plantado": p,
            "capitulo_pagado": q,
            "quien_la_percibe": ["lector"],
            "es_fair_play": True,
        }
        for i, (p, q) in enumerate(novela.pistas, 1)
    ]
    revelaciones = [
        {
            "id": f"rev-{i:03d}",
            "contenido": f"La revelación {i} demuestra que el apagón fue deliberado.",
            "pistas_que_la_pagan": [f"pis-{i:03d}"],
            "capitulo_previsto": q,
            "quien_la_recibe": "lector",
            "impacto": "alta",
        }
        for i, (_, q) in enumerate(novela.pistas, 1)
        if q is not None
    ]
    misterio = {
        "verdad_oculta": [
            "Tomás Reyes apagó el faro a mano para que el pesquero de su hermano encallara.",
            "Lo hizo para cobrar el seguro que había firmado tres semanas antes del naufragio.",
        ],
        "culpable_o_amenaza": TOMAS,
        "motivo_medio_oportunidad": {
            "motivo": "La deuda con la cofradía que Tomás escondía a todo el pueblo.",
            "medio": "La llave de la linterna que nunca devolvió al ayuntamiento.",
            "oportunidad": "La hora en que Inés cerraba la taberna y nadie miraba el cabo.",
        },
        "pistas": pistas,
        "pistas_falsas": [
            {
                "id": "pfa-001",
                "contenido": "Inés tenía una copia de la llave del faro desde el verano.",
                "a_quien_apunta": INES,
                "cuando_se_desmonta": max(1, novela.num_capitulos - 1),
            }
        ],
        "revelaciones": revelaciones,
        "giros": [],
        "reloj": {
            "descripcion": "El juicio por el seguro se celebra en diez días.",
            "limite": "dia 10",
        },
    }
    mundo = {
        "escenarios": [
            {
                "id": id_,
                "nombre": nombre,
                "descripcion": f"{nombre} en la novela sintética",
                "detalle_sensorial": "olor a sal",
                "quien_tiene_acceso": [ELENA, TOMAS],
            }
            for id_, nombre in (
                (FARO, "La casa del faro"),
                (PUERTO, "El puerto"),
                (ARCHIVO, "El archivo"),
            )
        ],
        "epoca_y_tecnologia": {
            "epoca": "1998",
            "existe": ["teléfono fijo"],
            "no_existe": ["móvil"],
        },
        "reglas_del_mundo": ["El faro solo se enciende desde la linterna."],
        "instituciones": [
            {"nombre": "Guardia Civil", "procedimientos": "Tarda dos horas en llegar."}
        ],
    }
    estilo = {
        "guia_de_voz_narrativa": "Frases cortas, sin adjetivos de relleno.",
        "ritmo": {
            "longitud_media_frase": 12.0,
            "proporcion_dialogo": 0.3,
            "proporcion_accion": 0.4,
            "proporcion_interioridad": 0.3,
        },
        "prohibiciones": ["de repente", "sin previo aviso"],
        "parrafos_canonicos": ["Elena no encendió la luz. Conocía la escalera de memoria."],
        "convenciones_formato": {"separador_escena": "***"},
    }
    premisa = {
        "logline": "Una farera vuelve al pueblo donde el faro se apagó la noche del naufragio.",
        "pregunta_dramatica": "¿Podrá Elena seguir en el pueblo cuando sepa quién fue?",
        "tema": "la culpa heredada",
        "promesa_al_lector": "un culpable que estuvo siempre a la vista",
    }
    return {
        "canon/premisa.md": _md(premisa, "La premisa de la novela sintética.\n"),
        "canon/mundo.md": _md(mundo, "Un pueblo de costa con un faro apagado.\n"),
        "canon/estilo.md": _md(estilo, "Seco y exacto.\n"),
        "canon/misterio.md": _md(misterio, "El misterio completo, solo para quien lo puede ver.\n"),
        f"canon/personajes/{ELENA}.md": _ficha(
            ELENA, "Elena Vidal", "protagonista", "No le pregunté nada.", None
        ),
        f"canon/personajes/{TOMAS}.md": _ficha(
            TOMAS, "Tomás Reyes", "antagonista", "Eso fue hace mucho.", "Debe dinero a la cofradía."
        ),
        f"canon/personajes/{INES}.md": _ficha(
            INES, "Inés Mar", "testigo", "Yo cerré a las once.", "Vio luz en el cabo aquella noche."
        ),
    }


# --- Plan: lo que escribiría el trazador -----------------------------------------------------


def plan(novela: Novela) -> dict[str, str]:
    n_total = novela.num_capitulos
    tercio = max(1, n_total // 3)
    actos = [
        {
            "numero": 1,
            "funcion_dramatica": "planteamiento",
            "capitulos": list(range(1, tercio + 1)),
        },
        {
            "numero": 2,
            "funcion_dramatica": "confrontación",
            "capitulos": list(range(tercio + 1, n_total)) or [n_total],
        },
        {"numero": 3, "funcion_dramatica": "desenlace", "capitulos": [n_total]},
    ]
    escaleta = {
        "actos": actos,
        "puntos_de_giro": {
            "detonante": 1,
            "punto_medio": max(1, n_total // 2),
            "crisis": max(1, n_total - 2),
            "climax": max(1, n_total - 1),
            "resolucion": n_total,
        },
        "curva_tension_objetivo": [2 + (7 * i) // max(1, n_total - 1) for i in range(n_total)],
    }
    ficheros = {"plan/escaleta.md": _md(escaleta, "La escaleta de la novela sintética.\n")}
    for n in range(1, n_total + 1):
        plantar, pagar = novela.pistas_de(n)
        abre, cierra = novela.hilos_de(n)
        ficha = {
            "capitulo": n,
            "pov": ELENA,
            "objetivo_dramatico": f"Al final del capítulo {n} Elena sabe algo que no sabía.",
            "escenas": [
                {
                    "id": f"esc-{nn(n)}-1",
                    "lugar": FARO,
                    "tiempo_diegetico": f"dia {n}, 21:00",
                    "personajes": [ELENA, TOMAS],
                    "dialogo": [ELENA, TOMAS],
                    "beat": "Tomás aparece sin avisar",
                    "conflicto": "Elena no puede echarle",
                },
                {
                    "id": f"esc-{nn(n)}-2",
                    "lugar": PUERTO,
                    "tiempo_diegetico": f"dia {n}, 23:00",
                    "personajes": [ELENA, INES],
                    "dialogo": [INES],
                    "beat": "Inés habla de más",
                    "conflicto": "Elena duda de ella",
                },
            ],
            "pistas_a_plantar": plantar,
            "pistas_a_pagar": pagar,
            "hilos_que_abre": abre,
            "hilos_que_cierra": cierra,
            "gancho_final": GANCHOS[n % len(GANCHOS)],
            "restriccion_de_apertura": f"Empieza con {APERTURAS[n % len(APERTURAS)]}.",
        }
        ficheros[f"plan/capitulos/{nn(n)}.md"] = _md(ficha, f"Ficha del capítulo {n}.\n")
    return ficheros


# --- Capítulo: lo que escribiría el escritor -------------------------------------------------


def frase_de_hecho(n: int) -> str:
    return f"En la noche {n} Elena comprobó que la puerta de la linterna seguía forzada."


def frase_de_hecho_extra(n: int) -> str:
    return f"En la noche {n} Elena encontró una colilla junto a la escalera."


def _origen(novela: Novela, hecho: str) -> int:
    return dict(novela.hechos_extra).get(hecho) or int(hecho[-3:])


def frase_de_uso(novela: Novela, n: int, hecho: str) -> str:
    origen = _origen(novela, hecho)
    return f"En la noche {n} Elena volvió a pensar en lo que supo en la noche {origen}."


def frase_de_escena(n: int, escena: int) -> str:
    return f"Aquella escena {escena} del capítulo {n} empezó con el viento del norte."


def frase_regenerada(n: int) -> str:
    return f"En la noche {n} Elena vio que la puerta de la linterna seguía intacta."


def capitulo(novela: Novela, n: int) -> str:
    plantar, pagar = novela.pistas_de(n)
    abre, cierra = novela.hilos_de(n)
    relleno = f"Elena contó los escalones del faro por {n} vez y el mar siguió en su sitio."
    parrafos = [frase_de_escena(n, 1) + " " + frase_de_hecho(n)]
    parrafos += [frase_de_hecho_extra(n) for _, c in novela.hechos_extra if c == n]
    parrafos += [frase_de_uso(novela, n, h) for c, h in novela.usados if c == n]
    parrafos += [f"Elena encontró la pista {p[-1]} donde nadie miraba." for p in plantar + pagar]
    cuerpo_min = " ".join(parrafos)
    while len(cuerpo_min.split()) < PALABRAS_POR_CAPITULO - 20:
        parrafos.append(relleno)
        cuerpo_min = " ".join(parrafos)
    mitad = len(parrafos) // 2
    cuerpo = (
        f"# Capítulo {n}\n\n"
        + "\n\n".join(parrafos[:mitad])
        + "\n\n***\n\n"
        + frase_de_escena(n, 2)
        + "\n\n"
        + "\n\n".join(parrafos[mitad:])
        + "\n"
    )
    meta = {
        "capitulo": n,
        "titulo": f"La linterna, noche {n}",
        "pov": ELENA,
        "palabras": len(cuerpo.split()),
        "escenas": [f"esc-{nn(n)}-1", f"esc-{nn(n)}-2"],
        "pistas_plantadas": plantar,
        "pistas_pagadas": pagar,
        "hilos_abiertos": abre,
        "hilos_cerrados": cierra,
        "version_canon": 1,
        "version_plan": 1,
        "run_id": run_id(n),
    }
    return _md(meta, cuerpo)


# --- Revisores y cronista --------------------------------------------------------------------


def informe(n: int, agente: str, **extra: Any) -> str:
    datos = {"capitulo": n, "agente": agente, "veredicto": "aprobado", "hallazgos": []} | extra
    return json.dumps(datos, ensure_ascii=False, indent=2)


def informes(novela: Novela, n: int) -> dict[str, str]:
    tension = 2 + (7 * (n - 1)) // max(1, novela.num_capitulos - 1)
    return {
        f"qa/{nn(n)}-continuidad.json": informe(n, "continuista"),
        f"qa/{nn(n)}-estilo.json": informe(n, "editor-estilo"),
        f"qa/{nn(n)}-suspense.json": informe(
            n,
            "lector-suspense",
            puntuaciones={"tension": tension, "fair_play": 0.9, "coherencia": 0.8},
        ),
    }


def delta(novela: Novela, n: int) -> dict[str, Any]:
    abre, cierra = novela.hilos_de(n)
    hilos = []
    for j, (a, c) in enumerate(novela.hilos, 1):
        if a == n or c == n:
            hilos.append(
                {
                    "id": f"hil-{j:03d}",
                    "estado": "cerrado" if c == n else "abierto",
                    "abierto_en": a,
                    "cerrado_en": c if c == n else None,
                    "descripcion": f"La pregunta {j} del faro.",
                }
            )
    assert {h["id"] for h in hilos if h["abierto_en"] == n} == set(abre)
    assert {h["id"] for h in hilos if h["cerrado_en"] == n} == set(cierra)
    hecho = f"hec-{n:03d}"
    return {
        "capitulo": n,
        "linea_temporal": [
            {
                "escena": f"esc-{nn(n)}-1",
                "capitulo": n,
                "inicio": f"dia {n}, 21:00",
                "duracion_min": 40,
                "cita": frase_de_escena(n, 1),
            },
            {
                "escena": f"esc-{nn(n)}-2",
                "capitulo": n,
                "inicio": f"dia {n}, 23:00",
                "duracion_min": 30,
            },
        ],
        "personajes": {
            ELENA: {
                "ubicacion": PUERTO,
                "estado_fisico": "cansada",
                "estado_emocional": "alerta",
                "condicion": "viva",
                "objetivo_activo": "saber quién apagó el faro",
                "ultima_aparicion": n,
            },
            TOMAS: {
                "ubicacion": FARO,
                "estado_fisico": "bien",
                "estado_emocional": "nervioso",
                "condicion": "viva",
                "objetivo_activo": "que nadie suba a la linterna",
                "ultima_aparicion": n,
            },
        },
        "conocimiento": {ELENA: [{"hecho": hecho, "desde_capitulo": n, "cita": frase_de_hecho(n)}]},
        "conocimiento_lector": [{"hecho": hecho, "desde_capitulo": n}],
        "relaciones": [
            {
                "de": ELENA,
                "a": TOMAS,
                "tipo": "sospecha",
                "intensidad": min(1.0, n / 24),
                "desde": 1,
            }
        ],
        "objetos": [
            {
                "id": "obj-001",
                "poseedor": TOMAS,
                "ubicacion": None,
                "capitulo_intro": 1,
                "relevancia": "alta",
            }
        ],
        "libro_de_hechos": [
            {
                "id": hecho,
                "texto": f"La puerta de la linterna estaba forzada en la noche {n}.",
                "capitulo": n,
                "cita": frase_de_hecho(n),
            }
        ]
        + [
            {
                "id": extra,
                "texto": f"Había una colilla junto a la escalera en la noche {n}.",
                "capitulo": n,
                "cita": frase_de_hecho_extra(n),
            }
            for extra, c in novela.hechos_extra
            if c == n
        ],
        "hechos_usados": [
            {"hecho": h, "cita": frase_de_uso(novela, n, h)} for c, h in novela.usados if c == n
        ],
        "hilos": hilos,
        "resumen": {
            "linea": f"Capítulo {n}: Elena vuelve a la linterna.",
            "parrafo": f"En el capítulo {n} Elena sube al faro, discute con Tomás y oye a Inés.",
            "escena": {
                f"esc-{nn(n)}-1": "Elena y Tomás en la casa del faro.",
                f"esc-{nn(n)}-2": "Inés habla de más en el puerto.",
            },
        },
    }


def capitulo_regenerado(novela: Novela, n: int) -> str:
    """El agente falso de la regeneración (spec 0007 §7): el mismo contrato de pistas e hilos y
    una frase más, que es la que cita el hecho nuevo."""
    meta, cuerpo = frontmatter.partir(capitulo(novela, n))
    cuerpo = cuerpo.replace("\n\n***\n\n", f"\n\n{frase_regenerada(n)}\n\n***\n\n", 1)
    return _md(meta | {"palabras": len(cuerpo.split())}, cuerpo)


def delta_regenerado(
    novela: Novela, n: int, peticion: PeticionDeCambio, vigente: Estado, anterior: Estado
) -> dict[str, Any]:
    """Lo que escribiría el cronista de un capítulo afectado: el hecho cambiado pasa al id
    reservado con el texto nuevo, los requeridos conservan id y texto, y los demás hechos que el
    capítulo introduce toman ids libres de las dos bases (P4). Los objetos que la versión nueva
    aún no tiene no se reintroducen: serían ids de la anterior."""
    d = delta(novela, n)
    requeridos = set(peticion.plan.requeridos.get(n, []))
    todos = [h.id for h in (*vigente.libro_de_hechos, *anterior.libro_de_hechos)]
    todos.append(peticion.hecho_nuevo)  # reservado aunque aún no esté en ninguna base
    libres = iter(range(max(int(h[-3:]) for h in todos) + 1, 1000))
    ids = {peticion.hecho: peticion.hecho_nuevo}
    for h in d["libro_de_hechos"]:
        if h["id"] == peticion.hecho:
            h |= {"texto": peticion.texto, "cita": frase_regenerada(n)}
        elif h["id"] not in requeridos:
            ids[h["id"]] = f"hec-{next(libres):03d}"
        h["id"] = ids.get(h["id"], h["id"])
    conocimiento = [e for es in d["conocimiento"].values() for e in es]
    for e in (*conocimiento, *d["conocimiento_lector"], *d["hechos_usados"]):
        e["hecho"] = ids.get(e["hecho"], e["hecho"])
    existen = {o.id for o in vigente.objetos}
    d["objetos"] = [o for o in d["objetos"] if o["id"] in existen]
    return d


def estados(raiz: Path, version: int) -> tuple[Estado, Estado]:
    """La base vigente de la raíz y la de `versiones/v<version>/`."""
    leidos = []
    for ruta in (raiz, raiz / "versiones" / f"v{version}"):
        with estado_db.abrir(ruta / "estado" / "estado.db", solo_lectura=True) as conn:
            leidos.append(estado_db.leer(conn))
    return leidos[0], leidos[1]


def memoria(novela: Novela, n: int) -> str:
    """Lo que renderiza aplicar-delta desde el resumen del delta."""
    resumen = Memoria(capitulo=n, **delta(novela, n)["resumen"])
    return frontmatter.unir(resumen.model_dump(mode="json"), "")


def escribir(raiz: Path, ficheros: dict[str, str]) -> None:
    for relativa, texto in ficheros.items():
        ruta = raiz / relativa
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(texto.encode("utf-8"))


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def cli(base: Path, *orden: str, run: str, entorno: dict[str, str] | None = None) -> Result:
    """`entorno` sustituye al de por defecto, que fija NOVELA_RUN_ID: sin él, el run sale del
    reloj, como en una sesión real."""
    fijo = {"NOVELAS_DIR": str(base), "NOVELA_RUN_ID": run}
    return CliRunner().invoke(app, list(orden), env=fijo if entorno is None else entorno)


def huella(raiz: Path) -> str:
    """Sin los -wal y -shm de SQLite, que son efímeros: en Windows, abrir la base en solo
    lectura los crea o los toca, y no son parte de lo que el subcomando escribe."""
    copia = raiz.parent / "huella"
    shutil.rmtree(copia, ignore_errors=True)
    shutil.copytree(raiz, copia, ignore=shutil.ignore_patterns("*-wal", "*-shm"))
    try:
        return huella_de(copia)
    finally:
        shutil.rmtree(copia)


def pedir_cambio(base: Path, slug: str, texto: str = TEXTO_CAMBIO) -> Result:
    """La petición de spec 0007 §7, sin NOVELA_RUN_ID: su run sale del reloj."""
    orden = ("cambio", slug, "--hecho", "hec-002", "--texto", texto)
    return cli(base, *orden, run="", entorno={"NOVELAS_DIR": str(base)})


def preparar_capitulo(
    base: Path,
    slug: str,
    novela: Novela,
    n: int,
    texto: str | None = None,
    delta_: dict[str, Any] | None = None,
    run: str | None = None,
) -> None:
    """El bucle por capítulo hasta dejar el delta escrito, con el CLI real y agentes falsos:
    lo que escribirían el escritor, los tres revisores y el cronista. `texto` y `delta_`
    sustituyen a los de la versión 1."""
    raiz, run = base / slug, run or run_id(n)

    def paso(*orden: str) -> None:
        resultado = cli(base, *orden, run=run)
        assert resultado.exit_code == 0, f"{orden}: {resultado.output}"

    paso("briefing", slug, str(n), "escritor")
    escribir(raiz, {f"capitulos/{nn(n)}.md": texto or capitulo(novela, n)})
    paso("validar", slug, str(n))
    for agente in ("continuista", "editor-estilo", "lector-suspense"):
        paso("briefing", slug, str(n), agente)
    escribir(raiz, informes(novela, n))  # el editor falso aprueba sin reescribir
    paso("briefing", slug, str(n), "cronista")
    datos = delta_ or delta(novela, n)
    escribir(raiz, {f"estado/deltas/{nn(n)}.json": json.dumps(datos, indent=2)})


def cerrar_capitulo(base: Path, slug: str, novela: Novela, n: int) -> None:
    """El bucle entero de un capítulo, sin una sola llamada a modelo (validators.md §3.5)."""
    preparar_capitulo(base, slug, novela, n)
    for orden in ("aplicar-delta", "checkpoint"):
        resultado = cli(base, orden, slug, str(n), run=run_id(n))
        assert resultado.exit_code == 0, f"{orden} {n}: {resultado.output}"


def v2(raiz: Path, orden: str, n: int, *resto: str) -> Result:
    """Una orden de la versión 2 sobre el capítulo `n`, en su run v2."""
    return cli(raiz.parent, orden, raiz.name, str(n), *resto, run=run_v2(n))


def reaplicar(raiz: Path, n: int) -> None:
    """Lo que hace el procedimiento con `NN reaplicar`: sin agentes."""
    for orden, resto in (("aplicar-delta", ("--reaplicar",)), ("checkpoint", ())):
        resultado = v2(raiz, orden, n, *resto)
        assert resultado.exit_code == 0, f"{orden} {n}: {resultado.output}"


def regenerado(raiz: Path, novela: Novela, n: int) -> tuple[str, dict[str, Any]]:
    """Capítulo y delta del agente falso de regeneración, sobre las bases de este momento."""
    peticion = PeticionDeCambio.model_validate_json(
        sorted((raiz / "cambios").glob("cam-*.json"))[-1].read_bytes()
    )
    vigente, anterior = estados(raiz, peticion.version_base)
    texto = capitulo_regenerado(novela, n)
    return texto, delta_regenerado(novela, n, peticion, vigente, anterior)


def cerrar_regenerado(
    raiz: Path, novela: Novela, n: int, texto: str, delta_: dict[str, Any]
) -> None:
    """El bucle de un capítulo afectado, con el CLI real, hasta el checkpoint."""
    preparar_capitulo(raiz.parent, raiz.name, novela, n, texto, delta_, run_v2(n))
    for orden in ("aplicar-delta", "checkpoint"):
        resultado = v2(raiz, orden, n)
        assert resultado.exit_code == 0, f"{orden} {n}: {resultado.output}"


def construir(
    base: Path, slug: str, novela: Novela, cerrados: int, instantaneas: dict[int, str] | None = None
) -> Path:
    """Crea el workspace con `novela nueva`, escribe canon y plan y cierra `cerrados` capítulos
    con el bucle real. `instantaneas` copia el workspace a otro slug al cerrar un capítulo."""
    total = novela.num_capitulos
    orden = ["nueva", slug, "--idea", "Un faro apagado.", "--capitulos", str(total)]
    orden += ["--palabras", str(PALABRAS_POR_CAPITULO * total)]
    resultado = CliRunner().invoke(app, orden, env={"NOVELAS_DIR": str(base)})
    assert resultado.exit_code == 0, resultado.output
    raiz = base / slug
    escribir(raiz, canon(novela) | plan(novela))
    for n in range(1, cerrados + 1):
        cerrar_capitulo(base, slug, novela, n)
        if instantaneas and n in instantaneas:
            shutil.copytree(raiz, base / instantaneas[n])
    return raiz

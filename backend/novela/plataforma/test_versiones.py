import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

from novela.dominio.estado import Cursor, Estado
from novela.dominio.version import PeticionDeCambio, RegistroDeVersiones, Version
from novela.plataforma import estado_db, versiones
from novela.plataforma.workspace import WorkspaceRepository, huella, sha256
from novela.slices.cambio import plan

Novelas = Callable[[str], WorkspaceRepository]
COPIADOS = ("capitulos", "estado/deltas", "memoria", "qa", "checkpoints")
BASE = Path("estado") / "estado.db"
TEXTO = "La puerta de la linterna estaba intacta en la noche 2."
CREADO = datetime.fromisoformat("2026-09-24T10:00:00+02:00")


def _peticion(ws: WorkspaceRepository, hecho: str = "hec-002") -> PeticionDeCambio:
    total = ws.config().parametros_obra.num_capitulos
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        hechos = {h.id: h for h in estado_db.leer(conn).libro_de_hechos}
        usos = [u for h in hechos for u in estado_db.usos(conn, h)]
    return PeticionDeCambio(
        id="cam-001",
        hecho=hecho,
        texto_anterior=hechos[hecho].texto,
        texto=TEXTO,
        hecho_nuevo=plan.id_reservado(hechos),
        version_base=1,
        version_nueva=2,
        plan=plan.plan_de_regeneracion(usos, hecho, total),
        estado="preparando",
        creado=CREADO,
    )


def _cambiar(ws: WorkspaceRepository, corte: Callable[[str], None] | None = None) -> None:
    peticion = _peticion(ws)
    versiones.registrar_peticion(ws, peticion)
    if corte is None:
        versiones.preparar(ws, peticion)
    else:
        versiones.preparar(ws, peticion, corte)


def _ficheros(raiz: Path) -> dict[str, str]:
    return {
        f.relative_to(raiz).as_posix(): sha256(f)
        for d in COPIADOS
        for f in sorted((raiz / d).rglob("*"))
        if f.is_file()
    }


def _leer(ruta: Path) -> Estado:
    with estado_db.abrir(ruta, solo_lectura=True) as conn:
        return estado_db.leer(conn)


def test_instantanea_byte_a_byte(novelas: Novelas) -> None:
    """CA-16 (RF-17): versiones/v1/ tiene exactamente los ficheros copiados con sus sha256, que
    version.json lista, y la base copiada lee igual que la vigente."""
    ws = novelas("demo-cambio")
    antes, estado_antes = _ficheros(ws.raiz), _leer(ws.estado_db)
    punto = ws.ultimo_checkpoint()
    assert punto is not None
    _cambiar(ws)
    v1 = ws.raiz / "versiones" / "v1"
    assert _ficheros(v1) == antes
    version = ws.leer_json(v1 / "version.json", Version)
    assert version.numero == 1 and version.cambio is None
    assert version.ficheros == antes | {BASE.as_posix(): sha256(v1 / BASE)}
    assert version.capitulos_sha256 == punto.capitulos_sha256
    presentes = {f.relative_to(v1).as_posix() for f in v1.rglob("*") if f.is_file()}
    assert presentes == set(version.ficheros) | {"version.json"}  # ni -wal ni -shm
    assert _leer(v1 / BASE) == estado_antes


def test_instantanea_excluye(novelas: Novelas) -> None:
    """CA-16 (RF-18): ni canon, ni plan, ni runs, ni export, ni brief, ni config.yaml."""
    ws = novelas("demo-cambio")
    _cambiar(ws)
    v1 = ws.raiz / "versiones" / "v1"
    for fuera in ("canon", "plan", "runs", "export", "brief", "config.yaml"):
        assert not (v1 / fuera).exists(), fuera


def test_raiz_restablecida(novelas: Novelas) -> None:
    """CA-17 (RF-19): directorios de la raíz vacíos, base vacía de la versión 2 con el cursor
    inicial, runs, canon y plan intactos, y el registro con v1 y v2."""
    ws = novelas("demo-cambio")
    intactos = {d: huella(ws.raiz / d) for d in ("runs", "canon", "plan")}
    _cambiar(ws)
    # Ni .tmp ni el -wal de la base anterior. Se mira antes de abrir nada: en Windows, abrir en
    # solo lectura una base WAL crea sus -wal y -shm.
    assert not [f for f in ws.raiz.rglob("*") if ".tmp" in f.name or f.name.endswith("-wal")]
    for d in COPIADOS:
        assert (ws.raiz / d).is_dir() and not [f for f in (ws.raiz / d).rglob("*") if f.is_file()]
    inicial = Cursor(capitulo=1, fase="escritura", ultimo_paso=None, intento=1)
    assert _leer(ws.estado_db) == Estado(cursor=inicial)
    with estado_db.abrir(ws.estado_db, solo_lectura=True) as conn:
        assert versiones.version_vigente(conn) == 2
        meta = dict(conn.execute("SELECT clave, valor FROM meta"))
        assert meta["cambio"] == "cam-001"
        assert estado_db.usos(conn, "hec-002") == []  # la base nueva ya tiene la tabla
    assert {d: huella(ws.raiz / d) for d in intactos} == intactos
    registro = ws.leer_json(ws.raiz / "versiones" / "versiones.json", RegistroDeVersiones)
    assert [(v.numero, v.cambio) for v in registro.versiones] == [(1, None), (2, "cam-001")]
    peticion = versiones.cambio_en_curso(ws)
    assert peticion is not None and peticion.estado == "en_curso" and peticion.id == "cam-001"


class Corte(Exception):
    pass


@pytest.mark.parametrize("punto", ["mitad_copia", "renombrado", "capitulos_vaciados"])
def test_recuperacion_tras_corte(novelas: Novelas, tmp_path: Path, punto: str) -> None:
    """CA-18 (RF-20): tras un corte en cada punto, repetir deja la misma huella que sin corte."""
    ws = novelas("demo-cambio")
    limpio = WorkspaceRepository(tmp_path / "limpio" / ws.slug)
    shutil.copytree(ws.raiz, limpio.raiz)
    _cambiar(limpio)

    def cortar(donde: str) -> None:
        if donde == punto:
            raise Corte(donde)

    with pytest.raises(Corte):
        _cambiar(ws, cortar)
    en_curso = versiones.ultimo_cambio(ws)
    assert en_curso is not None and en_curso.estado == "preparando"
    assert versiones.cambio_en_curso(ws) is None
    _cambiar(ws)
    assert huella(ws.raiz) == huella(limpio.raiz)


def test_version_inmutable(novelas: Novelas) -> None:
    """CA-19, la parte de RF-21: un versiones/v1/ sin cambio en preparando que lo explique es
    un workspace inválido y no se escribe nada."""
    ws = novelas("demo-cambio")
    (ws.raiz / "versiones" / "v1" / "capitulos").mkdir(parents=True)
    antes = huella(ws.raiz)
    with pytest.raises(versiones.VersionInexplicada, match="v1"):
        _cambiar(ws)
    assert huella(ws.raiz) == antes
    assert not (ws.raiz / "cambios").exists()


def test_el_secreto_no_se_copia(novelas: Novelas) -> None:
    """RNF-06 (R52): ningún fichero de versiones/ ni cambios/ contiene una cadena de 30 o más
    caracteres de canon/misterio.md."""
    ws = novelas("demo-cambio")
    misterio = (ws.raiz / "canon" / "misterio.md").read_text(encoding="utf-8")
    trozos = {misterio[i : i + 30] for i in range(len(misterio) - 29)}
    _cambiar(ws)
    for d in ("versiones", "cambios"):
        for f in (ws.raiz / d).rglob("*"):
            if f.is_file():
                texto = f.read_bytes().decode("utf-8", "ignore")
                assert not any(t in texto for t in trozos), f


def test_tamano_de_la_instantanea(novelas: Novelas) -> None:
    """RNF-08 (R54): versiones/v1/ ≤ 1,05 × lo copiado de la raíz, en demo-terminado."""
    ws = novelas("demo-terminado")
    copiado = sum((ws.raiz / f).stat().st_size for f in _ficheros(ws.raiz))
    copiado += ws.estado_db.stat().st_size
    _cambiar(ws)
    v1 = ws.raiz / "versiones" / "v1"
    assert sum(f.stat().st_size for f in v1.rglob("*") if f.is_file()) <= 1.05 * copiado

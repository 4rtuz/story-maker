-- DDL de estado/estado.db: una tabla por colección de la rama 4 (architecture.md §7.1).
--
-- Las cinco colecciones append-only lo son porque lo impone el motor: triggers BEFORE UPDATE y
-- BEFORE DELETE con RAISE(ABORT). No hay ruta de escritura —ni un delta mal formado, ni un
-- subcomando nuevo, ni un sqlite3 abierto a mano— por la que se reescriba la historia.
-- Las append-only se leen en orden de inserción (rowid); las mutables, por id.
-- STRICT: el motor rechaza un tipo equivocado aunque el modelo se lo haya dejado pasar.

CREATE TABLE meta (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
) STRICT;

CREATE TABLE cursor (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    capitulo    INTEGER NOT NULL,
    fase        TEXT NOT NULL,
    ultimo_paso TEXT,
    intento     INTEGER NOT NULL
) STRICT;

CREATE TABLE linea_temporal (
    escena       TEXT PRIMARY KEY,
    capitulo     INTEGER NOT NULL,
    inicio       TEXT NOT NULL,
    duracion_min INTEGER NOT NULL,
    cita         TEXT
) STRICT;

CREATE TABLE personajes (
    id               TEXT PRIMARY KEY,
    ubicacion        TEXT,
    estado_fisico    TEXT NOT NULL,
    estado_emocional TEXT NOT NULL,
    condicion        TEXT NOT NULL,
    objetivo_activo  TEXT NOT NULL,
    ultima_aparicion INTEGER NOT NULL
) STRICT;

CREATE TABLE conocimiento (
    personaje      TEXT NOT NULL,
    hecho          TEXT NOT NULL,
    desde_capitulo INTEGER NOT NULL,
    cita           TEXT
) STRICT;

CREATE TABLE relaciones (
    de         TEXT NOT NULL,
    a          TEXT NOT NULL,
    tipo       TEXT NOT NULL,
    intensidad REAL NOT NULL,
    desde      INTEGER NOT NULL,
    PRIMARY KEY (de, a)
) STRICT;

CREATE TABLE objetos (
    id             TEXT PRIMARY KEY,
    poseedor       TEXT,
    ubicacion      TEXT,
    capitulo_intro INTEGER NOT NULL,
    relevancia     TEXT NOT NULL
) STRICT;

CREATE TABLE libro_de_hechos (
    id       TEXT PRIMARY KEY,
    texto    TEXT NOT NULL,
    capitulo INTEGER NOT NULL,
    cita     TEXT NOT NULL
) STRICT;

CREATE TABLE hilos (
    id          TEXT PRIMARY KEY,
    estado      TEXT NOT NULL,
    abierto_en  INTEGER NOT NULL,
    cerrado_en  INTEGER,
    descripcion TEXT NOT NULL
) STRICT;

-- Derivada: la recalcula aplicar-delta desde el frontmatter y el canon, no viene en el delta.
CREATE TABLE pistas (
    id          TEXT PRIMARY KEY,
    estado      TEXT NOT NULL,
    plantada_en INTEGER,
    pagada_en   INTEGER
) STRICT;

CREATE TABLE conocimiento_lector (
    hecho          TEXT NOT NULL,
    desde_capitulo INTEGER NOT NULL,
    cita           TEXT
) STRICT;

CREATE TABLE tension_real (
    capitulo INTEGER PRIMARY KEY,
    valor    INTEGER CHECK (valor BETWEEN 1 AND 10)  -- NULL: hueco, capítulo sin puntuar
) STRICT;

-- Derivada, una sola fila.
CREATE TABLE metricas (
    id                 INTEGER PRIMARY KEY CHECK (id = 1),
    palabras_totales   INTEGER NOT NULL,
    desviacion_vs_plan REAL NOT NULL
) STRICT;

-- El largo plazo no se carga, se consulta (architecture.md §6.4): índices por capítulo y por
-- entidad, que es lo que filtra la capa de estado de cada briefing.
CREATE INDEX linea_temporal_por_capitulo ON linea_temporal (capitulo);
CREATE INDEX conocimiento_por_personaje ON conocimiento (personaje);
CREATE INDEX conocimiento_por_capitulo ON conocimiento (desde_capitulo);
CREATE INDEX conocimiento_lector_por_capitulo ON conocimiento_lector (desde_capitulo);
CREATE INDEX libro_de_hechos_por_capitulo ON libro_de_hechos (capitulo);
CREATE INDEX relaciones_por_destino ON relaciones (a);
CREATE INDEX objetos_por_poseedor ON objetos (poseedor);
CREATE INDEX hilos_por_estado ON hilos (estado);

CREATE TRIGGER libro_de_hechos_no_update BEFORE UPDATE ON libro_de_hechos
BEGIN SELECT RAISE(ABORT, 'libro_de_hechos es append-only'); END;
CREATE TRIGGER libro_de_hechos_no_delete BEFORE DELETE ON libro_de_hechos
BEGIN SELECT RAISE(ABORT, 'libro_de_hechos es append-only'); END;

CREATE TRIGGER conocimiento_no_update BEFORE UPDATE ON conocimiento
BEGIN SELECT RAISE(ABORT, 'conocimiento es append-only'); END;
CREATE TRIGGER conocimiento_no_delete BEFORE DELETE ON conocimiento
BEGIN SELECT RAISE(ABORT, 'conocimiento es append-only'); END;

CREATE TRIGGER linea_temporal_no_update BEFORE UPDATE ON linea_temporal
BEGIN SELECT RAISE(ABORT, 'linea_temporal es append-only'); END;
CREATE TRIGGER linea_temporal_no_delete BEFORE DELETE ON linea_temporal
BEGIN SELECT RAISE(ABORT, 'linea_temporal es append-only'); END;

CREATE TRIGGER conocimiento_lector_no_update BEFORE UPDATE ON conocimiento_lector
BEGIN SELECT RAISE(ABORT, 'conocimiento_lector es append-only'); END;
CREATE TRIGGER conocimiento_lector_no_delete BEFORE DELETE ON conocimiento_lector
BEGIN SELECT RAISE(ABORT, 'conocimiento_lector es append-only'); END;

CREATE TRIGGER tension_real_no_update BEFORE UPDATE ON tension_real
BEGIN SELECT RAISE(ABORT, 'tension_real es append-only'); END;
CREATE TRIGGER tension_real_no_delete BEFORE DELETE ON tension_real
BEGIN SELECT RAISE(ABORT, 'tension_real es append-only'); END;

-- Índice derivado (spec 0006): en qué capítulos aparece cada personaje y cada escenario, para la
-- ficha del libro. Lo escribe aplicar-delta y es append-only. Fuera de la vista Estado.
-- IF NOT EXISTS porque asegurar_apariciones ejecuta este bloque, entre sus marcas, sobre bases
-- anteriores.
-- apariciones: inicio
CREATE TABLE IF NOT EXISTS apariciones (
    entidad  TEXT NOT NULL,
    tipo     TEXT NOT NULL CHECK (tipo IN ('personaje', 'escenario')),
    capitulo INTEGER NOT NULL,
    PRIMARY KEY (entidad, capitulo)
) STRICT;
CREATE INDEX IF NOT EXISTS apariciones_por_capitulo ON apariciones (capitulo);
CREATE TRIGGER IF NOT EXISTS apariciones_no_update BEFORE UPDATE ON apariciones
BEGIN SELECT RAISE(ABORT, 'apariciones es append-only'); END;
CREATE TRIGGER IF NOT EXISTS apariciones_no_delete BEFORE DELETE ON apariciones
BEGIN SELECT RAISE(ABORT, 'apariciones es append-only'); END;
-- apariciones: fin

-- usos_de_hecho: índice hecho→capítulo (spec 0007), derivado de los deltas por aplicar-delta.
-- Aditivo sobre bases anteriores: asegurar_usos ejecuta desde la línea anterior hasta el final,
-- sentencia a sentencia y dentro de la transacción de quien llama, así que todo lo de aquí abajo
-- lleva IF NOT EXISTS. La clave empieza por `hecho`: la consulta hecho→capítulos usa su índice.
CREATE TABLE IF NOT EXISTS usos_de_hecho (
    hecho    TEXT NOT NULL,
    capitulo INTEGER NOT NULL,
    via      TEXT NOT NULL CHECK (via IN ('origen', 'conocimiento', 'lector', 'cita')),
    PRIMARY KEY (hecho, capitulo, via)
) STRICT;
CREATE INDEX IF NOT EXISTS usos_por_capitulo ON usos_de_hecho (capitulo);
CREATE TRIGGER IF NOT EXISTS usos_de_hecho_no_update BEFORE UPDATE ON usos_de_hecho
BEGIN SELECT RAISE(ABORT, 'usos_de_hecho es append-only'); END;
CREATE TRIGGER IF NOT EXISTS usos_de_hecho_no_delete BEFORE DELETE ON usos_de_hecho
BEGIN SELECT RAISE(ABORT, 'usos_de_hecho es append-only'); END;

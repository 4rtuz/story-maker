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
    valor    INTEGER NOT NULL CHECK (valor BETWEEN 1 AND 10)
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

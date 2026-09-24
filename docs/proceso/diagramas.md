# Diagramas

Cinco vistas del harness. Las piezas que añaden otras ramas llevan su rama al lado.

## 1. Arquitectura

```mermaid
flowchart LR
  OP["Operador"]
  subgraph CC["Claude Code"]
    ORQ["Orquestador<br/>sesión principal<br/>.claude/commands/"]
    subgraph AG[".claude/agents/"]
    ENT["entrevistador"]
    ARQ["arquitecto"]
    TRA["trazador"]
    ESC["escritor"]
    REV["continuista · editor-estilo<br/>lector-suspense"]
    JUEZ["juez-narrativo<br/>feat/juez"]
    VIS["revisor-visual<br/>feat/visual"]
    CRO["cronista"]
    end
    PRE["PreToolUse<br/>denegar-escritura-estado.py"]
    POST["PostToolUse<br/>validar-capitulo.py"]
  end
  CLI["CLI novela<br/>determinista, sin modelo"]
  subgraph WS["novelas/&lt;slug&gt;/ · un lock por novela"]
    BRIEF["brief/"]
    CANON["canon/ · plan/"]
    CAP["capitulos/ · qa/"]
    DB[("estado/estado.db")]
    RUNS["runs/ · briefings · harness.log"]
    EXP["export/novela.pdf"]
  end
  FORM["formal/lean · formal/tla<br/>feat/lean · feat/tla"]
  LF["Langfuse"]
  API["API FastAPI<br/>solo lectura + /lanzamientos"]
  PANEL["Panel<br/>frontend/"]
  MCP["MCP: Playwright<br/>+ servidor propio<br/>feat/visual · feat/mcp"]

  OP --> ORQ
  ORQ -- "Task" --> AG
  ORQ -- "Bash novela ..." --> CLI
  AG -. "cada escritura" .-> PRE
  AG -. "capitulos/NN.md" .-> POST
  POST --> CLI
  CLI --> RUNS
  RUNS -- "briefing" --> AG
  AG --> CAP
  AG --> CANON
  CLI -- "aplicar-delta, única escritura" --> DB
  CLI --> EXP
  CLI --> FORM
  CLI -- "scores" --> LF
  CC -- "trazas: plugin Stop/SessionEnd" --> LF
  API -. "lee" .-> WS
  PANEL --> API
  API -- "novela producir" --> CLI
  VIS --> MCP
```

## 2. Bucle por capítulo

```mermaid
flowchart TD
  S["novela pendiente · estado --breve<br/>¿intervencion.md vivo?"] -->|vivo| STOP
  S --> B1["novela briefing escritor"] --> E["Task escritor → capitulos/NN.md"]
  E -. "PostToolUse: validar --origen hook" .-> E
  E --> V1{"novela validar"}
  V1 -->|"1 · intentos < 2"| E
  V1 -->|"1 · 3.er intento"| STOP["intervencion.md<br/>parada"]
  V1 -->|0| B3["3 briefings de revisión<br/>antes de lanzar ninguno"]
  B3 --> R["continuista ‖ editor-estilo ‖ lector-suspense<br/>un turno, tres Task"]
  R --> V2{"novela validar<br/>el editor reescribió"}
  V2 -->|"1"| ED["reintento editor-estilo<br/>mismo briefing"] --> V2
  V2 -->|0| G{"veredicto de<br/>continuidad y suspense"}
  G -->|"rechazado · intentos < 2"| E
  G -->|"rechazado · 3.er intento"| STOP
  G -->|aprobado| C["briefing cronista → Task cronista<br/>estado/deltas/NN.json"]
  C --> D{"novela aplicar-delta"}
  D -->|"1 · custodia"| STOP
  D -->|"1 · intentos < 2"| C
  D -->|0| K["novela checkpoint<br/>scores a Langfuse"]
  K --> N["siguiente capítulo<br/>otra sesión"]
```

Cada reintento recibe solo las rutas de `qa/` que lo motivan. La cuenta sale de `harness.log`,
nunca de la conversación.

## 3. Esquema SQLite

Tal como está en `entrega`, en `backend/novela/plataforma/esquema.sql`. No hay claves foráneas
declaradas: las relaciones son por id y las valida `aplicar-delta`. Las tablas marcadas
«append-only» tienen triggers que abortan `UPDATE` y `DELETE`.

```mermaid
erDiagram
  meta {
    TEXT clave PK
    TEXT valor
  }
  cursor {
    INTEGER id PK "siempre 1"
    INTEGER capitulo
    TEXT fase
    TEXT ultimo_paso
    INTEGER intento
  }
  personajes {
    TEXT id PK
    TEXT ubicacion
    TEXT estado_fisico
    TEXT estado_emocional
    TEXT condicion
    TEXT objetivo_activo
    INTEGER ultima_aparicion
  }
  libro_de_hechos {
    TEXT id PK "append-only"
    TEXT texto
    INTEGER capitulo
    TEXT cita
  }
  conocimiento {
    TEXT personaje "append-only"
    TEXT hecho
    INTEGER desde_capitulo
    TEXT cita
  }
  conocimiento_lector {
    TEXT hecho "append-only"
    INTEGER desde_capitulo
    TEXT cita
  }
  linea_temporal {
    TEXT escena PK "append-only"
    INTEGER capitulo
    TEXT inicio
    INTEGER duracion_min
    TEXT cita
  }
  relaciones {
    TEXT de PK
    TEXT a PK
    TEXT tipo
    REAL intensidad
    INTEGER desde
  }
  objetos {
    TEXT id PK
    TEXT poseedor
    TEXT ubicacion
    INTEGER capitulo_intro
    TEXT relevancia
  }
  hilos {
    TEXT id PK
    TEXT estado
    INTEGER abierto_en
    INTEGER cerrado_en
    TEXT descripcion
  }
  pistas {
    TEXT id PK "derivada"
    TEXT estado
    INTEGER plantada_en
    INTEGER pagada_en
  }
  tension_real {
    INTEGER capitulo PK "append-only"
    INTEGER valor
  }
  metricas {
    INTEGER id PK "derivada, una fila"
    INTEGER palabras_totales
    REAL desviacion_vs_plan
  }
  apariciones {
    TEXT entidad PK "append-only, spec 0006"
    TEXT tipo
    INTEGER capitulo PK
  }
  usos_de_hecho {
    TEXT hecho PK "append-only, spec 0007"
    INTEGER capitulo PK
    TEXT via PK
  }

  personajes ||--o{ conocimiento : "sabe"
  libro_de_hechos ||--o{ conocimiento : "hecho"
  libro_de_hechos ||--o{ conocimiento_lector : "hecho"
  libro_de_hechos ||--o{ usos_de_hecho : "usado en"
  personajes ||--o{ relaciones : "de / a"
  personajes ||--o{ objetos : "poseedor"
  personajes ||--o{ apariciones : "entidad"
```

**Tras integrar `feat/lean` y `feat/guardrails`.** La integración añade tablas de cronología,
de listas prohibidas y de auditoría. Se dibujan como previstas: los nombres y columnas exactos
son los de [`docs/formal/lean.md`](../formal/lean.md) y [`docs/guardrails.md`](../guardrails.md).

```mermaid
erDiagram
  cronologia {
    TEXT evento "prevista · feat/lean"
    TEXT momento
    TEXT lugar
    TEXT personajes
    INTEGER capitulo
  }
  listas_prohibidas {
    TEXT termino "prevista · feat/guardrails"
    TEXT origen
  }
  auditoria_prohibidas {
    TEXT capitulo "prevista · feat/guardrails, append-only"
    TEXT termino
    TEXT decision
    TEXT momento
  }
  listas_prohibidas ||--o{ auditoria_prohibidas : "detectado"
```

## 4. Máquina de estados del flujo

```mermaid
stateDiagram-v2
  [*] --> Configuracion: novela brief iniciar
  Configuracion --> Configuracion: brief validar -> 1 (reintento agente ≤ 2, rondas usuario ≤ 5)
  Configuracion --> Planificacion: brief válido, novela nueva --brief
  Planificacion --> Planificacion: canon inválido (reintento arquitecto ≤ 2)
  Planificacion --> Escritura: canon y plan completos
  Escritura --> Validacion: capitulos/NN.md
  Validacion --> Escritura: gate fallido (≤ 2 reintentos)
  Validacion --> Registro: gates aprobados
  Registro --> Registro: delta rechazado (≤ 2 reintentos)
  Registro --> Escritura: checkpoint, quedan capítulos
  Registro --> Auditoria: checkpoint del último capítulo
  Auditoria --> Publicacion: auditar -> 0 y gates formales en verde
  Auditoria --> Intervencion: hallazgos
  Publicacion --> [*]: export/novela.pdf

  Configuracion --> Intervencion: tercer fallo
  Planificacion --> Intervencion: tercer fallo o misterio inválido
  Validacion --> Intervencion: tercer fallo
  Registro --> Intervencion: tercer fallo o custodia
  Intervencion --> Reanudacion: resuelto en intervencion.md
  Reanudacion --> Escritura: checkpoints/latest.json + primer paso no confirmado

  Publicacion --> Regeneracion: novela cambio
  Regeneracion --> Escritura: capítulo afectado, se regenera
  Regeneracion --> Registro: capítulo no afectado, aplicar-delta --reaplicar
```

Es el mismo flujo que modela `formal/tla/` ([`docs/formal/tla.md`](../formal/tla.md)).

## 5. Validadores

Dónde corre cada uno, dónde bloquea y qué score emite a Langfuse. Punto: **hook** (dentro de la
invocación del agente), **rol** (un agente revisor), **gate** (el CLI, antes de avanzar o de
publicar).

| Validador | Qué comprueba | Punto | Bloquea en | Score en Langfuse | Origen |
|---|---|---|---|---|---|
| `vp_schema` | Brief y salidas de cada rol contra su esquema | gate: `validar`, `checkpoint` | `checkpoint` | `vp_schema` | entrega |
| `vp_longitud` | Palabras dentro del rango | hook `PostToolUse` + gate `validar` | `validar` | `vp_longitud` | entrega |
| `vp_pistas` | Pistas de la ficha presentes | hook + gate `validar` | `validar` | `vp_pistas` | entrega |
| `vp_hilos` | Ningún hilo se cierra sin abrirse | hook + gate `validar` | `validar` | `vp_hilos` | entrega |
| `vp_ids` | Ids referenciados existen | hook + gate `validar` | `validar` | `vp_ids` | entrega |
| `vp_nombres` | Nombres como en la story bible | hook + gate `validar` | `validar` | `vp_nombres` | entrega |
| `vp_cobertura` | Cada elemento del brief aparece en algún capítulo | gate: `checkpoint`, `auditar` | `auditar` | `vp_cobertura` (fracción) | entrega |
| Continuidad | Capítulo contra hechos, línea temporal y canon | rol `continuista` | gate de revisión | `continuidad` | entrega |
| Estilo | Capítulo contra `canon/estilo.md` | rol `editor-estilo` | no bloquea, corrige | `estilo` | entrega |
| Tensión y fair play | Curva, fair play, coherencia | rol `lector-suspense` | gate de revisión | `tension`, `fair_play`, `coherencia` | entrega |
| Longitud relativa | `1 − \|palabras/objetivo − 1\|` | gate `checkpoint` | no bloquea | `longitud` | entrega |
| Delta | Esquema, cita literal, custodia, invariantes narrativos | gate `aplicar-delta` | `aplicar-delta` | — | entrega |
| Policy de escritura | Quién escribe dónde; misterio y base intocables | hook `PreToolUse` + `deny` | la herramienta | — | entrega |
| Validación del brief | Esquema, faltantes, contradicciones, procedencia literal | gate `novela brief validar` | `/novela-nueva --brief` | — (sin trazado: datos personales) | entrega |
| Auditoría | Pistas huérfanas, hilos sin cerrar, fair play | gate `novela auditar` | exportar | — | entrega |
| `vp_prohibidas` | Palabras y temas vetados, con audit log | hook + gate antes de publicar | publicar | `vp_prohibidas` | `feat/guardrails` |
| `lean_cronologia` | Ubicuidad, nacimiento y exclusión en Lean 4 | gate antes de cerrar y de publicar | publicar | `lean_cronologia` | `feat/lean` |
| `juez_*` | Continuidad, tono, arco, personajes, ritmo, personalización | rol `juez-narrativo` | no bloquea, informa | `juez_<criterio>` | `feat/juez` |
| `visual_lectura` | Índice, capítulos, ficha y portada en navegador | rol `revisor-visual` + gate `visual` | publicar | `visual_lectura` | `feat/visual` |
| `prosa_*` | Linters de prosa | gate, según `docs/linters-prosa.md` | según la rama | `prosa_<regla>` | `feat/prosa` |
| TLC | Nada se publica sin validar; reanudación sin pérdida; terminación | CI, job `tla` | el merge | — | `feat/tla` |

El catálogo de los `vp_*` está en `backend/novela/dominio/validadores.py`, y un test comprueba
que coincide con `docs/validators.md` §3.10. Los puntos exactos de lo que añaden otras ramas son
los de su documentación.

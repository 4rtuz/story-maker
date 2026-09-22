# Camino crítico de la información

Cómo viaja un dato desde la idea inicial hasta un capítulo aprobado, y cómo
vuelve al navegador. Detalle de cada pieza en `architecture.md`.

**Estado.** Lo dibujado con borde discontinuo no existe todavía: la cola, el
supervisor, `run.sh` y el log en vivo son las specs `0003` y `0004`, ambas en
`borrador`. Hasta que se implementen, el arranque lo hace un humano pegando el
comando `/novela-nueva` en una terminal (`architecture.md` §11.2 y §12.8).

```mermaid
flowchart TD

  U["USUARIO"]

  subgraph ARR["ARRANQUE — una sola vez por novela"]
    FORM["Frontend: formulario<br/>idea · nº capítulos · palabras"]
    POST["POST /cola<br/>valida y encola<br/>ÚNICA ESCRITURA DE LA API"]
    COLA["novelas/_cola/pendientes/<br/>solicitud en disco"]
    RUN["./run.sh<br/>levanta API y supervisor juntos"]
    SUP["SUPERVISOR<br/>shell · novela cola tomar<br/>decide qué novela empieza,<br/>no qué paso viene después"]
    CFG["config.yaml<br/>lo escribe siempre el backend"]
    ARQ["agente arquitecto"]
    CANON["canon/<br/>premisa · mundo · estilo · personajes<br/>+ misterio.md = SECRETO"]
    TRA["agente trazador<br/>sí ve el misterio"]
    PLAN["plan/<br/>escaleta + ficha de cada capítulo"]
  end

  subgraph BUC["BUCLE POR CAPÍTULO — una sesión cada uno"]
    ORQ["ORQUESTADOR<br/>sesión Claude Code<br/>reparte, no lee prosa"]
    BRIEF["novela briefing<br/>runs/RUN/briefings/NN-agente.md<br/>el contexto exacto de cada invocación"]
    ESC["agente escritor<br/>NUNCA ve canon/misterio.md"]
    CAP["capitulos/NN.md"]
    GATE{"novela validar<br/>esquema · longitud · pistas · hilos<br/>CÓDIGO, gratis, sin modelo"}
    REV["continuista · editor-estilo · lector-suspense<br/>3 llamadas a modelo"]
    QA["qa/NN-*.json<br/>los hallazgos viven aquí,<br/>no en la conversación"]
    VER{"¿veredicto?"}
    RET["reintento: al escritor solo el informe QA<br/>máximo 2"]
    STOP["PARADA<br/>runs/RUN/intervencion.md<br/>decisión humana"]
    CRO["agente cronista"]
    DELTA["estado/deltas/NN.json"]
    APL["novela aplicar-delta<br/>ÚNICA VÍA DE ESCRITURA DEL ESTADO"]
    DB[("estado/estado.db<br/>append-only · fuente única de verdad")]
    CK["novela checkpoint<br/>checkpoints/NN.json"]
    NEXT{"novela pendiente<br/>¿quedan capítulos?"}
    LOG["runs/RUN/harness.log<br/>se escribe durante todo el capítulo"]
  end

  subgraph LEC["LECTURA — el circuito del navegador"]
    API["FastAPI · backend/api<br/>no muta ninguna novela"]
    PANEL["Frontend<br/>estado: salta una vez por capítulo<br/>actividad: se mueve todo el rato"]
  end

  U --> FORM
  FORM --> POST --> COLA
  RUN --> SUP
  RUN --> API
  COLA --> SUP
  SUP --> CFG
  CFG --> ARQ --> CANON --> TRA --> PLAN

  PLAN --> ORQ
  ORQ --> BRIEF --> ESC --> CAP --> GATE
  GATE -- "falla" --> RET
  GATE -- "pasa" --> REV --> QA --> VER
  VER -- "hallazgos" --> RET
  RET --> ESC
  RET -- "3er intento" --> STOP
  VER -- "aprobado" --> CRO --> DELTA --> APL --> DB
  DB --> CK --> NEXT
  NEXT -- "sí" --> ORQ
  NEXT -- "no" --> FIN["novela auditar + exportar"]
  ORQ --> LOG

  DB -. "lee" .-> API
  CAP -. "lee" .-> API
  LOG -. "lee por tramos" .-> API
  API -. "JSON" .-> PANEL
  PANEL -. "polling" .-> API

  classDef escribe fill:#2d4a3e,stroke:#5a9,color:#fff
  classDef lee fill:#2a3a52,stroke:#69c,color:#fff
  classDef humano fill:#4a3a2a,stroke:#c94,color:#fff
  classDef gatecls fill:#4a2a2a,stroke:#c66,color:#fff
  classDef propuesto stroke-dasharray: 6 4

  class APL,DB,CAP,DELTA,CANON,PLAN,CFG,COLA,LOG escribe
  class API,PANEL,FORM lee
  class U,STOP humano
  class GATE,VER gatecls
  class POST,COLA,RUN,SUP,LOG propuesto
```

## Cómo leerlo

- Línea sólida: información que se **escribe**. Punteada: información que solo se **mira**.
- Borde discontinuo: propuesto en una spec en `borrador`, todavía no existe.
- Una sola flecha entra en `estado.db`, y viene de `aplicar-delta`.
- La API escribe en un único sitio, `_cola/`, y nunca dentro de `novelas/<slug>/`.
  El prefijo `_` no es un slug válido, así que la separación se sostiene por
  construcción y no por disciplina.
- `run.sh` levanta la API y el supervisor a la vez. No existe el estado «panel en
  pie, nadie ejecutando», y por eso el panel no necesita ofrecer nunca un comando
  para copiar.
- El circuito de lectura cuelga del disco, no del orquestador: el panel puede
  consultarse mientras el bucle escribe.
- Las dos velocidades del panel son distintas a propósito. El **estado** solo
  cambia en `aplicar-delta`, una vez por capítulo. La **actividad** sale de
  `harness.log`, que se escribe continuamente: es lo que distingue un capítulo en
  marcha de un bucle colgado.
- El `escritor` está aislado del misterio; el `trazador` y los revisores no (§6.3).
- El gate barato precede a las tres llamadas de revisión. Invertir ese orden gasta
  cuota en descubrir lo que un `assert` ya sabía.

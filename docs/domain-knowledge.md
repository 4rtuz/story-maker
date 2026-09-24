# Ontología de contexto — harness multiagente de novela de suspense

Seis vistas: la ontología general, el canon, el núcleo de contexto vivo, el grafo de orquestación, el mapa de acceso agente → artefacto y la jerarquía de trazas.

---

## 1. Visión general

```mermaid
mindmap
  root((CONTEXTO DEL HARNESS))
    1 CONFIGURACION
      idea semilla
      brief de regalo
        ocasion
        destinatario
        genero tono extension
        temas vetados
      parametros de obra
        longitud total
        num capitulos
        palabras por capitulo
        subgenero
        punto de vista
        tiempo verbal
        idioma
      parametros de sistema
        modelo por agente
        temperatura por agente
        presupuesto de requests y tokens
        politica de reintentos
        politica de checkpoint
    2 CANON
      premisa
      mundo
      personajes
      misterio
      estilo
    3 PLAN
      escaleta macro
      capitulos planificados
      curva de tension objetivo
    4 ESTADO NARRATIVO
      cursor
      linea temporal
      estado de personajes
      grafo de relaciones
      libro de hechos
      hilos abiertos
      estado de pistas
      conocimiento del lector
    5 MEMORIA
      inmediata
      reciente
      remota
      permanente
      indice recuperable
      recetas de ensamblado
    6 ARTEFACTOS EN DISCO
      config.yaml
      brief/
      canon/
      plan/
      estado/estado.db
      memoria/resumenes/
      capitulos/
      qa/
      checkpoints/
      CLAUDE.md
    7 AGENTES
      orquestador
      entrevistador
      arquitecto
      trazador
      escritor de capitulo
      continuista
      editor de estilo
      lector de suspense
      cronista
    8 PROTOCOLO
      fases
      loop por capitulo
      gates de calidad
      handoffs
      reanudacion
      presupuesto
    9 OBSERVABILIDAD LANGFUSE
      session igual a novela
      trace igual a capitulo
      span igual a agente
      generation igual a llamada LLM
      prompts versionados
      scores
      evaluadores LLM as judge
      datasets de regresion
    10 GUARDARRAILES
      esquema validado
      inmutabilidad del canon
      aislamiento del secreto
      fair play
      limites de longitud
      deteccion de deriva de voz
      auditoria de pistas huerfanas
```

---

## 2. CANON — la biblia de la obra

Versionado. Solo el orquestador autoriza cambios; `misterio.verdad_oculta` únicamente se amplía, nunca se reescribe.

```mermaid
mindmap
  root((CANON))
    premisa
      logline
      pregunta dramatica
      tema
      promesa al lector
    mundo
      escenarios
        id y nombre
        descripcion sensorial
        quien tiene acceso
      epoca y tecnologia
      reglas del mundo
      instituciones y procedimientos
    personajes
      identidad
        id, nombre, alias, rol narrativo
      fisico
      voz
        idiolecto y muletillas
        registro
        ejemplo de dialogo canonico
      psicologia
        deseo
        necesidad
        miedo
        herida
      secreto
        que oculta
        a quien se lo oculta
      arco previsto
      relaciones
      coartada y cronologia privada
    misterio
      verdad oculta
      culpable o amenaza
      motivo medio oportunidad
      pistas
        contenido
        capitulo de plantado
        capitulo de pago
        quien la percibe
        es fair play
      pistas falsas
        a quien apuntan
        cuando se desmontan
      revelaciones
      giros
      reloj de cuenta atras
    estilo
      guia de voz narrativa
      ritmo y proporcion dialogo accion interioridad
      prohibiciones y palabras vetadas
      parrafos canonicos de referencia
      convenciones de formato markdown
```

---

## 3. Núcleo de contexto vivo — PLAN, ESTADO y MEMORIA

La separación entre los tres es la decisión estructural clave: **canon** es lo que es verdad del mundo, **plan** es lo que debería pasar, **estado** es lo que ya pasó.

```mermaid
flowchart LR
    subgraph P["3 PLAN — lo que deberia pasar"]
        direction TB
        P1["escaleta macro<br/>actos y puntos de giro"]
        P2["curva de tension objetivo"]
        P3["capitulo n<br/>objetivo dramatico · pov · escenas"]
        P4["pistas a plantar / a pagar"]
        P5["hilos que abre / que cierra"]
        P6["gancho final · palabras objetivo"]
        P1 --> P3
        P2 --> P3
        P3 --> P4
        P3 --> P5
        P3 --> P6
    end

    subgraph E["4 ESTADO NARRATIVO — lo que ya paso"]
        direction TB
        E1["cursor<br/>capitulo · fase · ultimo paso · intento"]
        E2["linea temporal diegetica"]
        E3["personajes<br/>ubicacion · animo · condicion"]
        E4["conocimiento por personaje<br/>que sabe y desde cuando"]
        E5["relaciones<br/>confianza · sospecha · alianza"]
        E6["objetos y pruebas"]
        E7["libro de hechos inmutable"]
        E8["hilos<br/>abierto o cerrado"]
        E9["pistas<br/>plantada · pagada · pendiente · huerfana"]
        E10["conocimiento lector<br/>ironia dramatica"]
        E11["tension real"]
    end

    subgraph M["5 MEMORIA — que entra en cada prompt"]
        direction TB
        M1["inmediata<br/>capitulo anterior completo"]
        M2["reciente<br/>resumenes de los ultimos N"]
        M3["remota<br/>resumenes jerarquicos y por acto"]
        M4["permanente<br/>canon + libro de hechos"]
        M5["indice recuperable<br/>embeddings de escena"]
        M6["recetas de ensamblado<br/>por agente y presupuesto"]
        M1 --> M6
        M2 --> M6
        M3 --> M6
        M4 --> M6
        M5 --> M6
    end

    P3 -.->|"instrucciones del capitulo"| M6
    E7 -.->|"hechos no negociables"| M4
    E3 -.->|"estado de entrada de la escena"| M6
    M6 ==>|"contexto ensamblado"| OUT["prompt del escritor"]
    OUT ==>|"capitulo escrito"| E
```

---

## 4. Grafo de orquestación

El orquestador es el único proceso con visión del bucle completo; no escribe prosa.

```mermaid
flowchart TD
    S["idea semilla del usuario"] --> ARQ["arquitecto"]
    ARQ ==> CAN[("canon/")]
    CAN --> TRZ["trazador"]
    TRZ ==> PLN[("plan/")]
    PLN --> ENS

    subgraph LOOP["loop por capitulo n"]
        direction TB
        ENS["ensamblar contexto<br/>segun receta de memoria"]
        ENS --> ESC["escritor de capitulo"]
        ESC --> CAP["capitulos/NN.md"]
        CAP --> CON["continuista"]
        CON --> G1{"continuidad<br/>y hechos ok"}
        G1 -->|no| FIX["reescritura dirigida<br/>solo con el informe de QA"]
        FIX --> ESC
        G1 -->|si| EDI["editor de estilo"]
        EDI --> LEC["lector de suspense"]
        LEC --> G2{"tension, fair play<br/>y longitud ok"}
        G2 -->|no| FIX
        G2 -->|si| CRO["cronista"]
        CRO ==> UPD[("aplicar-delta<br/>estado.db + memoria/resumenes")]
        UPD --> CKP["checkpoint"]
    end

    CKP --> G3{"quedan capitulos"}
    G3 -->|si| ENS
    G3 -->|no| AUD["auditoria final<br/>pistas huerfanas · hilos abiertos"]
    AUD --> EXP["export novela completa"]

    ORQ["orquestador"] -.->|"invoca, aplica gates,<br/>controla presupuesto"| LOOP
    LF["Langfuse"] -.->|"span por agente,<br/>score por gate"| LOOP

    FIX -->|"3 intentos fallidos"| HALT["parada con informe<br/>de intervencion humana"]
```

---

## 5. Acceso agente → artefacto

Una fila por agente, con sus entradas a la izquierda y sus salidas a la derecha. Ningún artefacto es un nodo compartido: si aparece en varias filas, es que varios agentes lo tocan.

```mermaid
flowchart TB
    subgraph R0["entrevistador · solo en novelas de regalo"]
        direction LR
        i0["briefing de novela brief preparar<br/>entradas delimitadas"] --> a0(["entrevistador"])
        a0 --> o0["brief/borrador.json"]
        o0 -. "novela brief validar" .-> o00["brief/brief.json<br/>lo escribe el CLI"]
    end

    subgraph R1["arquitecto · solo en setup"]
        direction LR
        i1["config.yaml"] --> a1(["arquitecto"])
        i2["idea semilla"] --> a1
        i3["CLAUDE.md"] --> a1
        a1 --> o1["canon/premisa · mundo · personajes · estilo"]
        a1 --> o2["canon/misterio.md"]
    end

    subgraph R2["trazador · solo en setup"]
        direction LR
        i4["canon/ completo"] --> a2(["trazador"])
        i5["canon/misterio.md"] --> a2
        i6["config: num capitulos · longitud"] --> a2
        a2 --> o3["plan/escaleta.md"]
        a2 --> o4["plan/capitulos/NN.md"]
    end

    subgraph R3["escritor de capitulo"]
        direction LR
        i7["plan/capitulos/NN.md"] --> a3(["escritor"])
        i8["canon: premisa · mundo · estilo<br/>personajes de esta escena"] --> a3
        i9["memoria ensamblada<br/>inmediata + reciente + remota"] --> a3
        i10["estado: personajes · conocimiento<br/>hilos · objetos"] --> a3
        i11["canon/misterio.md"] -. "sin acceso" .-x a3
        a3 --> o5["capitulos/NN.md"]
    end

    subgraph R4["continuista"]
        direction LR
        i12["capitulos/NN.md"] --> a4(["continuista"])
        i13["libro de hechos + linea temporal"] --> a4
        i14["canon/ + canon/misterio.md<br/>acceso completo"] --> a4
        i15["coartadas y cronologia privada"] --> a4
        a4 --> o6["qa/NN-continuidad.json<br/>contradicciones estructuradas"]
    end

    subgraph R5["editor de estilo"]
        direction LR
        i16["capitulos/NN.md"] --> a5(["editor de estilo"])
        i17["canon/estilo + parrafos canonicos"] --> a5
        i18["voz de los personajes presentes"] --> a5
        a5 --> o7["capitulos/NN.md corregido"]
    end

    subgraph R6["lector de suspense"]
        direction LR
        i19["capitulos/NN.md"] --> a6(["lector de suspense"])
        i20["plan: tension objetivo · pistas"] --> a6
        i21["conocimiento del lector"] --> a6
        a6 --> o8["qa/NN-suspense.json<br/>tension · fair play · previsibilidad"]
        a6 --> o9["scores a Langfuse"]
    end

    subgraph R7["cronista"]
        direction LR
        i22["capitulos/NN.md aprobado"] --> a7(["cronista"])
        i23["estado.db actual"] --> a7
        a7 --> o10["estado.db actualizado"]
        a7 --> o11["el delta es su unica salida"]
        a7 --> o12["memoria/ y checkpoints/<br/>los escribe el CLI"]
    end

    R0 -. "novela nueva --brief" .-> R1
    R1 --> R2 --> R3 --> R4 --> R5 --> R6 --> R7
```

La asimetría clave está entre las filas 3 y 4: el escritor no ve `misterio.md` y el continuista sí. Es lo que permite verificar fair play contra la solución real sin que el escritor pueda filtrarla en el subtexto.

---

## 6. Jerarquía de trazas en Langfuse

```mermaid
flowchart TD
    SES["session = una novela<br/>session_id: novela_id + run"]
    SES --> T0["trace: setup<br/>canon + plan"]
    SES --> T1["trace: capitulo 01"]
    SES --> TN["trace: capitulo N"]
    SES --> TC["trace: cierre y auditoria"]

    T1 --> SP1["span: escritor"]
    T1 --> SP2["span: continuista"]
    T1 --> SP3["span: editor"]
    T1 --> SP4["span: lector de suspense"]
    T1 --> SP5["span: cronista"]

    SP1 --> GEN["generation<br/>modelo · tokens · coste · latencia"]

    T1 -.-> SC["scores<br/>coherencia · continuidad · tension<br/>longitud · fair play · estilo"]
    T1 -.-> MD["metadata<br/>capitulo_n · version_canon · version_plan<br/>receta_contexto · intento"]
    SES -.-> EV["evaluador de sesion<br/>LLM as judge comparativo"]
```

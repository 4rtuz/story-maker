---
description: Audita una novela terminada (pistas huérfanas, hilos sin cerrar, fair play), la puntúa con el juez y, si está limpia y pasa el umbral, la exporta a md y epub.
argument-hint: <slug>
---

`$ARGUMENTS` es `<slug>`. Sin slug, responde `uso: /novela-auditar <slug>` y para.

Cada orden `novela` va sola en su llamada a Bash, sin `;`, `&&`, `|` ni `echo $?`: el `allow`
solo autoriza órdenes que empiezan por `novela`. Un código distinto de 0 sale como error con
`Exit code N`; sin error, es 0.

1. `novela auditar <slug>`.
   - Sale con 1 → informa de los hallazgos, la salida del comando tal cual, y **no exportes**.
   - Cualquier otro código distinto de 0 → informa de la salida y para.
2. `novela verificar-lean <slug>`, el gate de la cronología en Lean.
   - Sale con 1 → intervención humana: la incoherencia está en capítulos ya cerrados, que no se
     reescriben (invariante 7). Cita `qa/lean.json`, escribe `runs/<run>/intervencion.md` con esa
     salida y para, **sin exportar**. Si dice que Lean no está instalado, también para: el gate no
     se salta.
   - Cualquier otro código distinto de 0 → informa de la salida y para.
3. Juicio (`docs/evaluacion/juez.md`). `novela estado <slug> --breve`: de su primera línea, `N` en
   «capítulo X de N»; de la segunda, el `run` del último checkpoint.
4. `novela briefing <slug> <N> juez`.
   - Sale con 4 y la salida nombra `brief/brief.json` → no es una novela de regalo y no hay
     juicio: salta al paso 7.
   - Cualquier otro código distinto de 0 → informa de la salida y para.
5. Task `juez` con `slug`, `briefing` (la ruta que imprimió el paso 4) y
   `salidas: qa/juicio.json`. Después, `novela juicio <slug>`.
   - Sale con 4 → `qa/juicio.json` no valida: repite el Task pasándole solo esa salida. Máximo
     dos reintentos; si el tercero tampoco valida, paso 6.
   - Sale con 1 → la novela queda bajo el umbral de la rúbrica: paso 6.
   - Sale con 0 → paso 7.
6. Escribe `runs/<run>/intervencion.md` con la salida de `novela juicio` tal cual y para, **sin
   exportar**. No se reintenta con el escritor ni con el `editor-estilo`: los capítulos están
   sellados (invariante 7) y reescribirlos es abrir una versión con `novela cambio`, lo que
   decide una persona.
7. `novela exportar <slug> --formato md`, `novela exportar <slug> --formato epub` y, si hay
   `brief/brief.json`, `novela exportar <slug> --formato pdf`; informa de las rutas y, si lo hubo,
   del resumen de `novela juicio`.

---
description: Audita una novela terminada (pistas huérfanas, hilos sin cerrar, fair play) y, si está limpia, la exporta a md y epub.
argument-hint: <slug>
---

`$ARGUMENTS` es `<slug>`. Sin slug, responde `uso: /novela-auditar <slug>` y para.

1. `novela auditar <slug>`.
2. Sale con 0 → `novela exportar <slug> --formato md` y `novela exportar <slug> --formato epub`,
   e informa de las dos rutas.
3. Sale con 1 → informa de los hallazgos, la salida del comando tal cual, y **no exportes**.
4. Cualquier otro código → informa de la salida y para.

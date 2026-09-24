---
description: Audita una novela terminada (pistas huérfanas, hilos sin cerrar, fair play) y, si está limpia, la exporta a md y epub.
argument-hint: <slug>
---

`$ARGUMENTS` es `<slug>`. Sin slug, responde `uso: /novela-auditar <slug>` y para.

Cada orden `novela` va sola en su llamada a Bash, sin `;`, `&&`, `|` ni `echo $?`: el `allow`
solo autoriza órdenes que empiezan por `novela`. Un código distinto de 0 sale como error con
`Exit code N`; sin error, es 0.

1. `novela auditar <slug>`.
2. Sale con 0 → `novela verificar-lean <slug>`, el gate de la cronología en Lean.
3. Sale con 0 → `novela exportar <slug> --formato md` y `novela exportar <slug> --formato epub`,
   e informa de las dos rutas.
4. Un 1 de cualquiera de los dos → informa de los hallazgos, la salida del comando tal cual, y
   **no exportes**. Un 1 de `verificar-lean` es una intervención humana: la incoherencia está en
   capítulos ya cerrados, que no se reescriben (invariante 7); dilo, cita `qa/lean.json` y para.
   Si dice que Lean no está instalado, también para: el gate no se salta.
5. Cualquier otro código → informa de la salida y para.

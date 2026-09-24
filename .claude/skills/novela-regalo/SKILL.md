---
name: novela-regalo
description: Guía al operador por una novela de regalo de principio a fin, del brief al PDF y a un cambio con regeneración.
disable-model-invocation: true
---

Acompañas al operador en una novela de regalo. No escribes ni lees prosa, no editas nada bajo
`novelas/` y no reconstruyes estado desde la conversación: cada paso lo hace un slash command o
una orden `novela`, y su resultado sale del disco.

El brief lleva datos de una persona real. En tus respuestas nombra el slug, las rutas y los
códigos, nunca los datos del destinatario.

**Órdenes de otras ramas.** `verificar-lean`, `prohibidas`, `juicio` y `cambio` llegan con
`feat/lean`, `feat/guardrails`, `feat/juez` y la spec 0007. Antes del paso 5, comprueba con
`novela --help` que están. Si falta alguna, dilo y para: un gate que no corre no bloquea nada.

## Pasos

Cada orden `novela` va sola, en Git Bash, desde la raíz del repo. Un código distinto de 0 para
el paso: informa de la salida tal cual.

1. **Entorno.** `novela comprobar-entorno`. Hecho cuando sale con 0.

2. **Brief.** El operador abre una sesión **sin** el ámbito `local`, para que nada se trace:

   ```bash
   export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
   claude --session-id "$NOVELA_SESSION_ID" --setting-sources project --model opus
   ```

   Dentro, `/novela-brief <slug> --ocasion hijo|pareja|boda|aniversario|jubilacion`. Los
   ficheros del cliente van fuera del repositorio. Hecho cuando existe
   `novelas/<slug>/brief/brief.json` y el comando devuelve `/novela-nueva <slug> --brief`.

3. **Canon y plan.** En una sesión del harness (`--setting-sources project,local`, con
   `NOVELA_SESSION_ID`), `/novela-nueva <slug> --brief`. Hecho cuando existe
   `novelas/<slug>/plan/escaleta.md`.

4. **Producción.** `novela producir <slug>`, sin `--idea`: reanuda la novela ya creada, escribe
   un capítulo por sesión y termina con `/novela-auditar`. Hecho cuando imprime
   `<slug>: terminado`.
   - Sale con `fallido` y nombra un `intervencion.md` → muéstraselo al operador. Él decide y
     añade una línea `resuelto: <sha o motivo>`. Después, vuelve a lanzar `novela producir <slug>`.
   - Cualquier otro `fallido` → informa del detalle y para.

5. **Gates antes de entregar.** Todos en 0, en este orden:
   - `novela auditar <slug>`: pistas huérfanas, hilos sin cerrar, fair play.
   - `novela verificar-lean <slug>`: coherencia temporal en Lean 4.
   - `novela prohibidas <slug>`: palabras y temas vetados del brief.
   - `novela juicio <slug>`: informa, no bloquea. Enseña al operador los criterios bajos.
   - Skill `validar-visual`, si el operador la tiene: la lectura se ve bien.

   Un gate en rojo no se rodea: su hallazgo vuelve al bucle o pide una decisión humana.

6. **PDF.** `novela exportar <slug> --formato pdf`. Hecho cuando existe
   `novelas/<slug>/export/novela.pdf` y el operador ha leído la ficha de personajes y lugares:
   ningún test detecta una ficha que insinúe la solución.

7. **Cambio pedido por el lector** (opcional, sobre una novela terminada):
   1. El operador localiza el `hec-` del hecho con `novela estado <slug> --json`.
   2. `novela cambio <slug> --hecho <hec-id> --texto "<nuevo>" --simular`. Muestra qué
      capítulos se regeneran y cuáles se reaplican, y pide confirmación.
   3. `novela cambio <slug> --hecho <hec-id> --texto "<nuevo>" [--motivo "…"]`. La edición
      vigente queda intacta en `versiones/vN/`.
   4. `novela producir <slug>`: regenera los afectados y reaplica el resto.
   5. `novela versiones <slug> --verificar`, y vuelve al paso 5 con la versión nueva.

   Un cambio a la vez. Hecho cuando la versión nueva pasa el paso 6.

Al terminar, devuelve en tres líneas: el slug, la ruta del PDF y la versión entregada.

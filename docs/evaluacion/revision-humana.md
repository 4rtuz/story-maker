# Revisión humana de una novela

Plantilla vacía. La rellena una persona que ha leído la novela entera, con la misma rúbrica que el
`juez` (`backend/config/rubrica.yaml`, versión `rubrica-1`), para medir cuánto se parece su
criterio al del modelo. No la rellena ningún agente.

- **Novela** (slug):
- **Rúbrica**: `rubrica-1`
- **Fecha**:
- **¿Has leído el juicio del juez antes?** Sí / No. Si es que sí, la comparación vale menos.

## Escala

Cada criterio de 1 a 5. La rúbrica describe el 1, el 3 y el 5; el 2 y el 4 son los intermedios.
Cada nota lleva una justificación de dos a cuatro frases y al menos una cita literal del texto,
con su capítulo. Sin cita, la nota no cuenta.

## Criterios

### continuidad

¿Los hechos, objetos, tiempos y personajes se mantienen coherentes entre capítulos?
1 contradicciones que cambian la trama · 3 algún desliz menor · 5 ninguna contradicción.

- Puntuación (1–5):
- Justificación:
- Cita (capítulo · texto):

### tono

¿El tono de la novela es el que pide el brief (campo `tono`) y se sostiene?
1 contradice el del brief · 3 coincide con tramos que se desvían · 5 es el del brief de principio
a fin.

- Puntuación (1–5):
- Justificación:
- Cita (capítulo · texto):

### arco

¿La historia tiene planteamiento, escalada y resolución que cierra lo planteado?
1 sin arco o sin resolución · 3 tramos planos o final apresurado · 5 cada acto avanza y el final
resuelve.

- Puntuación (1–5):
- Justificación:
- Cita (capítulo · texto):

### personajes

¿Los personajes actúan de acuerdo con su voz y psicología, o cambian con motivo?
1 incoherentes · 3 coherentes con algún comportamiento sin justificar · 5 voces distinguibles y
decisiones que nacen de quiénes son.

- Puntuación (1–5):
- Justificación:
- Cita (capítulo · texto):

### ritmo

¿El ritmo entre capítulos alterna tensión y respiro y mantiene el interés?
1 tensión plana · 3 algún tramo que se estanca o se precipita · 5 cada capítulo empuja al
siguiente.

- Puntuación (1–5):
- Justificación:
- Cita (capítulo · texto):

### personalizacion

¿Los recuerdos y rasgos del brief están integrados de forma natural, no forzada?
1 ausentes o a calzador · 3 reconocibles, alguno suena a inserción · 5 tejidos en la trama.

- Puntuación (1–5):
- Justificación:
- Cita (capítulo · texto):

## Formato máquina

Para comparar con el juez, pasa las notas a una copia de `docs/evaluacion/revision-humana.json`
(mismo esquema que el juez, `backend/schemas/juicio.schema.json`, con `evaluador: "humano"`),
fuera del repositorio si lleva citas de una novela de regalo, y ejecuta:

```bash
novela comparar-juicios <slug> --humano <ruta-a-tu-copia.json>
```

La plantilla JSON trae las puntuaciones a `null` a propósito: sin rellenar no valida.

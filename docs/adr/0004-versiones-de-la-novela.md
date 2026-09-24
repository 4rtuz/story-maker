---
adr: 0004
titulo: "Una versión de la novela es una línea de tiempo nueva, y la anterior queda intacta"
estado: aceptada
fecha: 2026-09-24
decide: "arturo.soto"
specs: [0007]
---

# 0004 — Una versión de la novela es una línea de tiempo nueva, y la anterior queda intacta

## Contexto

Un lector que ha terminado la novela pide cambiar un hecho: «la puerta de la linterna estaba
intacta en la noche 2». Cambiarlo obliga a reescribir el capítulo que lo introduce y los que se
apoyan en él. Dos reglas lo impedían tal como estaban escritas.

El invariante 2 hace append-only `libro_de_hechos` y `conocimiento`, con triggers que abortan
cualquier `UPDATE` o `DELETE`. Y el invariante 7 prohibía reescribir capítulos anteriores. Las
dos existen por la misma razón: un estado que cambia por detrás invalida toda verificación
posterior, y un capítulo reescrito en sitio deja desfasados el estado y los resúmenes de todo lo
intermedio (`architecture.md` §12, punto 5).

`estado.db` ya es reproducible: aplicar en orden `estado/deltas/*.json` sobre una base vacía da
el mismo estado (`validators.md` §4.14). Eso abarata reconstruirlo.

## Decisión

**Una versión es una línea de tiempo nueva, con una base propia reconstruida por reproducción.**
`novela cambio` guarda la edición vigente, entera e inmutable, en `versiones/vN/`, y deja la raíz
con una `estado.db` vacía. El bucle existente la rellena: los capítulos que usan el hecho cambiado
se regeneran con los agentes, y los demás se reaplican byte a byte desde la instantánea con
`aplicar-delta --reaplicar`.

Los invariantes 2 y 7 valen dentro de cada versión. Ninguna fila de ninguna base se modifica ni se
borra, y ningún capítulo de una versión se reescribe: el que cambia es de la versión siguiente. El
invariante 7 pasa a decir «No se reescriben capítulos de una versión», con la parada por problema
retroactivo intacta.

## Alternativas descartadas

**Columna `version` en todas las tablas.** Una sola base con claves primarias nuevas obliga a
`schema_version` 2.0.0, a migrar todos los workspaces y a filtrar por versión cada consulta del
CLI y de la API.

**Capa de sustituciones sobre una sola base.** Tablas paralelas para los capítulos regenerados que
«tapan» a las originales. Duplica la ontología, contra la regla de una sola de `AGENTS.md`, y cada
lector del estado tendría que saber combinar las dos.

**Reescritura en sitio con una excepción al invariante 7.** Es lo más barato de escribir y lo más
caro de sostener: hay que abrir una excepción también en el invariante 2 para borrar los hechos
viejos, y la versión anterior se pierde, así que nada permite comparar ni volver atrás.

## Consecuencias

**Lo que ganamos.** Nada de lo ya escrito cambia de valor: `versiones/vN/` es la edición anterior
completa, verificable con los sha256 de `version.json`. Los gates, el delta y el cursor funcionan
igual en la versión nueva, porque para ellos es una novela que se escribe desde el capítulo 1. Y la
regeneración cuesta cuota solo en los capítulos afectados.

**Lo que aceptamos.**

- **El disco crece con cada versión**: una copia de `capitulos/`, `estado/`, `memoria/`, `qa/` y
  `checkpoints/` por cambio.
- **Un capítulo que menciona el hecho sin declararlo en el delta se reaplica tal cual.** Si
  contradice el hecho nuevo, nada mecánico lo detecta; lo mitiga la cita literal de
  `hechos_usados`.
- **Un cambio a la vez**, y solo sobre una novela terminada.

## Cuándo reabrirla

Si hicieran falta cambios en cascada, varios cambios simultáneos o volver a una versión anterior,
la línea de tiempo lineal no basta: habría que decidir cómo se ramifican y se fusionan las
versiones, y eso es otro diseño.

---
spec: 0005
titulo: "Contención de agentes: secreto por briefing, guardias reales y plugins fuera"
estado: borrador
autor: "arturo.soto"
fecha: 2026-09-22
version: 0.1
afecta: [agentes, backend, docs]
depende_de: []
sustituye: []
adr: []
commit: null
---

# 0005 — Contención de agentes: secreto por briefing, guardias reales y plugins fuera

## 1. Propósito y alcance

Que las tres barreras que `architecture.md` y `validators.md` dan por puestas —aislamiento del secreto, escritura acotada y sandbox por `tools`— existan de verdad, y que las herramientas de desarrollo del repositorio no lleguen a ningún agente.

**Dentro del alcance**

- `canon/misterio.md` deja de ser una ruta que ningún agente lee. `novela briefing` **incrusta** su contenido en el briefing de los tres agentes autorizados.
- Regla `deny` sobre esa ruta en `.claude/settings.json`, aplicable a los siete agentes por igual gracias a lo anterior.
- Los dos hooks que `CLAUDE.md` da por existentes: `PreToolUse` de escritura y `Stop` de trazado.
- Los siete ficheros `.claude/agents/*.md` con el `tools` de `architecture.md` §7.4.
- Los plugins de desarrollo salen de `.claude/settings.json` y pasan a `.claude/settings.local.json`.
- Un test de contrato que impide que un agente gane una herramienta prohibida.

**Fuera del alcance**

- Aislamiento por contenedor. La contención sigue siendo por construcción, como reconoce `validators.md` §4.3.
- Permisos distintos por agente. Todo lo que se propone aquí es una regla igual para los siete; si hiciera falta diferenciar, sería otra spec.
- El contenido de los prompts de los agentes. Aquí solo se fija su frontmatter.
- Medir el coste en tokens del listado de herramientas. Ver §16.

## 2. Problema

Tres afirmaciones de la documentación de referencia no se sostienen.

**La primera es la grave.** `architecture.md` §6.3 sostenía el invariante 3 sobre dos capas, y la segunda decía que el frontmatter de `escritor.md` «restringe `tools` para que no pueda leer rutas arbitrarias». `tools` no hace eso: enumera herramientas, no rutas, y `Read` no lleva lista blanca. Un agente con `Read` y la ruta `canon/misterio.md` la lee. `validators.md` §4.3 ya lo decía bien —«la contención real son los permisos de `.claude/settings.json` y el frontmatter, no un aislamiento»— y los dos documentos se contradecían. La corrección de redacción ya está aplicada; lo que falta es la capa que se creía tener.

La regla `deny` obvia choca con que tres agentes —`trazador`, `continuista`, `lector-suspense`— sí necesitan el misterio. Una regla de permisos en `settings.json` vale para toda la sesión, no por agente, así que denegar la ruta los rompería.

**La segunda.** `CLAUDE.md` describe un hook `PreToolUse` que deniega escrituras bajo `estado/` y un hook `Stop` que envía trazas a Langfuse, y da instrucciones sobre qué hacer cuando saltan. `.claude/settings.json` no tiene sección `hooks`. Ninguno de los dos existe. El invariante 1 queda sostenido solo por los triggers append-only de SQLite, que impiden reescribir historia pero no impiden escribir en `estado/` por otra vía.

**La tercera.** `.claude/settings.json` declara seis plugins de marketplace. Son herramientas para desarrollar este repositorio y no tienen relación con generar novelas. Nada impide hoy que un agente los alcance, y además viajan en el fichero versionado, de modo que el repositorio declara como propias seis dependencias que el producto no usa.

Evidencia: `find .claude -type f` devuelve un único fichero, `settings.json`, cuyo contenido son `enabledPlugins` y `extraKnownMarketplaces`. No hay agentes, ni hooks, ni permisos.

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Agente `escritor` | Es a quien protege el invariante 3. Gana una barrera real y no cambia nada de lo que ve |
| Agente `editor-estilo` | Igual que el anterior, y es el único con `Edit` |
| Agentes `trazador`, `continuista`, `lector-suspense` | Reciben el misterio incrustado en vez de por ruta. Mismo contenido, distinto transporte |
| Orquestador | Ninguno. El bucle no cambia |
| Operador humano | Deja de tener en el repositorio versionado plugins que solo usa él |

## 4. Contexto y restricciones

- **Invariantes que aplican**: el **3** (el secreto) es el que motiva la spec; el **1** (estado solo por `aplicar-delta`) es el que protege el hook; el **7** de `architecture.md` (contexto mínimo suficiente) es el que justifica negar `Glob` y `Grep`.
- **Restricciones técnicas**: los permisos de `.claude/settings.json` valen para la sesión entera, no por subagente. Es la restricción que dicta el diseño de §5.1. Las claves viven en `settings.local.json`, que está en `.gitignore`.
- **Supuestos**: (a) un subagente cuyo `tools` no incluye `Skill` no puede invocar ninguna skill; (b) el hook `PreToolUse` se dispara también para las llamadas de herramienta de un subagente. Si (b) fuese falso, §5.3 no sirve y habría que sostener el invariante 1 solo con los triggers de SQLite.
- **Dependencias**: ninguna.

## 5. Propuesta

### 5.1 El misterio se incrusta, no se enruta

`novela briefing`, al componer el briefing de `trazador`, `continuista` o `lector-suspense`, vuelca el contenido de `canon/misterio.md` dentro del propio briefing. Para el resto de agentes no lo vuelca, como hasta ahora.

El efecto es que **ningún agente necesita abrir ese fichero**, y entonces la regla de permisos deja de tener excepciones:

```json
{
  "permissions": {
    "deny": ["Read(./novelas/*/canon/misterio.md)"]
  }
}
```

Una sola línea, igual para los siete, sin necesidad de permisos por agente. Es la medida que hace viable lo que §6.3 daba por hecho.

El coste en contexto es nulo: los tres agentes que lo reciben ya lo tenían en su ventana, solo que llegaba por una llamada a `Read` en vez de venir en el texto. Sí cambia dónde se contabiliza, y es una mejora: pasa a contar dentro del presupuesto que `novela briefing` verifica antes de invocar (§6.5), en lugar de aparecer después y por sorpresa.

### 5.2 Los siete ficheros de agente

Se crean `.claude/agents/{arquitecto,trazador,escritor,continuista,editor-estilo,lector-suspense,cronista}.md` con el `model` de `architecture.md` §2.2 y el `tools` de §7.4. Seis con `Read, Write`; `editor-estilo` con `Read, Edit, Write`.

Ninguno lleva `Glob`, `Grep`, `Bash`, `Task`, `Skill`, `WebFetch` ni `WebSearch`. La ausencia de `Skill` es lo que resuelve el problema de los plugins: una skill se invoca con esa herramienta, así que sin ella ningún plugin del repositorio alcanza a ningún agente, esté habilitado donde esté.

### 5.3 Los dos hooks

```
.claude/hooks/guardias.py     PreToolUse
.claude/hooks/trazas.py       Stop
```

`guardias.py` deniega, sin necesidad de saber qué agente llama:

- `Write` o `Edit` bajo `estado/` que no sea `estado/deltas/`,
- cualquier escritura fuera de `novelas/<slug>/`,
- `Read` sobre `canon/misterio.md`, como refuerzo de la regla de permisos por si un día alguien la quita de `settings.json`.

Python de la biblioteca estándar, sin dependencias y sin `uv run`: un hook que tarda en arrancar se acaba desactivando.

`trazas.py` es el envío a Langfuse que `architecture.md` §10 ya describe. Las claves las lee de `settings.local.json`, nunca del fichero versionado.

### 5.4 Los plugins, fuera del fichero versionado

`.claude/settings.json` queda con lo que el producto necesita: `hooks` y `permissions`. Los seis `enabledPlugins` y el `extraKnownMarketplaces` se mueven a `.claude/settings.local.json`.

Esto no es lo que impide que un agente los use —eso lo hace la ausencia de `Skill`— sino separación de código y datos: quien clone el repositorio para escribir una novela no debe arrastrar herramientas de desarrollo del harness.

### 5.5 Un test que lo mantenga

`backend/tests/test_contratos.py` recorre `.claude/agents/*.md` y comprueba el frontmatter contra la tabla de §7.4: el `model` esperado, el `tools` esperado y, sobre todo, que la intersección con la lista prohibida sea vacía.

Sin esto, dentro de tres meses alguien añade `Skill` a un agente «para una cosa rápida» y nadie se entera. La spec 0002 ya preveía un `test_tools_por_agente`; este lo absorbe y lo amplía.

## 6. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | `novela briefing` incrusta el contenido de `canon/misterio.md` en el briefing de `trazador`, `continuista` y `lector-suspense` | debe |
| RF-02 | `novela briefing` no incrusta ni nombra `canon/misterio.md` en el briefing de `arquitecto`, `escritor`, `editor-estilo` ni `cronista` | debe |
| RF-03 | Ningún briefing lista `canon/misterio.md` como ruta a leer | debe |
| RF-04 | `.claude/settings.json` deniega `Read` sobre `canon/misterio.md` para toda la sesión | debe |
| RF-05 | Existen los siete `.claude/agents/*.md` con el `model` y el `tools` de `architecture.md` §2.2 y §7.4 | debe |
| RF-06 | Ningún agente declara `Glob`, `Grep`, `Bash`, `Task`, `Skill`, `WebFetch` ni `WebSearch` | debe |
| RF-07 | El hook `PreToolUse` deniega escrituras bajo `estado/` salvo en `estado/deltas/`, y cualquier escritura fuera de `novelas/<slug>/` | debe |
| RF-08 | El hook `Stop` envía la traza a Langfuse leyendo las claves de `settings.local.json` | debe |
| RF-09 | `.claude/settings.json` no contiene `enabledPlugins` ni `extraKnownMarketplaces` | debe |
| RF-10 | Un test de contrato falla si el frontmatter de cualquier agente se desvía de §7.4 | debe |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-02 | Consumo de contexto | Incrustar el misterio no aumenta el contexto de los tres agentes que ya lo recibían, y pasa a contar dentro del presupuesto que `novela briefing` verifica |
| RNF-03 | Coste / cuota | Cero llamadas a modelo. El test de contrato corre en CI sin cuota |
| RNF-04 | Fiabilidad | `guardias.py` sin dependencias externas: un hook que falla al importar es un hook que alguien desactiva |
| RNF-05 | Observabilidad | Cada denegación de `guardias.py` se registra con la herramienta, la ruta y el motivo. Un guardrail silencioso es peor que ausente |
| RNF-07 | Seguridad | Las claves de Langfuse no aparecen en ningún fichero versionado. `guardias.py` no las lee ni las imprime |

## 8. Interfaces y contratos

**Contrato de agente** — **nuevo** (los ficheros no existían). Frontmatter de los siete según §7.4. La restricción sobre `Skill` es parte del contrato, no una recomendación.

**Ficheros del repositorio** — `.claude/settings.json` pasa de declarar plugins a declarar `hooks` y `permissions`: **ruptura** para quien dependiera de los plugins en ese fichero, resuelta moviéndolos a `settings.local.json`.

**CLI** — `novela briefing` cambia de comportamiento para tres agentes: **compatible**, la firma y las salidas no cambian. Lo que cambia es el contenido del briefing generado.

**API**: sin cambios.
**Esquemas**: sin cambios.

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | Sin cambios de contenido. Cambia quién puede abrir `misterio.md`: nadie |
| `plan/` | Sin cambios |
| `estado/estado.db` | Sin cambios. Gana una barrera preventiva delante |
| `memoria/` | Sin cambios |

## 10. Migración y compatibilidad

Los briefings ya generados en `runs/` no se tocan: son registro histórico de lo que vio cada agente y reescribirlos sería falsificarlo.

Para el operador, la migración es mover un bloque JSON de `settings.json` a `settings.local.json`. Si no lo hace, pierde los plugins en su sesión de desarrollo; no afecta a ninguna novela.

## 11. Criterios de aceptación

- [ ] **CA-01** (RF-01) El briefing de `continuista` contiene el texto de `canon/misterio.md`.
- [ ] **CA-02** (RF-02) El briefing de `escritor` no contiene ninguna línea de `canon/misterio.md`, comparando contra el fichero completo.
- [ ] **CA-03** (RF-03) Ningún briefing de ningún agente incluye la cadena `canon/misterio.md` en su lista de rutas.
- [ ] **CA-04** (RF-01, RNF-02) El briefing del `continuista` con el misterio incrustado sigue dentro del `presupuesto_tokens` de su receta, y `novela briefing` lo verifica antes de devolver.
- [ ] **CA-05** (RF-04) `settings.json` contiene la regla `deny` sobre esa ruta.
- [ ] **CA-06** (RF-05, RF-06, RF-10) El test de contrato recorre los siete ficheros y valida `model` y `tools`; falla si a cualquiera se le añade una herramienta de la lista prohibida.
- [ ] **CA-07** (RF-07) Una llamada `Write` a `estado/estado.db` se deniega. Una a `estado/deltas/07.json` se permite.
- [ ] **CA-08** (RF-07) Una llamada `Write` a una ruta fuera de `novelas/<slug>/` se deniega.
- [ ] **CA-09** (RNF-05) Cada denegación deja una línea con herramienta, ruta y motivo.
- [ ] **CA-10** (RF-09) `settings.json` no contiene `enabledPlugins` ni `extraKnownMarketplaces`.
- [ ] **CA-11** (RF-08) El hook `Stop` no lee ni emite ninguna clave presente en un fichero versionado.

## 12. Trazabilidad

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 | CA-01, CA-04 | `backend/tests/test_briefing.py::test_misterio_incrustado_para_autorizados` | pendiente |
| RF-02 | CA-02 | `backend/tests/test_briefing.py::test_misterio_ausente_para_escritor` | pendiente |
| RF-03 | CA-03 | `backend/tests/test_briefing.py::test_misterio_nunca_es_ruta` | pendiente |
| RF-04 | CA-05 | `backend/tests/test_contratos.py::test_deny_misterio` | pendiente |
| RF-05, RF-06, RF-10 | CA-06 | `backend/tests/test_contratos.py::test_frontmatter_por_agente` | pendiente |
| RF-07 | CA-07, CA-08 | `backend/tests/test_guardias.py::test_denegaciones_de_escritura` | pendiente |
| RF-08 | CA-11 | `backend/tests/test_guardias.py::test_stop_no_filtra_claves` | pendiente |
| RF-09 | CA-10 | `backend/tests/test_contratos.py::test_settings_sin_plugins` | pendiente |
| RNF-05 | CA-09 | `backend/tests/test_guardias.py::test_denegacion_se_registra` | pendiente |

## 13. Verificación

- CA-02 es el criterio del invariante 3 y merece ser **property-based**: para cualquier `misterio.md` generado, ninguna frase suya aparece en el briefing del `escritor`. Un ejemplo con tres líneas fijas no cubre la fuga por fragmento.
- CA-06 se prueba contra la tabla de §7.4 leída como dato, no duplicada en el test. Si alguien cambia la tabla sin cambiar los agentes, el test debe fallar.
- **Riesgos aceptados**:
  1. Un agente con `Write` sigue pudiendo escribir donde alcance la sesión si el hook se desactiva. `validators.md` §4.3 ya lo asume; esta spec estrecha el margen, no lo elimina.
  2. La regla `deny` protege la ruta conocida. Un enlace simbólico dentro del workspace que apunte a `misterio.md` la esquivaría. No se cubre: el workspace lo genera el propio harness y nadie crea enlaces ahí.
  3. El supuesto (a) de §4 —que sin `Skill` no hay skills— no está verificado. Si resultara falso, hace falta además una regla `deny` sobre la herramienta.

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | Ninguno cambia. El 3 y el 1 pasan de enunciados a mecanismos |
| Esquemas | Ninguno |
| Contratos de agente | Los siete, por primera vez: es esta spec la que los crea |
| Docs de referencia | `architecture.md` §6.3 y §7.4 y `validators.md` §4.4 ya están corregidos y describen el destino de esta spec. En el commit de implementación se les quita la referencia a la spec. `CLAUDE.md` gana una línea en «Permisos» y pierde la suposición de que los hooks existen |
| Frontend | Ninguno |

## 15. Alternativas descartadas

- **Permisos por agente en lugar de incrustar el misterio.** Sería lo directo si los permisos fueran por subagente. Son de sesión, así que denegar la ruta rompería a los tres agentes que la necesitan. Incrustar el contenido es lo que convierte una regla imposible en una regla trivial.
- **Sacar `misterio.md` del workspace y dejarlo donde solo lo lea el CLI.** Funciona, pero rompe la rama 2 de la ontología: el canon es una cosa y vive en un sitio. Partirlo por conveniencia de permisos es peor que incrustarlo al ensamblar.
- **Confiar solo en el prompt.** Es lo que hay hoy, más el aborto de `novela briefing`. El propio §6.3 dice por qué no basta: un modelo que conoce la solución la filtra en el subtexto, y es un fallo invisible en revisión capítulo a capítulo.
- **Desactivar los plugins en `settings.json` en vez de moverlos.** Deja el ruido en el fichero versionado y a un `true` de distancia de volver.
- **Contenedor por subagente.** La contención de verdad, y desproporcionada mientras el harness corra en una máquina de desarrollo. `validators.md` §5.6 ya la marca como requisito si algún día corre en CI.

## 16. Preguntas abiertas

- [ ] ¿El listado de herramientas y skills entra en el contexto de un subagente aunque su `tools` no las incluya? De la respuesta depende si mover los plugins es higiene o es necesario para la aritmética de §6.5, que presupuesta 10.000 tokens de fijo. Es una medición de minutos y no bloquea el resto de la spec — arturo.soto
- [ ] ¿Se dispara `PreToolUse` para las llamadas de herramienta de un subagente, o solo para las de la sesión principal? Si es lo segundo, §5.3 no protege nada y el invariante 1 queda solo con los triggers de SQLite — arturo.soto

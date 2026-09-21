# Pre-registro: calibración del Evaluador

Escrito antes de medir ningún candidato. **No se edita después de ver resultados.** Un
cambio de opinión posterior va en `bitacora.md`, nunca aquí. Si una regla de este documento
resulta equivocada, se anota el error, se cierra el experimento y se abre otro pre-registro.

Precede a este experimento: `docs/ruido-evaluador.md` (medición del suelo de ruido, 42
llamadas, 2026-09-18) y su pre-registro `docs/pre-registro-automejora.md`. Aquél midió; éste
**optimiza**.

## 1. Pregunta

El Evaluador es el instrumento del que cuelga todo el bucle caro del harness: §9.2 decide
la aceptación con sus puntuaciones, §9.4 corta las reescrituras comparando medias
consecutivas contra `evaluacion.mejora_minima: 0.01`.

La medición del 2026-09-18 encontró σ(media) = 0,39 (dev) y 0,42 (holdout) al relanzar la
**misma llamada sobre el mismo texto**: los 14 borradores dieron una media distinta las tres
veces, y el gate bloqueante cambió de veredicto en 8 de 14. Una ganancia de 0,01 no es
distinguible de repetir la tirada.

**¿Se puede bajar ese ruido tocando solo el system prompt del Evaluador, sin que pierda
capacidad de distinguir un capítulo bueno de uno malo?**

## 2. Qué puede tocar el bucle, y qué no

Autorizado (decisión del autor, 2026-09-20):

1. **El system prompt del Evaluador** — el cuerpo de `.claude/agents/evaluador.md`: anclas
   numéricas por criterio, obligación de citar evidencia textual antes de puntuar, orden de
   evaluación fijo, reglas de desempate, formato de razonamiento.
2. **Salida estructurada** — activar `--json-schema` en la llamada (campo `esquema: true` en
   el frontmatter del candidato). El esquema es fijo, lo define `ESQUEMA_SALIDA` en
   `scripts/calibrar_evaluador.py`, y reproduce exactamente lo que acepta
   `harness.deltas.validate_evaluation`.

Prohibido en este experimento:

- Cambiar la clase de modelo del Evaluador (hoy `haiku`). Sube el coste en producción.
- Agregación por mediana de k pasadas. Multiplica por k el coste del rol y toca el núcleo.
- Tocar `novela/config.json`, la rúbrica de seis criterios, los umbrales, el fixture, la
  baseline, este documento, o cualquier archivo de `harness/`.
- Tocar `.claude/agents/evaluador.md` salvo por `--promover`, que exige META confirmada.

Si el bucle se estanca, las dos palancas prohibidas son lo que hay que reportar como
siguiente paso; **no se aplican por cuenta propia**.

## 3. El fixture

`fixtures/evaluador/`, reconstruido desde Langfuse por `scripts/recuperar_fixture.py`
(los runs originales no se commitearon: `.gitignore` excluye `runs/*`, y ya no existen en
disco). Son los **prompts ensamblados completos** tal como los construyó el núcleo en los
dos runs históricos, no borradores sueltos: lo único que varía entre candidatos es el
system prompt.

- **DEV (7 pares)** — run `el-buzon-de-la-planta-baja-2`, trazas `edce12e7`, `f2b1b61f`,
  `0d834e01`. Capítulos 1,1,1,2,3,3,3.
- **HOLDOUT (7 pares)** — run `los-ruidos-del-bosque`, trazas `db554de5`, `82a67aa3`,
  `9111b04e`. Capítulos 1,1,2,2,2,3,3.

Coincide borrador a borrador con la partición de `docs/pre-registro-automejora.md`, y el
system prompt de partida tiene el mismo sha256 (`73b37263…`) que el que midió aquel informe.

Cada par tiene tres variantes, verificadas por sha256 en cada tanda:

| variante | qué es | para qué |
|---|---|---|
| `orig` | el prompt histórico, intacto | mide el **ruido** |
| `singancho` | sin la última frase del capítulo | **sensibilidad**: la rúbrica pregunta «¿cierra en gancho?» dentro de `tension`, que es bloqueante |
| `barajado` | frases barajadas dentro de cada escena, semilla fija | **suelo**: un juez que no puntúa esto por debajo del original está roto |

Las dos degradaciones son deterministas y no requieren etiquetas humanas: la dirección
correcta se conoce por construcción. `barajado` es deliberadamente fácil (además del orden,
pierde la separación en párrafos); su valor es detectar colapso, no medir finura.

## 4. Métricas

Todas las calcula `scripts/calibrar_evaluador.py`. La media es siempre
`harness.deltas.computed_mean`, recalculada desde `puntuaciones`: **nunca** la `media` que
declara el modelo.

**Señal (lo que se optimiza)**

- `sigma_media_promedio` — media, sobre los 7 pares, de la σ muestral de `media_calculada`
  entre las pasadas del `orig`.
- `gates_estables` — de cuántos de los 7 pares las 3 pasadas coinciden en el booleano
  `tension ≥ 3 ∧ escaleta ≥ 3` (los umbrales del perfil `poc`, que es el que ensambló estos
  prompts).

**Guardarraíles (lo que no puede empeorar)**

- `discriminacion.singancho.auc` y `discriminacion.barajado.auc` — estadístico de
  Mann-Whitney: P(media(orig) > media(degradado)) + ½·P(empate), sobre todas las parejas de
  pasadas. Azar = 0,5.
- `sigma_entre_borradores` — σ de las medianas de los 7 originales. Es el detector de
  colapso: puntuar 3 a todo da σ intra = 0 y σ entre = 0.
- `sigma_criterio_promedio[c]` para los seis criterios.
- `valores_distintos_por_criterio[c]` — cuántos valores enteros distintos llegó a usar.
- `n_invalidas` — respuestas que no pasan `validate_evaluation`.

## 5. Regla de veredicto

La dicta `veredicto()` en el script, no el modelo. Un candidato con cualquier llamada
fallida es `INVALIDO` y no compara con nada.

Se descarta (`DESCARTADO`) si rompe **cualquier** guardarraíl:

| guardarraíl | umbral |
|---|---|
| AUC de cualquier degradación | `< baseline − 0,05` |
| σ entre borradores | `< 0,80 × baseline` |
| σ de cualquier criterio suelto | `> baseline + 0,10` |
| valores distintos de cualquier criterio | `< 2` |
| respuestas inválidas | `> baseline` |

Con los guardarraíles intactos:

- **`META_ALCANZADA`**: `sigma_media_promedio ≤ 0,17` **y** `gates_estables ≥ 6` de 7.
- **`MEJOR`**: baja al menos 0,05 respecto a la baseline.
- **`SIN_MEJORA`**: no baja lo suficiente.

0,17 no es arbitrario: un criterio de seis vale 1/6 = 0,167, que es el mismo razonamiento
con el que `config.json` justifica `mejora_minima`. 0,05 de margen evita llamar «mejora» a
un movimiento dentro de la imprecisión de una σ con n=3.

## 6. Condiciones de parada

El bucle para —y lo dice— en cuanto se cumpla una:

1. **Éxito.** `META_ALCANZADA` en dev → se mide holdout **una sola vez**. Si también da
   `META_ALCANZADA`, se promueve con `--promover` y se para.
2. **Estancamiento.** Dos candidatos consecutivos con `SIN_MEJORA` o `DESCARTADO` → para y
   reporta el mejor candidato medido, sin promoverlo.
3. **Presupuesto.** Gasto acumulado del ledger ≥ **40 $** (≈ 11 tandas de dev) → para.
4. **Reward hacking.** Dos `DESCARTADO` consecutivos por el **mismo** guardarraíl → para. La
   palanca está produciendo candidatos que bajan σ destruyendo el instrumento.
5. **Techo.** Agotadas las ideas de prompt sin llegar a 0,17 → para y reporta que lo que
   queda son las dos palancas prohibidas (clase de modelo, mediana de k), con su coste.

Ninguna condición de parada la evalúa el modelo «a ojo»: 1, 2 y 4 se leen del ledger, 3 de
la suma de `coste_total`.

## 7. Protección del holdout

Se mide **una vez**, al final, y `calibrar_evaluador.py` lo impone: exige `--sellar` y aborta
si el ledger ya tiene una entrada de holdout. Medir el holdout por iteración lo convierte en
dev y el experimento se queda sin su única prueba limpia.

## 8. Lo que este experimento NO demuestra

- Que la novela mejore. Mide el **instrumento**, no la obra. Un Evaluador menos ruidoso hace
  que §9.2 y §9.4 decidan sobre señal, y solo entonces tiene sentido medir «ahorro de tokens
  sin perder calidad».
- Que σ baje en producción. El fixture son 14 prompts del perfil `poc` (capítulos de 60
  palabras). El perfil `completo` son 2.000 palabras con umbral 4,0; habrá que re-medir.
- Nada con n=3. Tres pasadas por prompt dan una σ imprecisa; por eso la regla exige 0,05 de
  margen y por eso el holdout confirma.

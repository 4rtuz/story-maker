# El juez: validación semántica de la novela completa

Los validadores programáticos (`vp_*`, `novela validar`, `novela auditar`) comprueban lo que se
puede contar: longitud, ids, pistas, hilos. Lo que no se puede contar —si el tono es el pedido, si
el arco cierra, si los recuerdos del brief suenan forzados— lo puntúa un modelo con una rúbrica
fija: el rol `juez` (LLM-as-judge), y, para calibrarlo, una persona con la misma rúbrica.

## Rúbrica

`backend/config/rubrica.yaml`, versión `rubrica-1`. Seis criterios, cada uno de 1 a 5, con
justificación y al menos una cita literal (capítulo y texto):

| Criterio | Qué mide |
|---|---|
| `continuidad` | Hechos, objetos, tiempos y personajes coherentes entre capítulos |
| `tono` | El tono es el del campo `tono` del brief y se sostiene |
| `arco` | Calidad narrativa: planteamiento, escalada y resolución |
| `personajes` | Calidad narrativa: coherencia con su voz y psicología |
| `ritmo` | Calidad narrativa: ritmo entre capítulos |
| `personalizacion` | Rasgos y recuerdos del brief integrados de forma natural, no forzada |

La lista de criterios es el `Literal` `Criterio` de `backend/novela/dominio/juicio.py`; un test
falla si la rúbrica no tiene exactamente esos, en ese orden. Cambiar un criterio, un descriptor o
el umbral es subir `version`: `novela juicio` rechaza un juicio de otra versión.

La salida es `qa/juicio.json`, validada contra `backend/schemas/juicio.schema.json` (modelo
`Juicio`). El mismo modelo sirve a la revisión humana: solo cambia `evaluador`.

## Dónde corre

En `/novela-auditar`, después de `novela auditar` limpio y antes de exportar:

1. `novela briefing <slug> <N> juez`, con N el último capítulo.
2. Task `juez` → `qa/juicio.json`. El hook de política solo le deja escribir ese fichero.
3. `novela juicio <slug>`: valida el fichero, imprime una línea por criterio y la media, y emite
   a Langfuse un score `juez_<criterio>` por criterio (valor 1–5, comentario = justificación) en
   el run del último checkpoint. Id determinista: repetir el juicio sustituye los scores.

Solo aplica a novelas de regalo: sin `brief/brief.json` el briefing sale con 4 y el procedimiento
salta al export. Tono y personalización se definen contra el brief; juzgarlos sin él sería
inventar la referencia.

### Qué ve el juez

Receta `juez` de `backend/config/recipes.yaml`, presupuesto 70.000 tokens (techo de 100.000 menos
10.000 fijos, ~5.000 de salida y 15.000 de margen):

- `brief/brief.json`, `canon/premisa`, `canon/estilo` y todas las fichas de personaje.
- La capa `obra`: los capítulos 1..N completos. Una novela de regalo (10 × 1.500 palabras como
  máximo, unos 26.000 tokens) cabe siempre entera.
- Si no cabe (novela larga), degrada en un paso: resúmenes a párrafo de todos los capítulos
  (`memoria/resumenes/`) y tres capítulos completos, el primero, el central y el último. Queda en
  `degradacion` del frontmatter del briefing como paso 4. Si ni así cabe, falla con
  `PresupuestoExcedido`; nunca se trunca.
- **Sin `canon/misterio.md`** (invariante 3): el juez puntúa como lector, y con la novela
  terminada lo que importa del misterio está en el texto. La receta lo excluye, así que el
  guardarraíl del briefing vigila también que no se cuele por otra capa. Fair play y revelaciones
  los cubren `lector-suspense` y `novela auditar`.

## Umbral y qué pasa si falla

En la rúbrica (`umbral`): pasa si la **media ≥ 3** y **ningún criterio < 2**. `novela juicio`:

| Código | Significado | `/novela-auditar` |
|---|---|---|
| 0 | Pasa el umbral | Exporta |
| 1 | Bajo el umbral | Escribe `runs/<run>/intervencion.md` con la salida y para sin exportar |
| 4 | `qa/juicio.json` ausente, fuera de esquema, de otra rúbrica o de otro evaluador | Repite el juez con esa salida, dos reintentos como máximo; después, intervención |

Bajo el umbral no se reintenta con el `editor-estilo` ni con el escritor. Los capítulos están
sellados (invariante 7) y reescribirlos es abrir una versión con `novela cambio`, algo que decide
una persona a la vista del juicio. `novela producir` ve una auditoría sin export y termina en
`fallido`.

## Comparación con la revisión humana

- Plantilla para personas: `docs/evaluacion/revision-humana.md`, con los mismos criterios, escala y
  justificación con cita.
- Formato máquina: `docs/evaluacion/revision-humana.json`, el mismo esquema con
  `evaluador: "humano"` y las puntuaciones a `null`, para que no valide hasta rellenarla.
- `novela comparar-juicios <slug> --humano <fichero>`: por criterio, nota del juez, nota humana,
  diferencia (humano − juez) y acuerdo (|diferencia| ≤ 1). Emite `juez_acuerdo_humano`, la
  fracción de criterios en acuerdo, con las diferencias en el comentario. Exige la misma
  `rubrica_version` en los dos.

No hay ninguna revisión humana hecha en el repo. El test usa
`backend/tests/fixtures/juicio/humano-FICTICIO.json`, inventado y marcado como tal en su nombre y
en cada justificación.

## Validadores y verificadores

**Validadores** (¿se construye lo correcto?):

- El juez mide la obra, no un capítulo: la receta le da todos los capítulos, o resúmenes y una
  muestra si no caben. Riesgo aceptado: con muestra, el ritmo se juzga en parte sobre resúmenes.
- El acuerdo humano–juez es la medida de si el juez sirve. Con acuerdo bajo de forma sostenida, se
  revisa la rúbrica (subiendo `version`) antes que el umbral.
- Riesgo aceptado: el juez es un modelo y su nota no es determinista. Por eso el gate usa umbrales
  holgados y la decisión bajo el umbral es humana.

**Verificadores** (¿se construye bien?), todos sin llamar a un modelo:

| Qué | Test |
|---|---|
| Esquema: seis criterios, escala 1–5, al menos una cita | `backend/novela/dominio/test_juicio.py` |
| Rúbrica con los criterios del modelo, en orden, y el umbral | `backend/novela/slices/juicio/test_rubrica.py` |
| Gate, scores por criterio con justificación, juicios inválidos | `backend/novela/slices/juicio/test_juicio.py` |
| Comparación humano–juez con fixture ficticio | `backend/novela/slices/juicio/test_juicio.py` |
| Capa `obra`: entera, degradada a muestra, o falla | `backend/novela/slices/briefing/test_assemble.py` |
| Briefing del juez por CLI; sin brief falla; sin misterio | `backend/novela/slices/briefing/test_briefing.py` |
| El misterio no entra en el briefing del juez (property-based) | `test_misterio_nunca_en_briefing` |
| Comentario por score en Langfuse | `backend/novela/plataforma/test_langfuse.py` |
| `juez` solo escribe `qa/juicio.json`; contrato del agente | `backend/tests/test_hook.py`, `backend/tests/test_contratos.py` |

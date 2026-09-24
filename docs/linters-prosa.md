# Linters de prosa

`novela lint-prosa <slug> [<cap>] [--stdout]` pasa cuatro reglas deterministas, en español, por el
cuerpo de `capitulos/NN.md` (el frontmatter YAML no se analiza). Sin capítulo, analiza todos los
escritos. No llama a ningún modelo.

- Código: `backend/novela/slices/prosa/` (`reglas.py` las reglas, `cmd.py` el subcomando).
- Listas versionadas: `backend/config/prosa.yaml` (palabras funcionales, muletillas, clichés,
  marcas de narrador y de tiempo). Cambiar una lista cambia los scores: va en su propio commit.
- Salida: `qa/NN-prosa.json`, escrito por el CLI con escritura atómica y bajo `state.lock`; con
  `--stdout`, el mismo JSON por la salida estándar y nada en disco.
- Scores: `prosa_repeticiones`, `prosa_legibilidad`, `prosa_lexico`, `prosa_estilo`, por el
  `ScoreSink` de `plataforma/langfuse.py` (no-op salvo `TRACE_TO_LANGFUSE=true`). Van a la sesión
  del `run_id` de `checkpoints/NN.json`; si el capítulo no tiene checkpoint, a `lint-prosa`.

**Es informativo.** Sale con 0 aunque haya hallazgos, ningún gate lo lee y el bucle por capítulo no
lo invoca. Son heurísticas de superficie: señalan dónde mirar, no deciden si un capítulo vale. Para
que bloqueara haría falta medir antes su tasa de falsos positivos sobre novelas reales.

## Informe

```json
{
  "schema_version": "1.0.0",
  "capitulo": 3,
  "bloqueante": false,
  "hallazgos": [
    {"regla": "lexico", "codigo": "cliche", "parrafo": 1, "evidencia": "no pudo evitar"}
  ],
  "scores": {"prosa_repeticiones": 1.0, "prosa_legibilidad": 1.0, "prosa_lexico": 0.5, "prosa_estilo": 1.0}
}
```

`parrafo` cuenta desde 1 los bloques de prosa separados por línea en blanco, sin los títulos
(`#`). `null` es un hallazgo del capítulo entero. Cada score vale
`1 − párrafos con hallazgo de la regla / párrafos`, con suelo 0; un hallazgo de capítulo cuenta
como un párrafo.

## Reglas

| Regla | Códigos | Qué mira |
|---|---|---|
| 1. `repeticiones` | `palabra_repetida`, `muletilla` | Palabra con contenido (4 letras o más, fuera de `funcionales`) 3 veces o más en un párrafo; una muletilla de la lista 2 veces o más. Sin lematizar: «puerta» y «puertas» son palabras distintas. |
| 2. `legibilidad` | `frase_larga`, `legibilidad_baja` | Frases de más de N palabras e índice de Fernández-Huerta por párrafo (desde 20 palabras), en su forma corregida: `206,84 − 60·sílabas/palabra − 1,02·palabras/frase`. Sílabas por núcleos vocálicos, aproximadas. |
| 3. `lexico` | `adverbios_mente`, `cliche` | Dos adverbios en -mente o más en un párrafo (con lista de excepciones: «mente», «siente»…); clichés y giros típicos de texto generado, como expresiones regulares. |
| 4. `estilo` | `narrador_primera_persona`, `narrador_tercera_persona`, `tiempo_verbal`, `tratamiento_mixto` | Solo en la narración (el diálogo con raya o comillas se aparta): marcas de primera persona si `punto_de_vista` es `tercera_limitada`; menos de una por cada 100 palabras de narración si es `primera_persona` (desde 30 palabras). Tiempo dominante del párrafo contra `tiempo_verbal`, por formas y terminaciones frecuentes, con 2 de diferencia. En el diálogo, «usted» y formas de tú en el mismo párrafo. `multiple` y `narrador_no_fiable` no comprueban narrador. |

Umbrales de la regla 2, del brief (`brief/brief.json`) si existe:

| Destinatario | Frase máxima | Fernández-Huerta mínimo |
|---|---|---|
| menor de 12 años | 20 palabras | 80 (fácil) |
| de 12 a 15 | 25 | 70 (bastante fácil) |
| adulto, tono `ligero` o `tierno` | 35 | 65 |
| adulto, otro tono, o sin brief | 35 | 55 (algo difícil) |

## Validadores y verificadores

- **Verificadores** (¿se construye bien?): `backend/novela/slices/prosa/test_reglas.py` da al menos
  un texto corto que dispara y uno que no por cada regla; `test_cmd.py` comprueba el informe en
  disco, que el frontmatter no se analiza, el modo sin capítulo, `--stdout` sin escritura, el
  umbral que baja con la edad del brief y un score por regla al `ScoreSink` con el run del
  checkpoint. Ningún test sale a la red.
- **Validadores** (¿se construye lo correcto?): la precisión de las heurísticas no se prueba con
  los tests; se valida leyendo los hallazgos de una novela de humo y ajustando
  `config/prosa.yaml`. Riesgos aceptados: el tiempo verbal y el narrador se detectan por una lista
  de formas y darán falsos negativos en prosa que no las use; el tratamiento no distingue
  hablantes, solo detecta la mezcla dentro de un párrafo; la «u» muda y la «y» vocal desvían
  algo el recuento de sílabas.

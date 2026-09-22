# Fase 3 — Cierre de novela

**Objetivo.** Que una novela terminada se pueda auditar y sacar del workspace.

**Al terminar existe**: `auditar` y `exportar`.

**Cierra**: RF-22, RF-23. CA-23, CA-24.

Fase corta y sin sorpresas. Los dos subcomandos **leen** estado ya construido y no escriben en
él: no tocan `estado.db`, no toman decisiones narrativas y no llaman a ningún agente. Requiere la
fase 1 (modelos y estado) y, para tener algo que auditar, una novela avanzada — pero puede
implementarse contra los fixtures sin esperar a nada.

Antes de empezar, lee las convenciones de ciclo del [README](README.md).

---

## 3.1 — `novela auditar`

**Construye**: `backend/novela/slices/auditoria/cmd.py` y su núcleo puro.

**Rojo**: `novela/slices/auditoria/test_auditoria.py::test_pista_huerfana`. Sobre el fixture
`demo-huerfana/`, con una pista plantada y nunca pagada, `auditar` la reporta y **sale con 1**.

**Verde**: cruza plan, canon y estado, y saca **cuatro** cosas:

| Hallazgo | De dónde sale |
|---|---|
| Pistas plantadas y nunca pagadas | cruce de `plan` con `pistas` del estado |
| Hilos abiertos y nunca cerrados | `hilos` con `estado: abierto` al terminar |
| Pistas falsas nunca desmontadas | `canon.misterio.pistas_falsas`, campo `cuando_se_desmonta` |
| Revelaciones sin pista plantada antes | cruce de `revelaciones` con `pistas` |

`definitions.md` §10 llama auditoría final a las tres primeras. **La cuarta la añade la spec**
(§5.4): es el invariante 4, fair play, y sin ella la auditoría no comprueba la regla central del
género.

```
novela auditar <slug>
```

Sale con 1 si hay hallazgos. El formato de salida es el informe de QA de la tarea 1.7: mismo
modelo, mismo esquema.

**Un matiz sobre el estado de las pistas.** `pistas` es una colección **derivada**
(`definitions.md` §4): se computa del cruce entre plan y texto escrito, no viene del delta. Si al
implementar esto resulta que `pistas` se está leyendo como dato almacenado en vez de calculado,
el bug está en la tarea 2.13, no aquí.

`definitions.md` es tajante sobre por qué esto importa: una pista plantada y nunca pagada es el
fallo de calidad más caro del género. Es la clase de error que ningún gate por capítulo puede
coger, porque cada capítulo pasa el suyo.

**Cierra**: CA-23, RF-22.

**Commit**: `feat(cli): novela auditar, cuatro comprobaciones de cierre`

---

## 3.2 — Exportar a markdown

**Construye**: `backend/novela/slices/export/markdown.py` y `cmd.py`.

**Rojo**: `novela/slices/export/test_export.py::test_md_concatena_en_orden`. Sobre
`demo-terminado/`, `export/novela.md` contiene los capítulos en orden y ninguno repetido.

**Verde**: concatena `capitulos/NN.md` en orden a `export/novela.md`.

```
novela exportar <slug> --formato md|epub
```

**No reescribe prosa. Es transporte, no edición.** Si aparece la tentación de arreglar un guion
largo o normalizar comillas al exportar, eso es trabajo del `editor-estilo` y ya pasó. Un
exportador que edita convierte el fichero exportado en una versión distinta del capítulo, y a
partir de ahí nadie sabe cuál es el texto.

El frontmatter de cada capítulo no va al export: es metadato del harness.

**Commit**: `feat(export): concatenación a markdown`

---

## 3.3 — Exportar a epub

**Construye**: `backend/novela/slices/export/epub.py`.

**Rojo**: `novela/slices/export/test_export.py::test_epub_reabrible`.
`exportar --formato epub` produce un `.epub` que **`ebooklib` reabre** con el número de capítulos
del fixture. No basta con que el fichero exista y pese: un epub corrupto pesa igual.

**Verde**: `ebooklib`, un capítulo por documento, el índice desde los títulos del frontmatter.

`ebooklib` entra como dependencia **aquí**, no en la tarea 1.1: una dependencia declarada tres
fases antes de usarse es una dependencia que nadie sabe si funciona.

RF-23 es de prioridad **«debería»**, la única de la spec que no es «debe». Si la fase 3 tuviera
que recortarse, este es el punto por donde se corta — `auditar` no, porque cierra un invariante.

**Cierra**: CA-24, RF-23.

**Commit**: `feat(export): epub con ebooklib`

---

## Al cerrar la fase

```bash
cd backend && uv run pytest && uv run mypy --strict . && uv run ruff check .
novela auditar demo-terminado; echo $?
novela exportar demo-terminado --formato epub
```

Sigue por [fase-4-api.md](fase-4-api.md), que es la última y la única que puede posponerse.

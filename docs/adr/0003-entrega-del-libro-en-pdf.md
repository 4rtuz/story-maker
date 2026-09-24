---
adr: 0003
titulo: "El libro de regalo se entrega como un PDF que genera el CLI"
estado: aceptada
fecha: 2026-09-24
decide: "arturo.soto"
specs: [0006]
---

# 0003 — El libro de regalo se entrega como un PDF que genera el CLI

## Contexto

`novela exportar` sacaba `md` y `epub`: capítulos concatenados, sin portada, dedicatoria ni ficha
de personajes. La auditoría del entregable (`docs/auditoria-entregable.md`, LEC-01) pedía un libro
navegable desde el backend y el trade-off entre web y PDF documentado.

El destinatario de un regalo no tiene el harness. No tiene `uv`, ni la API, ni el panel. La API se
arranca en local, solo lee, y el panel no lee el disco (`AGENTS.md` § Monorepo).

## Opciones

**(a) Una web servida por la API**: rutas nuevas que devuelven el libro en HTML, con enlaces entre
capítulos y ficha, consumidas por el panel.

**(b) Un PDF generado por el CLI**: `novela exportar --formato pdf` compone portada, índice,
capítulos y ficha con enlaces internos y marcadores, con `fpdf2`.

**(c) El epub actual ampliado**: portada, dedicatoria y ficha como documentos del epub.

## Criterios

1. El destinatario lo lee sin harness, sin servidor y sin red.
2. Es un único fichero que se puede regalar tal cual.
3. Tiene enlaces internos y marcadores.
4. Se genera y se prueba sin llamar a un modelo.
5. No obliga a la API a escribir ni a exponerse fuera de `localhost`.
6. No trae dependencias nativas del sistema (GTK, Pango, Cairo) ni compila en `uv sync` en Windows.

## Decisión

**(b)**. El PDF cumple los seis criterios. Lo genera `novela exportar <slug> --formato pdf` en
`export/novela.pdf`, con `fpdf2` (Python puro) y una fuente embebida en subconjunto. La ficha sale
de la tabla `apariciones` de `estado.db`, que solo escribe `aplicar-delta`. `pdf.py` es la única
frontera con la biblioteca.

## Alternativas descartadas

**(a) Web servida por la API.** Falla los criterios 1, 2 y 5: exige un servidor en marcha, no es
un fichero que se entregue, y servirlo fuera de `localhost` rompe el modelo de la API.

**(c) Epub ampliado.** Cumple 1, 2, 4 y 6, pero el soporte de enlaces internos y de maquetación
fija varía mucho entre lectores, y un lector de PDF lo tiene cualquier destinatario. El epub sigue
existiendo, sin cambios, para quien lo prefiera.

**WeasyPrint u otro HTML → PDF.** Falla el criterio 6: depende de Pango y Cairo en Windows.

## Consecuencias

**Lo que ganamos.** Un fichero que se regala, se abre en cualquier lector y se navega por índice,
ficha y marcadores. Se prueba entero con `pypdf` en la suite, sin cuota.

**Lo que aceptamos.**

- **`fpdf2` es LGPL-3.0.** Se usa como biblioteca sin modificar, así que no contamina el harness,
  pero un cambio de licencia o de mantenimiento obliga a reabrir esta decisión.
- **Revisión humana del PDF antes de entregarlo.** La ficha solo lleva nombre, alias y
  descripción, pero el `nombre` o la `descripcion` de un lugar podrían insinuar la solución. Eso
  no lo detecta ningún test: el operador lee la ficha antes de regalar el libro.
- **Los workspaces anteriores a la tabla `apariciones` no exportan en PDF.** Salen con 4 y nombran
  los capítulos; `md` y `epub` siguen funcionando.
- **Sin PDF/UA ni tipografía avanzada.** Hay marcadores, `/Lang` y texto extraíble, nada más.

## Cuándo reabrirla

Si `fpdf2` cambia de licencia o deja de mantenerse, si el libro tiene que leerse en línea (una web
pública ya no rompería el criterio 5, porque no sería la API del harness), o si el destinatario
necesita un formato accesible certificado (PDF/UA).

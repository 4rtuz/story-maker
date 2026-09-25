# Linter de edición manual (LSP)

Un servidor [LSP](https://microsoft.github.io/language-server-protocol/) de solo lectura para
cuando alguien edita a mano un capítulo: señala los problemas mientras escribe, en cualquier editor
con cliente LSP. Está en `backend/novela/lsp/` y se arranca por stdio:

```bash
cd backend && uv run python -m novela.lsp
```

Solo actúa sobre documentos cuya ruta es `<novelas>/<slug>/capitulos/NN.md` de un workspace
existente (con `config.yaml`): de la ruta saca el slug y el capítulo. Cualquier otro fichero no
recibe diagnósticos. Publica en `didOpen` y en cada `didChange`, sobre el texto del editor aunque no
esté guardado.

## Diagnósticos

Cada comprobación es la del gate correspondiente. El LSP no tiene lógica propia, solo convierte
cada hallazgo en un rango del documento, con el frontmatter incluido.

| `code` | Severidad | De dónde sale | Rango |
|---|---|---|---|
| `termino_prohibido` | error | `dominio/prohibidas.buscar` con los tres niveles de `policy_db.prohibidos` (docs/guardrails.md) | la forma exacta, aunque la frase cruce de línea |
| `nombre_mal_escrito` | error | `gates.erratas`, el mismo cálculo de `vp_nombres`, contra las fichas de `canon/personajes/` y el destinatario de `brief/brief.json` | el token |
| `hecho_cambiado` | aviso | la regla RF-33 de `aplicar-delta`: la cita de cada hecho de `libro_de_hechos` de ese capítulo tiene que aparecer literal (según `normalizar`) en el texto | la línea donde estaba la cita en el fichero guardado; la primera del cuerpo si no la encuentra |
| el `codigo` de la regla (`palabra_repetida`, `narrador_primera_persona`…) | información | `lint-prosa` (`slices/prosa/reglas.analizar`, docs/linters-prosa.md) | primera línea del párrafo; la del cuerpo si el hallazgo es del capítulo entero |

Si el workspace no se puede leer (canon inválido, `estado.db` ilegible), publica un solo error en
la línea 1 con la causa en lugar de caerse.

`estado.db` se abre con `mode=ro` y el servidor no toma `state.lock` ni escribe nada: no deja
auditoría del guardrail ni scores. Eso lo hacen `novela validar` y `novela prohibidas comprobar`.

## Conectarlo a VS Code

VS Code no trae un cliente LSP genérico, así que hace falta una extensión que lo tenga. Con
[Generic LSP Client](https://marketplace.visualstudio.com/items?itemName=llllvvuu.llllvvuu-glspc)
(`llllvvuu.llllvvuu-glspc`), en el `settings.json` de VS Code (claves del `package.json` de la
extensión; compruébalas en «Extension Settings» si tu versión es otra):

```json
{
  "glspc.serverCommand": "uv",
  "glspc.serverCommandArguments": [
    "run", "--directory", "C:/ruta/al/repo/backend", "python", "-m", "novela.lsp"
  ],
  "glspc.languageId": "markdown"
}
```

Pon la ruta de `backend` en absoluto, porque no se sabe desde qué directorio arranca la extensión
el servidor. No hace falta `NOVELAS_DIR`: el servidor deduce el workspace de la ruta del
documento. Los diagnósticos salen en el panel Problemas con origen `novela`.

Cualquier otro editor con cliente LSP vale igual. En Neovim, por ejemplo:

```lua
vim.lsp.start({ name = "novela", cmd = { "uv", "run", "--directory", "backend", "python", "-m", "novela.lsp" } })
```

## Publicar una edición que cambia un hecho

El LSP avisa, no publica. Invariante 7 de AGENTS.md: no se reescribe un capítulo de una versión, y
solo `novela cambio` abre una nueva. Así que el aviso `hecho_cambiado` significa que esa edición
exige una versión nueva, con este flujo y las órdenes que ya existen (spec 0007):

1. Guarda la edición fuera del workspace (p. ej. `editado-07.md`) y deshaz el cambio en
   `capitulos/07.md`.
2. Por cada hecho del aviso, `novela cambio <slug> --hecho hec-NNN --texto "<el hecho nuevo>"`.
   Admite un cambio en curso a la vez: con varios hechos, se completa uno y se pide el siguiente.
   `cambio` guarda la edición vigente en `versiones/vN/` y restablece la raíz.
3. `novela cambio <slug> --siguiente` dice qué capítulo toca. Para el capítulo editado (`NN
   regenerar`), el texto de `editado-07.md` ocupa el lugar del escritor: se copia a
   `capitulos/07.md` y se sigue el bucle de `/novela-continuar` desde `novela validar`: revisores,
   cronista, `aplicar-delta` y `checkpoint`. La custodia de `aplicar-delta` exige que validar,
   revisores y cronista hayan visto ese mismo fichero, y el gate RF-31 de `validar`, que plante,
   pague, abra y cierre lo mismo que en la versión anterior.
4. Los demás capítulos del plan: `NN reaplicar` con `aplicar-delta <slug> <cap> --reaplicar` y
   `checkpoint`, y los `NN regenerar` con el bucle normal.
5. Antes de exportar, `novela verificar-lean <slug>` (docs/formal/lean.md), `novela auditar
   <slug>` y `novela prohibidas comprobar <slug>`. Después, `novela exportar`.

No hay una orden `novela edicion` que haga esto de una vez. Los pasos 2 y 3 necesitan una decisión
humana (qué dice el hecho nuevo) y la custodia completa de la versión nueva, y automatizarlos
supondría saltarse la revisión del capítulo editado.

Una edición que no toca ningún hecho (estilo, una errata, un término vetado) tampoco se publica
sobre la versión cerrada. Sigue siendo un capítulo reescrito.

## Validadores y verificadores

- **Misma lógica que los gates.** `buscar` devuelve inicio y fin de cada coincidencia, y
  `gates.erratas` las posiciones que `vp_nombres` agrupa por línea. Las dos se prueban con
  property tests (`test_el_rango_de_una_palabra_contiene_su_forma`, `test_erratas_property`):
  el texto del rango es exactamente la forma señalada. `nombres` se calcula ahora a partir de
  `erratas`, y sus tests de siempre (`test_nombres_property`, `test_nombres_casos_fijos`) siguen
  en verde.
- **Diagnósticos sobre un workspace real.** `novela/lsp/test_lsp.py` usa `demo-24` de
  `tests/fixtures/fabrica.py`. El capítulo intacto no da errores ni avisos, y el sha256 de
  `estado.db` no cambia. Un término vetado y un nombre con otra grafía dan el rango exacto. Cambiar
  la frase citada por `hec-007` da `hecho_cambiado` en la línea de la cita, y un párrafo en primera
  persona da información. Fuera de un workspace no sale nada.
- **Por stdio de punta a punta.** `test_el_servidor_publica_en_did_open_y_did_change` lanza
  `python -m novela.lsp`, hace `initialize` y comprueba que `didOpen` y `didChange` publican, y que
  el término añadido en el cambio aparece en la segunda publicación.
- **Destinatario.** `validacion.formas` añade el nombre del destinatario de `brief/brief.json`
  a las formas de `vp_nombres`, que su docstring ya preveía. Desde este cambio, `novela validar`
  también lo comprueba (`test_grafia_del_destinatario_del_brief`).
- **Riesgos aceptados.** Las columnas son las del texto en NFC, en unidades de Python. Coinciden
  con las UTF-16 del protocolo para el español y con un fichero en NFC, pero no con NFD ni con
  emojis. La línea de `hecho_cambiado` es la del fichero guardado: si la edición mueve líneas, el
  aviso puede quedar desplazado. Cada `didChange` recalcula todo, con relectura del canon y de la
  base: basta para un capítulo, pero no se ha medido en novelas grandes.

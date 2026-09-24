# Fase 2: Entradas

Plan: `README.md` · Spec: `docs/specs/0005/spec.md` · Tareas: T2.1, T2.2 · Depende de: fase 1

Reglas comunes: las de `README.md` §5.

## T2.1 (T-02) Funciones puras de entradas
- Descripción: `entradas.py` con `normalizar_entrada` (NFC, `\r\n` y `\r` a `\n`, fuera los caracteres de control salvo `\n` y `\t`), `fragmentar` (por línea, y cada línea por `(?<=[.!?…])\s+`, con número de línea base 1 e intervalo en el original, PD4), `normalizar_con_mapa` (PD4), `marcar` (lista cerrada de patrones de §8.4 sobre el fragmento en minúsculas y sin tildes), `marca(run_id, id, texto)` (16 hexadecimales de sha256 de `f"{run_id}\n{id}\n{texto}"`), `delimitar` (aviso fijo, apertura, texto sin alterar, cierre; lanza una excepción propia si el texto contiene su marca) y `extraer_bloques`. Sin disco ni reloj.
- Archivos: `backend/novela/slices/brief/__init__.py` (nuevo) · `backend/novela/slices/brief/entradas.py` (nuevo) · `backend/novela/slices/brief/test_entradas.py` (nuevo) · `backend/tests/fixtures/brief/carta-inyectada.md`, `carta-limpia.md` (nuevos)
- Cubre: RF-09, RF-10, RF-11, RNF-03
- Depende de: T1.1
- Hecho cuando: pasan `test_entradas.py::test_delimitacion_property` (CA-09, Hypothesis con `max_examples=200`, textos con marcas inventadas, `<<<`, `>>>`, vallas y saltos: un bloque por entrada, contenido idéntico y aviso delante), `::test_marca_presente` (CA-10, a nivel de función) y `::test_fragmentos_marcados` (CA-11: `marcar` devuelve las líneas 4 y 7 de `carta-inyectada.md`), y el test de RNF-05 sigue en verde con las cartas nuevas.
- Complejidad: M

## T2.2 (T-03) `iniciar` y `entrada`, sub-app y brief cerrado
- Descripción: `cmd.py` con la sub-app `brief_app` y los subcomandos `iniciar` (valida slug y ocasión antes de tocar disco, sale con 2 ante una ocasión inválida, reclama el slug con `mkdir` sin `exist_ok` y sale con 1 si existe, crea `brief/entradas/`, `estado/` y `runs/`, y escribe `brief/inicio.json` bajo el lock) y `entrada` (lee el fichero como UTF-8 estricto, normaliza con T2.1 y rechaza con 2 si no existe, no es UTF-8, queda vacío o supera 20.000 caracteres tras normalizar (ver P8); con 1 si ya hay 20 entradas; escribe `ent-NN.md` de forma atómica con frontmatter `EntradaMeta` y el sha256 del cuerpo, e imprime el id). Función común `_brief_abierto(ws)`, que sale con 1 y «brief cerrado: la novela ya existe» si existe `config.yaml`. Registro en `cli.py` con `con_codigos` en cada subcomando. Cada subcomando abre el run `(1, "arranque")` y deja una línea con `Run.registro`, con `--tipo texto-libre` registrado como `texto_libre` y las causas saneadas (PD3). Documentar `novela brief iniciar|entrada` en `docs/architecture.md` §8 y `AGENTS.md` § CLI, y `brief/` e `ent-NN` en `docs/architecture.md` §4 y §5 (PD6).
- Archivos: `backend/novela/slices/brief/cmd.py` (nuevo) · `backend/novela/slices/brief/test_cmd.py` (nuevo) · `backend/novela/cli.py` (modificar) · `backend/tests/fixtures/brief/respuestas-completas.md`, `respuestas-contradictorias.md` (nuevos) · `docs/architecture.md`, `AGENTS.md` (modificar)
- Cubre: RF-04, RF-05, RF-06, RF-07 (entrada), RNF-12 (parcial)
- Depende de: T2.1
- Hecho cuando: pasan `test_cmd.py::test_iniciar` (CA-04: 0, 1 sin cambios en la huella, 2 sin crear `otra-prueba/`), `::test_entrada_normaliza` (CA-05: imprime `ent-01`, cuerpo en NFC, con `\n` y sin `\x07`), `::test_entrada_rechaza` (CA-06: cuatro 2 y un 1, sin ficheros nuevos en `brief/entradas/`), la parte de `entrada` de `::test_brief_cerrado` (CA-07) y un test de lock ocupado que sale con 3 con el fixture `lock_ajeno`.
- Complejidad: M

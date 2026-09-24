# formal/tla — el harness como máquina de estados

Dos modelos TLA+ que TLC comprueba exhaustivamente. El explainer, los invariantes, los resultados
y los hallazgos están en [`docs/formal/tla.md`](../../docs/formal/tla.md).

| Fichero | Qué es |
|---|---|
| `Harness.tla` | El flujo entero: brief → `/novela-nueva` → bucle por capítulo → `/novela-auditar` → publicación, con reintentos, caídas, reanudación y `novela cambio` |
| `Harness.cfg` | El modelo pequeño: 5 capítulos, 2 reintentos, 2 caídas, 1 cambio. Debe pasar |
| `Harness{Mutante,Reanudar,Export,Vaciar}.cfg` | Mutantes: cada uno desactiva una guarda real y debe dar contraejemplo |
| `Harness{Literal,Cuenta}.cfg` | Hallazgo H-2 del procedimiento: deben dar contraejemplo |
| `Regeneraciones.tla` / `.cfg` / `Mutante.cfg` | Dos `novela cambio` a la vez con `estado/state.lock` |
| `tlc.sh` | Ejecuta TLC y compara con lo esperado |

## Ejecutar

```bash
formal/tla/tlc.sh                 # todos los .cfg; sale con 1 si alguno no da lo esperado
formal/tla/tlc.sh Harness.cfg     # uno
JAVA=java TLA2TOOLS=~/tla2tools.jar SALIDA=/tmp/tlc formal/tla/tlc.sh
```

Un `.cfg` cuyo comentario dice «se espera … contraejemplo» tiene que violar su invariante; el
resto, pasar. La salida completa de TLC, con la traza, queda en `$SALIDA/<modelo>.out`.
`backend/tests/test_tla.py` lo lanza desde pytest y se salta si no hay java.

## Variables → código

| Variable | Dónde vive en el código | ¿Sobrevive a una caída? |
|---|---|---|
| `fase`, `paso`, `cap` | La sesión del orquestador (`claude -p`), `producir.flujo.producir` | No; `cap` se recalcula |
| `mec` | `qa/NN-validacion.json`: sin hallazgos y `capitulo_sha256` igual al disco (custodia, `delta/custodia.py`) | Sí |
| `ver` | `veredicto` de `qa/NN-continuidad.json` y `qa/NN-suspense.json` | Sí |
| `delta` | `estado/deltas/NN.json` y el cursor de `estado.db` en `aplicar-delta` | Sí |
| `revDespues` | Hay un `briefing NN continuista` en `harness.log` después de la última `validar NN` | Sí |
| `log[g]` | Líneas de `runs/<run_id>/harness.log` que cuenta § Cuenta de intentos | Sí, por run de capítulo |
| `fallos`, `reintentos` | Fantasmas: no existen en el código, sirven a los invariantes | — |
| `checkpoint` | `checkpoints/latest.json` (`capitulo`), lo que lee `novela pendiente` | Sí |
| `libro` | `capitulos_sha256` del checkpoint: los capítulos cerrados, en orden | Sí |
| `version` | `meta.version` de `estado.db` (spec 0007) | Sí |
| `guardadas` | `versiones/vN/` con su `version.json` | Sí |
| `cambioEstado`, `pasoCambio` | `cambios/cam-NNN.json` (`preparando`, `en_curso`) y si `vN/` ya está renombrado | Sí |
| `auditada` | `qa/auditoria.json` con `veredicto: aprobado` | Sí (se vacía con `cambio`) |
| `exportada` | Versión de lo que hay en `export/`; `cambio` no lo vacía | Sí |

## Acciones → código

| Acción | Orden o paso | Fichero |
|---|---|---|
| `BriefOK`, `BriefFalla` | `novela brief validar` y su reintento del `entrevistador` | `.claude/commands/novela-brief.md` paso 4 |
| `PlanOK`, `PlanFalla` | `arquitecto` + `novela briefing 1 trazador` (gate del arquitecto) + `trazador` | `novela-nueva.md` pasos 2-3 |
| `Escribir` | `novela briefing … escritor` + Task `escritor` | `novela-continuar.md` paso 2 |
| `ValidarOK/Falla("validar1")` | `novela validar`; reintento del `escritor` | paso 3, `slices/validacion/` |
| `Revisar` | Tres briefings de revisión y tres Task; el editor reescribe | paso 4 |
| `ValidarOK/Falla("validar2")`, `Editar` | `novela validar` otra vez; reintento del `editor-estilo` | paso 5 |
| `GateOK`, `GateFalla` | Lectura de `veredicto`; reintento del `escritor` | paso 6 (solo en el procedimiento) |
| `Cronista` | `novela briefing … cronista` + Task `cronista` | paso 7 |
| `AplicarOK`, `AplicarFalla`, `Custodia` | `novela aplicar-delta`; reintento del `cronista`; causa `custodia:` → intervención | paso 7, `slices/delta/cmd.py` |
| `Checkpoint` | `novela checkpoint` (exige cursor en `aplicar-delta`) | paso 8, `slices/checkpoint/cmd.py` |
| `Falla(g, …)` | § Cuenta de intentos y `intervencion.md` | `novela-continuar.md`, `novela-nueva.md` |
| `AuditarOK`, `AuditarFalla` | `novela auditar` + `novela exportar md/epub`; y cómo decide `producir` | `novela-auditar.md`, `slices/producir/flujo.py` |
| `CambioRegistrar` | `_nueva_peticion` + `registrar_peticion` | rama `spec-0007`: `slices/cambio/cmd.py` |
| `CambioCopiar` | `_copiar` + `os.replace(vN.tmp, vN)` | `plataforma/versiones.py` `preparar` |
| `CambioVaciar` | `_vaciar` + `_base_nueva` + `en_curso` | `plataforma/versiones.py` `preparar` |
| `Caida` | La sesión muere (`claude -p` sale distinto de 0, o se corta) | bucle desatendido de `AGENTS.md`, `flujo.py` |
| `Reanudar` | Relanzar: `novela pendiente`, `latest.json + 1`, § Punto de reanudación; con `cam-NNN` en `preparando`, repetir la misma petición (RF-20) | `novela-continuar.md`, `versiones.py` |
| `Fin` | Parada en `publicada`, `detenida` o `intervencion` | — |

## Simplificaciones

- Un capítulo reaplicable de `novela cambio` pasa por el bucle como uno regenerado: para los
  invariantes es lo mismo, un capítulo que llega a checkpoint validado.
- `checkpoint` escribe `NN.json` y después `latest.json`; se modela atómico porque una caída entre
  los dos reanuda en el paso 8 y lo repite, y `checkpoint` es idempotente. Lo mismo `aplicar-delta`
  entre el commit y su línea de log (`test_aplica_y_es_idempotente_en_disco`).
- La auditoría y la exportación van en una acción; las rondas de usuario del brief no se modelan.
- `Regeneraciones.tla` resume la regeneración de la versión nueva en una acción (`Regenerar`).

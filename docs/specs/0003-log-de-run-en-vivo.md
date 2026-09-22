---
spec: 0003
titulo: "Log de run en vivo: progreso intracapítulo en el panel"
estado: borrador
autor: "arturo.soto"
fecha: 2026-09-22
version: 0.1
afecta: [backend, frontend, docs]
depende_de: []
sustituye: []
adr: []
commit: null
---

# 0003 — Log de run en vivo: progreso intracapítulo en el panel

## 1. Propósito y alcance

Exponer `runs/<run_id>/harness.log` por la API para que el panel muestre qué está pasando **durante** un capítulo, y no solo cuando el capítulo termina.

**Dentro del alcance**

- `GET /novelas/{slug}/runs` — lista de `run_id` del workspace, del más reciente al más antiguo.
- `GET /novelas/{slug}/runs/{run_id}/log` — tramo del log desde un desplazamiento, con tope de tamaño por respuesta.
- Consumo desde el panel: una sección de actividad que hace *polling* sobre el run vigente.

**Fuera del alcance**

- Streaming (SSE, WebSocket). El panel ya hace *polling* para el estado; una segunda mecánica de transporte para el mismo patrón no se justifica. Ver §15.
- Estructurar el log. Hoy es texto; se sirve como texto. Convertirlo en eventos tipados es otra spec y probablemente innecesaria.
- Cualquier escritura. Los dos endpoints son `GET` y la API sigue sin mutar nada.
- Las trazas de Langfuse. Esto es el log local del harness, no la traza.

## 2. Problema

`estado/estado.db` solo cambia en `novela aplicar-delta`, que corre al final del capítulo. Entre medias hay una llamada al `escritor`, un gate de Python, tres revisores en paralelo y el `cronista`: varios minutos durante los cuales el panel consulta la API, recibe exactamente el mismo estado que hace un minuto y no tiene nada que mostrar.

El resultado es que el *polling* de `architecture.md` §11.2 sugiere una granularidad que no existe: la curva de tensión y el contador de capítulos se mueven a saltos, una vez por capítulo. Para el operador, un capítulo en curso y un bucle colgado son indistinguibles desde el navegador.

El dato que falta ya está en disco: `runs/<run_id>/harness.log` se escribe durante la ejecución. Nadie lo sirve.

Evidencia: ninguna de ejecución. `backend/` está vacío y no hay novelas escritas. Es una carencia deducida del diseño de §11.2 y del momento en que escribe `aplicar-delta`, no un fallo observado.

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Operador humano | Distinguir «va por el continuista» de «esto lleva veinte minutos parado» sin abrir una terminal |
| Frontend / API | Dos endpoints de lectura más; ningún modelo nuevo de dominio |
| Orquestador | Ninguno. No cambia el bucle, ni los gates, ni los briefings |

## 4. Contexto y restricciones

- **Invariantes que aplican**: el 5 (el contexto vive en disco) es lo que hace esto posible — el log ya está escrito, solo falta leerlo. Ninguno de los ocho se toca.
- **Restricciones técnicas**: API de solo lectura; el log puede estar siendo escrito mientras se lee; el fichero puede no existir todavía.
- **Supuestos**: `harness.log` se escribe línea a línea y vacía el buffer con frecuencia suficiente para que leerlo a mitad tenga sentido. Si el harness lo volcara de golpe al final, esta spec no sirve de nada.
- **Dependencias**: ninguna.

## 5. Propuesta

Dos endpoints de lectura sobre ficheros que ya existen.

**Listado de runs.** `GET /novelas/{slug}/runs` recorre `novelas/<slug>/runs/`, ordena por fecha de modificación descendente y devuelve el `run_id` y el instante de la última escritura. Hace falta porque hoy no hay forma de descubrir el `run_id` vigente: `GET /novelas/{slug}/runs/{run_id}` ya sirve el manifest, pero solo si lo conoces de antemano.

**Tramo de log.** `GET /novelas/{slug}/runs/{run_id}/log?desde=<byte>` abre el fichero, se posiciona en `desde`, lee como mucho 64 KiB y devuelve las líneas completas leídas más el desplazamiento donde se quedó. El cliente guarda ese desplazamiento y lo manda en la siguiente petición. Es la forma más simple de leer un fichero que crece: sin estado en el servidor, sin suscripción, sin cursor que caducar.

Una línea parcial al final del tramo —el proceso escribía mientras leíamos— se descarta y no se cuenta en el desplazamiento devuelto. Entra completa en la petición siguiente.

Si el fichero no existe todavía, la respuesta es `200` con cero líneas y desplazamiento `0`, no `404`: un run recién creado que aún no ha escrito nada es un estado normal, no un error.

## 6. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | `GET /novelas/{slug}/runs` devuelve los `run_id` del workspace ordenados por última modificación descendente | debe |
| RF-02 | `GET /novelas/{slug}/runs/{run_id}/log` devuelve las líneas del log a partir del byte `desde` y el desplazamiento resultante | debe |
| RF-03 | La respuesta nunca supera 64 KiB de log; si queda más, el desplazamiento devuelto lo refleja y el cliente vuelve a pedir | debe |
| RF-04 | Una línea incompleta al final del tramo se descarta y no cuenta en el desplazamiento | debe |
| RF-05 | Un `run_id` inexistente devuelve `404`; un log ausente para un run válido devuelve `200` vacío | debe |
| RF-06 | El panel muestra la actividad del run vigente y la refresca por *polling* | debería |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-01 | Rendimiento | La respuesta no depende del tamaño del log: se lee un tramo acotado desde un desplazamiento, nunca el fichero entero |
| RNF-03 | Coste / cuota | Cero llamadas a modelo. Cero cuota |
| RNF-04 | Fiabilidad | Leer el log mientras el harness escribe no bloquea al escritor ni corrompe la lectura; en el peor caso se pierde el final de una línea, que llega en la petición siguiente |
| RNF-06 | Compatibilidad | Aditivo. Las novelas ya empezadas funcionan; las que no tengan `harness.log` devuelven vacío |
| RNF-07 | Seguridad | `slug` y `run_id` se validan contra un patrón estricto antes de componer ninguna ruta. La ruta resuelta debe caer dentro de `novelas/<slug>/runs/`; si no, `404` |

## 8. Interfaces y contratos

**API** — dos rutas **nuevas**, ninguna ruptura:

```
GET /novelas/{slug}/runs
    200 → [{"run_id": str, "modificado": datetime}]

GET /novelas/{slug}/runs/{run_id}/log?desde=<int, por defecto 0>
    200 → {"run_id": str, "desplazamiento": int, "lineas": [str], "fin": bool}
    404 → run_id desconocido
```

`fin` indica que el tramo devuelto llega al final actual del fichero. Le ahorra al panel comparar desplazamientos para saber si debe volver a pedir de inmediato o esperar al siguiente ciclo.

**Modelos** — `RunResumen` y `TramoLog` en `backend/novela/models/`, como el resto. No describen entidades del dominio narrativo: son modelos de transporte, y conviene que eso quede dicho en su docstring para que nadie los confunda con ontología.

**CLI**: sin cambios.
**Contrato de agente**: sin cambios.
**Ficheros del workspace**: sin cambios. Solo se leen.

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | Sin cambios |
| `plan/` | Sin cambios |
| `estado/estado.db` | Sin cambios |
| `memoria/` | Sin cambios |

`runs/` no es ninguna de las cuatro ramas: es material de ejecución, desechable por definición (`architecture.md` §4). Servirlo no añade una fuente de verdad.

## 10. Migración y compatibilidad

No aplica: cambio aditivo y de solo lectura. Las novelas en curso siguen validando.

## 11. Criterios de aceptación

- [ ] **CA-01** (RF-01) Con dos runs en el workspace, `GET /novelas/{slug}/runs` los devuelve ambos, el modificado más recientemente primero.
- [ ] **CA-02** (RF-02) Sobre un log de tres líneas, `desde=0` devuelve las tres y un desplazamiento igual al tamaño del fichero.
- [ ] **CA-03** (RF-02) Repetir la petición con el desplazamiento devuelto da cero líneas y `fin: true`.
- [ ] **CA-04** (RF-03) Sobre un log de 200 KiB, una petición devuelve como mucho 64 KiB y `fin: false`.
- [ ] **CA-05** (RF-04) Si el fichero termina en una línea sin salto final, esa línea no aparece en la respuesta y el desplazamiento apunta antes de ella. Al completarse la línea, la petición siguiente la devuelve entera y una sola vez.
- [ ] **CA-06** (RF-05) Un `run_id` inexistente devuelve `404`. Un run que existe sin `harness.log` devuelve `200` con `lineas: []`.
- [ ] **CA-07** (RNF-07) Un `run_id` con `..`, con separador de ruta o con byte nulo devuelve `404` sin tocar el disco fuera de `runs/`.

## 12. Trazabilidad

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 | CA-01 | `backend/tests/test_api_runs.py::test_lista_runs_por_fecha` | pendiente |
| RF-02 | CA-02, CA-03 | `backend/tests/test_api_runs.py::test_tramo_log_incremental` | pendiente |
| RF-03 | CA-04 | `backend/tests/test_api_runs.py::test_tope_por_respuesta` | pendiente |
| RF-04 | CA-05 | `backend/tests/test_api_runs.py::test_linea_parcial_se_descarta` | pendiente |
| RF-05 | CA-06 | `backend/tests/test_api_runs.py::test_run_inexistente_y_log_ausente` | pendiente |
| RNF-07 | CA-07 | `backend/tests/test_api_runs.py::test_run_id_no_escapa_del_workspace` | pendiente |

## 13. Verificación

- No toca `validate.py` ni `delta.py`: los tests son de ejemplo, no property-based.
- CA-05 es el único criterio con aritmética real —desplazamientos y líneas partidas— y merece además una propiedad: para cualquier troceado de un log en N peticiones, la concatenación de las líneas devueltas es igual al log completo y ninguna línea aparece dos veces.
- **Riesgos aceptados**: el log se sirve tal cual. Si un agente escribiera una clave en él, la API la expondría. Hoy no ocurre porque las claves viven en `.claude/settings.local.json` y el harness no las imprime, pero nada lo impide mecánicamente.

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | Ninguno |
| Esquemas | Dos modelos de transporte nuevos; no son entidades del dominio, así que `docs/definitions.md` no cambia |
| Contratos de agente | Ninguno |
| Docs de referencia | `architecture.md` §11.1 (lista de endpoints) y §11.2 (qué muestra el panel), en el commit de implementación |
| Frontend | Sección de actividad nueva; nada de lo existente cambia |

## 15. Alternativas descartadas

- **SSE o WebSocket.** Transporte con estado para un caso que ya se resuelve con *polling*, que es lo que el panel hace para todo lo demás. Añade reconexión, contrapresión y un segundo modo de fallo a cambio de unos segundos de latencia.
- **Servir el fichero entero en cada petición.** Trivial de implementar y de coste creciente sin límite. El desplazamiento cuesta tres líneas más.
- **`tail -f` por subproceso.** Un proceso vivo por cliente, colgado del servidor. Lo contrario de lo que se le pide a una API de solo lectura.
- **Estructurar el log como eventos JSON.** Sería mejor dato, pero obliga a definir un esquema de eventos antes de saber qué eventos importan. Si el panel acaba pidiéndolo, es otra spec.

## 16. Preguntas abiertas

- [ ] ¿El panel descubre el run vigente con `GET /novelas/{slug}/runs` y toma el primero, o el `run_id` en curso debería salir en `GET /novelas/{slug}/estado`? Lo segundo es una petición menos y un campo más en un modelo de dominio que hoy no lo necesita — arturo.soto
- [ ] ¿Con qué frecuencia vacía el buffer el harness al escribir `harness.log`? Si no es línea a línea, RF-02 no aporta nada y la spec se descarta — arturo.soto

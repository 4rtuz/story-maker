---
spec: 0004
titulo: "Lanzamiento desde el panel: cola de solicitudes y supervisor"
estado: borrador
autor: "arturo.soto"
fecha: 2026-09-22
version: 0.2
afecta: [backend, frontend, docs]
depende_de: []
sustituye: []
adr: []
commit: null
---

# 0004 — Lanzamiento desde el panel: cola de solicitudes y supervisor

## 1. Propósito y alcance

Que el formulario del panel lance una novela de verdad, en lugar de imprimir un comando para que un humano lo copie en una terminal.

**Dentro del alcance**

- `POST /cola` — la API acepta una solicitud de novela y la deja en una cola en disco. Es la primera escritura de la API.
- `GET /cola` — estado de la cola y si hay un supervisor vivo.
- Subcomandos `novela cola tomar` y `novela cola cerrar`, que son cómo el supervisor consume la cola.
- `scripts/supervisor.sh` — el bucle que vacía la cola invocando Claude Code, en shell y con la misma forma que el bucle desatendido ya documentado.
- `backend/run.sh` — arranca la API y el supervisor a la vez. Un solo comando de puesta en marcha, para que no exista el estado «panel en pie, nadie ejecutando».
- El formulario del panel deja de mostrar un comando y pasa a encolar.

**Fuera del alcance**

- **Que la API mute una novela.** Sigue sin poder. Escribe en la cola y en ningún otro sitio; `novelas/<slug>/` solo lo toca el CLI. Esta distinción es el eje de la spec.
- Continuar, parar o intervenir una novela desde el panel. Solo se encola el arranque. Ver §15.
- Autenticación de usuarios, multiusuario, cuotas por persona. El supervisor gasta la suscripción de quien lo arranca, y por eso el servicio es local (RNF-07).
- Cancelar una solicitud encolada. El supervisor la recoge en segundos; un `DELETE` que casi nunca llega a tiempo es aparato sin uso.
- **Un camino de arranque manual desde el panel.** No hay modo «sin supervisor» con el comando para copiar: si el panel está en pie, el supervisor también (§5.5). Mantener las dos vías sería conservar justo lo que esta spec viene a eliminar.
- Cualquier cambio en el bucle por capítulo, los gates o los briefings.

## 2. Problema

El formulario de `architecture.md` §11.2 produce un `config.yaml` y «deja preparado el comando `/novela-nueva` para copiar». El usuario rellena cuatro campos en el navegador y el sistema le responde con deberes: abre una terminal, pega esto. Es la única costura manual del diseño y está en el primer paso que da cualquiera.

La razón por la que está ahí es real y no desaparece: escribir una novela exige invocar modelos, y este harness corre entero sobre la suscripción de Claude Code, que es un proceso CLI y no una librería que FastAPI pueda importar (`architecture.md` §2, «fuera del stack»). Un `POST` que escribiera un capítulo tendría que lanzar `claude -p` y esperar minutos: petición HTTP y ejecución de un capítulo no tienen la misma forma ni la misma duración.

Hay además una segunda incoherencia que sale a la luz al mirar este camino: el formulario genera un `config.yaml` **y** el comando `/novela-nueva` lleva los mismos parámetros como flags. Ningún documento dice cuál manda ni cómo llega ese fichero al workspace.

Evidencia: ninguna de ejecución. Ni `backend/` ni `frontend/` existen todavía. El problema es de diseño y se resuelve por argumento.

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Operador humano | Arranca una novela desde el navegador; deja de necesitar la terminal para el caso normal |
| Frontend / API | El formulario pasa a ser funcional; la API adquiere un verbo de escritura acotado |
| Orquestador | Ninguno dentro del capítulo. Recibe el arranque por otra vía, con el mismo contrato |
| Supervisor | Actor nuevo: un proceso de shell que vacía la cola. No decide nada sobre la novela |

## 4. Contexto y restricciones

- **Invariantes que aplican**:
  - El 8 (un proceso por workspace) es el que condiciona el diseño: un servidor HTTP es concurrente y un workspace admite un solo escritor. Por eso la API encola en vez de ejecutar.
  - El 6 (escritura atómica) rige el fichero de solicitud: `.tmp` y renombrado.
  - El 5 (el contexto vive en disco) es lo que permite que API y supervisor se coordinen sin hablarse.
- **Restricciones técnicas**: sin SDK de proveedores; FastAPI no invoca modelos ni lanza `claude`; la cuota es la suscripción personal de quien arranca el supervisor.
- **Supuestos**: hay un único operador en una única máquina, y el navegador y el supervisor corren en esa máquina. Si este supuesto cae, la spec se revisa entera: multiusuario exige autenticación y atribución de cuota, que están fuera de alcance.
- **Dependencias**: ninguna. `filelock` ya está en el stack.

## 5. Propuesta

Tres piezas que no se conocen entre sí. Se coordinan por un directorio.

### 5.1 La cola

Un directorio nuevo, fuera de cualquier workspace de novela:

```
novelas/_cola/
├── pendientes/          <marca-de-tiempo>-<slug>.json
├── en-curso/            <slug>.json
├── hechas/              <slug>.json
├── supervisor.lock
└── supervisor.latido
```

El prefijo `_` no puede aparecer en un slug válido (RNF-07), así que `_cola` no colisiona con ninguna novela y la regla «`novelas/<slug>/` lo toca solo el CLI» se mantiene por construcción, no por disciplina.

### 5.2 La API encola

`POST /cola` recibe una `SolicitudNovela` —`slug`, `idea`, `num_capitulos`, `palabras_objetivo`—, la valida y la escribe en `pendientes/` de forma atómica. Devuelve `202` y el identificador de la solicitud. No crea el workspace, no escribe `config.yaml`, no lanza nada.

Rechaza con `409` si el slug ya existe en `novelas/` o ya está encolado, y con `429` si hay más de diez solicitudes pendientes. Este último tope no es cortesía: cada solicitud aceptada acabará gastando cuota, y un formulario con un botón que se deja pulsar cincuenta veces es una factura.

### 5.3 El supervisor consume

Dos subcomandos deterministas en el CLI:

- `novela cola tomar` — toma el fichero pendiente más antiguo, lo mueve a `en-curso/` con un renombrado, e imprime el slug. Sale con código 1 si la cola está vacía. Toma el lock de `supervisor.lock`, de modo que dos supervisores a la vez no se pisan.
- `novela cola cerrar <slug> --estado ok|error` — mueve la solicitud a `hechas/` anotando el desenlace.

Y el supervisor, que es shell y no Python a propósito:

```bash
#!/usr/bin/env bash
# Vacía la cola del panel. Un supervisor por máquina.
set -u
while true; do
  slug=$(novela cola tomar) || { sleep 5; touch novelas/_cola/supervisor.latido; continue; }
  touch novelas/_cola/supervisor.latido
  if claude -p "/novela-nueva $slug"; then
    while novela pendiente "$slug"; do
      claude -p "/novela-continuar $slug --capitulos 1" || break
      touch novelas/_cola/supervisor.latido
    done
    novela cola cerrar "$slug" --estado ok
  else
    novela cola cerrar "$slug" --estado error
  fi
done
```

Es el bucle desatendido de `architecture.md` §2.3 con una fuente de trabajo delante. El `|| break` sigue significando lo mismo: ante un error se para y queda el checkpoint.

**Por qué shell y no un subcomando de Python.** Porque `architecture.md` §2.1 dice que orquesta la sesión de Claude Code y no un proceso Python, y conviene no erosionar eso. El supervisor no orquesta: no decide qué paso viene después de un gate, ni interpreta un informe de QA, ni elige entre reintentar y parar. Solo decide **qué novela empieza ahora**, que es planificación de trabajos, no de narrativa. Mantenerlo en quince líneas de shell hace esa frontera visible; meterlo en el CLI la borraría y la siguiente persona añadiría ahí la lógica del bucle.

### 5.4 El arranque lee la solicitud

`/novela-nueva <slug>`, cuando existe `novelas/_cola/en-curso/<slug>.json`, toma de ahí la idea y los parámetros. Cuando no, los toma de sus flags, como hoy. En ambos casos `config.yaml` lo escribe el mismo código Python a partir del mismo modelo Pydantic.

Esto resuelve de paso la ambigüedad de §2: el frontend deja de generar `config.yaml`. Genera una solicitud; `config.yaml` siempre lo escribe el backend.

### 5.5 Un solo comando de arranque

El modo de fallo más probable de todo lo anterior no es que el supervisor se caiga: es que nadie lo arranque. Son dos procesos —`uvicorn` y `supervisor.sh`— y basta con levantar solo el primero para que el panel funcione, el formulario funcione, la solicitud se encole y no pase nada nunca.

La solución no es detectar esa situación y ofrecer una alternativa. Es que la situación no exista:

```bash
cd backend && ./run.sh     # API y supervisor, juntos
```

`run.sh` levanta los dos y se lleva los dos por delante al terminar. Si el panel está servido, hay alguien ejecutando. No hay estado intermedio que explicar al usuario ni que documentar.

Ofrecer en el panel «no hay supervisor, copia este comando» sería conservar un segundo procedimiento de arranque —el que esta spec existe para eliminar—, y además hacerlo aparecer en el peor momento posible: la primera vez que alguien usa el sistema. Un camino alternativo visible se acaba usando, y entonces hay dos formas de arrancar una novela que mantener.

Que dos supervisores coincidan no necesita tratamiento especial: `supervisor.lock` (§5.3) hace que el segundo no tome nada.

**El latido sigue existiendo, pero como diagnóstico, no como bifurcación.** El supervisor toca `supervisor.latido` en cada vuelta y `GET /cola` informa de si es reciente. Si deja de serlo —el supervisor se colgó o murió a media faena— el panel muestra un aviso de avería: «el supervisor no responde, reinicia el backend». Es un estado roto que se arregla, no un modo de trabajo que se aprende.

## 6. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| RF-01 | `POST /cola` valida la solicitud y escribe `novelas/_cola/pendientes/<ts>-<slug>.json` de forma atómica; devuelve `202` y el identificador | debe |
| RF-02 | La API no escribe en ninguna ruta fuera de `novelas/_cola/` | debe |
| RF-03 | `POST /cola` devuelve `409` si el slug ya existe como novela o ya está encolado | debe |
| RF-04 | `POST /cola` devuelve `429` si hay diez o más solicitudes pendientes | debe |
| RF-05 | `novela cola tomar` mueve la solicitud más antigua a `en-curso/`, imprime su slug y sale 0; con la cola vacía no mueve nada y sale 1 | debe |
| RF-06 | `novela cola tomar` toma un lock exclusivo: dos invocaciones simultáneas nunca devuelven el mismo slug | debe |
| RF-07 | `novela cola cerrar <slug> --estado ok\|error` mueve la solicitud a `hechas/` con el desenlace anotado | debe |
| RF-08 | `/novela-nueva <slug>` toma los parámetros de `en-curso/<slug>.json` si existe, y de sus flags si no; `config.yaml` lo escribe el backend en ambos casos | debe |
| RF-09 | `GET /cola` devuelve las solicitudes pendientes y si el latido del supervisor es reciente | debe |
| RF-10 | `backend/run.sh` arranca la API y el supervisor, y al terminar detiene ambos | debe |
| RF-11 | El formulario del panel encola siempre. Si el latido está caducado, el panel muestra además un aviso de avería; en ningún caso ofrece un comando para copiar | debería |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-03 | Coste / cuota | La API no gasta cuota. Cada solicitud aceptada gastará la de quien arrancó el supervisor: de ahí el tope de RF-04 |
| RNF-04 | Fiabilidad | Una solicitud a medio escribir nunca es visible para `cola tomar`: se escribe en `.tmp` y se renombra. Si el supervisor muere con una solicitud en `en-curso/`, queda ahí; al relanzarlo se retoma ese slug antes de mirar `pendientes/` |
| RNF-06 | Compatibilidad | Aditivo. `/novela-nueva` con flags sigue funcionando igual y sin cola |
| RNF-07 | Seguridad | El servicio se sirve solo en `127.0.0.1`. `slug` valida contra `^[a-z0-9][a-z0-9-]{0,63}$` antes de componer ninguna ruta, lo que excluye `..`, separadores y el prefijo `_` de `_cola`. `idea` tiene tope de 2.000 caracteres; `num_capitulos` entre 1 y 200; `palabras_objetivo` entre 1.000 y 500.000 |

`slug` es el campo delicado: entra en el nombre de un fichero y después en una ruta de workspace. Se valida en el modelo Pydantic, no en el manejador, para que no haya forma de llegar al disco sin pasar por ahí.

## 8. Interfaces y contratos

**API** — dos rutas **nuevas**. `POST /cola` es la primera escritura de la API y por tanto una **ruptura de convención**, no de contrato: nada de lo existente cambia, pero la frase «la API no escribe» deja de ser cierta (ver §14).

```
POST /cola
     body → SolicitudNovela {slug, idea, num_capitulos, palabras_objetivo}
     202  → {"solicitud_id": str, "posicion": int}
     409  → slug ya existente o ya encolado
     422  → validación
     429  → cola llena

GET  /cola
     200  → {"pendientes": [SolicitudEncolada], "supervisor_vivo": bool}
```

**CLI** — dos subcomandos **nuevos**:

```
novela cola tomar              → imprime el slug; 0 si tomó algo, 1 si la cola está vacía
novela cola cerrar <slug> --estado ok|error   → 0
```

**Puesta en marcha** — `backend/run.sh` es **nuevo** y pasa a ser el comando de arranque documentado. `uv run uvicorn api.main:app --reload` sigue funcionando y levanta solo la API: queda como lo que se usa para trabajar en los endpoints, no para operar el sistema.

**Ficheros del workspace** — un directorio **nuevo**, `novelas/_cola/`, con la estructura de §5.1. Ningún cambio dentro de `novelas/<slug>/` salvo que `config.yaml` puede originarse ahora en una solicitud encolada.

**Esquemas** — `SolicitudNovela` y `SolicitudEncolada` en `backend/novela/models/`, exportadas a `backend/schemas/`.

**Contrato de agente** — sin cambios. Ningún agente ve la cola.

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | Sin cambios |
| `plan/` | Sin cambios |
| `estado/estado.db` | Sin cambios. La cola no es estado narrativo y no entra en la base |
| `memoria/` | Sin cambios |

La cola es una quinta cosa que no pertenece a las cuatro ramas de contexto: no es canon, ni plan, ni lo ocurrido, ni un resumen. Es trabajo pendiente del harness, del mismo orden que `runs/`. Vive fuera de los workspaces precisamente para que nadie la confunda con estado de una novela.

## 10. Migración y compatibilidad

No aplica a novelas existentes: ninguna cambia. El directorio `novelas/_cola/` se crea al vuelo la primera vez que se encola.

Revertir es borrar los dos endpoints, los dos subcomandos, el script y el cambio del formulario. Nada del bucle por capítulo depende de esto.

## 11. Criterios de aceptación

- [ ] **CA-01** (RF-01) `POST /cola` con una solicitud válida devuelve `202` y deja exactamente un fichero en `pendientes/`.
- [ ] **CA-02** (RF-01, RNF-04) Un fallo a mitad de escritura no deja ningún fichero visible en `pendientes/`; el `.tmp` no lo ve `cola tomar`.
- [ ] **CA-03** (RF-02) Tras ejercitar toda la API, ningún fichero bajo `novelas/<slug>/` ha cambiado de contenido ni de fecha de modificación.
- [ ] **CA-04** (RF-03) Encolar un slug que ya existe como directorio de novela devuelve `409`. Encolarlo dos veces seguidas devuelve `409` la segunda.
- [ ] **CA-05** (RF-04) La undécima solicitud pendiente devuelve `429`.
- [ ] **CA-06** (RNF-07) Un slug con `..`, con `/`, con `\`, con byte nulo o empezando por `_` devuelve `422` y no crea ningún fichero.
- [ ] **CA-07** (RF-05) Con tres solicitudes encoladas, tres `cola tomar` consecutivos devuelven los tres slugs en orden de encolado y el cuarto sale con código 1.
- [ ] **CA-08** (RF-06) Veinte `cola tomar` en paralelo sobre una cola de cinco devuelven cinco slugs distintos y quince salidas con código 1. Ninguna solicitud se pierde ni se duplica.
- [ ] **CA-09** (RF-07) `cola cerrar` deja la solicitud en `hechas/` con el estado, y `en-curso/` vacío.
- [ ] **CA-10** (RF-08) `novela nueva` produce el mismo `config.yaml` byte a byte desde una solicitud encolada y desde los flags equivalentes.
- [ ] **CA-11** (RF-09) Sin latido, o con un latido de hace más de un minuto, `GET /cola` devuelve `supervisor_vivo: false`.
- [ ] **CA-12** (RNF-04) Con una solicitud en `en-curso/` y el supervisor recién arrancado, el primer `cola tomar` devuelve ese slug y no toca `pendientes/`.
- [ ] **CA-13** (RF-10) `run.sh` deja la API respondiendo y el latido fresco. Al interrumpirlo, ninguno de los dos procesos sobrevive.
- [ ] **CA-14** (RF-11) Con `supervisor_vivo: false`, el formulario sigue permitiendo encolar y en ninguna rama del panel aparece un comando para copiar.

## 12. Trazabilidad

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 | CA-01, CA-02 | `backend/tests/test_api_cola.py::test_encola_atomico` | pendiente |
| RF-02 | CA-03 | `backend/tests/test_api_cola.py::test_api_no_toca_workspaces` | pendiente |
| RF-03 | CA-04 | `backend/tests/test_api_cola.py::test_slug_duplicado` | pendiente |
| RF-04 | CA-05 | `backend/tests/test_api_cola.py::test_tope_de_cola` | pendiente |
| RF-05 | CA-07 | `backend/tests/test_cola.py::test_tomar_orden_y_cola_vacia` | pendiente |
| RF-06 | CA-08 | `backend/tests/test_cola.py::test_tomar_concurrente` | pendiente |
| RF-07 | CA-09 | `backend/tests/test_cola.py::test_cerrar` | pendiente |
| RF-08 | CA-10 | `backend/tests/test_nueva.py::test_config_equivalente` | pendiente |
| RF-09 | CA-11 | `backend/tests/test_api_cola.py::test_latido_caducado` | pendiente |
| RF-10 | CA-13 | `backend/tests/test_arranque.py::test_run_sh_levanta_ambos` | pendiente |
| RF-11 | CA-14 | `frontend/` — prueba de componente del formulario | pendiente |
| RNF-04 | CA-12 | `backend/tests/test_cola.py::test_retoma_en_curso` | pendiente |
| RNF-07 | CA-06 | `backend/tests/test_api_cola.py::test_slug_no_escapa` | pendiente |

## 13. Verificación

- No se toca `validate.py` ni `delta.py`. Los tests son de ejemplo salvo los dos siguientes.
- **CA-08 es property-based.** La exclusión mutua de `cola tomar` es exactamente el tipo de cosa que un ejemplo no cubre: la propiedad es que para cualquier número de consumidores y cualquier cola inicial, la unión de lo devuelto es la cola entera y las intersecciones son vacías.
- **CA-06 también.** Se genera el slug, no se enumeran tres casos malos a mano.
- **El cuerpo del supervisor no tiene test.** Invoca `claude` y por tanto gasta cuota: ningún test del proyecto llama a un modelo. Lo que sí se prueba es todo aquello sobre lo que se apoya —`cola tomar`, `cola cerrar`, `pendiente`— de modo que lo que queda sin cubrir son quince líneas de pegamento.
- **CA-13 sí es automatizable, y conviene no confundirlo con lo anterior.** Con la cola vacía, el supervisor da vueltas sin llegar a invocar `claude` nunca: solo consulta, duerme y toca el latido. La prueba levanta `run.sh`, comprueba que la API responde y que el latido se refresca, y lo interrumpe. Cero cuota. Es una prueba de humo lenta y dependiente del sistema operativo, y como tal va marcada, no en la suite rápida.
- **Riesgos aceptados**:
  1. El cuerpo del supervisor sin cobertura, por lo anterior.
  2. El latido detecta un supervisor muerto, no uno atascado. Un supervisor colgado dentro de `claude -p` sigue latiendo si la vuelta anterior lo tocó, y el panel lo dará por vivo. Lo mitiga en parte la spec 0003: el log del run sí revela si hay avance.
  3. Sin autenticación. Todo lo que pueda llegar a `127.0.0.1` puede gastar la cuota del operador. Aceptable bajo el supuesto de máquina única de §4; si ese supuesto cae, esto es lo primero que hay que resolver.
  4. `run.sh` es shell, y en Windows depende de Git Bash. Si eso estorba, la salida es un `run.ps1` hermano, no meter la gestión de procesos en Python.

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | Ninguno de los ocho se rompe. El 8 es el que **obliga** a este diseño: la cola existe porque un workspace admite un solo escritor |
| Convenciones | **Cambian dos frases.** `AGENTS.md` («La API **no escribe**. No hay `POST` que mute una novela») y `architecture.md` §11.1 («La API no lanza agentes ni escribe en el workspace») pasan a decir que la API no muta una novela y que su única escritura es encolar una solicitud. La regla de fondo —mutar una novela es trabajo del CLI— no cambia |
| Esquemas | `SolicitudNovela` y `SolicitudEncolada`: regenerar `backend/schemas/` y añadirlas a `docs/definitions.md` en el commit de implementación |
| Contratos de agente | Ninguno |
| Docs de referencia | `architecture.md` §4 (estructura, por `novelas/_cola/`), §8 (ciclo de vida, por los subcomandos), §11.1 y §11.2, y la línea de arranque de §11.1 que hoy dice `uvicorn`. `AGENTS.md`, apartado «Proceso: ejecución», por el mismo motivo. `camino.md`, porque el salto manual desaparece del camino |
| Frontend | El formulario cambia de comportamiento; lo demás sigue igual |

## 15. Alternativas descartadas

- **`POST` que lanza `claude -p` y espera.** Una petición HTTP de varios minutos, con un proceso hijo por petición y sin control de concurrencia contra `state.lock`. El primer usuario impaciente que recarga la página arranca un segundo proceso sobre el mismo workspace.
- **`POST` que devuelve `202` y un job id, con gestor de trabajos en Python.** Es la cola de esta spec, pero con reintentos, estados, persistencia y cancelación construidos a mano. Un directorio con tres carpetas y un renombrado atómico hace el trabajo; el sistema de ficheros ya es la cola.
- **Celery, RQ, Redis, APScheduler.** Una dependencia y un servicio más para una cola de como mucho diez elementos en una sola máquina.
- **Supervisor como subcomando del CLI (`novela supervisor`).** Pondría en Python la decisión de qué se ejecuta, que es justo la frontera que `architecture.md` §2.1 traza entre la sesión de Claude Code y el código determinista. Ver §5.3.
- **Un hook de Claude Code que vigile la cola.** Los hooks se disparan por eventos de una sesión; aquí no hay sesión hasta que alguien la arranca. El huevo y la gallina.
- **Dejar el supervisor como proceso aparte y avisar en el panel cuando no esté.** Era la propuesta de la versión 0.1 de esta spec. Se descarta porque el aviso tenía que ofrecer una salida —el comando para copiar— y eso es un segundo camino de arranque: precisamente lo que la spec elimina, reapareciendo en el primer uso del sistema. Arrancar los dos juntos borra el problema en vez de señalizarlo.
- **Que la API arranque el supervisor al recibir la primera solicitud.** Cero configuración, y `supervisor.lock` haría inofensivo el arranque doble. Se descarta por dos motivos: le da a FastAPI la capacidad de lanzar procesos que gastan cuota, y con `--reload` cada fichero guardado durante el desarrollo deja un supervisor huérfano.
- **Un servicio del sistema (systemd, launchd, Task Scheduler).** Es la respuesta correcta para una instalación permanente y desatendida. Sobra en una máquina de trabajo, y obliga a mantener tres recetas de arranque distintas en lugar de un script.
- **Dejarlo como está y asumir el copy-paste.** Es lo que recomendaba el análisis previo para un operador único, y sigue siendo defendible: el pegado cuesta cinco segundos una vez por novela. Se descarta porque el coste de esta spec es acotado —dos endpoints, dos subcomandos, quince líneas de shell— y elimina la única costura manual del diseño.

## 16. Preguntas abiertas

- [ ] ¿La cola vive en `novelas/_cola/` o en un `cola/` en la raíz del repo? Dentro de `novelas/` hereda el `.gitignore` y queda junto a los datos, que es donde pertenece; en la raíz se lee mejor. Hoy la spec propone lo primero — arturo.soto
- [ ] ¿Un minuto es el umbral correcto para dar por muerto el latido? Depende de cuánto tarda una vuelta del bucle interior, que hoy nadie ha medido. Desde la versión 0.2 el latido solo enciende un aviso de avería, así que un umbral mal elegido molesta pero no bloquea a nadie — arturo.soto
- [ ] Si el supuesto de máquina única cae, ¿autenticación en la API o se deja detrás de un proxy? No bloquea esta spec, pero decide si `POST /cola` acaba necesitando un modelo de usuario — arturo.soto

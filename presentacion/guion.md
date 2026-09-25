# Guion del presentador

Un bloque por diapositiva, en el orden de [`deck/deck.json`](deck/deck.json). Los tiempos son orientativos: el cuerpo principal dura unos 15 minutos y el vídeo de la demo, 3:26 más. Los anexos no se presentan; se usan para responder preguntas.
---

## 1 · Portada (≈30 s)

«Buenos días. Soy Arturo Soto, de Qaracter, y os presento Story Maker a Cuentalia Regalos, una cadena de tiendas de regalo. Aclaro desde el principio que es un cliente ficticio. La idea es sencilla: vender con vosotros una novela de suspense única para cada cliente, escrita para una persona concreta, que llega como un libro de regalo. Sirve para una jubilación, una boda, un aniversario o el cumpleaños de un hijo.»

## 2 · Problema y cliente (≈60 s)

«¿Quién compra? Alguien que busca un regalo con significado para una ocasión. Hoy tiene tres opciones y ninguna le sirve.
El libro de plantilla es barato, pero solo cambia el nombre en una historia fija y no cuenta nada de la persona.
El escritor por encargo sí es personal, pero cuesta cientos de euros y tarda semanas.
Un chat de IA es rápido, pero se contradice entre capítulos, no garantiza lo que pidió el cliente y no protege sus datos.
Story Maker ocupa el hueco que queda: diez capítulos con los recuerdos de esa persona, verificados por programa, en unas horas y por menos de 80 euros.»

## 3 · Configuración y lectura (≈75 s)

«El recorrido del cliente tiene tres pasos.
Primero, **configurar**. Un entrevistador recoge nombre, edad, rasgos, recuerdos, género, tono, extensión y temas prohibidos. Detecta lo que falta y las contradicciones; por ejemplo, un niño de 7 años con tono noir. Si el cliente pega una carta o una anécdota, la tratamos como texto no confiable: ningún dato entra en el brief sin una cita literal de su fuente. Lo que sale es un brief validado con un schema.
Segundo, **leer**. El libro llega como PDF interactivo, con portada y dedicatoria, índice navegable y una ficha de personajes y lugares que enlaza el capítulo de cada aparición. Además hay una lectura web en el panel.
Tercero, **corregir**. Si el cliente quiere cambiar un hecho, lo pide. El sistema sabe qué capítulos usan ese hecho y regenera solo esos. Se entrega un PDF v2 con una página de novedades, y la versión 1 se conserva intacta.»

## 4 · Arquitectura del harness (≈75 s)

«Por dentro trabajan nueve roles, un orquestador y un CLI que es el que decide.
Los roles se agrupan por función: un entrevistador que configura, arquitecto y trazador que planifican, el escritor, cuatro críticos (continuista, editor de estilo, lector de suspense y juez) y un cronista que mantiene la memoria.
¿Por qué varios agentes? Porque cada rol ve solo lo que necesita. El escritor nunca lee la solución del misterio y el continuista sí.
Hay tres ideas clave. El contexto vive en disco: cada rol recibe un briefing a medida, de 100.000 tokens como máximo, y nada de la conversación. La story bible es una base SQLite con hechos append-only, cronología y apariciones. Y todo lo determinista lo hace el CLI `novela`, sin modelos: validar, aplicar deltas, guardrails, Lean y exportar. Así, un fallo de un modelo nunca decide por sí solo si un capítulo se acepta.»

## 5 · El bucle por capítulo (≈75 s)

«Así se escribe cada capítulo. Se genera el briefing y escribe el escritor. Un hook comprueba enseguida la longitud, el esquema, las pistas, los nombres y las palabras prohibidas. Después revisan el continuista, el editor de estilo y el lector de suspense. Se vuelve a validar, porque el editor ha reescrito el texto. El cronista extrae el delta de estado y el checkpoint cierra el capítulo.
Cada gate tiene dos reintentos. Al tercer fallo, el sistema escribe una petición de intervención y se para. Luego se reanuda desde el checkpoint sin duplicar ni perder capítulos.
En la novela de ejemplo, el hook de longitud saltó 11 veces y el escritor se corrigió todas ellas. Hubo tres intervenciones humanas en diez capítulos, y en las tres el sistema paró donde debía: un personaje sin ficha, una ficha que contradecía el canon y un error de ruta en el gate de Lean.»

## 6 · Cuatro tipos de validador (≈60 s)

«Validamos en cuatro capas, cada una en su punto.
Los **programáticos** son gratis y van primero: schema, longitud, nombres, cobertura del brief, palabras prohibidas y validación visual con Playwright. Detectan lo que no merece una llamada a un modelo.
Los **semánticos** son un juez LLM con una rúbrica versionada (continuidad, tono, arco, personajes, ritmo y personalización) y una revisión humana con la misma rúbrica.
El **formal de la historia** es Lean 4: cuatro invariantes sobre la cronología, con demostración general.
El **formal del sistema** es TLA+, que verifica el propio harness en desarrollo, no cada novela.
Cada resultado llega a Langfuse como score.»

## 7 · Cinco briefs (≈75 s)

«Probamos cinco briefs. La tabla se lee por columnas: cada brief avanza hasta el primer validador que lo para.
B1, la novela completa, pasa todo y el juez le da un 4,83 sobre 5.
B5, un brief con contradicciones, se para en la entrada con seis hallazgos.
B4, con recuerdos temporalmente imposibles, lo rechaza el arquitecto.
Lo más interesante es B3, el adversarial. La inyección no cambió ni la edad ni el tono, y tampoco coló el tema prohibido. Pero destapó otra cosa: el continuista copiaba el misterio en su informe, y ese informe lo lee después el escritor. Hoy lo para un hook determinista.
Cada fallo terminó en un cambio del harness.»

## 8 · Lo que solo ve Lean (≈60 s)

«Este caso lo preparamos a propósito. En el capítulo 2, Tomás se marcha en el ferry para siempre. En el 3 vuelve a estar en el faro. Además, un personaje lo recuerda en el puerto a una hora a la que el capítulo 1 lo tenía en el faro.
Cada capítulo es coherente por separado, así que ni los validadores programáticos ni la auditoría lo detectan: todos dan cero. Lean sí, y señala los dos eventos exactos.
Sobre la novela real, Lean demostró los 4 invariantes en los 32 eventos y no encontró nada, porque el escritor y el trazador ya habían corregido las incoherencias. Lo contamos tal cual. Si Lean falla, la versión no se publica.»

## 9 · TLC, 281.824 estados (≈60 s)

«TLA+ modela el flujo como una máquina de estados, y TLC recorre 281.824 estados en unos 40 segundos. Verifica, entre otras cosas, que nunca se cierra un capítulo sin validar, que solo se publica un libro completo y auditado, que reanudar no duplica ni pierde capítulos y que toda generación termina publicando o deteniéndose.
Encontró un bug real antes de que afectara a una novela: una exportación antigua hacía pasar por publicada una versión que no había superado la auditoría. Ya está arreglado. Otro hallazgo, la cuenta de reintentos, está documentado.
Y para comprobar que la especificación sirve, cinco mutantes desactivan guardas reales, y TLC encuentra el contraejemplo de cada uno en 3 o 4 segundos.»

## 10 · Tuning del cronista (≈60 s)

«El gate que más reintentos gastaba era aplicar-delta: una sola cita no literal rechaza el delta entero.
Con el prompt v1 en Haiku, el 35 % de las citas no eran literales y la novela necesitaba 2,5 intentos por capítulo. Con el prompt v2 en Sonnet, el 0 %, con 1,1 intentos.
Fue un A/B sobre el mismo capítulo, con tres ejecuciones por variante. Una variante con más reglas empeoró hasta el 39 % y la descartamos. El cambio de modelo fue lo que lo resolvió; el prompt solo lo mejoró. Cuesta 40 céntimos más por capítulo, a cambio de menos reintentos y ninguna intervención.»

## 11 · Langfuse (≈60 s)

«Cada novela es una sesión en Langfuse. La de ejemplo costó 24,52 dólares en 511 llamadas y dos horas y media de modelo. Estos números salen de Langfuse con `novela costes`; no son una estimación.
Cada rol y cada tool son un span con nombre, y todos los validadores emiten su score.
Se ve que el capítulo más caro es el que tuvo reintentos. Y un dato que nos marca la siguiente optimización: el orquestador supone el 28 % del coste, tanto como el escritor. La revisión v2 costó 11,71 dólares.»

## 12 · Guardrails (≈60 s)

«Lo que el cliente no quiere leer no se publica.
Las palabras prohibidas funcionan en tres niveles: global, del cliente (por ejemplo, "que no salga este nombre") y de la novela. Normalizamos mayúsculas, acentos, plurales, género y diminutivos. Cuando hay una coincidencia, el capítulo vuelve al escritor con el término y la línea.
Contra la inyección, el texto libre se marca como no confiable y cada dato cita su fuente.
En datos personales, guardamos solo lo imprescindible, la entrevista no se traza y cada rol lee solo su novela.
Todo queda en un audit log append-only.
Un apunte honesto: en la novela de ejemplo no hubo ninguna coincidencia, así que el ejemplo de detección de la diapositiva viene de los tests.»

## 13 · Presupuesto (≈60 s)

«79 euros por novela, con un margen del 40 %. Con 200 novelas al mes, el coste unitario es de 47,69 euros. Los tokens son reales, medidos por Langfuse: 22,56 euros la novela y 10,77 una revisión media. Esa revisión es una cota alta, porque incluye reintentos de dos bugs ya arreglados.
La revisión editorial humana de 20 minutos es una decisión de producto: es un regalo, y alguien lo hojea antes de enviarlo.
El proyecto de desarrollo cuesta 26.950 euros: 490 horas a 55 euros la hora. Los supuestos están declarados y un script los recalcula.»

## 14 · Volumen y sensibilidad (≈60 s)

«La escala mejora poco el margen, porque la infraestructura es casi fija y el coste lo dominan los tokens y la revisión humana: con 50 novelas al mes el margen es del 37,7 % y con 1.000, del 39,8 %.
Lo que importa es la sensibilidad. Si los tokens suben un 50 %, el margen baja al 18,5 % pero sigue siendo positivo. Si un cliente usa las tres revisiones incluidas, se queda en el 12 %. Una cuarta revisión gratis lo deja en negativo, así que a partir de la cuarta se cobran a 15 euros cada una.»

## 15 · Demo (≈45 s + vídeo de 3:26)

«Vamos a verlo. El cliente nos dice que la carta la guardaba en el cajón del mostrador de préstamos, no en casa. Una orden de simulación nos enseña qué capítulos usan ese hecho: 3 de 10. Al confirmar, la versión 1 queda guardada intacta y solo se regeneran esos tres capítulos, con los mismos gates que la primera vez, Lean incluido: 4 de 4 sobre 39 eventos, juez 4,67 y 11,71 dólares. El PDF nuevo abre con una página de novedades que enlaza cada capítulo cambiado.»

→ Reproduce [`demo.webm`](demo.webm). Sus tramos: brief (0:07), panel (0:39), cambio (1:47), PDF v2 (2:13), Langfuse (2:32), Lean y TLC (2:51).

## 16 · Riesgos y siguientes pasos (≈60 s)

«El riesgo principal no es técnico. Con datos reales de una persona hacen falta consentimiento y un entorno con una política RGPD pactada. El harness ya minimiza lo que guarda y lo que traza.
Otros riesgos: tres intervenciones en diez capítulos, todas justificadas; un coste sensible al precio de los tokens; y un juez que todavía no está calibrado contra la revisión humana.
Proponemos un piloto de 50 novelas con Cuentalia, la revisión humana de cinco de ellas para calibrar el juez, reducir el coste del orquestador y arreglar la cuenta de reintentos con su spec.»

## 17 · Contraportada (≈15 s)

«Gracias. Tenemos cinco minutos para preguntas técnicas.»

---

## Anexos: solo para preguntas

| Si te preguntan… | Diapositiva | Qué decir en una frase |
|---|---|---|
| «¿Cómo encaja todo?» | A1 Arquitectura | Claude Code orquesta, los hooks vigilan, el CLI hace todo lo determinista, y la lectura (API, panel y MCP) no escribe salvo `request_change` con confirmación. |
| «¿Qué modela TLA+ exactamente?» | A2 Máquina | Cinco estados, de la configuración a la publicación, y cada transición mapeada a su paso del código. |
| «¿Y la nota del juez?» | A3 Evals | 4,83 de media, con continuidad a 4. La revisión humana está preparada, pero todavía no la ha hecho nadie. |
| «¿Qué guarda la story bible?» | A4 SQLite | Hechos, conocimiento y auditoría append-only con triggers; solo escribe `aplicar-delta`. |
| «¿Por qué ese modelo en cada rol?» | A5 Coste por rol | Opus donde manda la calidad (escritor, arquitecto, orquestador), Haiku en revisiones acotadas y Sonnet en el cronista y el juez. |
| «¿Lo habéis atacado?» | A6 Red-team | Inyecciones, lecturas cruzadas entre novelas, fugas del misterio y escrituras en el estado: cada caso tiene quién lo paró y cómo. |

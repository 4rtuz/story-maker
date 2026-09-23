---
schema_version: 1.0.0
agente: escritor
capitulo: 8
run_id: r-20260923-1000
presupuesto_tokens: 60000
tokens_estimados: 2391
degradacion: []
---
## permanente · canon/premisa.md

---
logline: Una farera vuelve al pueblo donde el faro se apagó la noche del naufragio.
pregunta_dramatica: ¿Podrá Elena seguir en el pueblo cuando sepa quién fue?
tema: la culpa heredada
promesa_al_lector: un culpable que estuvo siempre a la vista
---
La premisa de la novela sintética.

## permanente · canon/mundo.md

---
escenarios:
- id: esc-casa-del-faro
  nombre: La casa del faro
  descripcion: La casa del faro en la novela sintética
  detalle_sensorial: olor a sal
  quien_tiene_acceso:
  - per-elena-vidal
  - per-tomas-reyes
- id: esc-puerto
  nombre: El puerto
  descripcion: El puerto en la novela sintética
  detalle_sensorial: olor a sal
  quien_tiene_acceso:
  - per-elena-vidal
  - per-tomas-reyes
- id: esc-archivo
  nombre: El archivo
  descripcion: El archivo en la novela sintética
  detalle_sensorial: olor a sal
  quien_tiene_acceso:
  - per-elena-vidal
  - per-tomas-reyes
epoca_y_tecnologia:
  epoca: '1998'
  existe:
  - teléfono fijo
  no_existe:
  - móvil
reglas_del_mundo:
- El faro solo se enciende desde la linterna.
instituciones:
- nombre: Guardia Civil
  procedimientos: Tarda dos horas en llegar.
---
Un pueblo de costa con un faro apagado.

## permanente · canon/estilo.md

---
guia_de_voz_narrativa: Frases cortas, sin adjetivos de relleno.
ritmo:
  longitud_media_frase: 12.0
  proporcion_dialogo: 0.3
  proporcion_accion: 0.4
  proporcion_interioridad: 0.3
prohibiciones:
- de repente
- sin previo aviso
parrafos_canonicos:
- Elena no encendió la luz. Conocía la escalera de memoria.
convenciones_formato:
  separador_escena: '***'
---
Seco y exacto.

## personajes · per-elena-vidal

---
identidad:
  id: per-elena-vidal
  nombre: Elena Vidal
  alias: []
  edad: 40
  rol_narrativo: protagonista
fisico:
  pelo: gris
voz:
  idiolecto: seco
  registro: llano
  dialogo_canonico:
  - No le pregunté nada.
psicologia:
  deseo: Elena Vidal quiere irse
  necesidad: quedarse
  miedo: el agua
  herida: el hermano
coartada_y_cronologia_privada:
- momento: dia 1, 23:10
  ubicacion: esc-casa-del-faro
  detalle: Elena Vidal sube al faro
---
Elena Vidal es personaje de la novela sintética.

## personajes · per-tomas-reyes

---
identidad:
  id: per-tomas-reyes
  nombre: Tomás Reyes
  alias: []
  edad: 40
  rol_narrativo: antagonista
fisico:
  pelo: gris
voz:
  idiolecto: seco
  registro: llano
  dialogo_canonico:
  - Eso fue hace mucho.
psicologia:
  deseo: Tomás Reyes quiere irse
  necesidad: quedarse
  miedo: el agua
  herida: el hermano
coartada_y_cronologia_privada:
- momento: dia 1, 23:10
  ubicacion: esc-casa-del-faro
  detalle: Tomás Reyes sube al faro
secreto:
  que_oculta: Debe dinero a la cofradía.
  a_quien:
  - per-elena-vidal
---
Tomás Reyes es personaje de la novela sintética.

## personajes · per-ines-mar

---
identidad:
  id: per-ines-mar
  nombre: Inés Mar
  alias: []
  edad: 40
  rol_narrativo: testigo
fisico:
  pelo: gris
voz:
  idiolecto: seco
  registro: llano
  dialogo_canonico:
  - Yo cerré a las once.
psicologia:
  deseo: Inés Mar quiere irse
  necesidad: quedarse
  miedo: el agua
  herida: el hermano
coartada_y_cronologia_privada:
- momento: dia 1, 23:10
  ubicacion: esc-casa-del-faro
  detalle: Inés Mar sube al faro
secreto:
  que_oculta: Vio luz en el cabo aquella noche.
  a_quien:
  - per-elena-vidal
---
Inés Mar es personaje de la novela sintética.

## estado · personajes

```yaml
per-elena-vidal:
  ubicacion: esc-puerto
  estado_fisico: cansada
  estado_emocional: alerta
  condicion: viva
  objetivo_activo: saber quién apagó el faro
  ultima_aparicion: 7
per-tomas-reyes:
  ubicacion: esc-casa-del-faro
  estado_fisico: bien
  estado_emocional: nervioso
  condicion: viva
  objetivo_activo: que nadie suba a la linterna
  ultima_aparicion: 7
```

## estado · conocimiento

```yaml
per-elena-vidal:
- hecho: hec-001
  desde_capitulo: 1
  cita: En la noche 1 Elena comprobó que la puerta de la linterna seguía forzada.
- hecho: hec-002
  desde_capitulo: 2
  cita: En la noche 2 Elena comprobó que la puerta de la linterna seguía forzada.
- hecho: hec-003
  desde_capitulo: 3
  cita: En la noche 3 Elena comprobó que la puerta de la linterna seguía forzada.
- hecho: hec-004
  desde_capitulo: 4
  cita: En la noche 4 Elena comprobó que la puerta de la linterna seguía forzada.
- hecho: hec-005
  desde_capitulo: 5
  cita: En la noche 5 Elena comprobó que la puerta de la linterna seguía forzada.
- hecho: hec-006
  desde_capitulo: 6
  cita: En la noche 6 Elena comprobó que la puerta de la linterna seguía forzada.
- hecho: hec-007
  desde_capitulo: 7
  cita: En la noche 7 Elena comprobó que la puerta de la linterna seguía forzada.
```

## estado · hilos_abiertos

```yaml
- id: hil-001
  estado: abierto
  abierto_en: 1
  cerrado_en: null
  descripcion: La pregunta 1 del faro.
- id: hil-002
  estado: abierto
  abierto_en: 4
  cerrado_en: null
  descripcion: La pregunta 2 del faro.
- id: hil-003
  estado: abierto
  abierto_en: 7
  cerrado_en: null
  descripcion: La pregunta 3 del faro.
```

## estado · objetos

```yaml
- id: obj-001
  poseedor: per-tomas-reyes
  ubicacion: null
  capitulo_intro: 1
  relevancia: alta
```

## inmediata · capítulo 07

---
capitulo: 7
titulo: La linterna, noche 7
pov: per-elena-vidal
palabras: 298
escenas:
- esc-07-1
- esc-07-2
pistas_plantadas: []
pistas_pagadas: []
hilos_abiertos:
- hil-003
hilos_cerrados: []
version_canon: 1
version_plan: 1
run_id: r-20260107-0900
---
# Capítulo 7

Aquella escena 1 del capítulo 7 empezó con el viento del norte. En la noche 7 Elena comprobó que la puerta de la linterna seguía forzada.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

***

Aquella escena 2 del capítulo 7 empezó con el viento del norte.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

Elena contó los escalones del faro por 7 vez y el mar siguió en su sitio.

## reciente · parrafo

### Capítulo 05

En el capítulo 5 Elena sube al faro, discute con Tomás y oye a Inés.

### Capítulo 06

En el capítulo 6 Elena sube al faro, discute con Tomás y oye a Inés.

### Capítulo 07

En el capítulo 7 Elena sube al faro, discute con Tomás y oye a Inés.

## remota · una_linea

- 01: Capítulo 1: Elena vuelve a la linterna.
- 02: Capítulo 2: Elena vuelve a la linterna.
- 03: Capítulo 3: Elena vuelve a la linterna.
- 04: Capítulo 4: Elena vuelve a la linterna.

## plan · capítulo 08

---
capitulo: 8
pov: per-elena-vidal
objetivo_dramatico: Al final del capítulo 8 Elena sabe algo que no sabía.
escenas:
- id: esc-08-1
  lugar: esc-casa-del-faro
  tiempo_diegetico: dia 8, 21:00
  personajes:
  - per-elena-vidal
  - per-tomas-reyes
  dialogo:
  - per-elena-vidal
  - per-tomas-reyes
  beat: Tomás aparece sin avisar
  conflicto: Elena no puede echarle
- id: esc-08-2
  lugar: esc-puerto
  tiempo_diegetico: dia 8, 23:00
  personajes:
  - per-elena-vidal
  - per-ines-mar
  dialogo:
  - per-ines-mar
  beat: Inés habla de más
  conflicto: Elena duda de ella
pistas_a_plantar:
- pis-004
pistas_a_pagar: []
hilos_que_abre: []
hilos_que_cierra: []
gancho_final: decision_pendiente
restriccion_de_apertura: Empieza con una frase de menos de 6 palabras.
---
Ficha del capítulo 8.


### Pistas de este capítulo

- pis-004 · plantar · El reloj de la linterna marca las 4 y cuarto en la pista 4.

## variacion · restricción de apertura

Empieza con una frase de menos de 6 palabras.

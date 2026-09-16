# story-maker

Generador de novelas de suspense con IA

Harness multiagente que escribe una novela capítulo a capítulo con cinco roles LLM y control
humano en tres puertas. Sin dependencias: solo stdlib de Python 3.12.

## Línea de órdenes

```bash
python -m harness init      # crea novela/ y estado.json
python -m harness next      # siempre lo primero: devuelve "ACCION: <x>"
python tests/dry_run.py     # 40 comprobaciones offline, sin gastar cuota
```

Para escribir un capítulo, abre Claude Code en el repositorio y escribe `/novela`. Una
invocación escribe un capítulo y para.

## Panel web

```bash
python -m panel             # http://127.0.0.1:8000
```

Lanzar una novela nueva, ver el progreso de la orquestación y leer los capítulos, con un
visor 3D del libro navegable capítulo a capítulo.

Es un binding secundario: no orquesta nada por su cuenta, arranca el orquestador de Claude
Code como subproceso y observa su salida. Ver `docs/anexo-c-panel-web.md`.

- Escucha solo en `127.0.0.1`. Lanza subprocesos: no puede salir a la red.
- Si `claude` no está en el PATH, podrás crear ejecuciones y leer capítulos, pero no lanzar
  agentes; el panel te da la orden para pegarla a mano.
- Cada novela nueva vive en `runs/<identificador>/`. `novela/` no se toca nunca.
- El visor 3D carga Three.js por CDN con la versión fijada. Para trabajar sin red, descarga
  los dos archivos a `panel/static/vendor/` y cambia las URLs del importmap de
  `panel/static/index.html`.

Opciones: `--port`, `--repo`, `--no-browser`, `--skip-permissions`.

## Documentación

- `CLAUDE.md` — convenciones del proyecto.
- `docs/harness-novela-suspense.md` — especificación canónica.
- `docs/SETUP.md` — guía de operador.
- `docs/anexo-c-panel-web.md` — el panel como binding: puertos, progreso y riesgos.

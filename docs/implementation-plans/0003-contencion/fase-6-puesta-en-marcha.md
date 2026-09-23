# Fase 6 — Puesta en marcha y bucle desatendido

**Se ejecuta antes que la fase 5** (ver [README](README.md), «Orden de ejecución»).

**Objetivo.** Que esta máquina pueda correr `claude -p` sin nadie delante, y que `AGENTS.md`
diga cómo prepararla.

**Al terminar existe**: `novela` en el PATH, el repo con la confianza aceptada, `python` y `uv`
resolviendo, y el bucle de la spec §5.6 en `AGENTS.md`, `CLAUDE.md` y `architecture.md`.

**Cierra**: RF-22, RF-23, RF-30. CA-13.

La mitad de esta fase son pasos de máquina, no commits. La otra mitad es documentación.

---

## 6.1 — Preparar la máquina

Una vez por máquina. Cada paso tiene su comprobación, que es lo que importa: si falla en
silencio, el síntoma aparece tres fases más tarde con otra cara.

| # | Paso | Comprobación | Si no se hace |
|---|---|---|---|
| 1 | `uv` en el PATH, de forma persistente: añadir `%APPDATA%\Python\Python312\Scripts` al PATH de usuario (Configuración → Variables de entorno), no solo a la sesión | En una terminal **nueva**, Git Bash y PowerShell: `uv --version` | El hook de Langfuse cae a `python3` y falla (E-11); `uv tool` no existe |
| 2 | `uv tool install --editable ./backend` desde la raíz | `uv tool dir --bin` está en el PATH; `novela --help` en Git Bash y en PowerShell | Toda orden `novela` del procedimiento falla con «command not found» |
| 3 | Abrir `claude` en la raíz del repo y aceptar el diálogo de confianza | `~/.claude.json`, proyecto `story-maker`: `hasTrustDialogAccepted: true` | `claude -p` ignora el `allow` (E-6) y el bucle no avanza |

Y una comprobación que no es un paso de la spec, pero de la que depende la fase 2:

| — | `python` resuelve a un intérprete real, no al alias de la Store | `python -c "import sys; print(sys.executable)"` en Git Bash y en PowerShell | **El hook falla abierto**: sale con un código distinto de 2 y la escritura pasa |

Si `python` no resuelve, la solución es desactivar el alias en «Configuración → Aplicaciones →
Alias de ejecución de aplicaciones» o poner Python 3.12 por delante en el PATH. No se cambia el
comando del hook a una ruta absoluta: rompería en cualquier otra máquina.

**Comprobación de conjunto, sin modelo**:

- `novela comprobar-entorno` → sale con 0 y no imprime nada. Cubre `python`, el script del hook y
  `settings.local.json`, y que `novela` arranque ya prueba el paso 2.
- `echo '{"tool_name":"Write","tool_input":{"file_path":"novelas/x/estado/estado.db"},"cwd":"."}' | python .claude/hooks/denegar-escritura-estado.py; echo $?` → `2`.

---

## 6.2 — Documentación

**`AGENTS.md`, «Puesta en marcha»**: los tres pasos de 6.1, en tres líneas, sin las
comprobaciones (esas se quedan aquí y en `architecture.md` §11.1). Es la única sección que crece
en toda la spec, y RF-23 la exige.

**`AGENTS.md` y `CLAUDE.md`, bucle desatendido**: se **sustituye** el bloque actual por el de la
spec §5.6, literal:

```bash
export MSYS_NO_PATHCONV=1                 # sin esto, "/novela-continuar" llega como ruta de Windows
export CC_LANGFUSE_TRACE_TAGS=<slug>
novela comprobar-entorno || exit 1
while novela pendiente <slug>; do
  antes=$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)
  export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
  claude -p "/novela-continuar <slug> --capitulos 1" --session-id "$NOVELA_SESSION_ID" \
    --setting-sources project,local --permission-mode dontAsk --model opus || break
  [ "$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)" != "$antes" ] || break
done
```

Con una línea antes: «En Git Bash.» El texto que explica el `|| break` se conserva y gana media
frase: «`comprobar-entorno` para antes de la primera sesión, y la última línea, si una sesión no
avanza el checkpoint».

Y después, la forma de abrir una sesión interactiva del harness (RF-30), también literal de la
spec:

```bash
export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
claude --session-id "$NOVELA_SESSION_ID" --setting-sources project,local --model opus
```

Con una frase: «Las sesiones de desarrollo del harness no exportan la variable». Es lo que
distingue a la regla 5 del hook una sesión que orquesta de una que desarrolla. Sin la variable,
`/novela-nueva` correría sin la restricción de subagentes.

En `CLAUDE.md` el bloque aparece una sola vez (sección «Slash commands»). No lo dupliques en
«Bucle por capítulo».

**`architecture.md`**: §2.3, el mismo bucle. §11.1, los tres pasos **con** sus comprobaciones y la
de `python`.

**Revisión** (CA-13): `AGENTS.md` contiene los tres pasos, el bucle de §5.6 con
`novela comprobar-entorno`, y la forma de abrir una sesión interactiva del harness.

**Cierra**: RF-23, RF-30. CA-13.

**Commit**: `docs: puesta en marcha y bucle desatendido con claude -p`

---

## 6.3 — El freno del bucle, en seco (RF-22)

RF-22 se acepta de verdad en la fase 7, con el bucle real. Pero la línea del freno se puede
probar gratis ahora, sustituyendo `claude` por una función que no hace nada, que es exactamente
el fallo que el freno tiene que parar (una sesión que termina con 0 sin avanzar):

```bash
novela nueva freno --idea "x" --capitulos 3 --palabras 9000
claude() { return 0; }            # sesión que no avanza
# … pega el bucle de 6.2 con <slug> = freno …
```

Resultado esperado: una iteración y salida del bucle, no un bucle infinito.

Y el freno previo, igual de gratis: con una copia de seguridad de `.claude/settings.local.json`,
añádele `"permissions": {}` y repite. El bucle tiene que salir **antes** de la primera
iteración, con el hallazgo de `comprobar-entorno` en pantalla. Restaura el fichero.

Después, `rm -rf novelas/freno`.

No se commitea como test: depende de Git Bash y del PATH de la máquina, y lo que prueba son tres
líneas de shell que ya están escritas en la documentación.

**Cierra**: RF-22 (en seco; se confirma en la fase 7).

---

## Al terminar la fase

- Los tres pasos y la comprobación de `python`, hechos y verificados en esta máquina.
- Actualiza la memoria del proyecto `uv-fuera-del-path.md`: `uv` ya está en el PATH. La nota de
  `PYTHONUTF8=1` para mutmut sigue valiendo.

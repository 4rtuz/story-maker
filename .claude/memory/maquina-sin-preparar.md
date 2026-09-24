---
name: maquina-sin-preparar
description: "Preparación de la máquina de desarrollo (Windows, 2026-09-24): qué hace falta para que claude -p corra el harness"
metadata:
  node_type: memory
  type: project
  originSessionId: beb0ce0e-06d3-4b8c-880c-28abc4e11ab2
  modified: 2026-09-24T07:59:17.672Z
---

Estado a 2026-09-24, después de prepararla. La confianza del repo está aceptada, el plugin de Langfuse está instalado y habilitado en `.claude/settings.local.json`, y `LANGFUSE_PUBLIC_KEY` está en el entorno de usuario.

Dos cosas propias de esta máquina, que `AGENTS.md` no cubre:

- Git está instalado por usuario, así que `claude` necesita `CLAUDE_CODE_GIT_BASH_PATH` apuntando a `AppData\Local\Programs\Git\bin\bash.exe`. Sin ella, la sesión solo tiene PowerShell, y los hooks corren en PowerShell y fallan.
- Device Guard bloquea el `novela.exe` de `~/.local/bin` (el de `uv tool`). El de `backend\.venv\Scripts` sí corre, así que esa carpeta va por delante en el PATH.

- Device Guard bloquea también los `.exe` de una venv nueva (p. ej. `mypy.exe` en un worktree recién sincronizado): usa `uv run python -m mypy --strict .`.

En la raíz hay un `.env` con claves reales. No lo leas.

**Why:** sin estos dos arreglos, el bucle no puede ejecutar `novela`. Las sesiones del harness también cargan esta memoria, así que tiene que decir la verdad actual.
**How to apply:** si una sesión del harness no puede ejecutar `novela`, revisa estos dos puntos antes de culpar a la confianza. Ver [[hook-regla-4-commits]].

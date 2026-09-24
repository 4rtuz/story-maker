---
name: entorno-frontend
description: "Cómo trabajar el frontend en esta máquina (2026-09-24): Node portátil, puerto 8000 ocupado, trampas de Git Bash y cómo se hicieron las capturas de revisión"
metadata:
  node_type: memory
  type: project
  originSessionId: a76c93b7-ed7e-4581-b873-b8cc67e935ba
  modified: 2026-09-24T16:18:24.956Z
---

Estado a 2026-09-24: fases 1 a 6 de la spec 0004 hechas (T-01 a T-15); la 7 en curso.

- **Node 24** es el portátil de `%LOCALAPPDATA%\Programs\node-v24.21.0-win-x64`. El usuario lo añadió al PATH el 2026-09-24, pero una shell abierta antes no lo ve: si `node` no resuelve, antepón `export PATH="$LOCALAPPDATA/Programs/node-v24.21.0-win-x64:$PATH"`.
- **El puerto 8000 está libre** desde el 2026-09-24 (el usuario desinstaló `claude-science.exe`): la API va en 8000, lo que esperan `VITE_API_URL` por defecto y los tests.
- **Git Bash**: un heredoc con comillas simples revienta por el hook de rtk; un argumento que empieza por `/` o `//` se convierte en ruta de Windows (usa `MSYS_NO_PATHCONV=1`, y para ediciones, Write/Edit o un script). El hook del repo deniega órdenes que nombren `estado.db` o el misterio.
- **Capturas**: `@playwright/test@1.63.0` con `npm install --no-save` (cualquier `npm install` posterior lo poda) y Chromium ya descargado; se arranca Vite con `createServer({configFile})` y se fotografía a 1440 × 900. Los workspaces sintéticos se generan con `fabrica` aislando `run.RAIZ_REPO` y `LANGFUSE_*`, como hará `panel.py` en T-16.
- Chromium registra un `console.error` por el 404 esperado de `…/escaleta` en `recien-creada`: RNF-16 tendrá que contemplarlo en los e2e.
- El paso 1 del pre-commit casaría con los valores ficticios de `docs/specs/0004/validators.md:226`; desaparece al borrarlo en T-23.

**Why:** son fricciones de esta máquina que no dicen AGENTS.md ni el plan, y costaron tiempo en la primera sesión.
**How to apply:** al retomar la fase 6 o 7, empieza por el PATH de Node y el puerto de la API. Ver [[maquina-sin-preparar]] y [[hook-regla-4-commits]].

"""Nucleo determinista del harness de novela (secciones 1-17 de la especificacion).

Este paquete NO conoce el runtime. No menciona Claude Code, ni OpenRouter, ni
ningun identificador de modelo: eso vive en el binding (.claude/, Anexo A).
Aqui solo hay lo que la especificacion marca como determinista y prohibe
delegar a un subagente: ensamblado de contexto (§7), reglas bloqueantes (§8.2),
auditoria final (§8.3), verificacion de parches (§9.5), aplicacion de deltas
(§A.5 paso 14) y regeneracion del resumen rodante (§A.5 paso 16, §6.9).
"""

__version__ = "1.0.0"

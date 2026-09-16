"""Panel web del harness: binding secundario, solo lectura sobre el nucleo.

Implementa P4 (humano) trasladando la respuesta de las puertas al CLI, y delega
P1 (invocar) en el binding de Claude Code lanzandolo como subproceso. No
reimplementa nada de `harness/`: todo lo determinista sigue saliendo de
`python -m harness`.

Ver `docs/anexo-c-panel-web.md` para el mapeo completo de los seis puertos.
"""

__version__ = "1.0.0"

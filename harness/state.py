"""Persistencia atomica de estado.json y gobernador de cuota (§10.1, §10.2, §12)."""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import Config

# Estados de la maquina de §10. El orden no implica transicion.
STATES = [
    "INIT", "ENTREVISTA", "GENERANDO_BIBLIA", "GATE_PLAN",
    "ESCRIBIENDO", "EVALUANDO", "PARCHEANDO", "ACEPTANDO",
    "GATE_BLOQUEO", "EDITANDO_ACTO", "GATE_ACTO", "REVISANDO_ESCALETA",
    "AUDITORIA_FINAL", "GATE_FINAL", "COMPLETADO", "CUOTA_PAUSADA", "ERROR",
]

GATES = {"GATE_PLAN", "GATE_ACTO", "GATE_FINAL", "GATE_BLOQUEO"}


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class State:
    """Punto unico de verdad de la ejecucion. Se reescribe entero tras cada
    transicion y tras cada llamada al modelo, sin excepcion (§10.1)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.path = cfg.path("archivo_estado")
        self.data = self._read()

    # -- E/S atomica --------------------------------------------------------
    def _read(self) -> dict:
        if not self.path.exists():
            return self._initial()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _initial(self) -> dict:
        return {
            "version": 1,
            "estado": "INIT",
            "capitulo_actual": 1,
            "acto_actual": 1,
            "iteracion": 0,
            "intentos": [],
            "capitulos_aceptados": [],
            "puerta_pendiente": None,
            "cuota": {
                "fecha_utc": _utc_today(),
                "llamadas_hoy": 0,
                "limite_diario": self.cfg["ejecucion"]["cuota"]["limite_diario"],
                "limite_por_minuto": self.cfg["ejecucion"]["cuota"]["limite_por_minuto"],
                "ts_ultima_llamada": None,
            },
            "clases_modelo": {rol: datos["clase_modelo"]
                              for rol, datos in self.cfg["agentes"].items()},
            "binding": "claude-code",
            "perfil": self.cfg.profile_name,
            "ultimo_error": None,
        }

    def save(self) -> None:
        """Escritura atomica: temporal + os.replace. Una escritura interrumpida
        no puede dejar el archivo a medias (§10.1, puerto P3)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.data, ensure_ascii=False, indent=2) + "\n"
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    # -- acceso -------------------------------------------------------------
    def __getitem__(self, key): return self.data[key]
    def __setitem__(self, key, value): self.data[key] = value
    def get(self, key, default=None): return self.data.get(key, default)

    @property
    def name(self) -> str:
        return self.data["estado"]

    def transition(self, new_state: str, **fields) -> None:
        if new_state not in STATES:
            raise ValueError(f"Estado desconocido: {new_state}")
        self.data["estado"] = new_state
        self.data.update(fields)
        self.save()

    def at_gate(self) -> bool:
        return self.name in GATES

    # -- gobernador de cuota (puerto P6, §12) -------------------------------
    def roll_quota_day(self) -> bool:
        """Si el dia UTC ha cambiado, resetea el contador. Devuelve True si reseteo."""
        q = self.data["cuota"]
        today = _utc_today()
        if q["fecha_utc"] != today:
            q["fecha_utc"] = today
            q["llamadas_hoy"] = 0
            self.save()
            return True
        return False

    def quota_left(self) -> int:
        q = self.data["cuota"]
        return max(0, q["limite_diario"] - q["llamadas_hoy"])

    def has_budget(self, needed: int = 1) -> bool:
        self.roll_quota_day()
        return self.quota_left() >= needed

    def record_usage(self, n: int = 1) -> None:
        self.roll_quota_day()
        q = self.data["cuota"]
        q["llamadas_hoy"] += n
        q["ts_ultima_llamada"] = time.time()
        self.save()

    def chapter_fits(self) -> bool:
        """§12: no se empieza un capitulo que no cabe en la cuota del dia.
        Un ciclo minimo son 3 llamadas logicas: escritor + evaluador + continuista."""
        if not self.cfg["ejecucion"]["cuota"].get("parar_si_no_cabe_un_capitulo", True):
            return self.has_budget(1)
        return self.has_budget(3)

    # -- intentos (§9.4) ----------------------------------------------------
    def record_attempt(self, iteration: int, mean: float, path: str) -> None:
        self.data["intentos"] = [a for a in self.data["intentos"]
                                 if a["iteracion"] != iteration]
        self.data["intentos"].append(
            {"iteracion": iteration, "media": mean, "ruta": path})
        self.data["intentos"].sort(key=lambda a: a["iteracion"])
        self.save()

    def best_attempt(self) -> dict | None:
        """§9.4 regla 1: gana la media mas alta, no el ultimo intento.
        A igualdad de media, el mas temprano (una reescritura que no mejora, no gana)."""
        if not self.data["intentos"]:
            return None
        return min(self.data["intentos"], key=lambda a: (-a["media"], a["iteracion"]))

    def reset_chapter_scratch(self) -> None:
        self.data["iteracion"] = 0
        self.data["intentos"] = []
        self.save()

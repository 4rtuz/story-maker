"""Carga de novela/config.json con fusion profunda del perfil activo (§6.0)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _deep_merge(base: Any, override: Any) -> Any:
    """Fusiona `override` sobre `base`. Los dicts se mezclan clave a clave;
    cualquier otro tipo (incluidas las listas, como `actos`) se reemplaza entero."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = _deep_merge(base.get(key), value) if key in base else value
        return merged
    return override


class Config:
    """Vista del config con el perfil activo ya fusionado sobre `base`."""

    def __init__(self, raw: dict, root: Path):
        self.raw = raw
        self.root = root
        self.profile_name = raw["perfil_activo"]
        profile = raw.get("perfiles", {}).get(self.profile_name, {})
        self.data = _deep_merge(raw["base"], {k: v for k, v in profile.items()
                                              if not k.startswith("_")})

    # -- acceso por seccion -------------------------------------------------
    def __getitem__(self, section: str) -> Any:
        return self.data[section]

    def get(self, section: str, default: Any = None) -> Any:
        return self.data.get(section, default)

    # -- rutas resueltas contra la raiz del repo ----------------------------
    def path(self, key: str) -> Path:
        return self.root / self.data["rutas"][key]

    def chapter_path(self, n: int) -> Path:
        return self.path("capitulos") / f"{n:02d}-capitulo.md"

    def card_path(self, n: int) -> Path:
        return self.path("capitulos") / f"{n:02d}-ficha.md"

    def attempt_path(self, n: int, iteration: int) -> Path:
        return self.path("intentos") / f"{n:02d}-i{iteration}.md"

    def report_path(self, act: int) -> Path:
        return self.path("informes") / f"acto-{act}.md"

    def bible_path(self, name: str) -> Path:
        return self.path("biblia") / name

    def state_path(self, name: str) -> Path:
        return self.path("estado") / name

    # -- helpers de acto ----------------------------------------------------
    def act_of(self, chapter: int) -> int:
        for act in self.data["actos"]:
            if act["desde"] <= chapter <= act["hasta"]:
                return act["numero"]
        raise ValueError(f"El capitulo {chapter} no cae en ningun acto declarado")

    def is_act_end(self, chapter: int) -> bool:
        return any(a["hasta"] == chapter for a in self.data["actos"])

    @property
    def total_chapters(self) -> int:
        return self.data["capitulos"]["total"]


def load(root: Path | None = None) -> Config:
    root = Path(root or Path.cwd()).resolve()
    # config.json vive bajo rutas.raiz, pero rutas.raiz esta dentro de config.json:
    # se busca en las ubicaciones convencionales antes de rendirse.
    for candidate in (root / "novela" / "config.json", root / "novel" / "config.json"):
        if candidate.exists():
            raw = json.loads(candidate.read_text(encoding="utf-8"))
            return Config(raw, root)
    raise FileNotFoundError(f"No se encuentra config.json bajo {root}")

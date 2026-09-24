"""`novela prompts publicar`: una versión por texto distinto, nunca dos por el mismo."""

import urllib.error
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from novela.slices.observabilidad import prompts
from novela.slices.observabilidad.api import Api


class LangfuseFalso:
    """La Prompt Management de Langfuse en memoria: nombre → versiones con sus etiquetas."""

    def __init__(self) -> None:
        self.versiones: dict[str, list[dict[str, Any]]] = {}

    def pedir(self, metodo: str, ruta: str, cuerpo: Any = None, *_: object) -> Any:
        if metodo == "GET":
            nombre = ruta.split("/prompts/")[1].split("?")[0]
            prod = [v for v in self.versiones.get(nombre, []) if "production" in v["labels"]]
            if not prod:
                raise urllib.error.HTTPError(ruta, 404, "no", Message(), None)
            return prod[-1]
        for v in self.versiones.get(cuerpo["name"], []):
            v["labels"] = [e for e in v["labels"] if e != "production"]
        nueva = {**cuerpo, "version": len(self.versiones.get(cuerpo["name"], [])) + 1}
        self.versiones.setdefault(cuerpo["name"], []).append(nueva)
        return nueva


def test_publicar_es_idempotente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    falso = LangfuseFalso()
    monkeypatch.setattr(Api, "pedir", lambda _api, *a, **k: falso.pedir(*a, **k))
    api = Api("https://langfuse.invalid", "p", "s")
    (tmp_path / "escritor.md").write_text("---\nname: escritor\n---\nEscribe.", encoding="utf-8")
    (tmp_path / "cronista.md").write_text("---\nname: cronista\n---\nRegistra.", encoding="utf-8")

    assert prompts.publicar(api, tmp_path, "abc1234") == {"cronista": "v1", "escritor": "v1"}
    assert prompts.publicar(api, tmp_path, "def5678") == {"cronista": "igual", "escritor": "igual"}
    (tmp_path / "escritor.md").write_text("---\nname: escritor\n---\nEscribe mejor.", "utf-8")
    assert prompts.publicar(api, tmp_path, "0badf00") == {"cronista": "igual", "escritor": "v2"}

    (v1, v2) = falso.versiones["escritor"]
    assert v2["labels"] == ["0badf00", "production"] and v1["labels"] == ["abc1234"]
    assert v2["type"] == "text" and v2["config"]["sha256"] == prompts.huellas(tmp_path)["escritor"]


def test_la_traza_registra_la_huella_de_cada_rol(tmp_path: Path) -> None:
    (tmp_path / "escritor.md").write_text("x", encoding="utf-8")
    meta = prompts.metadatos_de_version(tmp_path)
    assert meta["prompt_escritor"] == prompts.huellas(tmp_path)["escritor"][:12]
    assert meta["sha_commit"]

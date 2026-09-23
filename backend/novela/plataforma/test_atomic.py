from pathlib import Path

import pytest

from novela.plataforma import atomic


def test_corte_deja_fichero_anterior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-04: una excepción entre la escritura del .tmp y el replace deja el anterior íntegro."""
    destino = tmp_path / "capitulos" / "07.md"
    atomic.escribir(destino, "versión buena\n")
    antes = destino.read_bytes()

    def corte(*_: object) -> None:
        raise OSError("corte de luz")

    monkeypatch.setattr("os.replace", corte)
    with pytest.raises(OSError, match="corte"):
        atomic.escribir(destino, "versión a medias")
    assert destino.read_bytes() == antes
    assert list(destino.parent.iterdir()) == [destino]  # ni rastro del .tmp


def test_destino_abierto_por_otro(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """validators.md §3.5: en Windows replace falla si otro proceso tiene abierto el destino. Se
    reintenta con espera acotada; si agota, error y fichero anterior intacto. En POSIX, pasa."""
    monkeypatch.setattr(atomic, "_ESPERA_S", 0.001)
    destino = tmp_path / "07.md"
    atomic.escribir(destino, "anterior")
    with open(destino, "rb"):
        try:
            atomic.escribir(destino, "nuevo")
        except PermissionError:
            assert destino.read_bytes() == b"anterior"
        else:
            assert destino.read_bytes() == b"nuevo"
    assert not destino.with_name("07.md.tmp").exists()


def test_escribe_bytes_sin_traducir_saltos(tmp_path: Path) -> None:
    destino = tmp_path / "x.md"
    atomic.escribir(destino, "a\nb\n")
    assert destino.read_bytes() == b"a\nb\n"

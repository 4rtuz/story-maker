import pytest
import yaml
from pydantic import ValidationError

from novela.dominio.ids import Agente
from novela.slices.briefing import recipes


def test_receta_valida() -> None:
    """Las siete recetas del fichero cargan; una capa desconocida se rechaza."""
    cargadas = recipes.cargar()
    assert set(cargadas) == set(Agente)
    assert cargadas[Agente.ESCRITOR].excluir == ["canon/misterio"]
    assert all(r.presupuesto_tokens <= 100_000 for r in cargadas.values())

    texto = recipes.RUTA.read_text(encoding="utf-8")
    datos = yaml.safe_load(texto)
    datos["escritor"]["capas"].append({"intuicion": "lo que haga falta"})
    with pytest.raises(ValidationError):
        recipes.validar(datos)
    sin_cronista = {k: v for k, v in yaml.safe_load(texto).items() if k != "cronista"}
    with pytest.raises(ValidationError, match="cronista"):
        recipes.validar(sin_cronista)


def test_orden_de_capas_es_el_del_fichero() -> None:
    capas = recipes.cargar()[Agente.ESCRITOR].capas
    assert [type(c).__name__ for c in capas][:3] == ["Permanente", "Personajes", "EstadoFiltrado"]


def test_capas_de_regeneracion() -> None:
    """Spec 0007 RF-28 y RF-29: la capa cambio, para escritor, continuista y cronista; la versión
    anterior, solo para el escritor."""
    recetas = recipes.cargar()

    def con(tipo: type) -> set[Agente]:
        return {a for a, r in recetas.items() if any(isinstance(c, tipo) for c in r.capas)}

    assert con(recipes.Cambio) == {Agente.ESCRITOR, Agente.CONTINUISTA, Agente.CRONISTA}
    assert con(recipes.VersionAnterior) == {Agente.ESCRITOR}

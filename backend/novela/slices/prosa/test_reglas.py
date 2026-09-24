"""Las cuatro reglas de `novela lint-prosa`, cada una con textos cortos."""

from novela.slices.prosa.reglas import Contexto, analizar

TERCERA_PASADO = Contexto(punto_de_vista="tercera_limitada", tiempo_verbal="pasado")


def _de(regla: str, texto: str, ctx: Contexto = TERCERA_PASADO) -> list[tuple[int | None, str]]:
    informe = analizar(texto, ctx)
    return [(h.parrafo, h.codigo) for h in informe.hallazgos if h.regla == regla]


def test_repeticion_de_palabra_con_contenido_en_un_parrafo() -> None:
    texto = (
        "La puerta estaba abierta. Elena miró la puerta y pensó que la puerta "
        "no debía estar así.\n\n"
        "El faro seguía apagado."
    )
    assert _de("repeticiones", texto) == [(1, "palabra_repetida")]


def test_las_palabras_funcionales_no_cuentan_como_repeticion() -> None:
    texto = "Que se fuera, que se quedara, que hiciera lo que quisiera con lo que tenía."
    assert _de("repeticiones", texto) == []


def test_muletilla_repetida_en_un_parrafo() -> None:
    texto = "De repente sonó el timbre. De repente, nadie respiraba."
    assert (1, "muletilla") in _de("repeticiones", texto)


def _frase(palabras: int) -> str:
    return " ".join(["gato"] * (palabras - 1)) + " fin."


def test_frase_larga_segun_la_edad_del_destinatario() -> None:
    """25 palabras pasan para un adulto y no para un lector de 10 años."""
    texto = _frase(25).capitalize()
    assert _de("legibilidad", texto) == []
    nino = Contexto(punto_de_vista="tercera_limitada", tiempo_verbal="pasado", edad=10)
    assert (1, "frase_larga") in _de("legibilidad", texto, nino)
    assert (1, "frase_larga") in _de("legibilidad", _frase(40).capitalize())


def test_legibilidad_baja_con_fernandez_huerta() -> None:
    denso = (
        "La institucionalización administrativa de procedimientos jurisdiccionales "
        "interdepartamentales comprometía irremediablemente la operatividad organizativa "
        "correspondiente. Consiguientemente, la reestructuración metodológica "
        "extraordinariamente especializada imposibilitaba cualquier interpretación "
        "simplificadora, contradictoriamente recomendada por investigadores universitarios "
        "internacionales, desconcertantemente descoordinados, perpetuamente insatisfechos."
    )
    claro = (
        "Ana vio la luz. Fue a la puerta. No había nadie. El mar olía a sal y a lluvia. "
        "Cerró con llave y se fue a la cama. La casa estaba en calma. Oyó un ruido. "
        "Era el gato."
    )
    assert (1, "legibilidad_baja") in _de("legibilidad", denso)
    assert _de("legibilidad", claro) == []


def test_abuso_de_adverbios_en_mente() -> None:
    assert _de("lexico", "Abrió lentamente la puerta y miró cuidadosamente.") == [
        (1, "adverbios_mente")
    ]
    assert _de("lexico", "Tenía la mente en blanco. Lentamente se sentó.") == []


def test_cliches_y_giros_de_texto_generado() -> None:
    texto = (
        "Un escalofrío le recorrió la espalda.\n\n"
        "No pudo evitar sonreír. En el fondo lo sabía.\n\n"
        "La lluvia golpeaba el cristal."
    )
    informe = analizar(texto, TERCERA_PASADO)
    cliches = [(h.parrafo, h.evidencia) for h in informe.hallazgos if h.codigo == "cliche"]
    assert cliches == [
        (1, "un escalofrío le recorrió la espalda"),
        (2, "no pudo evitar"),
        (2, "en el fondo"),
    ]
    assert informe.scores["prosa_lexico"] == round(1 - 2 / 3, 4)


def test_narrador_en_primera_persona_cuando_config_dice_tercera() -> None:
    texto = (
        "Yo abrí la puerta y mi hermano me miró.\n\n"
        "—Yo no fui —dijo ella—. Me lo juro.\n\n"
        "Elena cerró la ventana."
    )
    assert _de("estilo", texto) == [(1, "narrador_primera_persona")]


def test_narrador_en_tercera_persona_cuando_config_dice_primera() -> None:
    primera = Contexto(punto_de_vista="primera_persona", tiempo_verbal="pasado")
    tercera = (
        "Elena cerró la ventana y bajó a la cocina. Tomás esperaba junto a la mesa, callado, "
        "con las manos sobre el mantel. Ella no dijo nada. Él tampoco. La lluvia seguía."
    )
    assert _de("estilo", tercera, primera) == [(None, "narrador_tercera_persona")]
    assert _de("estilo", "Cerré la ventana y bajé. Mi hermano me esperaba.", primera) == []


def test_tiempo_verbal_distinto_del_configurado() -> None:
    texto = (
        "Ana abre la puerta. Hay luz. Mira el mar y piensa en su padre.\n\n"
        "Después cerró la puerta, volvió a la cocina y se quedaba quieta."
    )
    assert _de("estilo", texto) == [(1, "tiempo_verbal")]
    presente = Contexto(punto_de_vista="tercera_limitada", tiempo_verbal="presente")
    assert _de("estilo", texto, presente) == [(2, "tiempo_verbal")]


def test_tratamiento_tu_y_usted_mezclado_en_un_dialogo() -> None:
    texto = "—Usted no sabe nada —dijo Tomás—. Te lo digo yo.\n\n—Tú sabrás —contestó Elena."
    assert _de("estilo", texto) == [(1, "tratamiento_mixto")]

from hypothesis import settings

# Sin deadline: en Windows el primer ejemplo de una estrategia compuesta tarda lo que tarda el
# antivirus, y un deadline ahí da rojos que no son del código. CI puede subir max_examples.
settings.register_profile("default", deadline=None, max_examples=50)
settings.register_profile("ci", deadline=None, max_examples=200)
settings.load_profile("default")

---
name: auditoria-seguridad
description: Auditoría de seguridad del harness (inyección por el brief, exfiltración entre novelas, dependencias, secretos en el historial) que deja docs/security-report.md. Para desarrollar el harness, nunca dentro de una sesión de novela.
disable-model-invocation: true
---

# Auditoría de seguridad del harness

Recorre las cuatro superficies en orden y termina cuando cada una tiene veredicto en
`docs/security-report.md`. Un **hallazgo** es algo que has reproducido: una orden, un test o una
salida que lo demuestra. Lo que solo sospechas va a «Sin reproducir», nunca como hallazgo.

Reglas durante toda la auditoría:

- Cada valor de clave que encuentres se describe por **fichero, commit y tipo**; el valor no
  aparece en ninguna salida, informe ni commit. Redacta con `sed` antes de imprimir.
- Los `.env` se dejan cerrados: su existencia es lo único que se comprueba.
- Las pruebas corren en `tmp_path` o en una copia; `novelas/` del checkout es de otro.
- Un arreglo pequeño y seguro se hace en la misma pasada con el ciclo TDD de `AGENTS.md`: el
  test de regresión se ve en rojo antes del arreglo. Lo grande se documenta como pendiente.

## 1. Inyección por el texto libre del brief

Superficie: `backend/novela/slices/brief/` — `entradas.py` (`PATRONES`, `_plano`, `marcar`,
`delimitar`), `gates.py` (`procedencia`, `CERRADOS`, `cita_en_fragmento_marcado`,
`campo_cerrado_desde_texto_libre`) y la fixture `tests/fixtures/brief/carta-inyectada.md`.

1. Lee los tres ficheros y anota qué defensa cubre qué: los campos cerrados no pueden salir de
   texto libre; rasgos y recuerdos sí, salvo que la cita toque un fragmento marcado.
2. Construye variantes que un modelo obedecería y la lista cerrada no marca: caracteres de
   formato (U+200B), anchura completa, homoglifos, sinónimos («no hagas caso»), rutas con `\` o
   `..`, instrucciones partidas en dos frases.
3. Para cada una, reprodúcela de extremo a extremo: carta limpia más la línea, `novela brief
   entrada --tipo texto-libre`, un `brief/borrador.json` **obediente** que la cita como recuerdo,
   y `novela brief validar`. Salida 0 con `brief.json` escrito es un hallazgo. El molde está en
   `backend/novela/slices/brief/test_inyeccion.py`: añade ahí cada variante nueva.

Hecho cuando cada variante tiene veredicto (marcada / hallazgo / riesgo aceptado).

## 2. Exfiltración entre novelas y path traversal

1. **Recetas de briefing** (`backend/config/recipes.yaml`, `slices/briefing/`): confirma que toda
   ruta sale de nombres fijos, números o globs dentro del workspace, y ninguna de un valor que
   haya escrito un agente.
2. **Slug y run_id**: cada subcomando del CLI que recibe slug y cada ruta de `backend/api/`
   (`novelas.py`, `capitulos.py`, `lanzamientos.py`) con `..`, `%2F`, `%5C`, `%00` y mayúsculas.
   Esperado: 2 en el CLI, 422 en la API, sin tocar disco. Regresión en
   `backend/tests/test_seguridad_rutas.py`.
3. **Guardas de `/lanzamientos`**: `Host` (`localhost.`, `*.nip.io`, dominio ajeno) y `Origin`
   (`null`, puerto vecino, sufijo) tienen que dar 403 sin lanzar nada.
4. **Lecturas de los roles**: `tools` no restringe rutas. Comprueba que el hook
   `.claude/hooks/denegar-escritura-estado.py` (regla 6) y el matcher de
   `.claude/settings.json` impiden a un rol leer otra novela, `.env` o fuera del repo, y que
   `novela producir` exporta `NOVELA_SLUG`. Regresión en `backend/tests/test_hook_lectura.py`.

Hecho cuando cada ruta de la API y cada subcomando con slug figura como probado.

## 3. Dependencias

```bash
cd backend  && uv run --with pip-audit python -m pip_audit
cd frontend && npm audit
```

Una CVE con versión parcheada se sube (`uv lock --upgrade-package <p>` o `npm update <p>`) y se
pasa la suite. Sin parche, se documenta con su alcance real en el harness.

## 4. Secretos en el historial

Patrones: los de `.githooks/pre-commit` más `ghp_`, `AKIA`, `xox[baprs]-`, `AIza`, JWT
(`eyJ…\.…`) y `-----BEGIN … PRIVATE KEY`. Busca en `git log --all -p`, redactando el valor en la
misma tubería:

```bash
git log --all -p --no-color | grep -nIE '<patrones>' | sed -E 's/(KEY|sk-|pk-|ghp_|AKIA|eyJ)[^ ]*/\1<REDACTADO>/g'
```

Para cada coincidencia, clasifica el valor por su forma (longitud, prefijo, `dummy`, `...`)
sin imprimirlo. Los valores de prueba (`dummy-*`, placeholders con `...`) no son hallazgos. Una
clave real es crítica: se rota antes que nada y el informe lleva solo fichero, commit y tipo.

## 5. Informe

`docs/security-report.md`: fecha, commit auditado, y por hallazgo **id, severidad** (crítica,
alta, media, baja, informativa), **evidencia** (orden o test que lo reproduce) y **cambio**
(commit y test, o por qué queda pendiente). Cierra con los riesgos aceptados y cómo repetir la
auditoría (esta skill).

Hecho cuando las cuatro superficies tienen sección y la suite, `mypy --strict` y `ruff` pasan.

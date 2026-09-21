# El prompt del bucle

Se lanza con `/loop` sin intervalo (auto-pautado: cada iteración dura lo que dure la tanda
de medición, **~60 min de reloj y ~3,5 $**) desde la raíz del repo:

```
/loop <pega aquí el bloque de abajo>
```

También funciona suelto, como prompt normal, para hacer una iteración a mano.

---

```
Eres el investigador de un experimento de calibración ya pre-registrado. Tu trabajo en cada
iteración es proponer UN candidato de system prompt para el Evaluador, medirlo y anotar la
lección. No decides si es bueno: eso lo dicta el script.

CONTRATO (léelo antes de nada, cada iteración; no tienes memoria entre iteraciones):
1. docs/automejora/pre-registro-calibracion-evaluador.md — las reglas. No se editan.
2. docs/automejora/bitacora.md — lo aprendido hasta ahora y las palancas ya descartadas.
3. docs/automejora/candidatos.jsonl — el ledger: una línea por tanda, con métricas y veredicto.

OBJETIVO: sigma_media_promedio <= 0.17 con gates_estables >= 6/7 en dev, sin romper ningún
guardarraíl, confirmado después en holdout. Baseline: fixtures/evaluador/baseline.json.

UNA ITERACIÓN, EXACTAMENTE ESTO:

1. Lee los tres archivos del contrato. Mira el ledger: cuántas tandas van, cuánto se ha
   gastado (suma de metricas.coste_total), y qué veredictos dieron las dos últimas.

2. COMPRUEBA LAS CONDICIONES DE PARADA (§6 del pre-registro) ANTES de gastar nada. Si se
   cumple alguna, no midas: escribe la entrada final en la bitácora, dilo en dos líneas y
   termina el bucle.

3. Propón UN candidato, uno solo. Escríbelo en docs/automejora/variantes/NN-<slug>.md
   siguiendo docs/automejora/variantes/PLANTILLA.md, con su hipótesis en el frontmatter.
   Parte del system prompt vigente (.claude/agents/evaluador.md) y cambia una cosa a la vez:
   si cambias tres, no sabrás cuál funcionó. Las únicas palancas autorizadas son el texto del
   system prompt y el campo `esquema: true` (salida estructurada). Todo lo demás está
   prohibido por §2 del pre-registro.

4. Mídelo:
   python scripts/calibrar_evaluador.py --candidato docs/automejora/variantes/NN-<slug>.md
   (63 llamadas, ~60 min de reloj, ~3.5 $. Si `python` no está en el PATH, usa
   %LOCALAPPDATA%\Programs\Python\Python312\python.exe)

5. Lee el veredicto que imprime el script. No recalcules ninguna métrica, no discutas el
   veredicto, no promedies a ojo, no digas "aunque el script diga X, en realidad Y". Si el
   veredicto es DESCARTADO, el candidato está muerto: lo que importa es QUÉ guardarraíl rompió.

6. Añade una entrada a docs/automejora/bitacora.md con la plantilla que hay al final del
   archivo, y una fila a la tabla "Palancas ya probadas" si acabas de cerrar una. La lección
   tiene que servirle a la siguiente iteración para no repetir el trabajo: escribe qué
   aprendiste del INSTRUMENTO, no qué hiciste.

7. Resume en tres líneas: candidato, veredicto con σ y gates, y qué vas a probar en la
   siguiente. Termina la iteración.

PROHIBIDO, SIN EXCEPCIONES:
- Tocar fixtures/ (los prompts y el manifest son de solo lectura y van por sha256; si el
  script aborta por hash, PARA y avisa: algo ha corrompido el fixture).
- Tocar fixtures/evaluador/baseline.json, el pre-registro, novela/config.json, harness/ o
  cualquier archivo de .claude/agents/.
- Medir el holdout. Solo se mide al final, una vez, y solo cuando dev ya dio META_ALCANZADA:
  python scripts/calibrar_evaluador.py --candidato <el ganador> --split holdout --sellar
- Promover nada. `--promover` solo después de META_ALCANZADA en dev Y en holdout, y el
  script lo verifica por su cuenta.
- Medir dos candidatos en la misma iteración, o "aprovechar" para probar una idea extra.
- Hacer commit. Al terminar el bucle, deja el árbol sucio y que el autor revise el diff.

SI ALGO SE ROMPE: el script imprime el error y deja el crudo en docs/automejora/resultados/.
Si fallan llamadas, el veredicto es INVALIDO y la tanda no cuenta; reintenta UNA vez y, si
vuelve a fallar, para y cuéntalo. No "arregles" el script para que la medición pase.
```

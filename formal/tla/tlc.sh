#!/usr/bin/env bash
# Ejecuta TLC sobre los modelos de formal/tla/ y comprueba el resultado esperado:
# los .cfg que dicen «se espera ... contraejemplo» deben violar su invariante; el resto, pasar.
#   formal/tla/tlc.sh                      todos los .cfg
#   formal/tla/tlc.sh Harness.cfg ...      solo esos
# JAVA y TLA2TOOLS se pueden sobreescribir; la salida completa queda en $SALIDA (por defecto,
# un directorio temporal).
set -u
cd "$(dirname "$0")"
JAVA="${JAVA:-C:/Users/arturo.soto/tools/jdk-21.0.12.1+1-jre/bin/java.exe}"
TLA2TOOLS="${TLA2TOOLS:-C:/Users/arturo.soto/tools/tla2tools.jar}"
SALIDA="${SALIDA:-$(mktemp -d)}"
[ $# -gt 0 ] || set -- *.cfg
mal=0
for cfg in "$@"; do
  nombre="${cfg%.cfg}"
  case "$nombre" in Regeneraciones*) modulo=Regeneraciones ;; *) modulo=Harness ;; esac
  inicio=$(date +%s)
  "$JAVA" -XX:+UseParallelGC -cp "$TLA2TOOLS" tlc2.TLC -workers auto -cleanup \
    -metadir "$SALIDA/$nombre.meta" -config "$cfg" "$modulo.tla" > "$SALIDA/$nombre.out" 2>&1
  segundos=$(( $(date +%s) - inicio ))
  estados=$(grep -oE '[0-9.,]+ distinct states found' "$SALIDA/$nombre.out" | tail -1)
  if grep -q "No error has been found" "$SALIDA/$nombre.out"; then resultado=pasa
  elif grep -qE "is violated|Deadlock reached" "$SALIDA/$nombre.out"; then resultado=contraejemplo
  else resultado=error
  fi
  esperado=pasa
  grep -qi "se espera.*contraejemplo" "$cfg" && esperado=contraejemplo
  [ "$resultado" = "$esperado" ] && marca=ok || { marca=FALLO; mal=1; }
  echo "$marca $cfg: $resultado (esperado $esperado) · $estados · ${segundos}s"
done
exit $mal

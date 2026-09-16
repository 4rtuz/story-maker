#!/usr/bin/env sh
# Enlaza el contenido de ../my-factory dentro de .claude/ para que Claude Code lo cargue.
# Idempotente: se puede reejecutar cada vez que se anada algo a la fabrica.
#   sh scripts/link-factory.sh
# Windows necesita Modo Desarrollador (o admin) para crear symlinks.
set -e
export MSYS=winsymlinks:nativestrict

cd "$(dirname "$0")/.."
FACTORY=../my-factory
[ -d "$FACTORY" ] || { echo "no existe $FACTORY"; exit 1; }

# Enlaza $1 (ruta dentro de la fabrica) en .claude/$2/<basename>.
link() {
  dest=".claude/$2/$(basename "$1")"
  mkdir -p ".claude/$2"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "  omitido (propio del repo): $dest"
    return
  fi
  rm -f "$dest"
  # .claude/<x>/<y> esta a 2 niveles: ../../.. llega al padre de story-maker.
  ln -s "../../../my-factory/${1#$FACTORY/}" "$dest"
  echo "  $dest"
}

# Limpia enlaces rotos (algo borrado en la fabrica).
find .claude/skills .claude/agents .claude/commands -maxdepth 1 -type l 2>/dev/null \
  | while read -r l; do [ -e "$l" ] || { rm -f "$l"; echo "  roto, eliminado: $l"; }; done

echo "skills:"
find "$FACTORY" -name SKILL.md -not -path '*/.git/*' | while read -r f; do link "$(dirname "$f")" skills; done

echo "agents:"
find "$FACTORY" -path '*/agents/*.md' -not -path '*/.git/*' | while read -r f; do link "$f" agents; done

echo "commands:"
find "$FACTORY" -path '*/commands/*.md' -not -path '*/.git/*' | while read -r f; do link "$f" commands; done

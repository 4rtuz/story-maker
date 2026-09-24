"""Citas no literales de un delta frente al capítulo, con la misma comparación que aplicar-delta."""
import json, sys
from novela.dominio import frontmatter
from novela.dominio.texto import normalizar
delta = json.load(open(sys.argv[1], encoding="utf-8"))
cuerpo = frontmatter.partir(open(sys.argv[2], encoding="utf-8").read())[1]
texto = normalizar(cuerpo)
citas = [h.get("cita") for h in delta.get("libro_de_hechos", [])]
citas += [e.get("cita") for e in delta.get("linea_temporal", [])]
citas += [e.get("cita") for e in delta.get("conocimiento_lector", [])]
citas += [e.get("cita") for es in delta.get("conocimiento", {}).values() for e in es]
citas += [u.get("cita") for u in delta.get("hechos_usados", [])]
citas = [c for c in citas if c]
malas = [c for c in citas if normalizar(c) not in texto]
print(json.dumps({"citas": len(citas), "no_literales": len(malas), "ejemplos": malas[:3]}, ensure_ascii=False))

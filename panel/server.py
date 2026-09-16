"""Servidor del panel: solo stdlib, igual que el nucleo.

Sirve tres vistas (lanzar, progreso, lector) sobre una API minima. Las ordenes
que cambian algo —crear una ejecucion, responder una puerta, pedir el siguiente
paso— son siempre una llamada a `python -m harness`; el sondeo de progreso, en
cambio, no ejecuta nada: lee `estado.json` y `.intentos/` y devuelve lo que hay.

Lanzar agentes arranca el binding de Claude Code (`claude -p /novela`) como
subproceso y vuelca su stream a `.intentos/panel-run.jsonl`. El panel observa esa
orquestacion, no la sustituye.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import runs

STATIC = Path(__file__).resolve().parent / "static"
TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript",
         ".svg": "image/svg+xml", ".json": "application/json",
         ".woff": "font/woff", ".woff2": "font/woff2"}

# Herramientas que el orquestador necesita y ninguna mas: lee el contexto que le
# monta el nucleo, escribe la respuesta cruda del subagente y lanza subagentes.
# Los dos shells porque el primario depende de la plataforma (PowerShell en
# Windows, Bash en el resto). Cualquier otra orden pide permiso y se deniega:
# eso es lo que queremos, y el orquestador se recupera reintentando mas simple.
ALLOWED_TOOLS = ["Bash(python -m harness:*)", "PowerShell(python -m harness:*)",
                 "Read", "Write", "Task"]

MAX_BODY = 64 * 1024


class Launcher:
    """Un orquestador vivo por ejecucion, con su hilo de volcado al log."""

    def __init__(self, repo: Path, skip_permissions: bool = False):
        self.repo = repo
        self.skip_permissions = skip_permissions
        self.procs: dict[str, subprocess.Popen] = {}
        # ponytail: un solo lock para todas las ejecuciones. Con una decena de
        # runs sobra; si alguna vez estorba, uno por slug.
        self.lock = threading.Lock()

    @staticmethod
    def available() -> str:
        return shutil.which("claude") or ""

    def alive(self, slug: str) -> bool:
        proc = self.procs.get(slug)
        return bool(proc and proc.poll() is None)

    def command(self, slug: str) -> list[str]:
        cmd = [self.available() or "claude", "-p", self.prompt(slug),
               "--output-format", "stream-json", "--verbose"]
        if self.skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        else:
            cmd += ["--permission-mode", "acceptEdits", "--allowedTools", *ALLOWED_TOOLS]
        return cmd

    def prompt(self, slug: str) -> str:
        """El prompt de arranque. Para una ejecucion fuera de la raiz hay que
        decirle donde vive, porque las ordenes literales de la skill no llevan
        `--root`.

        ponytail: el encaminamiento va en el prompt y depende de que el
        orquestador lo respete. Si se vuelve un problema, la solucion es una
        skill que acepte `--root`, no tocar el nucleo.
        """
        if slug == runs.ROOT_SLUG:
            return "/novela"
        rel = f"{runs.RUNS_DIR}/{slug}"
        return ("/novela\n\n"
                f"Esta sesión trabaja sobre la ejecución `{rel}`, no sobre `novela/`.\n"
                f"Añade `--root {rel}` a TODAS las órdenes `python -m harness ...`, y usa\n"
                f"`{rel}/novela/.intentos/` para los archivos de contexto y de respuesta.")

    def start(self, slug: str) -> dict:
        with self.lock:
            if self.alive(slug):
                raise ValueError("Ya hay un orquestador en marcha para esta ejecución.")
            if not self.available():
                raise ValueError(
                    "No encuentro el binario `claude` en el PATH. Abre Claude Code en "
                    "este repositorio y escribe `/novela` a mano.")

            cfg = runs.load_cfg(self.repo, slug)
            log = runs.log_path(cfg)
            log.parent.mkdir(parents=True, exist_ok=True)

            proc = subprocess.Popen(
                self.command(slug), cwd=str(self.repo),
                env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                errors="replace", bufsize=1,
            )
            self.procs[slug] = proc
            threading.Thread(target=self._drain, args=(proc, log),
                             daemon=True, name=f"panel-{slug}").start()
            return {"pid": proc.pid, "orden": " ".join(self.command(slug)[:2]) + " …"}

    @staticmethod
    def _drain(proc: subprocess.Popen, log: Path) -> None:
        """Vuelca el stream tal cual llega. No lo interpreta: de eso se encarga
        `runs.events` al leerlo, para que una linea rara nunca tumbe el hilo."""
        try:
            with log.open("a", encoding="utf-8", newline="\n") as fh:
                for line in proc.stdout:  # type: ignore[union-attr]
                    fh.write(line if line.endswith("\n") else line + "\n")
                    fh.flush()
        finally:
            proc.wait()

    def stop(self, slug: str) -> dict:
        with self.lock:
            proc = self.procs.get(slug)
            if not proc or proc.poll() is not None:
                raise ValueError("No hay ningún orquestador en marcha.")
            proc.terminate()
            return {"detenido": proc.pid}


class Handler(BaseHTTPRequestHandler):
    server_version = "panel-novela"
    repo: Path
    launcher: Launcher

    # -- utilidades ---------------------------------------------------------
    def log_message(self, fmt, *args):  # silencio: el panel no es un access log
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload, code: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _error(self, code: int, message: str) -> None:
        self._json({"error": message}, code)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("Cuerpo de la petición demasiado grande.")
        if not length:
            return {}
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"JSON no válido: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Se esperaba un objeto JSON.")
        return data

    # -- estatico -----------------------------------------------------------
    def _static(self, name: str) -> None:
        # Frontera de confianza: nombre plano, sin separadores ni `..`, y solo
        # las extensiones que el panel sirve.
        if "/" in name or "\\" in name or name.startswith("."):
            return self._error(HTTPStatus.NOT_FOUND, "No encontrado.")
        path = STATIC / name
        if not path.is_file() or path.suffix not in TYPES:
            return self._error(HTTPStatus.NOT_FOUND, "No encontrado.")
        charset = "; charset=utf-8" if path.suffix in (".html", ".css", ".js") else ""
        self._send(HTTPStatus.OK, path.read_bytes(), TYPES[path.suffix] + charset)

    # -- rutas --------------------------------------------------------------
    def do_HEAD(self):  # noqa: N802
        self.do_GET()

    def do_GET(self):  # noqa: N802
        parts = [p for p in self.path.split("?")[0].split("/") if p]
        try:
            if not parts:
                return self._static("index.html")
            if parts[0] == "static" and len(parts) == 2:
                return self._static(parts[1])
            if parts[0] != "api":
                return self._error(HTTPStatus.NOT_FOUND, "No encontrado.")
            return self._get_api(parts[1:])
        except ValueError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except FileNotFoundError as exc:
            self._error(HTTPStatus.NOT_FOUND, str(exc))
        except Exception as exc:  # noqa: BLE001
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"{type(exc).__name__}: {exc}")

    def _get_api(self, parts: list[str]):
        if parts == ["runs"]:
            return self._json({
                "runs": [runs.summary(self.repo, s) for s in runs.discover(self.repo)],
                "claude": bool(Launcher.available()),
                **self._profiles(),
            })
        if len(parts) == 3 and parts[0] == "runs" and parts[2] == "estado":
            slug = parts[1]
            data = runs.snapshot(self.repo, slug)
            data["vivo"] = self.launcher.alive(slug)
            data["agente_en_curso"] = runs.running_agent(data["eventos"])
            return self._json(data)
        if len(parts) == 3 and parts[0] == "runs" and parts[2] == "capitulos":
            return self._json({"capitulos": runs.chapters(self.repo, parts[1])})
        if len(parts) == 4 and parts[0] == "runs" and parts[2] == "capitulos":
            if not parts[3].isdigit():
                raise ValueError("Número de capítulo no válido.")
            found = runs.chapter(self.repo, parts[1], int(parts[3]))
            if found is None:
                raise FileNotFoundError("Ese capítulo todavía no está escrito.")
            return self._json(found)
        return self._error(HTTPStatus.NOT_FOUND, "No encontrado.")

    def _profiles(self) -> dict:
        """Los perfiles declarados y cual esta activo. Sin lo segundo, el panel
        ofreceria el primero por orden alfabetico y una novela nueva saldria con
        un perfil que el autor no ha elegido."""
        raw = json.loads((self.repo / "novela" / "config.json").read_text(encoding="utf-8"))
        return {"perfiles": sorted(raw.get("perfiles", {})),
                "perfil_activo": raw.get("perfil_activo", "")}

    def do_POST(self):  # noqa: N802
        parts = [p for p in self.path.split("?")[0].split("/") if p]
        try:
            if not parts or parts[0] != "api":
                return self._error(HTTPStatus.NOT_FOUND, "No encontrado.")
            return self._post_api(parts[1:], self._body())
        except ValueError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except RuntimeError as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
        except Exception as exc:  # noqa: BLE001
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"{type(exc).__name__}: {exc}")

    def _post_api(self, parts: list[str], body: dict):
        if parts == ["runs"]:
            slug = (body.get("slug") or runs.slugify(body.get("titulo", ""))).strip()
            if not slug:
                raise ValueError("Hace falta un identificador.")
            return self._json(runs.create(self.repo, slug, body.get("idea", ""),
                                          body.get("perfil", "")), HTTPStatus.CREATED)

        if len(parts) != 3 or parts[0] != "runs":
            return self._error(HTTPStatus.NOT_FOUND, "No encontrado.")
        slug, action = parts[1], parts[2]
        if not runs.exists(self.repo, slug):
            raise ValueError(f"No existe la ejecución `{slug}`.")

        if action == "lanzar":
            return self._json(self.launcher.start(slug))
        if action == "parar":
            return self._json(self.launcher.stop(slug))
        if action == "puerta":
            return self._json(self._gate(slug, body))
        if action == "siguiente":
            # `harness next` tiene efectos laterales (cuota, bloqueo de
            # auditoría): solo se ejecuta cuando el autor lo pide, nunca en el
            # sondeo.
            rc, out = runs.cli(self.repo, runs.root_for(self.repo, slug), "next")
            return self._json({"codigo": rc, "salida": out.strip()})
        return self._error(HTTPStatus.NOT_FOUND, "No encontrado.")

    def _gate(self, slug: str, body: dict) -> dict:
        """Puerto P4: traslada la respuesta literal del autor al nucleo."""
        answer = str(body.get("respuesta", "")).strip()
        if not answer:
            raise ValueError("La puerta necesita una respuesta.")
        if len(answer) > 500:
            raise ValueError("Respuesta demasiado larga.")
        with self.launcher.lock:
            rc, out = runs.cli(self.repo, runs.root_for(self.repo, slug),
                               "gate", "--answer", answer)
        if rc != 0:
            raise RuntimeError(out.strip() or "El núcleo rechazó la respuesta.")
        return {"salida": out.strip()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="panel", description="Panel web del harness de novela.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--skip-permissions", action="store_true",
                    help="lanza el orquestador con --dangerously-skip-permissions")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / "novela" / "config.json").exists():
        print(f"ERROR: no encuentro `novela/config.json` bajo {repo}", file=sys.stderr)
        return 1

    Handler.repo = repo
    Handler.launcher = Launcher(repo, skip_permissions=args.skip_permissions)

    # Solo local: este servidor lanza subprocesos, no puede escuchar fuera.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Panel en {url}  (Ctrl+C para parar)")
    if not Launcher.available():
        print("AVISO: `claude` no está en el PATH; podrás crear y leer, no lanzar agentes.")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPanel detenido.")
    finally:
        server.server_close()
    return 0

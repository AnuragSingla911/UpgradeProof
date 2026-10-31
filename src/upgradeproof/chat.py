"""Local page that sends a GitHub URL and a prompt through the harness."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from upgradeproof.github_app import upgrade_repository

_PAGE = Path(__file__).resolve().parents[2] / "web" / "index.html"
_DEFAULT_URL = "https://github.com/AnuragSingla911/Java11to17UpgradeSample"


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    _default_jdks()
    page = _PAGE.read_text(encoding="utf-8")
    prompt = (Path(__file__).resolve().parents[2] / "test-data" / "chat-prompt.md").read_text(encoding="utf-8")
    page = page.replace("{{REPO_URL}}", _DEFAULT_URL).replace("{{PROMPT}}", _escape(prompt))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/index.html"):
                self.send_error(404)
                return
            body = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/upgrade":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                incoming = json.loads(self.rfile.read(length).decode("utf-8"))
                result = upgrade_repository(
                    str(incoming.get("repository", "")),
                    str(incoming.get("prompt", "")),
                    push=bool(incoming.get("push", True)),
                )
                status = 200
            except Exception as exc:  # noqa: BLE001
                result = {"verdict": "unresolved", "reason": str(exc), "journey": "", "pushed": False}
                status = 400
            payload = json.dumps(result).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args) -> None:
            print(f"{self.address_string()} {fmt % args}")

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"UpgradeProof chat at http://{host}:{port}")
    server.serve_forever()


def _default_jdks() -> None:
    for version in ("11", "17"):
        key = f"UPGRADEPROOF_JDK_{version}"
        if os.environ.get(key):
            continue
        for prefix in (Path(f"/opt/homebrew/opt/openjdk@{version}"), Path(f"/usr/local/opt/openjdk@{version}")):
            if (prefix / "bin" / "javac").is_file():
                os.environ[key] = str(prefix)
                break


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

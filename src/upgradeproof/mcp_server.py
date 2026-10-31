"""Minimal MCP stdio server over the same functions the CLI uses.

The server is an application-level file boundary. It is not an operating-system
sandbox. Run it on a workspace you already trust, or inside a disposable job
with no credentials.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from upgradeproof import __version__
from upgradeproof.checks import (
    classify_failure,
    parse_requirements,
    resolve_inside,
    validate_diff_text,
)

_PROTOCOL = "2024-11-05"
_READ_LIMIT = 12_000
_SEARCH_HITS = 20


def serve(root: Path) -> None:
    context = {"root": root.resolve(), "allow_network": False}
    while True:
        message = _read_message()
        if message is None:
            return
        response = handle(message, context)
        if response is not None:
            _write_message(response)


def handle(message: dict, context: dict) -> dict | None:
    method = message.get("method")
    request_id = message.get("id")
    if method and method.startswith("notifications/"):
        return None
    try:
        result = _dispatch(method, message.get("params") or {}, context)
    except PermissionError as exc:
        return _error(request_id, -32001, str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error(request_id, -32000, str(exc))
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _dispatch(method: str | None, params: dict, context: dict) -> dict:
    if method == "initialize":
        return {
            "protocolVersion": _PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "upgradeproof", "version": __version__},
        }
    if method == "tools/list":
        return {"tools": _tool_specs()}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        payload = _call_tool(str(name), arguments, context)
        return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}], "isError": False}
    raise ValueError(f"unsupported method {method}")


def _call_tool(name: str, arguments: dict, context: dict) -> dict:
    root: Path = context["root"]
    if name == "list_dependencies":
        text = resolve_inside(root, "requirements.txt").read_text(encoding="utf-8")
        return {"dependencies": parse_requirements(text)}
    if name == "classify_failure":
        return {"failure_class": classify_failure(str(arguments.get("log", "")))}
    if name == "validate_diff":
        reasons = validate_diff_text(str(arguments.get("diff", "")))
        return {"accepted": not reasons, "reasons": reasons}
    if name == "read_file":
        path = resolve_inside(root, str(arguments["path"]))
        if not path.is_file():
            raise FileNotFoundError(str(arguments["path"]))
        text = path.read_text(encoding="utf-8")
        truncated = len(text) > _READ_LIMIT
        return {"path": str(arguments["path"]), "text": text[:_READ_LIMIT], "truncated": truncated}
    if name == "search_code":
        return {"hits": search_code(root, str(arguments.get("query", "")))}
    if name == "package_metadata":
        return package_metadata(str(arguments["name"]), allow_network=bool(context.get("allow_network")))
    if name == "run_tests":
        return run_tests(root)
    raise ValueError(f"unknown tool {name}")


def search_code(root: Path, query: str) -> list[dict[str, object]]:
    if not query:
        return []
    hits: list[dict[str, object]] = []
    source = root / "src"
    if not source.exists():
        return []
    for path in sorted(source.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if query in line:
                hits.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "line": number,
                        "text": line.strip()[:200],
                    }
                )
                if len(hits) >= _SEARCH_HITS:
                    return hits
    return hits


def package_metadata(name: str, *, allow_network: bool) -> dict:
    """Local description unless the server was started with network allowed.

    Network is off by default so a tool call cannot spend money or reach PyPI
    by accident. There is still no paid-model call on this path.
    """

    payload: dict[str, object] = {"name": name, "network": "disabled"}
    if not allow_network:
        return payload
    import urllib.request

    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=15) as response:
        document = json.loads(response.read().decode("utf-8"))
    info = document.get("info") or {}
    payload["network"] = "pypi"
    payload["version"] = info.get("version")
    payload["license"] = info.get("license")
    payload["summary"] = info.get("summary")
    return payload


def run_tests(root: Path) -> dict:
    """Run the workspace's public tests. The caller cannot choose the path."""

    tests = root / "tests"
    if not tests.is_dir():
        return {"ok": False, "output": "workspace has no tests directory"}
    python = root / ".venv" / "bin" / "python"
    if not python.is_file():
        python = Path(sys.executable)
    completed = subprocess.run(
        [str(python), "-m", "pytest", "-p", "no:cacheprovider", "--tb=line", "-q", str(tests)],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    return {"ok": completed.returncode == 0, "failure_class": None if completed.returncode == 0 else classify_failure(output), "output": output[-4000:]}


def _tool_specs() -> list[dict]:
    return [
        {"name": "list_dependencies", "description": "Parse requirements.txt in the workspace.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "classify_failure", "description": "Classify a test or installer log.", "inputSchema": {"type": "object", "properties": {"log": {"type": "string"}}, "required": ["log"]}},
        {"name": "validate_diff", "description": "Reject diffs that edit tests or delete assertions.", "inputSchema": {"type": "object", "properties": {"diff": {"type": "string"}}, "required": ["diff"]}},
        {"name": "read_file", "description": "Read a file inside the workspace, size limited.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
        {"name": "search_code", "description": "Substring search under src/, at most 20 hits.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
        {"name": "package_metadata", "description": "Describe a package. Network lookup is off unless the server was configured to allow it.", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        {"name": "run_tests", "description": "Run the workspace tests directory. The path cannot be redirected.", "inputSchema": {"type": "object", "properties": {}}},
    ]


def _read_message() -> dict | None:
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("ascii").partition(":")
        headers[key.lower().strip()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def _write_message(payload: dict) -> None:
    raw = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def _error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

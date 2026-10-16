"""Local web UI (standard library only).

Three screens in one page: the student's phone, the family's phone and the
Glass Box in the middle that shows every workflow step, what the model saw,
the limits and the audit chain. Every action goes through Sandbox.act().

Security choices: binds to 127.0.0.1 only; every POST needs JSON plus the
custom X-StudyBridge header (a cross-site form cannot set it, which blocks
CSRF); request bodies are capped at 8 KB; responses carry a strict CSP and
the page renders all text with textContent, never innerHTML. The role
switch is a sandbox demo control: there is no user login (known risk).
"""
import json
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import PACKAGE_ROOT
from .security.audit import AuditLog
from .stories import STORY_BY_ID

STATIC = PACKAGE_ROOT / "static"
MAX_BODY = 8 * 1024
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_FILES = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/i18n.js": ("i18n.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/favicon.svg": ("favicon.svg", "image/svg+xml")}


def _audit_tail(path: Path, n: int = 40) -> list:
    if not path.exists():
        return []
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()][-n:]
    out = []
    for l in lines:
        r = json.loads(l)
        out.append({"seq": r["seq"], "event": r["event"], "ts": r["ts"], "hash": r["hash"][:10],
                    "prev": r["prev_hash"][:10], "data": json.dumps(r["data"], ensure_ascii=False)[:220]})
    return out


def _tamper_test(path: Path) -> dict:
    """Change one character in a COPY of the log and verify it. The real log is never touched."""
    tmp = Path(tempfile.mkdtemp()) / "audit_copy.jsonl"
    shutil.copy(path, tmp)
    lines = tmp.read_text(encoding="utf-8").splitlines()
    idx = next((i for i in range(len(lines) - 1, -1, -1) if '"event":"executed"' in lines[i]), len(lines) // 2)
    line = lines[idx]
    # A content change (not whitespace): the parsed record differs, so its hash no longer matches.
    lines[idx] = (line.replace("SANDBOX_SETTLED", "SANDBOX_SETTLEX", 1) if "SANDBOX_SETTLED" in line
                  else line.replace('"ts":"2', '"ts":"1', 1))
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = AuditLog(tmp).verify()
    res["changed_line"] = idx + 1
    return res


def _make_handler(sandbox):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code, body: bytes, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, default=str).encode())

        def _local(self, post=False) -> bool:
            """Only answer requests addressed to this machine. A DNS-rebinding page sends its own host name
            in Host, and a cross-site page sends its own Origin; both are refused."""
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
            if host not in _LOCAL_HOSTS:
                return False
            origin = self.headers.get("Origin")
            if post and origin and (urlsplit(origin).hostname or "").lower() not in _LOCAL_HOSTS:
                return False
            return True

        def do_GET(self):
            if not self._local():
                return self._json(403, {"error": "unexpected host"})
            self.path = urlsplit(self.path).path
            if self.path in _FILES:
                name, ctype = _FILES[self.path]
                return self._send(200, (STATIC / name).read_bytes(), ctype)
            with lock:
                if self.path == "/api/state":
                    return self._json(200, sandbox.snapshot())
                if self.path == "/api/stories":
                    return self._json(200, sandbox.stories())
                if self.path == "/api/audit/tail":
                    return self._json(200, _audit_tail(sandbox.audit.path))
                if self.path == "/api/audit/verify":
                    return self._json(200, sandbox.audit.verify())
            self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._local(post=True):
                return self._json(403, {"error": "unexpected host or origin"})
            if self.headers.get("X-StudyBridge") != "1" or \
                    not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._json(403, {"error": "missing required header"})
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                return self._json(400, {"error": "invalid Content-Length"})
            if length < 0 or length > MAX_BODY:
                return self._json(413, {"error": "request too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                return self._json(400, {"error": "invalid JSON"})
            if not isinstance(body, dict):
                return self._json(400, {"error": "invalid JSON"})
            with lock:
                if self.path == "/api/act":
                    args = body.get("args") if isinstance(body.get("args"), dict) else {}
                    resp = sandbox.act(str(body.get("actor", "")), str(body.get("action", "")), args)
                    return self._json(200, {"response": resp.to_dict(), "state": sandbox.snapshot()})
                if self.path == "/api/story":
                    sid, idx = str(body.get("id", "")), body.get("step", 0)
                    if sid not in STORY_BY_ID or not isinstance(idx, int) or not 0 <= idx < len(STORY_BY_ID[sid].steps):
                        return self._json(400, {"error": "unknown story or step"})
                    step = sandbox.story_step(sid, idx)
                    return self._json(200, {"step": step, "state": sandbox.snapshot()})
                if self.path == "/api/audit/tamper-test":
                    return self._json(200, _tamper_test(sandbox.audit.path))
            self._json(404, {"error": "not found"})

    return Handler


def serve(sandbox, port: int = 8765, host: str = "127.0.0.1"):
    server = ThreadingHTTPServer((host, port), _make_handler(sandbox))
    a = sandbox.agent
    print(f"StudyBridge web UI on http://{host}:{port}  (tier {a.session.granted_tier.name}, "
          f"LLM {'on: ' + a.llm.model if a.llm else 'off'})  Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

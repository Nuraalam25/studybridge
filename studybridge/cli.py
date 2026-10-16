"""Command-line entry points: chat, demo, web, verify-audit, stories."""
import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

from . import DEFAULT_PROFILE, PROJECT_ROOT
from .agent import StudentFinanceAgent
from .config import OLLAMA_URL
from .llm import OllamaClient
from .security.audit import AuditLog
from .security.permissions import Tier
from .wallet import SandboxWallet


def build_agent(args) -> StudentFinanceAgent:
    llm = None
    if args.llm:
        client = OllamaClient(base_url=os.environ.get("OLLAMA_URL", OLLAMA_URL), model=args.model)
        if client.available():
            llm = client
        else:
            print(f"[warn] Ollama model '{args.model}' not reachable; running rules-only.", file=sys.stderr)
    today = date.fromisoformat(args.today) if args.today else None
    return StudentFinanceAgent(SandboxWallet.from_file(args.profile), AuditLog(args.audit),
                               granted_tier=Tier[args.tier], llm=llm, today=today)


def cmd_chat(args):
    agent = build_agent(args)
    print("StudyBridge sandbox (you are the student). Commands: /confirm <id>, /cancel <id>, /wallet, "
          "/verify, /quit\nFamily actions (sandbox only, from this screen): /approve <REQ-id>, /reject <REQ-id>")
    while True:
        try:
            msg = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg in ("/quit", "/exit"):
            break
        if msg.startswith("/confirm "):
            resp = agent.confirm(msg.split(maxsplit=1)[1])
        elif msg.startswith("/cancel "):
            resp = agent.cancel(msg.split(maxsplit=1)[1])
        elif msg.startswith(("/approve ", "/reject ")):
            # The actor comes from the command, not from chat text.
            resp = agent.family_decide(msg.split(maxsplit=1)[1], msg.startswith("/approve"), actor="family")
        elif msg == "/wallet":
            resp = agent.handle("show my wallet balance")
        elif msg == "/verify":
            print(agent.audit.verify())
            continue
        else:
            resp = agent.handle(msg)
        print(f"\nstudybridge> {resp.text}")


def cmd_verify(args):
    result = AuditLog(args.audit).verify()
    print(result)
    sys.exit(0 if result["ok"] else (2 if result.get("error") else 1))   # 2 = no log found, 1 = chain broken


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studybridge")
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE))
    ap.add_argument("--audit", default=str(PROJECT_ROOT / "var" / "audit.jsonl"))
    ap.add_argument("--tier", default="ADVISE", choices=[t.name for t in Tier if t < Tier.ADMIN])
    ap.add_argument("--llm", action="store_true", help="use local Ollama for parsing and explanations")
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD) for reproducible runs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("chat")
    sub.add_parser("verify-audit")
    sub.add_parser("stories", help="list the 31 test stories")
    demo = sub.add_parser("demo")
    demo.add_argument("--out", default=str(PROJECT_ROOT / "evidence"))
    web = sub.add_parser("web")
    web.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    web.add_argument("--host", default="127.0.0.1", help="keep 127.0.0.1 unless inside a container")
    args = ap.parse_args(argv)
    if not args.today:      # lets a hosted demo pin the sandbox date without a command-line flag
        args.today = os.environ.get("STUDYBRIDGE_TODAY") or None

    if args.cmd == "chat":
        cmd_chat(args)
    elif args.cmd == "verify-audit":
        cmd_verify(args)
    elif args.cmd == "demo":
        from .demo import run_demo
        run_demo(args, Path(args.out))
    elif args.cmd == "stories":
        from .stories import GROUPS, STORIES
        for s in STORIES:
            print(f"{s.id}  {GROUPS[s.group]:24s} {s.title}")
    elif args.cmd == "web":
        from .sandbox import Sandbox
        from .web import serve
        probe = build_agent(args)
        start = datetime.fromisoformat(args.today + "T09:00") if args.today else None
        # The Qwen switch on the screen turns this client on; it is only used if Ollama answers then.
        client = probe.llm or OllamaClient(base_url=os.environ.get("OLLAMA_URL", OLLAMA_URL), model=args.model)
        sandbox = Sandbox(args.profile, probe.audit, llm=probe.llm, tier=Tier[args.tier], start=start,
                          ticking=True, llm_client=client)
        serve(sandbox, args.port, args.host)

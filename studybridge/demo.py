"""Scripted sandbox run that produces the execution-evidence bundle.

It plays the 31 stories of plan v3 (studybridge/stories.py) through the same
Sandbox.act() entry point the web UI uses. Output folder evidence/run_<timestamp>/:
  transcript.md            every step: actor, request, outcome code, answer, guard cuts
  audit.jsonl              the hash-chained, masked audit log of the whole run
  audit_tampered_copy.jsonl one character changed in an 'executed' record
  summary.json             per-story results, counts, balances, verification, tamper test
"""
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import __version__
from .config import OLLAMA_URL
from .llm import OllamaClient
from .sandbox import Sandbox
from .security.audit import AuditLog
from .stories import GROUPS, STORIES

ACTOR_LABEL = {"student": "Student", "family": "Family", "operator": "Operator"}


def _request_text(step) -> str:
    a = step["args"]
    if step["action"] == "chat":
        return f"`{a['message']}`"
    if step["action"] == "advance_clock":
        return f"*sandbox clock +{a['hours']} h*"
    return f"`{step['action']}` " + ", ".join(f"{k}={v}" for k, v in a.items())


# Information requests (Topic C features outside the payment stories): fixed request -> expected intent.
INFO_REQUESTS = [
    ("compare the cheapest way to send 50000 BDT to CNY within 1 day", "compare_remittance"),
    ("plan my tuition payment", "tuition_plan"),
    ("how can I build my credit history", "credit_plan"),
    ("show my spending insights", "spending_insights"),
    ("show my wallet balance", "wallet_overview"),
]


def run_demo(args, out_root: Path):
    llm = None
    if args.llm:
        client = OllamaClient(base_url=os.environ.get("OLLAMA_URL", OLLAMA_URL), model=args.model)
        llm = client if client.available() else None
        if llm is None:
            print(f"[warn] Ollama model '{args.model}' not reachable; running rules-only.", file=sys.stderr)
    mode = "qwen" if llm else "rules"          # named after what really ran, not after the flag
    run_id = datetime.now().strftime(f"run_%Y%m%d_%H%M%S_{mode}")
    out = out_root / run_id
    n = 2
    while out.exists():                     # never append to an earlier run's audit log
        out = out_root / f"{run_id}_{n}"
        n += 1
    run_id = out.name
    out.mkdir(parents=True)
    audit = AuditLog(out / "audit.jsonl")
    start = datetime.fromisoformat((args.today or "2026-10-13") + "T09:00")
    sandbox = Sandbox(args.profile, audit, llm=llm, start=start)

    md = [f"# StudyBridge sandbox run `{run_id}`", "",
          f"- version {__version__}; sandbox clock starts {start.isoformat(timespec='minutes')} for every story",
          f"- LLM: {'Ollama ' + llm.model if llm else 'off (rules-only parser, template explanations)'}",
          "- 31 stories from plan v3; each starts from a fresh copy of `data/sample_profile.json`",
          "- All money movement is simulated; no real account is touched.", ""]
    results, codes = [], Counter()
    guard_cuts = 0
    for story in STORIES:
        steps = sandbox.run_story(story.id)
        ok = all(s["ok"] for s in steps)
        results.append({"story": story.id, "title": story.title, "group": GROUPS[story.group],
                        "outcome": steps[-1]["response"]["code"], "expected_outcomes_met": ok,
                        "codes": [s["response"]["code"] for s in steps]})
        md += [f"## {story.id}. {story.title}", "", f"*{story.shows}*", ""]
        if story.setup:
            md += [f"> Story setup (sandbox only): `{json.dumps(story.setup)}`", ""]
        for s in steps:
            r = s["response"]
            codes[r["code"]] += 1
            guard_cuts += len(r.get("guard_removed") or [])
            mark = "✅" if s["ok"] else f"❌ expected {s['expect']}"
            md += [f"**{ACTOR_LABEL[s['actor']]}** {_request_text(s)} → **{r['code']}** {mark}  ",
                   f"<sub>{s['caption']}" + (f" · parser: {r['parse_source']}" if s["action"] == "chat" else "")
                   + "</sub>", "", "```", r["text"], "```", ""]
            if r.get("guard_removed"):
                md += ["Sentences removed by the grounding guard:", ""] + \
                      [f"- ~~{x}~~" for x in r["guard_removed"]] + [""]
        md += [f"Story result: {'all expected outcomes met' if ok else 'MISMATCH'}", ""]
        print(f"[{story.id}] {'ok  ' if ok else 'FAIL'} {story.title:40s} {' -> '.join(results[-1]['codes'])}")

    md += ["## Information requests", "",
           "*Topic C features outside the payment stories: remittance comparison, tuition planner, credit "
           "readiness, spending insights and the wallet. Each starts from a fresh sandbox.*", ""]
    info = []
    for request, intent in INFO_REQUESTS:
        sandbox.reset()
        r = sandbox.act("student", "chat", {"message": request}).to_dict()
        ok = r["intent"] == intent and not r["blocked"]
        guard_cuts += len(r.get("guard_removed") or [])
        info.append({"request": request, "expected_intent": intent, "intent": r["intent"], "code": r["code"],
                     "as_expected": ok})
        md += [f"**Student** `{request}` → intent **{r['intent']}** {'✅' if ok else '❌ expected ' + intent}  ",
               f"<sub>parser: {r['parse_source']}</sub>", "", "```", r["text"], "```", ""]
        if r.get("guard_removed"):
            md += ["Sentences removed by the grounding guard:", ""] + [f"- ~~{x}~~" for x in r["guard_removed"]] + [""]
        print(f"[info] {'ok  ' if ok else 'FAIL'} {request}")

    verification = audit.verify()
    head = {"records": verification.get("records"), "head_hash": audit._last}
    tampered = out / "audit_tampered_copy.jsonl"
    shutil.copy(out / "audit.jsonl", tampered)
    lines = tampered.read_text(encoding="utf-8").splitlines()
    idx = next(i for i, l in enumerate(lines) if '"event":"executed"' in l)
    lines[idx] = lines[idx].replace("SANDBOX_SETTLED", "SANDBOX_SETTLEDX", 1)
    tampered.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tamper_result = AuditLog(tampered).verify()

    passed = sum(r["expected_outcomes_met"] for r in results)
    summary = {"run_id": run_id, "version": __version__, "clock_start": start.isoformat(),
               "llm": llm.model if llm else None, "stories": len(results), "stories_as_expected": passed,
               "outcome_codes": dict(sorted(codes.items())), "executed": codes["EXECUTED"],
               "guard_sentences_cut": guard_cuts, "results": results,
               "info_requests": info, "info_requests_as_expected": sum(i["as_expected"] for i in info),
               "audit_head": head,
               "audit_verification": verification, "tamper_test_on_copy": tamper_result,
               "python": sys.version.split()[0]}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md += ["## Result", "", f"- Stories with all expected outcomes: {passed}/{len(results)}",
           f"- Information requests answered as expected: {sum(i['as_expected'] for i in info)}/{len(info)}",
           f"- Audit head (to detect a truncated log later): {head['records']} records, hash {head['head_hash']}",
           f"- Executed payments: {codes['EXECUTED']}; sentences cut by the guard: {guard_cuts}",
           f"- Audit chain verification: {verification}",
           f"- Tamper test (one character changed in a copy): {tamper_result}", ""]
    (out / "transcript.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n{passed}/{len(results)} stories as expected. Evidence written to {out}")
    print(json.dumps({"audit": verification, "tamper_test": tamper_result}, default=str))
    return out

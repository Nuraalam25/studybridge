# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The parent folder's `../CLAUDE.md` summarises the team's confirmed plan. This code implements plan v4 (v3 plus the 16 October review fixes and small fixes) as v0.3.0 (the v3 changes over v2 are listed in `docs/TECHNICAL_DOCUMENTATION.md` §3.2 and §3.5).

## Commands

Python 3.10+, **standard library only** (no requirements file, no third-party deps; keep it that way). Local git repo (no remote); `pyright studybridge` type-checks, but most of its errors are false positives from `= None` defaults and `fail()` in `gate1` not being typed `NoReturn`.

```bash
python -m unittest discover -s tests -t .                                  # all 146 tests (~1s)
python -m unittest tests.test_payments.TestStories                         # the 31 stories
python -m unittest tests.test_security.TestInjection.test_detector         # one test
python -m studybridge --today 2026-10-13 --tier TRANSACT web               # UI on http://127.0.0.1:8765
python -m studybridge --today 2026-10-13 demo                              # 31 stories + 5 info requests -> evidence/run_<timestamp>_rules/ (--out DIR for trial runs)
python -m studybridge --llm --today 2026-10-13 demo                        # same with qwen2.5:7b -> run_<timestamp>_qwen/ (~5-6 min total)
python -m studybridge --audit <path.jsonl> verify-audit                    # exit 1 if the hash chain is broken
```

Global flags go **before** the subcommand. `--tier` defaults to ADVISE, which cannot pay; use TRANSACT for payments. The UI reads static files from disk on every request, but Python changes need a server restart.

## Architecture

Core rule: **AI suggests, code decides, the student confirms last.** Qwen only parses and explains, and never owns a number, a permission, an actor or an approval.

- [studybridge/agent.py](studybridge/agent.py) runs the plan's 11-step workflow (the `PIPELINE` constant; step keys "1"–"11", with "6a" for tuition and "6b/7b/8b" for everyday). `handle()` is for student chat. `family_decide()`, `confirm()` and the other actor methods sit outside chat. Each message opens a **case** (`self.cases`) whose steps, Gate 1 checks and `glass` (rules vs Qwen vs final parse, explanation cuts) feed the UI's Glass Box. `_step(case, key, status, detail)` is how a step gets recorded. Student actions outside chat: `acknowledge()` (opens a tuition approval; only then is the 2-minute confirmation created), `request_limit_raise()`, `submit_account_change()`. When the rules reader and Qwen disagree on a money intent, `_check_reading()` returns `CLARIFY` with `reading`; the UI resends with `reading_confirmed: true`, which uses the rules reading (injection check and gates still run).
- [studybridge/payments.py](studybridge/payments.py) `PaymentBook` holds the rules on stored data: `gate1()` raises `PaymentBlocked(code, detail)` carrying `.checks`, plus `everyday_route()` (family limit, then `bank_check()`: the USD 300 bank limit is a daily card total), `find_allowance()` (single-use or monthly rent, keyed by the bill's due month), `bank_review()`, `decide()` (also limit raises and account changes, which need `phone_verified` and then a 24 h hold applied in `expire()`), and the expiry logic. Payee, account and payee type always come from `data/sample_profile.json` (payees, invoices, documents, family), never from the message; the amount too, except food/QR (capped CNY 300). Reported new account numbers live in `_new_accounts`, never in requests or snapshots.
- [studybridge/reasons.py](studybridge/reasons.py): every refusal code with its meaning and fix step. A new code must be added here, because `PaymentBlocked` asserts that it exists. Non-refusal outcomes (`READY_TO_CONFIRM`, `AWAITING_FAMILY`, `EXECUTED`…) are in `STATUS`.
- [studybridge/sandbox.py](studybridge/sandbox.py) `Sandbox.act(actor, action, args)` is the single entry point for the web UI, the stories and the demo. The actor comes from the screen. `ACTOR_ACTIONS` in [security/permissions.py](studybridge/security/permissions.py) decides who may do what. Tier (`TOOL_TIERS`) is a separate check. `MONEY_MOVING` intents need both parsers to agree and fail closed on bad model output.
- [studybridge/stories.py](studybridge/stories.py): the 31 stories as data (step = actor, action, args, caption, expected code; `$request`/`$pending`/`$used` placeholders). `tests/test_payments.py`, `demo.py` and the UI autopilot all run them. If you change behaviour, update the expected codes here.
- [studybridge/clock.py](studybridge/clock.py) `SandboxClock`: all expiries read it. Tests, demo and stories use a frozen start (2026-10-13 09:00); the web UI ticks, and the operator can advance it.
- Funding: tuition (institution) is paid with the existing student-file remittance (`wallet.send` via the cheapest provider that delivers the exact invoice amount). Everyday payments use `wallet.card_pay` (debits BDT). Hard caps (BDT 400k/600k) and balance are checked in `agent._guardrails`.
- `tuition.plan()` takes the open tuition invoices (one full transfer each, no splitting). The guard (`enforce_grounding`) also checks number labels (`_labelled`) and takes `status_words_forbidden(result)` from `agent.py` on top of `FORBIDDEN_TERMS`.
- Unchanged v0.1 pieces: `fx`, `remittance`, `credit`, `budget` and the hash-chained audit log with masking.
- [web.py](studybridge/web.py) and `static/` (`index.html`, `app.js`, `style.css`, `i18n.js`): stdlib server with a strict CSP (no inline script/style, so use CSSOM for dynamic styles), the `X-StudyBridge: 1` header on POSTs, and `textContent` only. Endpoints: `/api/state`, `/api/act`, `/api/story`, `/api/stories`, `/api/audit/{tail,verify,tamper-test}`. `/?story=A6` (or `all`) autoplays.

## Tests and evidence

- `tests/test_data.py` checks `data/sample_profile.json` (re-derives each invoice's Gate 1 code independently) and fails if any code in `reasons.py` is not exercised by a test or story. Run it after any data or reason-code change.
- Qwen sees only `llm_view(result)` (agent.py): free-text keys (`note`, `purpose`, `memo`, `warnings`, `summary`, ...) are stripped. Keep it that way; `test_note_purpose_and_memos_never_reach_qwen` records every prompt.
- `PaymentBook` shares the wallet's payee dicts (`payees=wallet.beneficiaries`), so an applied account change is what the wallet pays. Don't copy them.
- The web handler refuses non-local `Host`/`Origin` (DNS rebinding); tests start it on a random port.
- Tests use a `FakeLLM` (no Ollama) and a frozen clock. Guard regression tests contain real qwen2.5:7b sentences; don't weaken them.
- Evidence comes only from `python -m studybridge demo` after the code freeze. Never hand-edit logs. Keep [evidence/README.md](evidence/README.md) counts in sync with `summary.json`. v0.1 runs stay unedited in `evidence/archive_v0.1/`; the v0.2 runs (`evidence/run_20261015_*`) are labelled as the earlier version. For trial runs use `demo --out <scratch dir>` so `evidence/` only holds post-freeze runs.
- When behaviour changes, keep the counts and claims in [README.md](README.md), [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md) and [docs/SECURITY_SELF_ASSESSMENT.md](docs/SECURITY_SELF_ASSESSMENT.md) in sync, along with their BUILT / ASSUMPTION / TEAM-STATED labels.

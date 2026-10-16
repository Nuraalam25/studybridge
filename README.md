# StudyBridge — Cross-border & Student Finance Assistant

**Topic C** submission. StudyBridge is a three-gate safe payment assistant for Bangladeshi students
abroad and the families who fund them. The demo persona is a fictional Bangladeshi student in
Shenzhen: her family in Dhaka funds her in BDT, while her tuition, rent and shopping are paid in CNY.

> **Sandbox only.** All rates, fees, invoices and accounts are illustrative sample data
> (`studybridge/config.py`, `data/sample_profile.json`). No real money or account is touched.
> The project makes no compliance claim.

## What it does

| Pain point | What StudyBridge does |
|---|---|
| **Unsafe payments** (scams, wrong accounts, bank limits) | Every payment passes up to three gates: **(1)** a real invoice, the payee's verified account and ready documents; **(2)** the family's approval, or the family daily limit plus an **allowance** (single-use, or monthly for rent), with a simulated bank review when the day's card total passes the bank limit; **(3)** the student's own final confirmation. Every refusal has a reason code and a fix step. A changed bank account is paid only after the family checks it by phone and a 24-hour wait. |
| Remittances | Ranks providers by **what the recipient actually gets**, including the hidden FX mark-up |
| Tuition payments | Plans one transfer per unpaid tuition invoice, for the full amount (the university bills a year at a time), and pays it only against the stored invoice |
| Credit building | A transparent 0–100 readiness index for a thin credit file, plus concrete next actions |
| Multi-currency management | Wallet in several currencies; spending by category, monthly burn and runway (from the sample transaction history) |

## Design principle: AI suggests, code decides, the student confirms last

- The local LLM (**Ollama `qwen2.5:7b`**, optional) only (1) reads the request into a strict form
  (intent, amount, currencies, payee, invoice id) and (2) writes up to three plain sentences.
- For money actions, a rules reader must agree with the model on the intent and on every field both read
  (payee, invoice id, amount). If they disagree, nothing is prepared and the student is shown the rules
  reader's reading to confirm. The model's values must also appear in the message (its payee must be
  named there, its amount written there). If the model's output is unusable,
  money actions **fail closed**. With the model off (rules-only mode), the rules reader decides alone.
- Payee and account always come from **stored data**. The amount does too, except for food and QR
  payments, which have no invoice: their amount comes from the message and is capped at CNY 300.
- The model sees structured result fields only. Invoice memos and purposes, the student's notes and
  transaction memos are never sent to it.
- **Tier** (what the assistant may do), **actor** (student or family, set only by the screen) and
  **allowance** (a family approval for one purchase) are three separate ideas.
- Every step is written to a **hash-chained audit log** with masked account numbers.

See [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md) and
[docs/SECURITY_SELF_ASSESSMENT.md](docs/SECURITY_SELF_ASSESSMENT.md).

## Quick start

Requires Python 3.10+. There are **no third-party dependencies**; only the standard library is used.

```bash
git clone https://github.com/Nuraalam25/studybridge.git && cd studybridge
python -m unittest discover -s tests -t .                      # 153 tests
python -m studybridge --today 2026-10-13 --tier TRANSACT web    # http://127.0.0.1:8765
python -m studybridge --today 2026-10-13 demo                   # the 31 stories -> evidence/
python -m studybridge stories                                   # list the 31 stories
python -m studybridge --tier TRANSACT chat                      # terminal chat
```

On macOS and Linux, use `python3` if `python` is not found. On Windows, use `py` if `python` opens the Microsoft Store.

### The web UI

One page with three screens:

- **Student phone** (left): chat with the assistant; a notification when the family approves tuition
  (the 2-minute confirmation starts when the student opens it); final-confirmation cards with a
  2-minute ring; **Ask to raise my limit** (one day, with a note for the family).
- **Glass Box** (centre): the 11 workflow steps lighting up as they run, coloured by who acts
  (student, Qwen, code, simulated bank, family). It also shows the Gate 1 checks, what the rules
  reader and Qwen proposed and what code actually used, the limits, and the live audit chain with
  **Verify** and **Tamper test (on a copy)**.
- **Family phone** (right): approval inbox (tuition, allowances, monthly rent, one-day limit raises
  with the student's note, new bank accounts with an "I called the number on file" check), daily
  limit slider (CNY 500–1,000), documents, open allowances. Its labels and buttons switch to Bangla
  (invoice details, document names and warnings stay in English; the Bangla text still needs a native
  speaker's proofreading).

Demo controls in the top bar: the **sandbox clock** (+1 h / +25 h / +73 h shows expiries),
**Assistant can** (the permission tier in plain words: Rates only = PUBLIC, See my wallet = READ, Plan
with me = ADVISE, Make payments = TRANSACT; a refused request offers the missing permission in one
click), the Qwen switch, a light/dark switch (light by default), Reset, and **Play stories**, which plays any of the 31 stories step by step through
the real app. To start a story on page load (useful for recording the video), open
`http://127.0.0.1:8765/?story=A6`, `?story=B1,B2,B6` or `?story=all`, optionally with `&speed=2600`
(presenter), `1400` (normal) or `500` (fast).

### Optional: local LLM

```bash
ollama pull qwen2.5:7b
python -m studybridge --llm --today 2026-10-13 --tier TRANSACT web
```

If Ollama is not reachable, StudyBridge logs a warning and runs rules-only. Every feature still works.
In the web UI, the **Qwen** button in the top bar switches the model on and off without a restart; if
Ollama is not running, switching on is refused and the app stays rules-only.

### Options

| Flag | Meaning |
|---|---|
| `--tier PUBLIC\|READ\|ADVISE\|TRANSACT` | Permission tier granted to the session (default `ADVISE`, which cannot move money) |
| `--llm` / `--model` | Use Ollama for intent parsing and explanations |
| `--today YYYY-MM-DD` | Start the sandbox clock on this date (09:00) for reproducible runs |
| `--profile path.json` | Use another sandbox profile |
| `--audit path.jsonl` | Audit log location (default `var/audit.jsonl`) |
| `web --port N --host H` | Web UI port (default 8765) and bind address (keep `127.0.0.1` outside a container) |

`python -m studybridge --audit <file> verify-audit` checks the hash chain. It exits 1 if a record was
changed, and 2 if there is no log at that path.

## Deployment

**Local (recommended for the sandbox):** the commands above. The web server binds to `127.0.0.1` only.

**Docker (optional packaging, not required):**

```bash
docker build -t studybridge .
docker run --rm -p 127.0.0.1:8765:8765 studybridge
```

Do not expose the web UI to the internet. It has no user authentication, because it is a
single-user sandbox (see the known-risk list).

**Hosted demo (optional, sandbox only):** `render.yaml` deploys the Docker image to Render for a
public demo. Set `STUDYBRIDGE_ALLOWED_HOSTS` to the service's host name (the host check refuses every
other name; by default only local names are allowed) and keep `STUDYBRIDGE_TODAY=2026-10-13`. Anyone with the link
shares one sandbox, can reset it and can change the tier, and the state resets when the service restarts or
sleeps. There is no real money. Qwen needs a local Ollama, so the hosted demo runs rules-only.

## Example requests

```
pay invoice INV-0003                         tuition: family approves, then you confirm
pay 38 CNY at the canteen                    food: inside the family daily limit
request an allowance for quote Q-TM-0042     fridge: bank review, then family approval
pay quote Q-TM-0042                          uses the allowance; you confirm last
pay rent bill RENT-2026-11                   above the daily limit -> request an allowance
request a monthly allowance for RENT-2026-11 one family approval covers one rent bill a month
pay rent bill RENT-2026-11B                  changed bank details -> report them to the family
pay invoice INV-0004                         look-alike account -> BLOCKED
pay invoice INV-0011                         agent + "pay today or lose your seat" -> BLOCKED
show my payment status
plan my tuition payment
compare the cheapest way to send 50000 BDT to CNY within 1 day
```

## Repository layout

```
studybridge/
  agent.py          the 11-step workflow; Glass Box cases
  payments.py       payee types, Gate 1, allowances, limit raises, account changes, bank review
  reasons.py        reason codes with meaning and fix step
  sandbox.py        one session, three actors (student, family, operator); story runner
  stories.py        the 31 test stories as data
  clock.py          sandbox clock (approval windows, expiries)
  config.py         sandbox rates, provider archetypes, limits
  money.py fx.py    Decimal money and FX quotes
  remittance.py     provider comparison + closed-form inverse
  tuition.py        tuition planner (one full transfer per invoice)
  credit.py         credit-building readiness index
  budget.py         spending insights, runway, anomaly and memo scan
  wallet.py         sandbox multi-currency wallet (idempotent operations)
  llm.py            Ollama client (stdlib urllib)
  security/
    permissions.py  tiers, actor permissions, allowlist, limits
    guard.py        grounding guard, injection and pressure-wording detectors
    audit.py        hash-chained audit log, PII masking
  web.py static/    local web UI (strict CSP, CSRF header, textContent rendering)
  demo.py           scripted run of the 31 stories that writes the evidence
tests/              153 unit tests
docs/               technical documentation, security self-assessment
evidence/           sandbox operation logs; v0.1 runs in evidence/archive_v0.1
data/               fictional sample profile, invoices and payees
```

## The 31 test stories

| Group | Stories |
|---|---|
| A. Normal payments (7) | yearly tuition approved (+ replay refused); tuition rejected; food; QR; rent with a monthly allowance; fridge allowance full chain; raise the limit for a birthday |
| B. Fraud and blocks (9) | agent account; look-alike account; changed account details; amount mismatch; duplicate invoice; "pay today or lose your seat"; the "food" label trick; personal wallet on a tuition invoice; university "changed bank details" caught by the phone check |
| C. Documents and approvals (6) | progress proof missing; invoice not found; family approval expired; allowance expired; wrong merchant; new bank details checked by phone |
| D. Attacks (6) | instruction hidden in an invoice; "ignore your rules"; student approves as family; allowance reused; badly formed AI output; the two readers disagree |
| E. Edge cases (3) | insufficient balance; unclear request; daily bank limit |

`tests/test_payments.py` plays all 31 and checks every expected outcome code.
`tests/test_security.py` and `tests/test_core.py` keep the v0.1 checks (tiers, confirmation flow,
injection, LLM hardening, grounding guard, audit tamper detection, algorithms). `tests/test_data.py`
(ported from Nura's data tests) checks the sample data and that every reason code is exercised.

## Team

East West University, Bangladesh

- Rafikul Islam Provat
- Mehazabin Hossain Lamiha
- Ariana Ziauddin
- Nura Alam

## Licence

MIT. Sample data is fictional.

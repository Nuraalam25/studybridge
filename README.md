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

- The LLM (**Ollama `qwen2.5:7b`** locally, or a hosted Qwen such as Groq's; optional) only (1) reads the request into a strict form
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
git clone https://github.com/MehazabinLamiha/StudyBridge.git && cd StudyBridge
python -m unittest discover -s tests -t .                      # 254 tests
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

Also on screen (built by Nura, merged 17 October): **Try to scam it** (ready-made attacks and a
free-text box, each sent through the normal student chat, with a scoreboard where "money moved without both"
stays 0); the **Invoice X-ray** (**Why?** on a suspicious bill: the wrong digit, the missing letter, pressure
wording and instructions aimed at the AI); a **scams stopped** counter beside the logo; the family phone's
**Stopped for your student** list with every reason in Bangla; and Banglish/Bangla input (works fully with
Qwen off; with Qwen on, some Bangla messages end as a question back). After a blocked scam bill, the chat
offers one tap to pay the payee's own bill instead.

New in v0.4 (18 October):

- **What Qwen does is visible, and its absence is too.** The Glass Box has a Qwen card: which reader (rules or
  Qwen) read each message, whether Qwen was asked, and what it was sent. With Qwen on, a money request that only
  Qwen reads (the rules reader finds no payment) is offered back to the student as a question written by code,
  never run on Qwen's say-so. Attacks are stopped *before* Qwen and the Glass Box says so.
- **Try to scam StudyBridge** now has 35 ready-made attacks in seven groups, labelled with the OWASP Top 10 for LLM
  Applications (2025) where one applies: payment scams, five patterns copied from public reports (each links to its
  source page), prompt injection (spaced letters, leetspeak, Banglish, base64, role-play,
  a hidden instruction in a bill), secret and system-prompt requests, excessive agency (claiming to be the family
  or admin), markup, and floods. Free text is recognised and named. When an attack is caught the whole screen
  turns dark red with a banner naming the threat; it clears by itself after a few seconds.
- **Invoice lab** (second tab of the same panel): build any bill (payee, amount, issuer name, account, note) and
  try to pay it, or let the code make random bills. A random bill is a genuine bill changed in one known way; the
  plan decides what must happen, and the code compares. "Check 100 random bills" runs in a throwaway sandbox.
- **Scam check** (student Home → "Check a message"): paste a message and see which words look like a scam
  (pressure, a stranger offering to pay, fake police, secrecy, changed bank details, a refund that needs money first,
  account numbers the family never saved). It never says "safe", never sends the pasted text to Qwen and never writes
  it to the audit log. **Spot the scam** is an 8-message quiz that reveals what gave each message away, with the
  public report it copies.
- **Family safe word** (family Settings): the family agrees a word with the student offline. With it set, approving
  CNY 10,000 or more, a changed bank account, or a request with warnings needs it; three wrong tries lock it for
  15 minutes; only a salted hash is kept. The app cannot tell who is calling: it stops one-tap approval under pressure.
- **Save a new payee** (family Settings): a payee saved now can be paid only after 48 hours.
- **Save report (.md)** in the scam panel: a plain-text record of the session's attempts (not demo evidence).
- **Problem research** with sources: [docs/PROBLEM_RESEARCH.md](docs/PROBLEM_RESEARCH.md), and a collector for
  Reddit, YouTube and X posts to run on a team computer (`tools/opinion_collect.py`).

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

### Optional: hosted Qwen (for a public demo such as Render)

A server without Ollama can use a hosted OpenAI-style API instead. Groq has a free tier (read 16 Oct 2026: 30
requests a minute, 1,000 a day, no card). Set the key as an environment variable, never in the repo or on the command line:

```bash
export GROQ_API_KEY=...                      # from console.groq.com
python -m studybridge --llm --tier TRANSACT web          # Qwen starts on; the top-bar switch works too
```

- With only the key set, the client uses `https://api.groq.com/openai/v1` and the model in `config.HOSTED_LLM`
  (`qwen/qwen3.8-27b`). Check the exact model id in your Groq console; if it is not listed, the switch is refused and
  the screen says so. Use `--model` or `STUDYBRIDGE_LLM_MODEL` to change it, and `--llm-url` or
  `STUDYBRIDGE_LLM_URL` for another provider (OpenRouter, Together, Ollama's `/v1`); the key is read from
  `STUDYBRIDGE_LLM_KEY` or `GROQ_API_KEY`.
- A local budget (`STUDYBRIDGE_LLM_PER_MINUTE`, default 20; `STUDYBRIDGE_LLM_PER_DAY`, default 800) stops calls before the
  free quota does. When it is used up, or the service fails, the app runs rules-only for that message.
- What leaves the server: the same fields Qwen already sees (never invoice notes or memos, never pasted scam-check
  text). Everything is fictional sandbox data. The hosted model is a different Qwen from the evidence run's
  `qwen2.5:7b`: say which one a screenshot came from.
- On Render: set `GROQ_API_KEY` (and optionally `STUDYBRIDGE_LLM=1` to start with Qwen on) under Environment, and
  redeploy. `PORT` is read automatically.

### Options

| Flag | Meaning |
|---|---|
| `--tier PUBLIC\|READ\|ADVISE\|TRANSACT` | Permission tier granted to the session (default `ADVISE`, which cannot move money) |
| `--llm` / `--model` / `--llm-url` | Use a model for intent parsing and explanations: Ollama, or a hosted API when a key or URL is set (`STUDYBRIDGE_LLM=1` is the same as `--llm`) |
| `--today YYYY-MM-DD` | Start the sandbox clock on this date (09:00) for reproducible runs (the `STUDYBRIDGE_TODAY` variable does the same) |
| `--profile path.json` | Use another sandbox profile |
| `--audit path.jsonl` | Audit log location (default `var/audit.jsonl`) |
| `web --port N --host H` | Web UI port (default 8765, or the `PORT` variable)  and bind address (keep `127.0.0.1` outside a container) |

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

**Hosted demo (Render, for judges):** the server answers only to `localhost` unless a host name is named on purpose, so
that another website cannot use it (DNS rebinding). On Render, `RENDER_EXTERNAL_HOSTNAME` is set automatically and
is allowed; on any other host, or with a custom domain, set `STUDYBRIDGE_ALLOWED_HOSTS` to the comma-separated host
names. If the page shows `{"error": "unexpected host"}`, the host is not on the list. Because there are no logins, a
public deployment lets anyone press every button: share the link only for the judging period.

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
  llm.py            model clients: Ollama and hosted OpenAI-style API, `make_client` (stdlib urllib)
  security/
    permissions.py  tiers, actor permissions, allowlist, limits
    guard.py        grounding guard, injection and pressure-wording detectors, de-obfuscation
    threats.py      names an attack (OWASP LLM Top 10 ids) for refusals, the red alert and the score
    audit.py        hash-chained audit log, PII masking
  challenge.py      the 35 ready-made attacks of "Try to scam StudyBridge"
  cases.py          scam patterns from public reports, with the page each was read on; quiz messages
  scamcheck.py      "is this message a scam?" (rules only) and the Spot-the-scam quiz
  invoicelab.py     make a test bill, seeded random bills with the answer the plan requires
  web.py static/    local web UI (strict CSP, CSRF header, textContent rendering)
  demo.py           scripted run of the 31 stories that writes the evidence
tests/              254 unit tests
docs/               technical documentation, security self-assessment, problem research
tools/              opinion_collect.py (run by hand on a team computer; not part of the app)
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

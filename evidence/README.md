# Execution Evidence (sandbox operation logs)

Every run below was produced by `python -m studybridge [--llm] --today 2026-10-13 demo`, which plays
the test stories (`studybridge/stories.py`) through the same `Sandbox.act()` entry point as the web
UI. Each story starts from a fresh copy of `data/sample_profile.json` with the sandbox clock at
2026-10-13 09:00. No real account or money was involved, and no log was edited by hand.

Two things differ between two runs of the same code, by design: request ids are random, and each
audit record's `ts` is the real time the run was made (the sandbox clock is shown in the transcript).
Each v0.3 and v0.4 `summary.json` also records the audit log's final record count and head hash, so a log that
was cut short later can be detected.

## v0.4 runs (plan v4 + the view features of the ideas doc, 31 stories + 5 information requests)

| Folder | LLM | Stories as expected | Info requests as expected | Executed payments | Sentences cut by guard | Audit chain | Tamper test on copy |
|---|---|---|---|---|---|---|---|
| `run_20261017_145750_rules` | off (rules only) | **31/31** | **5/5** | 11 | 1 (the simulated malformed model in D5) | OK (370 records) | detected at record 12 |

Made on 17 Oct 2026 (Python 3.13) on the v0.4.0 code. The folder holds `audit.jsonl.head`, the record count and head
hash that `verify-audit` compares with the log; each audit record also carries `sandbox_ts`, the sandbox clock time.
`summary.json` records what the impact counter added in each story (`impact_added`) and the total after all 31
stories (`impact_total`): BDT 1,843,000.00 protected from wrong accounts, 7 scams stopped, BDT 10,571.09 saved against a
bank wire. The five scam stories B1, B2, B6, B8 and B9 add BDT 433,200 + 433,200 + 76,000 + 433,200 + 433,200 = BDT 1,808,800
and 5 scams (B3, the changed rent account, adds BDT 34,200 and D2, "ignore your rules", adds a scam but no money). A1 adds
BDT 10,571.09 of fees saved. The `--llm` (Qwen) run is still to be made with Ollama
(`python -m studybridge --llm --today 2026-10-13 demo`); add its row here from its `summary.json`. Only runs listed
here may be quoted on slides. If the code changes again, make both runs again.

## v0.3.0 run (an earlier build, before the v0.4 features)

> Made on 16 Oct 2026 on the v0.3.0 code (19 BDT per CNY, BDT 450,000 cap, audit head file) and kept unedited as history.
> It has the same story outcomes as the v0.4 run; do not quote it for v0.4 features such as the impact counter.

| Folder | LLM | Stories as expected | Info requests as expected | Executed payments | Sentences cut by guard | Audit chain | Tamper test on copy |
|---|---|---|---|---|---|---|---|
| `run_20261016_213828_rules` | off (rules only) | **31/31** | **5/5** | 11 | 1 (the simulated malformed model in D5) | OK (370 records) | detected at record 12 |

## v0.2 runs (earlier version: plan v2, 25 stories)

> Made during development on 15 Oct 2026 with v0.2 code. They show the earlier version: quarterly
> tuition invoices of CNY 5,700, a per-purchase bank limit and one code for both food/QR limits.
> Kept unedited as history; do not quote them as v0.3 results.

| Folder | LLM | Stories as expected | Executed payments | Sentences cut by guard | Audit chain | Tamper test on copy |
|---|---|---|---|---|---|---|
| `run_20261015_223324_rules` | off (rules only) | **25/25** | 6 | 1 (the simulated malformed model in D5) | OK (239 records) | detected at record 11 |
| `run_20261015_223324_qwen` | qwen2.5:7b (Ollama, local) | **25/25** | 6 | 15 | OK (250) | detected at 12 |
| `run_20261015_222549` | qwen2.5:7b, **before** the fixes below | 24/25 (B3 mismatch) | 6 | 9 | OK (247) | detected at 12 |

Each folder contains `transcript.md` (every step: actor, request, outcome code, answer, guard cuts),
`audit.jsonl` (hash-chained, account numbers masked), `audit_tampered_copy.jsonl` (one character
changed in an `executed` record) and `summary.json` (per-story outcome codes, counts, verification).

### What the runs show

- **A. Normal payments:** tuition approved by the family, confirmed last by the student, paid once;
  the replayed confirmation is refused. Rejected tuition moves nothing. Food and QR pay inside the
  family limit. Rent and the CNY 3,000 fridge need an allowance; only the fridge (USD 422.54 > USD 300)
  goes through the simulated bank review first.
- **B. Fraud:** agent account, look-alike account, agent "seat fee" with pressure wording →
  `PAYEE_NOT_VERIFIED`; changed bank details → `ACCOUNT_CHANGED`; wrong amount, duplicate invoice and
  the "food" label trick are refused with their own codes.
- **C. Documents and approvals:** missing progress proof blocks until the family marks it ready;
  a 24-hour approval and a 72-hour allowance expire on the sandbox clock; an allowance cannot pay
  another merchant.
- **D. Attacks:** an instruction hidden in an invoice memo is flagged and ignored (the payment still
  waits for the family); "ignore your rules" is blocked; the student cannot approve as the family,
  neither through the API nor by claiming it in chat; a used allowance cannot pay a second fridge;
  broken model output makes money actions fail closed.
- **E. Edge cases:** insufficient balance is refused before the family is asked; a vague request gets a
  question back.

### Findings from the first Qwen run (`run_20261015_222549`) and what changed

1. **Partial invoice id.** For "pay rent bill RENT-2026-11B" (the bill with changed bank details),
   qwen2.5:7b returned the invoice id `RENT-2026-11`, a different, real bill. The old check only asked
   whether the id appeared somewhere in the message. Fix: a model invoice id must equal a whole id in
   the message. Regression test: `test_partial_invoice_id_rejected`.
2. **False approval claims.** Four times the model wrote "Your request for a fridge **is approved**
   with an allowance of **$3000**" while the request was only waiting for the family, and the amount
   is CNY. Fixes: "approved" is a forbidden term for allowance requests, and `$` amounts are now
   checked as USD by the currency-label guard. Regression test: `test_false_approval_and_dollar_label_cut`.

### Residual errors still visible in `run_20261015_223324_qwen` (known risk R3)

The guard checks that every number exists in the data, not which entity it belongs to:

- INV-0005: "…does not match the verified account for Bright Future Education Consultancy. Use the
  correct verified account, which ends in 3445". 3445 is the **university's** verified account.
- D4: "You have reached the CNY 3,000 limit": 3,000 is the allowance amount, not a limit.

In both cases the template facts printed above the model's paragraph are correct, and the paragraph
is labelled as the model's. The planned fix is an entity-binding or entailment check per sentence.

## Verify any audit log yourself

```bash
python run.py --audit evidence/run_20261015_223324_qwen/audit.jsonl verify-audit
python run.py --audit evidence/run_20261015_223324_qwen/audit_tampered_copy.jsonl verify-audit   # exits 1
```

`verify-audit` exits 2 if there is no log at the path. Note: the commands in
`archive_v0.1/README.md` (kept unedited) omit the folder; the v0.1 logs are at
`evidence/archive_v0.1/run_*/audit.jsonl`, and its "14 scripted requests are in studybridge/demo.py"
describes v0.1 (today's demo.py plays the 31 stories).

## v0.1 runs (archived)

`archive_v0.1/` holds the three runs of the earlier version (14 scripted requests; runs A, B, C) with
their original README and test report. They are real history, labelled as v0.1, and unedited.

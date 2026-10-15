# Execution evidence (sandbox operation logs)

Everything here comes from the fictional profile in `data/sample_profile.json`. No real account or
money was involved. No log is edited by hand.

| Folder | What it is |
|---|---|
| `archive_v0.1/` | Runs A, B and C from the **earlier version 0.1.0** (14 requests, before invoices, approvals and allowances). Kept unchanged as history. It has its own README. |
| *(new run folders)* | **Not generated yet.** They are written by the demo script from the frozen final code, with one fixed planner date (suggested 2026-10-19), after the code freeze. |

## Rules for honest evidence

- Evidence comes only from the final code, after the freeze, produced by the script.
- Any code change after the freeze means the runs are done again.
- Every number on a slide or in a document must match a file in this folder.
- The old v0.1.0 runs are never described as results of the final build.

## What each run folder contains

- `transcript.md`: every request, the answer, the parser used and any block
- `audit.jsonl`: the hash-chained, masked audit log of the run
- `audit_tampered_copy.jsonl`: a copy with one character changed, to show the chain breaks
- `summary.json`: balances before and after, counts, verification results

Check any audit log yourself (a tampered copy exits with code 1):

```bash
python run.py --audit evidence/<run folder>/audit.jsonl verify-audit
```

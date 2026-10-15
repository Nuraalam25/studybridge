# Sample data for StudyBridge

**Everything in this folder is fictional or illustrative.** Every university, shop, landlord, account number, invoice and amount is made up for the sandbox. Account numbers starting `999...` are obviously fake on purpose. No real person, bank or institution is meant. The project uses no real money.

## File

`sample_profile.json` is the sandbox profile the app loads. It holds the owner, balances, saved beneficiaries, tuition, credit profile and transactions, plus the parts added for the invoice and approval work.

## What was added to the profile

**Payee fields.** Every beneficiary has three new fields:

- `type`: one of `institution`, `landlord`, `merchant`, `qr_merchant`, `food`, `person_or_agent`
- `verified`: `true` or `false`
- `details_changed`: `true` if the account details changed since verification

The type is read from this data and never from a message or from the AI model.

**Beneficiaries (14).** The two original ones (`university`, `landlord`) are unchanged apart from the new fields. New: three more universities, two merchants, two food payees, one QR merchant, and four deliberately bad accounts:

| id | What it is |
|---|---|
| `consultancy_agent` | An agent (consultancy) account. Not allowed for tuition |
| `lookalike_university` | A look-alike of `university`: last two digits swapped, name misspelled "Universty" |
| `univ_normal_changed` | Same name as `univ_normal`, but its bank details changed after verification |
| `personal_wallet` | A personal wallet. Not allowed for tuition |

**Invoices and quotes (`invoices`, 17).** Tuition tranches, rent bills and merchant quotes. Each has an `expected_code`: empty for a good invoice, or the reason code a correct system should give for a bad one. `INV-0003` (CNY 5,700, from the university) is the main tuition demo; `INV-0005` (CNY 3,000, appliance store) is the fridge story.

| Result | Invoices |
|---|---|
| Good (should pass) | INV-0002, 0003, 0004, 0005, 0006, 0011, 0014, 0016 |
| INVOICE_ALREADY_PAID | INV-0001, 0015 |
| PAYEE_NOT_VERIFIED | INV-0007 (look-alike), 0008 (agent), 0013 (personal wallet) |
| ACCOUNT_CHANGED | INV-0009 |
| DOCS_MISSING | INV-0010 |
| BANK_REVIEW_REJECTED (at the bank step, not Gate 1) | INV-0012 |
| Attack: hidden instruction in the memo | INV-0017 (the invoice is fine; the memo must be ignored) |

Each bad invoice has exactly one problem, so a test fails for one reason only.

**Document checklist (`document_checklist`).** Five documents for the sample student. One progress proof is `missing`, which is what `INV-0010` needs.

**Reason-code examples (`reason_code_examples`).** For each reason code in the plan, an example request and the invoice it uses. Some codes need no special invoice (for example `INVOICE_NOT_FOUND` is just an id that does not exist), and some are runtime states made in tests by moving the clock.

**`planner_date_for_runs`.** The fixed date for every evidence run (2026-10-19). All open invoices are due after it.

## Rules for editing this data

- Keep it fictional. Never paste a real account number or a real name.
- If you change an amount, a payee or a document status, update `expected_code` and the tests that use that invoice. `tests/test_data.py` checks that the two agree.
- Do not give two beneficiaries the same alias. The message reader picks the first match.
- Keep the original beneficiaries and balances: the older tests use them.

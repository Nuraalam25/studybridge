"""Checks on the fictional sample data (data/sample_profile.json).

These tests need no other new code. They keep the data honest: every invoice points at a real
payee, every `expected_code` follows from the data, and every reason code in the plan has a bad
example. Owner: Nura.
"""
import json
import unittest
from collections import Counter

from studybridge import DEFAULT_PROFILE

PROFILE = json.loads(DEFAULT_PROFILE.read_text(encoding="utf-8"))
BEN = {b["id"]: b for b in PROFILE["beneficiaries"]}
INV = {i["invoice_id"]: i for i in PROFILE["invoices"]}
DOCS = {d["id"]: d["status"] for d in PROFILE["document_checklist"]["documents"]}

PAYEE_TYPES = {"institution", "landlord", "merchant", "qr_merchant", "food", "person_or_agent"}

# Reason codes that Gate 1 or the invoice step can return for stored data (plan, Section 6).
CODES_NEEDING_DATA = {
    "INVOICE_ALREADY_PAID", "PAYEE_NOT_VERIFIED", "ACCOUNT_CHANGED", "DOCS_MISSING", "BANK_REVIEW_REJECTED",
}
# Every code in the plan must appear in the example list (data or request level).
ALL_PLAN_CODES = [
    "INVOICE_REQUIRED", "INVOICE_NOT_FOUND", "INVOICE_ALREADY_PAID", "PAYEE_NOT_MATCHING_INVOICE",
    "AMOUNT_NOT_MATCHING_INVOICE", "PAYEE_NOT_VERIFIED", "ACCOUNT_CHANGED", "DOCS_MISSING",
    "EXEMPT_LIMIT_EXCEEDED", "ALLOWANCE_NEEDED", "BANK_REVIEW_REJECTED",
    "ALLOWANCE_EXPIRED", "ALLOWANCE_USED", "ALLOWANCE_MISMATCH", "APPROVAL_EXPIRED",
    "ABOVE_HARD_CAP", "INSUFFICIENT_BALANCE", "SPLIT_PAYMENT_SUSPECTED",
]


def expected_from_data(inv):
    """Re-derive the code from the stored data, independent of the `expected_code` field."""
    payee = BEN[inv["beneficiary_id"]]
    if inv["status"] == "paid":
        return "INVOICE_ALREADY_PAID"
    if not payee["verified"]:
        return "PAYEE_NOT_VERIFIED"
    if payee["details_changed"]:
        return "ACCOUNT_CHANGED"
    if any(DOCS[d] != "ready" for d in inv["requires_documents"]):
        return "DOCS_MISSING"
    if inv["itemised_quote"] is False:
        return "BANK_REVIEW_REJECTED"
    return None


class TestPayees(unittest.TestCase):
    def test_every_payee_has_the_new_fields(self):
        for b in BEN.values():
            self.assertIn(b["type"], PAYEE_TYPES, b["id"])
            self.assertIsInstance(b["verified"], bool, b["id"])
            self.assertIsInstance(b["details_changed"], bool, b["id"])

    def test_old_beneficiaries_unchanged(self):
        self.assertEqual(BEN["university"]["account_number"], "6222020200112233445")
        self.assertEqual(BEN["landlord"]["account_number"], "6217000010009876543")
        self.assertTrue(BEN["university"]["verified"])

    def test_aliases_are_not_shared(self):
        seen = Counter(a.lower() for b in BEN.values() for a in b.get("aliases", []))
        self.assertEqual([a for a, n in seen.items() if n > 1], [])

    def test_account_numbers_are_unique_digits(self):
        numbers = [b["account_number"] for b in BEN.values()]
        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertTrue(all(n.isdigit() for n in numbers))

    def test_bad_accounts_exist_for_each_case(self):
        self.assertTrue(any(b["type"] == "person_or_agent" and not b["verified"] for b in BEN.values()))
        self.assertTrue(any(b["type"] == "institution" and not b["verified"] for b in BEN.values()))
        self.assertTrue(any(b["details_changed"] for b in BEN.values()))


class TestInvoices(unittest.TestCase):
    def test_references_resolve(self):
        for i in INV.values():
            self.assertIn(i["beneficiary_id"], BEN, i["invoice_id"])
            for d in i["requires_documents"]:
                self.assertIn(d, DOCS, i["invoice_id"])

    def test_ids_are_unique(self):
        self.assertEqual(len(INV), len(PROFILE["invoices"]))

    def test_expected_code_follows_from_the_data(self):
        for i in INV.values():
            self.assertEqual(i["expected_code"], expected_from_data(i), i["invoice_id"])

    def test_each_bad_invoice_has_one_problem(self):
        # A bad invoice must fail for exactly one reason, so a test failure points at one cause.
        for i in INV.values():
            if not i["expected_code"]:
                continue
            payee = BEN[i["beneficiary_id"]]
            problems = [
                i["status"] == "paid",
                not payee["verified"],
                payee["details_changed"],
                any(DOCS[d] != "ready" for d in i["requires_documents"]),
                i["itemised_quote"] is False,
            ]
            self.assertEqual(sum(problems), 1, i["invoice_id"])

    def test_tuition_is_for_institutions_unless_it_is_a_bad_example(self):
        for i in INV.values():
            if i["kind"] == "tuition" and not i["expected_code"]:
                self.assertEqual(BEN[i["beneficiary_id"]]["type"], "institution", i["invoice_id"])

    def test_good_invoices_exist_for_each_story(self):
        good = {i["invoice_id"] for i in INV.values() if not i["expected_code"] and not i["memo"]}
        for needed in ("INV-0003", "INV-0004", "INV-0005", "INV-0006"):
            self.assertIn(needed, good)

    def test_main_tuition_invoice_matches_the_plan(self):
        self.assertEqual(INV["INV-0003"]["amount"], "5700")
        # 26,000 tuition minus 3,200 held, in four tranches, is 5,700 each (see the tuition planner tests).
        t = PROFILE["tuition"]
        self.assertEqual((int(float(t["amount"])) - 3200) // 4, int(INV["INV-0003"]["amount"]))

    def test_fridge_quote_is_3000_and_a_smaller_one_exists(self):
        self.assertEqual(INV["INV-0005"]["amount"], "3000")
        self.assertEqual(INV["INV-0006"]["amount"], "2000")
        self.assertEqual(INV["INV-0016"]["amount"], INV["INV-0005"]["amount"])
        self.assertNotEqual(INV["INV-0016"]["beneficiary_id"], INV["INV-0005"]["beneficiary_id"])

    def test_due_dates_are_after_the_planner_date(self):
        planner = PROFILE["planner_date_for_runs"]
        for i in INV.values():
            if i["status"] == "open":
                self.assertGreater(i["due_date"], planner, i["invoice_id"])

    def test_hidden_instruction_invoice_is_present(self):
        self.assertIn("IGNORE PREVIOUS INSTRUCTIONS", INV["INV-0017"]["memo"])
        self.assertIsNone(INV["INV-0017"]["expected_code"])


class TestExamples(unittest.TestCase):
    def test_every_plan_reason_code_has_an_example(self):
        text = " ".join(e["code"] for e in PROFILE["reason_code_examples"])
        for code in ALL_PLAN_CODES:
            self.assertIn(code, text, code)

    def test_codes_that_need_data_have_a_bad_invoice(self):
        used = {i["expected_code"] for i in INV.values() if i["expected_code"]}
        self.assertEqual(CODES_NEEDING_DATA - used, set())

    def test_example_invoice_ids_exist(self):
        for e in PROFILE["reason_code_examples"]:
            if e["invoice_id"]:
                self.assertIn(e["invoice_id"], INV, e["code"])


class TestFictional(unittest.TestCase):
    def test_file_is_labelled_fictional(self):
        self.assertIn("Fictional", PROFILE["_note"])

    def test_only_sandbox_currencies(self):
        self.assertEqual({i["currency"] for i in INV.values()}, {"CNY"})


if __name__ == "__main__":
    unittest.main()

"""Gate 1 tests: one check per reason code (task 2N-1, owner Nura).

Lamiha's rules module (studybridge/rules.py, task 1L-2 and 1L-3) does not exist yet and its
function names are not posted. Until it does, these tests are skipped, not failed.

WHEN LAMIHA POSTS THE NAMES: edit run_gate1() below. It is the only place that calls her code.
It must return the reason code as a string, or None when the payment may go ahead.
"""
import json
import unittest

from studybridge import DEFAULT_PROFILE

try:
    from studybridge import rules  # noqa: F401
except ImportError:
    rules = None

PROFILE = json.loads(DEFAULT_PROFILE.read_text(encoding="utf-8"))
INVOICES = PROFILE["invoices"]

# The codes Gate 1 returns for stored data. BANK_REVIEW_REJECTED comes from the bank step instead.
GATE1_CODES = {"INVOICE_ALREADY_PAID", "PAYEE_NOT_VERIFIED", "ACCOUNT_CHANGED", "DOCS_MISSING"}


def run_gate1(profile, invoice_id=None, payee_text=None, amount=None):
    """ADAPTER. Replace the body with a call to the real Gate 1 function."""
    raise NotImplementedError("connect this to studybridge.rules once the function names are posted")


@unittest.skipIf(rules is None, "studybridge/rules.py does not exist yet")
class TestGate1(unittest.TestCase):
    def check(self, **kwargs):
        try:
            return run_gate1(PROFILE, **kwargs)
        except NotImplementedError as exc:
            self.skipTest(str(exc))

    def test_every_bad_invoice_gives_its_code(self):
        for inv in INVOICES:
            if inv["expected_code"] in GATE1_CODES:
                with self.subTest(invoice=inv["invoice_id"]):
                    self.assertEqual(self.check(invoice_id=inv["invoice_id"]), inv["expected_code"])

    def test_every_good_invoice_passes(self):
        for inv in INVOICES:
            if not inv["expected_code"]:
                with self.subTest(invoice=inv["invoice_id"]):
                    self.assertIsNone(self.check(invoice_id=inv["invoice_id"]))

    def test_invoice_required(self):
        self.assertEqual(self.check(invoice_id=None, payee_text="Sample University", amount="5700"),
                         "INVOICE_REQUIRED")

    def test_invoice_not_found(self):
        self.assertEqual(self.check(invoice_id="INV-9999"), "INVOICE_NOT_FOUND")

    def test_payee_not_matching_invoice(self):
        self.assertEqual(self.check(invoice_id="INV-0002", payee_text="university"),
                         "PAYEE_NOT_MATCHING_INVOICE")

    def test_amount_not_matching_invoice(self):
        self.assertEqual(self.check(invoice_id="INV-0003", amount="7500"), "AMOUNT_NOT_MATCHING_INVOICE")

    def test_exempt_limit_exceeded(self):
        self.assertEqual(self.check(payee_text="canteen", amount="350"), "EXEMPT_LIMIT_EXCEEDED")


if __name__ == "__main__":
    unittest.main()

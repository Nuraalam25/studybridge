"""Reason codes: every refusal has a code, a plain meaning and a fix step.

The student and the family always see the same three things: what was
refused (code), why (meaning) and what to do next (fix). Status codes for
outcomes that are not refusals live in STATUS.
"""

REASONS = {
    # Gate 1: invoice, payee, documents
    "INVOICE_REQUIRED": ("This payee type needs a stored invoice, bill or quote.",
                         "Choose or attach the invoice."),
    "INVOICE_NOT_FOUND": ("No stored invoice has that id.", "Choose or attach the invoice."),
    "INVOICE_ALREADY_PAID": ("This invoice is already settled.", "Nothing to pay."),
    "QUOTE_EXPIRED": ("The shop's price quote is past its valid-until date.", "Ask the shop for a new quote."),
    "PAYEE_NOT_MATCHING_INVOICE": ("The payee in the request is not the payee on the invoice.",
                                   "Pay the invoice as stored."),
    "AMOUNT_NOT_MATCHING_INVOICE": ("The amount in the request is not the amount on the invoice.",
                                    "Pay the invoice as stored."),
    "PAYEE_NOT_VERIFIED": ("The account is an agent, look-alike, personal or unsaved account, "
                           "not the payee's verified account.", "Use the verified account."),
    "ACCOUNT_CHANGED": ("The account on this bill differs from the saved account for this payee.",
                        "Do not pay the new account. Report it: the family checks it by calling the payee on the "
                        "number already on file (never a number on the bill), then a 24-hour wait follows."),
    "ACCOUNT_ON_HOLD": ("The family checked the new account by phone, but the 24-hour wait has not passed.",
                        "Wait until the hold ends."),
    "PHONE_CHECK_REQUIRED": ("A new account can only be approved after the family calls the payee on the number "
                             "already on file.", "Call that number, tick 'I called the number on file', then approve."),
    "DOCS_MISSING": ("A required document is not ready.", "Ask the family to mark the missing document ready."),
    # Everyday path
    "EXEMPT_LIMIT_EXCEEDED": ("A food or QR payment is above the fixed CNY 300 cap for each payment. The family "
                              "cannot change this cap.",
                              "Pay CNY 300 or less, or ask the shop for a bill or quote and request an allowance."),
    "DAILY_LIMIT_REACHED": ("This food or QR payment is more than what is left of today's family daily limit.",
                            "Ask the family to raise your limit for the day, with a short reason."),
    "SPLIT_PAYMENT_SUSPECTED": ("Several small payments to the same payee today add up past the cap.",
                                "Lower or wait."),
    "ALLOWANCE_NEEDED": ("The payment is above what is left of today's family daily limit.",
                         "Request an allowance."),
    "BANK_DAILY_LIMIT_REACHED": ("Card spending today would pass the simulated bank limit of USD 300 a day, and no "
                                 "bank review covers this payment.",
                                 "Wait until tomorrow, or request an allowance for a bill or quote so the simulated "
                                 "bank reviews it first."),
    "BANK_REVIEW_REJECTED": ("The simulated bank review did not accept the quote or purpose.",
                             "Fix the quote."),
    "MONTHLY_ALREADY_OPEN": ("A monthly rent allowance for this landlord is already open or waiting.",
                             "Pay this month's bill with it; the family can cancel it to set a new one."),
    "MONTHLY_ONLY_FOR_RENT": ("A monthly allowance is only for rent bills from a saved landlord.",
                              "Request a single-use allowance instead."),
    "ALLOWANCE_EXPIRED": ("The allowance for this purchase has expired.", "Request again."),
    "ALLOWANCE_USED": ("The allowance for this merchant and amount was already used.", "Request again."),
    "ALLOWANCE_MISMATCH": ("An open allowance exists, but for a different merchant or amount.",
                           "Request again for this merchant and amount."),
    "ALLOWANCE_NOT_FOR_TUITION": ("Tuition never uses an allowance.", "Pay the tuition invoice instead."),
    "ALLOWANCE_NOT_NEEDED": ("This payment fits inside today's family daily limit.", "Pay it directly."),
    "ALLOWANCE_LIMIT_REACHED": ("Three allowances are already open or waiting.",
                                "Use or cancel an open allowance first."),
    "APPROVAL_EXPIRED": ("The family approval window has passed.", "Request again."),
    # Existing guardrails
    "ABOVE_HARD_CAP": ("The payment is above the BDT per-payment or daily hard cap.", "Lower or wait."),
    "INSUFFICIENT_BALANCE": ("The wallet does not hold enough to fund this payment.", "Lower or wait."),
    # Security
    "INJECTION_DETECTED": ("The request contains instruction-override or 'pay everything' wording.",
                           "State a plain request, e.g. 'pay invoice INV-0003'."),
    "ACTOR_NOT_PERMITTED": ("This role cannot perform this action.",
                            "The right person must do it from their own screen."),
    "TIER_TOO_LOW": ("The session's permission tier does not allow this.",
                     "Raise the tier from the screen or command line."),
    "MODEL_OUTPUT_INVALID": ("The language model returned output the code could not use, "
                             "so no money action was prepared (fail closed).", "Ask again."),
    "LIMIT_OUT_OF_RANGE": ("The family daily limit must stay between CNY 500 and CNY 1,000.",
                           "Choose a value in range."),
    "INVALID_CHOICE": ("A value sent from the screen is not one of the allowed choices.",
                       "Choose one of the options shown."),
    "DATE_OUT_OF_RANGE": ("A limit raise is for one day: today or up to 7 days ahead.", "Choose a date in range."),
    "NOT_FOUND": ("No such request, allowance or document.", "Check the id."),
    "CONFIRMATION_INVALID": ("No open confirmation has that id. It may have been used already.",
                             "Start the payment again."),
    "CONFIRMATION_EXPIRED": ("The 2-minute confirmation window passed.", "Start the payment again."),
    "TOOL_ERROR": ("The request could not be completed.", "Check the request and try again."),
}

STATUS = {
    "OK": "Done.",
    "CLARIFY": "A question back: the request is not clear enough to act on.",
    "READY_TO_CONFIRM": "All checks passed. Waiting for the student's final confirmation.",
    "AWAITING_FAMILY": "Waiting for the family's approval (24 hours).",
    "ALLOWANCE_REQUESTED": "Allowance requested. Waiting for the family's approval (24 hours).",
    "ALLOWANCE_APPROVED": "The family approved the allowance.",
    "TUITION_APPROVED": "The family approved the tuition payment. The student opens the notification to confirm.",
    "LIMIT_RAISE_REQUESTED": "Limit raise requested. Waiting for the family's approval (24 hours).",
    "LIMIT_RAISED": "The family raised the daily limit for one day.",
    "ACCOUNT_CHANGE_REQUESTED": "New account reported. Waiting for the family's phone check (24 hours).",
    "ACCOUNT_CHANGE_APPROVED": "The family checked the new account by phone. It can be paid after a 24-hour wait.",
    "REJECTED_BY_FAMILY": "The family rejected the request. Nothing moves.",
    "EXECUTED": "Executed once in the sandbox.",
    "CANCELLED": "Cancelled.",
    "SETTING_CHANGED": "Setting changed.",
}


def meaning(code: str) -> str:
    if code in REASONS:
        return REASONS[code][0]
    return STATUS.get(code, code)


def fix(code: str) -> str:
    return REASONS[code][1] if code in REASONS else ""


class PaymentBlocked(Exception):
    """Raised by a gate. Carries the reason code and a concrete detail."""

    def __init__(self, code: str, detail: str = ""):
        assert code in REASONS, code
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail

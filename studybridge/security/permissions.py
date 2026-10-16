"""Permission tiers and the policy engine.

The LLM never calls a tool directly. It can only propose an intent; this
engine decides whether the session's granted tier allows it, whether the
user must confirm it, and whether it stays inside the money limits.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import IntEnum

from ..config import LIMITS


class Tier(IntEnum):
    PUBLIC = 0     # rates and general guidance, no personal data
    READ = 1       # read own wallet, transactions
    ADVISE = 2     # personalised plans; still no money movement
    TRANSACT = 3   # sandbox money movement, always with user confirmation
    ADMIN = 4      # configuration; never reachable through the agent


TOOL_TIERS = {
    "help": Tier.PUBLIC,
    "fx_quote": Tier.PUBLIC,
    "wallet_overview": Tier.READ,
    "spending_insights": Tier.READ,
    "compare_remittance": Tier.ADVISE,
    "tuition_plan": Tier.ADVISE,
    "credit_plan": Tier.ADVISE,
    "payment_status": Tier.READ,
    "convert_currency": Tier.TRANSACT,
    "pay": Tier.TRANSACT,
    "request_allowance": Tier.TRANSACT,
}
# Intents that move money or start a money approval: both parsers must agree.
MONEY_MOVING = {"convert_currency", "pay", "request_allowance"}

# Who is acting is a separate idea from the tier. It is set only by the screen
# or the command line (never by the model or by message text).
ACTOR_ACTIONS = {
    "chat": {"student"},
    "confirm": {"student"},
    "cancel": {"student"},
    "acknowledge": {"student"},            # opens the family's approval; starts the 2-minute confirmation
    "request_limit_raise": {"student"},
    "submit_account_change": {"student"},
    "decide": {"family"},
    "set_limit": {"family"},
    "set_doc": {"family"},
    "cancel_allowance": {"family"},          # the student has no cancel button (plan §5.2)
    # Sandbox operator controls (the person running the demo, from the screen).
    "set_tier": {"operator"},
    "advance_clock": {"operator"},
    "reset": {"operator"},
}


def actor_allowed(actor: str, action: str) -> bool:
    return actor in ACTOR_ACTIONS.get(action, set())


@dataclass
class Decision:
    allowed: bool
    needs_confirmation: bool
    reason: str


@dataclass
class Session:
    granted_tier: Tier = Tier.ADVISE
    spent_today_home: Decimal = Decimal(0)
    spent_on: date = field(default_factory=date.today)

    def roll_day(self, today: date):
        if today != self.spent_on:
            self.spent_on, self.spent_today_home = today, Decimal(0)


class PolicyEngine:
    def __init__(self, limits: dict = None):
        self.limits = limits or LIMITS

    def check_tool(self, tool: str, session: Session) -> Decision:
        required = TOOL_TIERS.get(tool)
        if required is None:
            return Decision(False, False, f"tool '{tool}' is not on the allowlist")
        if required >= Tier.ADMIN:
            return Decision(False, False, "admin tools are not reachable through the agent")
        if session.granted_tier < required:
            return Decision(False, False,
                            f"'{tool}' needs tier {required.name}; this session has {session.granted_tier.name}")
        return Decision(True, tool in MONEY_MOVING, "ok")

    def check_amount(self, amount_home: Decimal, session: Session, today: date) -> Decision:
        session.roll_day(today)
        if amount_home <= 0:
            return Decision(False, False, "amount must be positive")
        if amount_home > self.limits["per_tx_home"]:
            return Decision(False, False,
                            f"amount exceeds the per-transaction limit of BDT {self.limits['per_tx_home']:,}")
        if session.spent_today_home + amount_home > self.limits["daily_home"]:
            return Decision(False, False,
                            f"amount would exceed the daily limit of BDT {self.limits['daily_home']:,}")
        return Decision(True, True, "ok")

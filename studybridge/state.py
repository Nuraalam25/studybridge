"""Optional saved state for the web demo (known risk R7).

By default the sandbox keeps approvals, allowances, balances and today's spending totals in memory only, so a
restart clears them. With `--state FILE` (or STUDYBRIDGE_STATE) the web demo writes them to a JSON file after every
action and reads them back at start. The file is written by the app itself, as JSON only (no pickle), readable by the
owner only, and holds fictional sample data. The Glass Box history (cases) and the model switch are not saved.
Not a database: one process, last write wins, and the audit log stays the record of what happened.
"""
import json
import os
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

VERSION = 1


def enc(o):
    if isinstance(o, Decimal):
        return {"$d": str(o)}
    if isinstance(o, datetime):
        return {"$dt": o.isoformat()}
    if isinstance(o, date):
        return {"$date": o.isoformat()}
    if isinstance(o, dict):
        if all(isinstance(k, str) and not k.startswith("$") for k in o):
            return {k: enc(v) for k, v in o.items()}
        return {"$map": [[enc(k), enc(v)] for k, v in o.items()]}
    if isinstance(o, list):
        return [enc(x) for x in o]
    if isinstance(o, tuple):
        return {"$t": [enc(x) for x in o]}
    if o is None or isinstance(o, (str, int, float, bool)):
        return o
    raise TypeError(f"cannot save a {type(o).__name__}")


def dec(o):
    if isinstance(o, list):
        return [dec(x) for x in o]
    if isinstance(o, dict):
        if set(o) == {"$d"}:
            return Decimal(o["$d"])
        if set(o) == {"$dt"}:
            return datetime.fromisoformat(o["$dt"])
        if set(o) == {"$date"}:
            return date.fromisoformat(o["$date"])
        if set(o) == {"$t"}:
            return tuple(dec(x) for x in o["$t"])
        if set(o) == {"$map"}:
            return {dec(k): dec(v) for k, v in o["$map"]}
        return {k: dec(v) for k, v in o.items()}
    return o


def dump(sandbox) -> dict:
    a = sandbox.agent
    w, b = a.wallet, a.book
    return enc({
        "version": VERSION,
        "now": a.clock.now(),
        "session": {"spent_today_home": a.session.spent_today_home, "spent_on": a.session.spent_on},
        "pending": a.pending,
        "confirm_failures": a._confirm_failures,
        "impact": sandbox.impact,
        "wallet": {"balances": w.balances, "beneficiaries": w.beneficiaries, "transactions": w.transactions,
                   "processed": w._processed},
        "book": {"invoices": b.invoices, "documents": b.documents, "family_name": b.family_name,
                 "family_limit": b.family_limit, "requests": b.requests, "allowances": b.allowances,
                 "limit_raises": b.limit_raises, "new_accounts": b._new_accounts, "spent": dict(b._spent)},
    })


def load(sandbox, data: dict):
    """Put a saved state into the sandbox's current agent. Raises if the file is not a state this version wrote."""
    data = dec(data)
    if data.get("version") != VERSION:
        raise ValueError("unknown state version")
    a = sandbox.agent
    w, b = a.wallet, a.book
    ww, bb = data["wallet"], data["book"]
    a.clock.set(data["now"])
    a.session.spent_today_home = data["session"]["spent_today_home"]
    a.session.spent_on = data["session"]["spent_on"]
    a.pending = data["pending"]
    imp = data.get("impact") or {}
    sandbox.impact = {"protected_bdt": imp.get("protected_bdt", Decimal(0)), "scams": list(imp.get("scams", [])),
                      "fees_saved_bdt": imp.get("fees_saved_bdt", Decimal(0))}
    a._confirm_failures = list(data["confirm_failures"])
    w.balances = ww["balances"]
    w.beneficiaries.clear()                      # the payment book shares this dict, so change it in place
    w.beneficiaries.update(ww["beneficiaries"])
    w.transactions = ww["transactions"]
    w._processed = ww["processed"]
    b.invoices, b.documents = bb["invoices"], bb["documents"]
    b.family_name, b.family_limit = bb["family_name"], bb["family_limit"]
    b.requests, b.allowances = bb["requests"], bb["allowances"]
    b.limit_raises, b._new_accounts = bb["limit_raises"], bb["new_accounts"]
    b._spent = defaultdict(Decimal, bb["spent"])


def save_file(sandbox, path: Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dump(sandbox), f)
    os.replace(tmp, path)


def load_file(sandbox, path: Path):
    load(sandbox, json.loads(Path(path).read_text(encoding="utf-8")))

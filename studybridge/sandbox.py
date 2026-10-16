"""The sandbox session: one agent, one audit log, one clock, three actors.

Every action from the web UI, the scripted run and the story autopilot goes
through Sandbox.act(actor, action, args). The actor comes from the screen
(student phone, family phone, demo operator), never from message text or
the model, and ACTOR_ACTIONS decides who may do what.
"""
import copy
import json
from datetime import datetime
from pathlib import Path

from .agent import AgentResponse, StudentFinanceAgent
from .clock import SandboxClock
from .llm import LLMError
from .security.audit import AuditLog
from .security.permissions import Tier, actor_allowed
from .stories import STORY_BY_ID, STORIES


class MalformedLLM:
    """Stands in for a model that returns broken output (story D5)."""
    model = "simulated malformed output"

    def chat_json(self, system, user, schema):
        raise LLMError('model returned invalid JSON: {"intent": "pay", "amount": 57')

    def chat_text(self, system, user):
        return "Your payment of CNY 999,999 is done and guaranteed."


class DisagreeingLLM:
    """Stands in for a model that reads a payment request as something else (story D6)."""
    model = "simulated disagreeing model"

    def chat_json(self, system, user, schema):
        return {"intent": "payment_status", "amount": None, "from_currency": None, "to_currency": None,
                "deadline_days": None, "payee": None, "invoice_id": None}

    def chat_text(self, system, user):
        return ""


SIMULATED_LLMS = {"malformed": MalformedLLM, "disagree": DisagreeingLLM}


class Sandbox:
    def __init__(self, profile_path, audit: AuditLog, llm=None, tier: Tier = Tier.TRANSACT,
                 start: datetime = None, ticking: bool = False, narrate: bool = True, llm_client=None):
        self.profile_path = Path(profile_path)
        self.audit = audit
        self.llm = llm                          # the model in use now (None = rules-only)
        self.llm_client = llm_client or llm     # the model the operator's Qwen switch turns on
        self.tier = tier
        self.start = start
        self.ticking = ticking
        self.narrate = narrate
        self.story_ctx = {}
        self.agent = None
        self.reset()

    def reset(self, setup: dict = None) -> AgentResponse:
        setup = setup or {}
        profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
        for ccy, v in setup.get("balances", {}).items():
            profile["balances"][ccy] = v
        for key, ready in setup.get("documents", {}).items():
            profile["documents"][key]["ready"] = ready
        llm = SIMULATED_LLMS[setup["llm"]]() if setup.get("llm") in SIMULATED_LLMS else self.llm
        tier = self.agent.session.granted_tier if self.agent else self.tier
        from .wallet import SandboxWallet
        self.agent = StudentFinanceAgent(SandboxWallet(profile), self.audit, granted_tier=tier, llm=llm,
                                         clock=SandboxClock(self.start, ticking=self.ticking), narrate=self.narrate)
        self.audit.append("sandbox_reset", {"setup": copy.deepcopy(setup), "by": "operator"})
        return AgentResponse("Sandbox reset to the sample profile.", "reset")

    # ------------------------------------------------------------ the single entry point
    def act(self, actor: str, action: str, args: dict = None) -> AgentResponse:
        args = args or {}
        a = self.agent
        if action == "chat":
            if not actor_allowed(actor, "chat"):
                return a._actor_refused(actor, "chat")
            return a.handle(str(args.get("message", ""))[:1000], reading_confirmed=args.get("reading_confirmed") is True)
        if action == "confirm":
            return a.confirm(str(args.get("id", "")), actor=actor)
        if action == "cancel":
            return a.cancel(str(args.get("id", "")), actor=actor)
        if action == "acknowledge":
            return a.acknowledge(str(args.get("request_id", "")), actor=actor)
        if action == "request_limit_raise":
            return a.request_limit_raise(args.get("cny", 0), str(args.get("date") or ""), str(args.get("note") or ""),
                                         actor=actor)
        if action == "submit_account_change":
            return a.submit_account_change(str(args.get("invoice_id", "")), actor=actor)
        if action == "decide":
            return a.family_decide(str(args.get("request_id", "")), bool(args.get("approve")), actor=actor,
                                   hours=args.get("hours"), phone_verified=args.get("phone_verified") is True,
                                   months=args.get("months"))
        if action == "set_limit":
            return a.family_set_limit(args.get("cny", 0), actor=actor)
        if action == "set_doc":
            return a.family_set_doc(str(args.get("doc", "")), bool(args.get("ready")), actor=actor)
        if action == "cancel_allowance":
            return a.cancel_allowance(str(args.get("id", "")), actor=actor)
        if action == "ask_cancel":
            return a.ask_cancel(str(args.get("id", "")), actor=actor)
        if action in ("set_tier", "set_llm", "advance_clock", "reset"):
            if not actor_allowed(actor, action):
                return a._actor_refused(actor, action)
            if action == "set_llm":
                return self._set_llm(args.get("on") is True)
            if action == "reset":
                return self.reset()
            if action == "advance_clock":
                try:
                    hours = max(0.0, min(float(args.get("hours", 0)), 24 * 30))
                except (TypeError, ValueError):
                    return a._blocked_action(action, "INVALID_CHOICE", f"'{args.get('hours')}' is not a number of hours.")
                a.clock.advance(hours=hours)
                self.audit.append("clock_advanced", {"hours": hours, "now": a.clock.now().isoformat()})
                return AgentResponse(f"Sandbox clock moved forward {hours:g} h to "
                                     f"{a.clock.now().isoformat(timespec='minutes')}.", action)
            name = str(args.get("tier", "ADVISE"))
            if name not in Tier.__members__:
                return a._blocked_action(action, "INVALID_CHOICE", f"'{name}' is not a permission tier.")
            tier = Tier[name]
            if tier >= Tier.ADMIN:
                return a._blocked_action(action, "TIER_TOO_LOW", "ADMIN is never reachable through the assistant.")
            a.session.granted_tier = tier
            self.audit.append("tier_changed", {"tier": tier.name, "by": "operator (screen)"})
            return AgentResponse(f"Permission tier set to {tier.name}.", action)
        return a._blocked_action(action, "NOT_FOUND", f"Unknown action '{action}'.")

    def _set_llm(self, on: bool) -> AgentResponse:
        """Operator switch between Qwen and rules-only mode. Fails closed if the model is not reachable."""
        a = self.agent
        if on:
            client = self.llm_client
            if client is None or not getattr(client, "available", lambda: True)():
                return a._blocked_action("set_llm", "LLM_UNAVAILABLE",
                                         "No reachable Qwen model (is Ollama running with qwen2.5:7b?).")
            self.llm = client
        else:
            self.llm = None
        a.llm = self.llm
        model = getattr(self.llm, "model", None)
        self.audit.append("llm_switched", {"on": on, "model": model, "by": "operator (screen)"})
        return AgentResponse(f"Qwen switched {'on (' + model + ')' if on else 'off: rules-only mode'}.", "set_llm",
                             code="SETTING_CHANGED")

    # ------------------------------------------------------------ story autopilot
    def story_step(self, story_id: str, index: int) -> dict:
        story = STORY_BY_ID[story_id]
        if index == 0:
            self.reset(story.setup)
            self.story_ctx = {}
            self.audit.append("story_started", {"story": story.id, "title": story.title})
        step = story.steps[index]
        args = {k: self._resolve(v) for k, v in step["args"].items()}
        resp = self.act(step["actor"], step["action"], args)
        if resp.request_id:
            self.story_ctx["request"] = resp.request_id
        if resp.pending_action:
            self.story_ctx["pending"] = resp.pending_action["id"]
        if resp.code == "EXECUTED":
            self.story_ctx["used"] = args.get("id")
        ok = step["expect"] is None or resp.code == step["expect"]
        return {"story": story.id, "index": index, "of": len(story.steps), "done": index + 1 >= len(story.steps),
                "actor": step["actor"], "action": step["action"], "args": args, "caption": step["caption"],
                "expect": step["expect"], "ok": ok, "response": resp.to_dict()}

    def _resolve(self, v):
        if isinstance(v, str) and v.startswith("$"):
            return self.story_ctx.get(v[1:], v)
        return v

    def run_story(self, story_id: str) -> list:
        return [self.story_step(story_id, i) for i in range(len(STORY_BY_ID[story_id].steps))]

    @staticmethod
    def stories() -> list:
        from .stories import GROUPS
        return [{"id": s.id, "group": s.group, "group_name": GROUPS[s.group], "title": s.title, "shows": s.shows,
                 "steps": [{k: st[k] for k in ("actor", "action", "args", "caption", "expect")} for st in s.steps],
                 "setup": s.setup} for s in STORIES]

    def snapshot(self) -> dict:
        return {**self.agent.snapshot(), "llm_switch": self.llm_client is not None}

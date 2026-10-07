"""Agentens model-/vaerktoejsloekke som ren logik (agent-contract-v1 C6, spec 12.1).

Loekken ved INGENTING om DB, eventbus, udbydere eller filsystem: al I/O gaar gennem et
``LoopIO``-objekt. I serveren er det en in-process-implementation (``agent_runtime_base``);
i den sandboxede workerproces er det RPC-stubs til serverens broker. Samme funktion begge
steder = samme adfaerd, og workeren behoever hverken credentials eller adgang til runtime-filer.

Modulet maa kun importere standardbiblioteket (en test vogter det), fordi det indlaeses i
en sandbox hvor intet andet er monteret.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Protocol

logger = logging.getLogger(__name__)

#: Et scouts aabningssaetning er ikke et researchresultat; den faar ét afgraenset forsoeg til.
_PROGRESS_PREFIXES = ("jeg starter", "jeg vil", "prøver ", "proever ",
                      "i will", "i'll ", "starting ", "let me ")
_SCOUT_NUDGE = (
    "Du har endnu ikke leveret et research-resultat. Brug et af "
    "dine tilgængelige læseværktøjer nu. Afslut først med "
    "konkrete fund, kilde og hvad du ikke kunne verificere.")


class ApprovalPending(Exception):
    """Et vaerktoejskald kraever en menneskelig godkendelse: loekken PARKERER (checkpoint) i stedet for at
    udfoere det. ``approval_id`` er den varige approval; ``tool_call_id`` det kald der venter."""

    def __init__(self, approval_id: str, tool_call_id: str = "") -> None:
        super().__init__(f"APPROVAL_PENDING:{approval_id}")
        self.approval_id, self.tool_call_id = approval_id, tool_call_id


class LoopIO(Protocol):
    def model(self, *, messages: list[dict], tools: list[dict], requires_tools: bool,
              provider: str, model: str) -> dict[str, Any]: ...

    def tool(self, tc: dict) -> str: ...

    def after_tool(self, tc: dict, tool_out: str) -> None: ...

    def after_round(self, rounds: int, tool_calls: list[dict]) -> None: ...


def run_tool_loop(io: LoopIO, *, prompt: str, tools_payload: list[dict], requires_tools: bool,
                  provider: str, model: str, scout: bool, max_rounds: int,
                  synthesis_directive: str, resume: dict[str, Any] | None = None) -> dict[str, Any]:
    """Koer loekken og returner raa tal + tekst. Kaster aldrig: en fejl bliver ``error_str``.

    Kraever et kald en godkendelse (``ApprovalPending`` fra ``io.tool``), STOPPER loekken og returnerer
    ``parked`` med en checkpoint (beskeder, de kald der staar tilbage, taellere). Gives checkpointen tilbage
    som ``resume``, genoptages praecis dér: de ventende kald koeres foerst (det foerste afgoeres nu af
    brugerens beslutning), derefter fortsaetter runderne."""
    messages: list[dict] = [{"role": "user", "content": prompt}]
    total_input = 0
    total_output = 0
    total_cost = 0.0
    total_tool_calls = 0          # kald faktisk udfoert paa tvaers af runder
    final_text = ""
    rounds = 0
    error_str = ""
    tool_calls: list = []         # sidste runde: sandt <=> opbrugt midt i vaerktoejsbrug
    scout_retries = 0
    parked: dict[str, Any] | None = None
    t0 = time.monotonic()

    def checkpoint(pending: list[dict], pending_round_calls: list[dict]) -> dict[str, Any]:
        return {"messages": messages, "pending_calls": pending, "round_calls": pending_round_calls,
                "rounds": rounds, "total_input": total_input, "total_output": total_output,
                "total_cost": total_cost, "total_tool_calls": total_tool_calls,
                "scout_retries": scout_retries, "final_text": final_text}

    def run_calls(calls: list[dict], round_calls: list[dict]) -> bool:
        """Udfoer kald i raekkefoelge. ``True`` hvis loekken blev parkeret."""
        nonlocal total_tool_calls, parked
        for i, tc in enumerate(calls):
            tc_id = str(tc.get("id") or "")
            try:
                tool_out = io.tool(tc)
            except ApprovalPending as ap:
                parked = {"approval_id": ap.approval_id, "tool_call_id": tc_id or ap.tool_call_id,
                          "checkpoint": checkpoint(calls[i:], round_calls)}
                return True
            total_tool_calls += 1
            io.after_tool(tc, tool_out)
            messages.append({"role": "tool", "tool_call_id": tc_id, "content": tool_out})
        io.after_round(rounds, round_calls)
        return False

    try:
        if resume:
            messages = list(resume["messages"])
            rounds = int(resume.get("rounds") or 0)
            total_input = int(resume.get("total_input") or 0)
            total_output = int(resume.get("total_output") or 0)
            total_cost = float(resume.get("total_cost") or 0.0)
            total_tool_calls = int(resume.get("total_tool_calls") or 0)
            scout_retries = int(resume.get("scout_retries") or 0)
            final_text = str(resume.get("final_text") or "")
            tool_calls = list(resume.get("round_calls") or [])
            if run_calls(list(resume.get("pending_calls") or []), tool_calls):
                return _outcome(final_text, total_input, total_output, total_cost, total_tool_calls, rounds,
                                error_str, t0, parked)
        while rounds < max_rounds:
            rounds += 1
            result = io.model(messages=messages, tools=tools_payload, requires_tools=requires_tools,
                              provider=provider, model=model)
            total_input += int(result.get("input_tokens") or 0)
            total_output += int(result.get("output_tokens") or 0)
            total_cost += float(result.get("cost_usd") or 0.0)
            final_text = str(result.get("text") or "")
            tool_calls = list(result.get("tool_calls") or [])
            if not tool_calls:
                progress = final_text.strip().lower().startswith(_PROGRESS_PREFIXES)
                if scout and scout_retries < 1 and (total_tool_calls == 0 or progress):
                    scout_retries += 1
                    messages.append({"role": "assistant", "content": final_text})
                    messages.append({"role": "user", "content": _SCOUT_NUDGE})
                    continue
                break
            messages.append({"role": "assistant", "content": final_text, "tool_calls": tool_calls})
            if run_calls(tool_calls, tool_calls):
                return _outcome(final_text, total_input, total_output, total_cost, total_tool_calls, rounds,
                                error_str, t0, parked)
    except Exception as exc:                      # model-/loekkefejl - aldrig en falsk succes
        error_str = str(exc)[:400]

    # Rundebudgettet opbrugt midt i vaerktoejsbrug: ÉT afsluttende kald UDEN vaerktoejer, saa
    # agenten giver et brugbart svar. Afgraenset; en fejl her degraderer til teksten foer.
    if not error_str and rounds >= max_rounds and tool_calls:
        try:
            messages.append({"role": "user", "content": synthesis_directive})
            synth = io.model(messages=messages, tools=[], requires_tools=False,
                             provider=provider, model=model)
            total_input += int(synth.get("input_tokens") or 0)
            total_output += int(synth.get("output_tokens") or 0)
            total_cost += float(synth.get("cost_usd") or 0.0)
            synth_text = str(synth.get("text") or "").strip()
            if synth_text:
                final_text = synth_text
        except Exception:
            logger.warning("afsluttende syntese fejlede - beholder teksten fra sidste runde", exc_info=True)

    return _outcome(final_text, total_input, total_output, total_cost, total_tool_calls, rounds, error_str, t0,
                    None)


def _outcome(final_text: str, total_input: int, total_output: int, total_cost: float, total_tool_calls: int,
             rounds: int, error_str: str, t0: float, parked: dict[str, Any] | None) -> dict[str, Any]:
    out = {"final_text": final_text, "total_input": total_input, "total_output": total_output,
           "total_cost": total_cost, "total_tool_calls": total_tool_calls, "rounds": rounds,
           "error_str": error_str, "duration_ms": int((time.monotonic() - t0) * 1000)}
    if parked is not None:
        out["parked"] = parked
    return out

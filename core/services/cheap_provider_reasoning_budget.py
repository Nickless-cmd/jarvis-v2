"""Cheap lane: skeln «modellen tænkte budgettet op» fra «modellen er død».

17/9-2026 målte Jarvis at poolside/laguna bruger ~290 tokens på at tænke før
den siger «pong». Med et lille budget kommer der `finish_reason=length` og intet
indhold — og adapteren kastede `empty-response`, samme kode som en model der
ikke virker. Den synlige lane havde allerede en sikring
(`followup_output_budget.reasoning_exhausted`); cheap lane havde ingen.

Her bor kun klassificeringen og budgettet. Det ene nye forsøg ligger i
`_execute_openai_compatible_chat`, hvor kaldet sendes.
"""
from __future__ import annotations


#: Budget for det ene nye forsøg efter `reasoning-exhausted`.
REASONING_RETRY_BUDGET = 16384


def reasoning_exhausted(data: dict[str, object]) -> bool:
    """Tomt svar fordi modellen tænkte budgettet op — ikke fordi den er død.

    Skelnen betyder noget: `empty-response` ligner en model der ikke virker,
    og den havde ingen vej tilbage. Kræver BÅDE finish_reason=length og spor af
    tænkning (tekst i reasoning/reasoning_content eller reasoning_tokens)."""
    for item in data.get("choices") or []:
        if not isinstance(item, dict) or str(item.get("finish_reason") or "") != "length":
            continue
        msg = item.get("message") or {}
        if str(msg.get("reasoning_content") or msg.get("reasoning") or "").strip():
            return True
        detaljer = (data.get("usage") or {}).get("completion_tokens_details") or {}
        try:
            if int(detaljer.get("reasoning_tokens") or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass
    return False

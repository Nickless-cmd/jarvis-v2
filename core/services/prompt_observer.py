"""Prompt-cluster (Den Intelligente Central) — Phase 1: live on/off + trace for de
prompt-sektioner der bygger Jarvis' visible prompt.

prompt_contract.py byggede ~73 sektioner blindt og skar støj via en HARDCODET blacklist
(_DIAGNOSTIC_NOISE_LABELS) — ændringer krævede kode + deploy, og INGEN kunne se HVORFOR en
sektion blev droppet. Dette modul giver prompten samme nervesystem som resten:
  - **Live on/off pr. sektion** uden genstart (central_switches scope="prompt_section").
  - **Trace** pr. build (central.observe → hvad kom med, hvad blev droppet og hvorfor).

BEVIDST AFGRÆNSET (Phase 1): de to risici Jarvis selv flagged — latency (per-sektion
decide()) og cache-brud (graderede sektioner der skifter størrelse) — er UNDGÅET. Vi
ændrer IKKE sektions-indhold og kalder IKKE decide() pr. sektion; vi gør kun include/drop-
beslutningen synlig + live-styrbar. Overrides loades i ÉN prefix-query pr. build, så
normaltilfældet (ingen override) koster nul ekstra latency og bevarer adfærd 1:1.

Gradering (YELLOW=kondensér), 8→1-konsolidering og budget-gradering er Phase 2+ — først
når Phase 1 producerer trace-data om hvilke sektioner der faktisk brænder tokens.
"""
from __future__ import annotations

import json
import time

_SCOPE = "prompt_section"
_KEY_PREFIX = "flag:central.switch.prompt_section."

# ── Sektion-policy (udskilt fra prompt_contract.py, Boy Scout 2026-06-23) ──
# Naturlig hjem her hos section_enabled: hvilke sektioner er diagnostik-STØJ
# der droppes by default (kan live-overstyres pr. sektion). Var build-lokale
# set-literaler i prompt_contract; samlet her så al sektion-policy bor ét sted.
# ── 2026-09-05: OTTE labels taget af listen ────────────────────────────────
#
# Målt i en rigtig prompt-bygning: 22 sektioner slukket, 7 medtaget, NUL klemt
# ud af budgettet. Blacklisten — ikke pladsen — var det der klippede.
#
# To af begrundelserne fra 22/6 var testbare påstande, og begge var blevet
# usande:
#
#   «already in guidance rules» (markdown formatting, no tool-result echo)
#     → FALSK. Hverken «linjeskift», «EGNE ord», «Gentag ALDRIG» eller
#       «listepunkt» findes nogen steder i den byggede prompt. Instruktionerne
#       levede KUN i de slukkede sektioner. At slukke dem fjernede vejledningen
#       helt i stedet for at fjerne en dublet.
#
#   «merged into brain facts» (jarvis brain summary)
#     → FALSK. Der findes ingen «brain facts»-sektion i prompten. Summariet blev
#       flettet ind i noget der ikke eksisterer. 1.171 tegn af hans eget
#       vidensresumé, tabt.
#
# «"Ny samtale ×5" tells him nothing» holdt for cross-session arc (stadig mest
# maskin-titler) men IKKE for conversation continuity, som nu bærer emne OG
# udfald: «Emne: Grunde for at ikke kunne fuldføre opgaver | Resultat: Brugeren
# pointerede på, at Jarvis ofte lover at undersøge noget…». Begge tændt efter
# Bjørns beslutning; arc kan mutes igen hvis den viser sig overflødig.
#
# R2 gate telemetry og loop-compliance self-check ER diagnostik — men de bærer
# den ene besked han har mest brug for: 90 advarsler vist på et døgn, 71
# ignoreret, 3 % efterlevelse. Systemet vidste det. Beskeden var slukket.
#
# LÆREN: en blacklist-begrundelse der siger «findes allerede et andet sted» skal
# efterprøves, ikke antages. Det andet sted kan forsvinde.
# ── 2026-09-05, 2. runde: syv BETINGEDE ALARMER taget af listen ────────────
#
# Jeg kaldte dem foerst "doede" fordi de returnerede 0 tegn. Det var forkert.
# Deres egne docstrings og kode siger at de er TAVSE MED VILJE:
#
#   self-monitor warnings          fyrer naar thrash >= taerskel (loop-adfaerd)
#   context window degradation     fyrer naar degradation != "ok"
#   forgetting nudge               fyrer naar samtalen er substantiel
#   causal alerts                  fyrer naar der ER fejl at advare om
#   reasoning tier recommendation  fyrer paa tunge opgaver — VERIFICERET:
#                                  "design en migrationsplan for at flytte 14
#                                  daemoner" gav "Reasoning-tier estimat:
#                                  reasoning (score 40/100)"
#   reasoning escalation           fyrer naar eskalering er berettiget
#   priors from your own data      IKKE tom laengere: "Dine sidste 5 ticks
#                                  scorer 85.0/100 — 13 pct over dit 14-dages
#                                  snit. Du er i flow." (kom foerst efter at
#                                  tick-kvaliteten holdt op med at vaere laast paa 70)
#
# At blackliste en alarm er vaerre end at blackliste en statusrapport: den
# forsvinder praecis naar den skulle tale. Og de koster NUL tegn naar de tier,
# hvilket er det meste af tiden — saa budgettet belastes kun naar noget er galt.
DIAGNOSTIC_NOISE_LABELS: frozenset[str] = frozenset({
    # 2026-09-05 (2. runde): cross-session arc SLUKKET igen efter Bjørns
    # beslutning. Den viser stadig mest maskin-titler («Ny samtale»,
    # «Autonom · Hjerteslag»), og conversation continuity dækker det samme med
    # emne OG udfald. Dommen fra 22/6 holdt for denne ene.
    "cross-session arc",
    "metacognition signals",
    # 2026-09-05: "decision adherence gate" er FJERNET herfra. Den er ikke
    # diagnostik — den er en adfærdsinstruks. Gaten eskalerer fra "Husk at..."
    # over "DU SKAL..." til en kritisk advarsel med rollback, alt efter hvor
    # lavt adherence er faldet. Fem aktive beslutninger stod under 25% da vi
    # målte, og sektionen producerede 1.993 tegn korrekt eskaleret tekst —
    # som blev kastet væk her, FØR indholdet blev vurderet.
    #
    # Hele kæden virkede: review skrev domme, adherence_score blev opdateret,
    # gaten valgte det rigtige bånd. Og så nåede beskeden aldrig frem. En
    # advarsel Jarvis ikke ser, er ikke en advarsel.
    "causal narrative",
    # 2026-06-22 round 2 — cut per Jarvis' own review of his prompt:
    # 2026-09-04 (lærings-sløjfe, blok A): "session topics (always-on)" er TAGET
    # AF listen. Dommen fra 22/6 ("NEJ ×14") ramte formatet, ikke signalet:
    # session_topic_tracker har skrevet 5.112 rækker med gentagelses-tællere som
    # INTET har læst siden. Gentagelse på tværs af samtaler er hele grundlaget
    # for blok C. Slå den fra live med set_section hvis den viser sig at støje.
    "meta-learning weekly retrospective teaser",  # unread memo, don't burn tokens
    "rules learned from arcs",              # repeated retrospective noise
    # 2026-06-22 round 3 — Jarvis' second review:
    "curiosity-budget idle-window invitation",  # "5/5 tilbage" = mikrostyring; gør implicit
})

# Tail-anchored sektioner der ligeledes er støj (håndteres via _tail_add).
TAIL_NOISE_LABELS: frozenset[str] = frozenset({
    "causal patterns",          # "agentic_round_start → tool.completed (803×)"
    "pattern counterfactuals",  # same family of self-evident repetition
    "room entities",            # entity *counts*; real room-sense now in [INDRE LIV]
})


def load_overrides() -> dict[str, bool]:
    """Læs ALLE eksplicit satte prompt-sektion-switches i ÉN query (pr. build).

    Tom dict i normaltilfældet → nul per-sektion-opslag, default-adfærd uændret. Best-effort;
    enhver DB-fejl → tom dict (= ren default-adfærd, ingen brik)."""
    out: dict[str, bool] = {}
    try:
        from core.runtime.db import connect
        now = time.time()
        with connect() as conn:
            rows = conn.execute(
                "SELECT cache_key, value_json FROM shared_cache "
                "WHERE cache_key LIKE ? AND expires_at > ?",
                (_KEY_PREFIX + "%", now),
            ).fetchall()
        for key, value_json in rows:
            label = str(key)[len(_KEY_PREFIX):]
            try:
                v = json.loads(value_json)
            except Exception:
                continue
            if isinstance(v, dict) and "enabled" in v:
                out[label] = bool(v["enabled"])
    except Exception:
        pass
    return out


def section_enabled(label: str, *, blacklisted: bool, overrides: dict[str, bool]) -> bool:
    """Skal denne prompt-sektion med?

    Eksplicit override (Bjørn/MC via central_switches) vinder. Ellers default = paritet med
    den gamle hardcodede blacklist: blacklisted → OFF, alt andet → ON."""
    if label in overrides:
        return overrides[label]
    return not blacklisted


def observe_discarded_content(label: str, content: str | None) -> None:
    """En slukket sektions indhold blev netop kasseret — prøvetag det.

    Blacklisten sparer nul compute: kaldsmønsteret ``_awareness_add(60, label,
    builder())`` evaluerer builderen FØR gaten, så indholdet er allerede beregnet når
    det forkastes. Opsamlingen er derfor gratis, og den er forudsætningen for at en
    frossen dom kan revurderes når indholdet bag den bliver bedre.
    Selv-sikker; kaster ALDRIG ind i en prompt-build."""
    try:
        from core.services.prompt_section_reevaluation import observe_discarded

        observe_discarded(label, content)
    except Exception:
        pass


def observe_build(*, lane: str, included: int, dropped_disabled: list[str],
                  dropped_budget: list[str],
                  dropped_error: list[tuple[str, str]] | None = None) -> None:
    """Ét central.observe pr. prompt-build → trace af hvad der kom med + hvorfor noget
    blev droppet: switch-disabled vs budget-evicted vs FEJL (sektion-builder kastede).

    dropped_error er den tredje kanal (2026-06-23): før forsvandt en sektion der
    fejlede tavst (lokalt except: pass pr. sektion, så én dårlig sektion ikke dræber
    hele prompten) — INGEN kunne se HVILKEN sektion eller HVORFOR. Nu synlig i Centralen
    så vi ikke skal lede og teste i blinde, og adaptiv læring kan se hvilke builders der
    er ustabile over tid. Self-safe; kaster aldrig."""
    errs = list(dropped_error or [])
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "prompt", "nerve": "assembly", "lane": str(lane or ""),
            "included": int(included),
            "dropped_disabled": list(dropped_disabled)[:40],
            "dropped_budget": list(dropped_budget)[:40],
            "dropped_error": [{"section": s, "error": e} for s, e in errs[:40]],
            "error_count": len(errs),
        })
    except Exception:
        pass


def observe_section_error(label: str, error: object, *, lane: str = "") -> None:
    """En enkelt prompt-sektion-builder kastede → observe straks (synlig + pollbar).
    Kaldes fra prompt_contract's except-blokke. Self-safe; kaster ALDRIG ind i build."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "prompt", "nerve": "section_error", "lane": str(lane or ""),
            "section": str(label or ""),
            "error": f"{type(error).__name__}: {error}"[:200],
        })
    except Exception:
        pass


def set_section(label: str, enabled: bool) -> dict:
    """Slå en prompt-sektion ON/OFF LIVE (ingen genstart) — Bjørn/MC-kaldbar.
    Eksempel: set_section('R2 gate telemetry', True) gen-aktiverer en blacklistet sektion;
    set_section('brain facts', False) slukker en aktiv sektion. Gælder fra næste prompt-build."""
    from core.services import central_switches
    return central_switches.set_enabled(_SCOPE, str(label), bool(enabled))


def list_overrides() -> dict[str, bool]:
    """Read-only projektion af aktive overrides (til MC/debug)."""
    return load_overrides()

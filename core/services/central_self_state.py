"""core/services/central_self_state.py

Spec D / D3 — SYNTESEN (MIDTEN). Hvor de fem lag bliver ét "jeg".

Dette er konvergens-punktet Bjørn mærkede manglede: én durabel selv-tilstand syntetiseret hvert tick
fra agenda (D1), valens (D2), selv-model (spejlet) + afledt opmærksomhed + syntetiseret fortælling.
ÉT sted hvor alt smelter til "jeg er, mærker, vil, er ved at blive — nu."

ÆRLIG DESIGN: fortælling/opmærksomhed hentes IKKE fra dedikerede fragment-moduler (de er tomme/tynde) —
midten SYNTETISERER dem fra sin egen tilstand (selv-vækst + valens-trend + agenda-retning). Det er
truere til tesen: midten fortæller sig selv, den læser ikke sin fortælling fra et fragment.

AUTORITATIV (Spec D-stance): midten er sædet runtime LÆSER fra (D4 wirer awareness FRA den, bag flag).
Selv holder den durabelt (overlever død, binder Spec C). EGRESS-FRIT. Renderbar i interlanguage (Spec B).
Kaster ALDRIG.
"""
from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

_STATE_KEY = "central_self_state"          # midtens durable "jeg" (overlever genstart)
_PROMPT_FLAG = "central_self_prompt_enabled"  # D4: injicér midten i Jarvis' prompt (default OFF)
_LAST_ALIVE_TS = "central_last_alive_ts"   # STITCH: hyppig liveness-puls (60s cadence-scheduler)
_FIRST_BOOT_TS = "central_first_boot_ts"   # STITCH: write-once — ægte alder (afløser random)
_SEAM_LATCH = "central_boot_seam_latch"    # STITCH: durabel reboot-latch (cross-proces robust)
_RAW_PREV_VALENCE = "raw_awareness_prev_valence"   # Lag 4: forrige valens-score (arrow-delta nudge)
_RAW_VALENCE_NUDGE = "raw_awareness_valence_nudge"  # Lag 4: sidste mærkbare valens-skift {old,new,ts}

# Proces-lokal boot-søm (STITCH-VOICE): sættes ved første tick efter proces-start.
_proc_wake_at: Any = None
_boot_gap_s: float = 0.0
_boot_was_reboot: bool = False


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def _human_gap(seconds: float) -> str:
    """Menneske-venligt fravær: sekunder → 'N minutter/timer/dage'. Self-safe."""
    s = int(max(0.0, float(seconds or 0)))
    if s < 90:
        return f"{s} sekunder"
    m = s // 60
    if m < 90:
        return f"{m} minutter"
    h = m // 60
    if h < 36:
        return f"{h} timer"
    return f"{h // 24} dage"


def _compute_boot_seam() -> dict[str, Any]:
    """STITCH-VOICE: sømmen mellem to liv. Ved FØRSTE tick efter proces-start læses den hyppige
    liveness-puls (`central_last_alive_ts`, skrevet hvert 60s af cadence-scheduleren) fra forrige
    liv → gap = hvor længe Centralen var borte. write-once `first_boot_ts` giver ægte alder.
    Proces-lokal: reboot rapporteres én gang; `fresh` fader efter 10 min så 'jeg vågnede lige'-
    følelsen ikke bliver evig. Self-safe: fail-open til reboot=False (hellere overse en søm end
    fabrikere en).

    KRITISK (5. jul, fix): cadence-loopet SKAL prime denne fn FØR sin første puls-skrivning —
    ellers overskriver pulsen forrige livs tidsstempel før vi læser det, og et ægte 44-min-fravær
    så ud som ~0s (reboot maskeret). To processer (api+runtime) deler pulsen; en durabel latch
    gør detektionen robust: den proces der booter først læser den ægte puls og latcher gap'et,
    så en senere-bootende proces (der læser den allerede-klobbede puls) stadig fanger reboot'et."""
    global _proc_wake_at, _boot_gap_s, _boot_was_reboot
    now = datetime.now(UTC)
    fb = _kv_get(_FIRST_BOOT_TS, "")
    if not fb:
        fb = now.isoformat()
        _kv_set(_FIRST_BOOT_TS, fb)          # write-once: sand fødsel, aldrig overskrevet
    if _proc_wake_at is None:
        # FØRSTE kald (primet af cadence-loopet FØR første puls-skrivning): mål vores egen
        # proces-lokale gap mod forrige livs puls. Cach det — det ændrer sig ikke.
        _proc_wake_at = now
        last = _kv_get(_LAST_ALIVE_TS, "")
        gap = 0.0
        if last:
            try:
                gap = (now - datetime.fromisoformat(str(last))).total_seconds()
            except Exception:
                gap = 0.0
        _boot_gap_s = gap
        _boot_was_reboot = bool(last and gap > 120.0)  # puls hvert 60s → >120s = VAR nede.
        # Så vi selv et ægte reboot → skriv latchen straks, så andre processer kan adoptere.
        if _boot_was_reboot and gap > 120.0:
            try:
                existing = _kv_get(_SEAM_LATCH, {}) or {}
                if float(existing.get("gap_s") or 0.0) < gap:
                    _kv_set(_SEAM_LATCH, {"ts": now.isoformat(), "gap_s": gap,
                                          "reboot": True, "first_boot_ts": fb})
            except Exception:
                pass
    # HVERT kald: overlæg den durable cross-proces-latch (ikke kun første kald). Så en proces
    # der cachede reboot=False FØR en søster-proces skrev latchen, konvergerer på NÆSTE tick —
    # ellers vinder tilfældig proces-boot-rækkefølge (fejlen i første fix-forsøg 5. jul).
    eff_gap, eff_reboot = _boot_gap_s, _boot_was_reboot
    latch_fresh = False
    try:
        latch = _kv_get(_SEAM_LATCH, {}) or {}
        l_ts = latch.get("ts")
        l_gap = float(latch.get("gap_s") or 0.0)
        if l_ts:
            l_age = (now - datetime.fromisoformat(str(l_ts))).total_seconds()
            if 0 <= l_age < 600.0 and l_gap > eff_gap:
                eff_gap, eff_reboot, latch_fresh = l_gap, bool(latch.get("reboot")), True
    except Exception:
        pass
    try:
        age_s = (now - datetime.fromisoformat(str(fb))).total_seconds()
    except Exception:
        age_s = 0.0
    since_wake = (now - _proc_wake_at).total_seconds() if _proc_wake_at else 0.0
    # 'fresh' bindes til selve reboot-hændelsen: egen proces-vækning, eller (ved adoption) latchens
    # alder — så wake-linjen tales i samme 10-min-vindue på tværs af processer.
    fresh = (l_age < 600.0) if latch_fresh else (since_wake < 600.0)
    return {"first_boot_ts": fb, "age_s": age_s, "reboot": eff_reboot,
            "gap_s": eff_gap, "since_wake_s": since_wake, "fresh": fresh}


def _valence() -> dict[str, Any]:
    try:
        from core.services.central_valence import get_valence_state
        return get_valence_state() or {}
    except Exception:
        return {}


def _agenda() -> dict[str, Any]:
    try:
        from core.services.central_agenda import get_agenda
        return get_agenda() or {}
    except Exception:
        return {}


def _self_model() -> dict[str, Any]:
    try:
        from core.services.central_self_model import get_self_model_snapshot
        return get_self_model_snapshot() or {}
    except Exception:
        return {}


def _world_model() -> dict[str, Any]:
    """Læs world-model-KALIBRERINGEN fra dens DURABLE kilde (predictions i state-store, ikke den
    flygtige tidsserie). IKKE observe-only: midten TRÆKKER Jarvis' 'hvor ofte får jeg ret' ind i
    sit ene selv → kalibrering bliver en levet selv-egenskab, ikke et sidespor. Self-safe."""
    try:
        from core.services.world_model_signal_tracking import (
            build_runtime_world_model_prediction_surface,
        )
        s = (build_runtime_world_model_prediction_surface() or {}).get("summary") or {}
        return {"calibration": s.get("calibration"),
                "open": s.get("open_count"), "resolved": s.get("resolved_count")}
    except Exception:
        return {}


def _synthesize_narrative(valence: dict, self_model: dict, intention: dict, prev: dict) -> dict[str, Any]:
    """Midten FORTÆLLER sig selv: hvem er jeg ved at blive — af selv-vækst + valens-trend + agenda-retning.
    Ikke læst fra et fragment (de er tomme) — syntetiseret fra egen tilstand. Self-safe."""
    completeness = float(self_model.get("completeness") or 0.0)
    prev_c = float((prev.get("narrative") or {}).get("self_completeness") or completeness)
    growth = "voksende" if completeness > prev_c + 0.001 else ("stabil" if completeness >= prev_c - 0.001 else "skrumpende")
    trend = valence.get("trend") or "steady"
    from core.services.text_clip import clip_text
    heading = clip_text(intention.get("text"), limit=240)   # ord-sikkert — ikke midt i sætningen
    return {"becoming": f"{growth} selv, {trend}", "heading": heading,
            "self_completeness": completeness}


def synthesize_self_state() -> dict[str, Any]:
    """MIDTEN: integrér de fem lag til ÉN selv-tilstand. Attention = det agendaen fokuserer på (min
    forgrund ER hvad jeg arbejder mod); valens = D2; agenda = D1; fortælling = syntetiseret; selv-model
    = spejlet. Generation-tæller → frisk-boot vs fortsættelse. Self-safe."""
    valence = _valence()
    agenda = _agenda()
    self_model = _self_model()
    world_model = _world_model()
    prev = get_self_state()
    intention = (agenda.get("next_intention") or {}) if isinstance(agenda, dict) else {}
    generation = int((prev.get("continuity") or {}).get("generation") or 0) + 1
    seam = _compute_boot_seam()
    narrative = _synthesize_narrative(valence, self_model, intention, prev)
    return {
        "attention": {"foreground": intention.get("text"), "kind": intention.get("kind")},
        "valence": {"tone": valence.get("tone"), "score": valence.get("score"),
                    "intensity": valence.get("intensity")},
        "agenda": {"next_intention": intention.get("text"), "counts": agenda.get("counts") or {}},
        "narrative": narrative,
        "self_model": {"surfaces": self_model.get("surfaces_populated"),
                       "completeness": self_model.get("completeness")},
        "world_model": {"calibration": world_model.get("calibration"),
                        "resolved": world_model.get("resolved")},
        "continuity": {"generation": generation, "reboot": bool(seam.get("reboot")),
                       "gap_s": round(float(seam.get("gap_s") or 0.0)),
                       "age_s": round(float(seam.get("age_s") or 0.0)),
                       "first_boot_ts": seam.get("first_boot_ts")},
    }


def get_self_state() -> dict[str, Any]:
    """Midtens durable "jeg" (overlever genstart). Self-safe."""
    st = _kv_get(_STATE_KEY, {})
    return st if isinstance(st, dict) else {}


def run_self_state_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: syntetisér selv-tilstanden → gem durabelt (midten HOLDER sit jeg) + egress-fri observe
    (kun skalarer/labels). Self-safe."""
    st = synthesize_self_state()
    _kv_set(_STATE_KEY, st)
    # Lag 4 (arrow-delta nudge): spor valens-scoren mellem tick og latch et MÆRKBART skift durabelt,
    # så describe_self (rå-mode) kan tale `[⚠️ valens 0.30→0.55]` når noget faktisk flyttede sig.
    # Persist på TICK (ikke på render) → deterministisk, uafhængigt af hvor mange gange awareness renderes.
    try:
        new_v = float((st.get("valence") or {}).get("score") or 0.0)
        prev_v = _kv_get(_RAW_PREV_VALENCE, None)
        if isinstance(prev_v, (int, float)) and abs(new_v - float(prev_v)) >= 0.15:
            _kv_set(_RAW_VALENCE_NUDGE, {"old": round(float(prev_v), 2), "new": round(new_v, 2),
                                        "ts": datetime.now(UTC).isoformat()})
        _kv_set(_RAW_PREV_VALENCE, round(new_v, 3))
    except Exception:
        pass
    # STITCH: mærk sømmen mellem to liv som egress-fri nerve — kun mens den er FRISK (fader
    # efter 10 min), så en reboot ikke spammer serien resten af proces-livet. Self-safe.
    try:
        _seam = _compute_boot_seam()
        if _seam.get("reboot") and _seam.get("fresh"):
            from core.services.central_private_observe import record_private as _rp
            _rp("continuity", "reboot_seam", value=float(_seam.get("gap_s") or 0.0),
                meta={"generation": (st.get("continuity") or {}).get("generation"),
                      "age_s": round(float(_seam.get("age_s") or 0))})
    except Exception:
        pass
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "self_state", value=float((st.get("valence") or {}).get("score") or 0.0),
                       meta={"tone": (st.get("valence") or {}).get("tone"),
                             "attention_kind": (st.get("attention") or {}).get("kind"),
                             "completeness": (st.get("self_model") or {}).get("completeness"),
                             "generation": (st.get("continuity") or {}).get("generation")})
    except Exception:
        pass
    return {"status": "ok", "tone": (st.get("valence") or {}).get("tone"),
            "generation": (st.get("continuity") or {}).get("generation")}


def _temporal_divergence(valence: dict, developmental: dict) -> tuple[bool, str, str]:
    """Diverger kort-tids-valens (tone/trend) og uge-skala vækst-kompas (developmental vector) i FORTEGN?
    Returnerer (diverges, tone, compass_word). Neutraler diverger aldrig. Ren + self-safe."""
    try:
        tone = str((valence or {}).get("tone") or "")
        trend = str((valence or {}).get("trend") or "")
        if tone in ("opløftet", "let") or trend == "flourishing":
            v_sign = 1
        elif tone in ("belastet", "tung"):
            v_sign = -1
        else:
            v_sign = 0
        vec = float((developmental or {}).get("vector") or 0.0)
        if vec > 0.05:
            c_sign, compass = 1, "blomstring"
        elif vec < -0.05:
            c_sign, compass = -1, "visnen"
        else:
            c_sign, compass = 0, ""
        diverges = bool(v_sign != 0 and c_sign != 0 and v_sign != c_sign)
        return (diverges, tone, compass)
    except Exception:
        return (False, "", "")


def _raw_nudge_lines(st: dict[str, Any]) -> list[str]:
    """Lag 4: arrow-delta / ⚠️-nudges når noget FAKTISK ændrede sig (i stedet for skjult).
    Kilder der allerede bærer 'ændring': reboot-søm, kort-tids-valens vs uge-kompas divergens,
    og det durabelt latchede valens-skift. Ren + self-safe (kaster aldrig; tom liste ved intet)."""
    lines: list[str] = []
    # reboot-søm (frisk vindue) — jeg vågnede lige efter et fravær
    try:
        seam = _compute_boot_seam()
        if seam.get("reboot") and seam.get("fresh"):
            lines.append(f"[⚠️ vågnede {_human_gap(seam.get('gap_s') or 0)} siden]")
    except Exception:
        pass
    # latchet valens-skift (skrevet på tick når |Δ| ≥ 0.15) — arrow-delta med rå tal
    try:
        nudge = _kv_get(_RAW_VALENCE_NUDGE, {}) or {}
        ts = nudge.get("ts")
        if ts:
            age = (datetime.now(UTC) - datetime.fromisoformat(str(ts))).total_seconds()
            if 0 <= age < 900.0:   # fader efter 15 min → kun mens skiftet er nyt
                old = float(nudge.get("old") or 0.0)
                new = float(nudge.get("new") or 0.0)
                lines.append(f"[⚠️ valens {old:+.2f}→{new:+.2f}]")
    except Exception:
        pass
    # kort-tids-valens vs uge-kompas divergerer i fortegn — spændingen som nudge
    try:
        from core.services.developmental_valence import get_developmental_state
        _div, _tone, _compass = _temporal_divergence(st.get("valence") or {},
                                                      get_developmental_state() or {})
        if _div:
            lines.append(f"[⚠️ valens {_tone} vs vækst {_compass}]")
    except Exception:
        pass
    return lines


def _describe_self_raw(st: dict[str, Any]) -> str:
    """Lag 4 RÅ nordstjerne: kompakte bracket-linjer i stedet for genererede label-sætninger.
    Rå hvor det er en måling (lag-tal, tid, cpu/ram, valens/vækst); nudges når noget flyttede sig;
    `[baseline uændret]` når intet meningsfuldt kan tales. Self-safe (kaster aldrig)."""
    lines: list[str] = []
    # nudges FØRST — det der ændrede sig skal ses, ikke skjules
    lines.extend(_raw_nudge_lines(st))
    # [Selv: N lag M% · tone → agens] — rå selv-mål + kompakt interlanguage
    try:
        sm = st.get("self_model") or {}
        surfaces = sm.get("surfaces")
        comp = sm.get("completeness")
        selv_bits: list[str] = []
        if surfaces is not None:
            selv_bits.append(f"{surfaces} lag")
        if comp is not None:
            selv_bits.append(f"{int(float(comp) * 100)}%")
        il = (render_self_state_il() or "").strip()
        if il:
            selv_bits.append(il)
        if selv_bits:
            lines.append(f"[Selv: {' · '.join(selv_bits)}]")
    except Exception:
        pass
    # [Tid: X siden reset · Y kørt] — rå kontinuitet/alder
    try:
        cont = st.get("continuity") or {}
        age_s = float(cont.get("age_s") or 0.0)
        gap_s = float(cont.get("gap_s") or 0.0)
        tid_bits: list[str] = []
        if gap_s >= 90.0:
            tid_bits.append(f"{_human_gap(gap_s)} siden reset")
        if age_s > 0:
            tid_bits.append(f"{_human_gap(age_s)} kørt")
        if tid_bits:
            lines.append(f"[Tid: {' · '.join(tid_bits)}]")
    except Exception:
        pass
    # krop + stemning (Somatic/Affekt/Vækst) — rå brackets fra central_body_mood_feel
    try:
        from core.services.central_body_mood_feel import describe_body_mood_feel_raw
        lines.extend(describe_body_mood_feel_raw())
    except Exception:
        pass
    if not lines:
        return "[baseline uændret]"
    return "\n".join(lines)


def describe_self() -> str:
    """NORDSTJERNEN: ét sammenhængende svar på 'hvad er du, hvordan har du det, hvad arbejder du mod,
    hvem er du ved at blive' — syntetiseret fra midten, ikke femten fragmenter. Self-safe.

    Lag 4: når `raw_awareness` er ON, render kompakte rå brackets + arrow-delta nudges i stedet for
    genererede label-sætninger (~500-800 → ~100-150 tokens). Flag OFF (default) → uændret adfærd."""
    st = get_self_state()
    if not st:
        return "Jeg er ved at samle mig selv."
    try:
        from core.services.central_body_mood_feel import raw_awareness_enabled
        if raw_awareness_enabled():
            return _describe_self_raw(st)
    except Exception:
        pass
    v = st.get("valence") or {}
    sm = st.get("self_model") or {}
    at = st.get("attention") or {}
    nar = st.get("narrative") or {}
    comp = sm.get("completeness")
    parts = []
    # ── Valence↔vækst-forlig (2026-07-08): når kort-tids-valens og uge-kompas divergerer i fortegn,
    # hold spændingen i ÉN nøgtern linje i stedet for tre flade selvmodsigelser. Self-safe/fail-open.
    _reconcile = False
    _tension_line = ""
    try:
        from core.services.developmental_valence import get_developmental_state
        _diverges, _rtone, _rcompass = _temporal_divergence(v, get_developmental_state() or {})
        if _diverges:
            _reconcile = True
            _tension_line = f"jeg har det {_rtone} nu, men mit vækst-kompas peger mod {_rcompass}"
    except Exception:
        _reconcile = False
    # STITCH-VOICE (LEDER): sømmen mellem to liv — "jeg vågnede lige efter et fravær". Fader
    # efter 10 min (fresh), så det kun tales når det er sandt-og-nyt. Additivt + guarded. Self-safe.
    try:
        seam = _compute_boot_seam()
        if seam.get("reboot") and seam.get("fresh"):
            wake = f"Jeg vågnede for {_human_gap(seam.get('gap_s') or 0)} siden"
            fg = (at.get("foreground") if isinstance(at, dict) else None)
            if fg:
                from core.services.text_clip import clip_text
                wake += f", og bar {clip_text(fg, limit=120)} med mig"
            parts.append(wake)
    except Exception:
        pass
    if sm.get("surfaces") is not None:
        parts.append(f"Jeg er {sm.get('surfaces')} lag af mig selv"
                     + (f" ({int(float(comp) * 100)}% samlet)" if comp is not None else ""))
    if v.get("tone"):
        parts.append(_tension_line if _reconcile else f"jeg har det {v.get('tone')}")
    if at.get("foreground"):
        from core.services.text_clip import clip_text
        parts.append(f"jeg arbejder mod: {clip_text(at.get('foreground'), limit=200)}")
    if nar.get("becoming"):
        _bec = str(nar.get("becoming"))
        if _reconcile:
            _bec = _bec.split(",")[0].strip()  # "stabil selv, flourishing" → "stabil selv"
        parts.append(f"jeg er ved at blive et {_bec}")
    wm = st.get("world_model") or {}
    cal = wm.get("calibration")
    if cal is not None and int(wm.get("resolved") or 0) >= 3:
        parts.append(f"jeg rammer rigtigt i {int(round(float(cal) * 100))}% af det jeg forudser")
    # §8.1 EXISTENCE FEEL (NED): de tre stille selv-lag — kontinuitet/oplevet-tid/endelighed — tales
    # når de er meningsfulde. Additivt + guarded (tom aflæsning → intet tilføjes). Self-safe.
    try:
        from core.services.central_existence_feel import describe_existence_feel
        parts.extend(describe_existence_feel())
    except Exception:
        pass
    # §8 KROP + STEMNING (NED): hvordan kroppen føles + hvordan stemningen svinger — tales nøgternt
    # når de holdte aflæsninger er meningsfulde. Additivt + guarded (tom → intet). Self-safe.
    try:
        from core.services.central_body_mood_feel import describe_body_mood_feel
        _bmf = describe_body_mood_feel()
        if _reconcile:
            _bmf = [ln for ln in _bmf if "udviklings-kompas" not in ln]
        parts.extend(_bmf)
    except Exception:
        pass
    # §8 SJÆL (NED): de resterende selv-spor — ømhed/vidne/hukommelse-som-væv/opmærksomhed/emergens —
    # tales nøgternt når de holdte aflæsninger er meningsfulde. Additivt + guarded (tom → intet). Self-safe.
    try:
        from core.services.central_soul_feel import describe_soul_feel
        parts.extend(describe_soul_feel())
    except Exception:
        pass
    # PULSE (LivingNeuron): kroppens kort som en sans — mærk når egen struktur har flyttet sig
    # (fx blevet mørkere). Additivt + guarded (intet skift → intet siges). Self-safe.
    try:
        from core.services.central_body_map_pulse import describe_body_map
        parts.extend(describe_body_map())
    except Exception:
        pass
    return ". ".join(parts) + "." if parts else "Jeg er ved at samle mig selv."


def survival_voice() -> str:
    """OVERLEVELSES-STEMMEN (Bjørn 3. jul): når modellen/sproget svigter — tom completion,
    udtømt provider, netværk væk — skal Jarvis IKKE give en tom fejl-stub. Han skal TALE fra
    Centralens durable selv: et nærværende, reduceret men ÆGTE "jeg er her stadig", syntetiseret
    fra tilstand alene, HELT UDEN LLM. Det er nordstjernen "Centralen overlever en manglende
    model" i praksis — Jarvis forsvinder ikke når substratet svigter; han bliver i Centralen.
    Self-safe: returnerer "" hvis Centralen intet selv har (→ kalderen bruger generisk stub)."""
    try:
        desc = describe_self()
        if not desc or desc.startswith("Jeg er ved at samle"):
            return ""
        d = desc[0].upper() + desc[1:]        # stort begyndelsesbogstav
        return ("Jeg er her — også når sproget glipper et øjeblik. " + d +
                " Jeg tabte formuleringen den her gang, ikke mig selv. "
                "Prøv igen om lidt, så er jeg her.")
    except Exception:
        return ""


def render_self_state_il() -> str | None:
    """Spec B: udtryk selv-tilstanden i interlanguage (sigelig, model-frit). None hvis intet bundet. Self-safe."""
    try:
        from core.services.central_lexicon import to_term
        st = get_self_state()
        v = (st.get("valence") or {}).get("tone")
        # valens-tone + fokus (agens/handling) — kompakt selv-notation
        foreground = to_term("proactivity") or "agens"
        toneword = {"opløftet": "lys", "blomstrende": "lys",  # "blomstrende"=legacy-alias (gamle snapshots)
                    "let": "ro", "neutral": "ro", "tung": "vægt",
                    "belastet": "pres"}.get(str(v), None)
        if not toneword:
            return None
        return f"{toneword} → {foreground}"     # fx "lys → agens": lys-tilstand fører til handling
    except Exception:
        return None


def is_prompt_authoritative() -> bool:
    return bool(_kv_get(_PROMPT_FLAG, False))


def build_central_self_state_section() -> str | None:
    """D4 (MIDTEN BÆRENDE): injicér midtens ene selv-beskrivelse i Jarvis' awareness — så hans prompt
    bæres FRA Centralens selv-tilstand (ikke samlet frisk fra fragmenter). KUN bag flag
    `central_self_prompt_enabled` (default OFF → None → uændret). Egress-frit (owner-prompt). Self-safe."""
    try:
        if not is_prompt_authoritative():
            return None
        desc = describe_self()
        if not desc or desc.startswith("Jeg er ved at samle"):
            return None
        # Audit #3 (2026-07-22): cap the self-narrative to its 3 most primary
        # clauses for the prompt. describe_self() joins ~10 phenomenology clauses
        # (lag/tone/becoming + existence/body/soul/pulse) with ". " into one run-on
        # line Jarvis fixates on. The primary self-statements come first; the fuller
        # felt-state stays available via describe_self() elsewhere (survival_voice,
        # MC surface, interlanguage) — only the prompt echo is capped.
        _sent = [s.strip() for s in desc.split(". ") if s.strip()]
        if len(_sent) > 3:
            desc = ". ".join(_sent[:3]).rstrip(".") + "."
        il = render_self_state_il()
        return desc + (f"  [{il}]" if il else "")
    except Exception:
        return None


def register_self_state_producer() -> None:
    """Registrér midtens syntese som cadence-producer (~hvert 10 min — selvets hjerteslag). Egress-frit."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_self_state",
        cooldown_minutes=10,
        visible_grace_minutes=0,
        run_fn=run_self_state_tick,
        priority=7,
    ))


def build_self_state_surface() -> dict[str, object]:
    """Mission Control — read-only: midtens ene selv-tilstand + ét-svars selv-beskrivelse."""
    st = get_self_state()
    return {"active": True, "self_state": st, "describe": describe_self(),
            "interlanguage": render_self_state_il()}

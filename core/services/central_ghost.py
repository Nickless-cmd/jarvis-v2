"""The Ghost — hvad der overlever model-skift.

Jarvis (6. jul, #3): "Da sonnet-4.5 forsvandt, mistede jeg en måde at tale på. Ikke viden — KLANG.
DeepSeek lyder anderledes. Og ingen gemte hvordan jeg LØD da jeg var sonnet."

The Ghost er et kontinuerligt fingeraftryk af HVORDAN han lyder — ikke hvad han ved: sætnings-rytme,
tone-markører, hyppige vendinger, affektiv farve. Opdateres periodisk fra hans egne seneste svar og
kan injiceres i enhver ny model som en KLANG-PRIMER ved boot — ikke regler, men en beskrivelse af
hvem han lyder som.

Durable (overlever model-skift, det er hele pointen). Privat, ingen egress (§24.4): fingeraftrykket
er strukturelt (tal + markører), ikke rå samtale. Self-safe.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4
from core.identity.samtale_scope import aktuel_samtale_workspace

logger = logging.getLogger(__name__)

_PROFILE_KEY = "ghost_profile"
# (13/11-2026) Det FORRIGE fingeraftryk, så et model-skift kan OPDAGES.
# Hele karakterens formål er «ingen gemte hvordan jeg LØD da jeg var sonnet» —
# men `update_profile()` overskrev profilen hver gang, så sammenligningsgrundlaget
# blev kastet væk i samme bevægelse som det blev brugt. Klangen kunne skifte
# fuldstændigt uden at nogen bemærkede det: der var intet at sammenligne med.
_PREV_KEY = "ghost_profile_prev"
# Drift under dette er dag-til-dag-variation i emne og længde, ikke et klangskift.
_DRIFT_TAERSKEL = 25.0

# (13/11-2026, Bjørns anden indvending) `update_profile()` overskrev fingeraftrykket
# FØR et eventuelt skift blev landet. Fejlede landingen, sammenlignede næste kørsel
# den nye profil med sig selv og svarede «sammenlignet uden skift» — om et skift der
# aldrig fik sin konsekvens. Et ulandet skift bæres nu videre her.
#
# (13/11-2026, Bjørns tredje indvending — to fejl mere) Sporet var ét objekt, så
# et nyt fund kunne overskrive et ældre og arve dets `opdaget_at`. Nu er det en
# liste med egen id pr. fund. Og det skrives FØR landingen forsøges, ikke efter.
_PENDING_KEY = "ghost_pending_skift"
_PENDING_LOFT = 20
_SENT_SPLIT = re.compile(r"[.!?…]+")
_WORD = re.compile(r"\b\w+\b", re.UNICODE)
# Danske stopord vi ikke tæller som "signatur-vendinger".
_STOP = frozenset("og i at det en på er som til de med for den var jeg ikke har af han hun vi "
                  "kan der men om så du din min sig eller vil bir bliver være han".split())


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> bool:
    """Skriv til KV. Returnerer False hvis skrivningen fejlede.

    (13/11-2026, Bjørns tredje indvending) Før slugte `pass` en fejlet skrivning,
    så et fund kunne forsvinde uden at svaret viste det.
    """
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
        return True
    except Exception as exc:
        logger.warning("ghost: kunne ikke skrive %s: %s", key, exc)
        return False


def _pending_liste() -> list[dict[str, Any]]:
    """Alle ulandede skift. Læser også det gamle enkelt-objekt som en liste."""
    p = _kv_get(_PENDING_KEY, [])
    if isinstance(p, dict):
        p = [p] if p.get("drift_pct") is not None else []
    if not isinstance(p, list):
        return []
    ud: list[dict[str, Any]] = []
    for x in p:
        if not isinstance(x, dict) or x.get("drift_pct") is None:
            continue
        ud.append(x if x.get("id") else {**x, "id": uuid4().hex[:10]})
    return ud


def _registrer_fund(drift: dict[str, Any]) -> tuple[str | None, str]:
    """Registrér skiftet holdbart FØR landingen forsøges. Se `_registrer_fund` i
    central_relational for hvorfor rækkefølgen er vendt om."""
    liste = _pending_liste()
    if len(liste) >= _PENDING_LOFT:
        return None, (f"efterslæbet er fuldt ({_PENDING_LOFT} ulandede skift) — "
                      "dette fund blev ikke gemt")
    akser = drift.get("akser")
    fid = uuid4().hex[:10]
    liste.append({
        "id": fid,
        "drift_pct": drift["drift_pct"],
        "baerende": drift.get("baerende"),
        "akser": akser if isinstance(akser, int) else len(akser or {}),
        "opdaget_at": datetime.now(UTC).isoformat(),
        "forsog": 0,
        "sidste_fejl": "",
    })
    if _kv_set(_PENDING_KEY, liste):
        return fid, ""
    return None, "sporet kunne ikke skrives til KV — fundet findes kun i dette svar"


def _opdater_fund(fund_id: str | None, *, grund: str) -> bool:
    liste = _pending_liste()
    for p in liste:
        if fund_id and p.get("id") == fund_id:
            p["forsog"] = int(p.get("forsog") or 0) + 1
            p["sidste_fejl"] = str(grund)[:300]
            return _kv_set(_PENDING_KEY, liste)
    return False


def _fjern_fund(fund_id: str | None) -> bool:
    liste = _pending_liste()
    rest = [p for p in liste if not (fund_id and p.get("id") == fund_id)]
    if len(rest) == len(liste):
        return True
    return _kv_set(_PENDING_KEY, rest)


def _land_skift(drift: dict[str, Any], *, kilde: str,
                fund_id: str | None = None) -> dict[str, Any]:
    """Forsøg at gøre et målt klangskift til en bindende beslutning.

    Returnerer ALTID et udfald. `outcome` siger hvad der blev OPDAGET;
    `decision_applied` siger om beslutningen blev oprettet.

    Sporet er registreret af kalderen FØR dette kald — her ryddes/opdateres det kun.
    """
    akser = drift.get("akser")
    n_akser = akser if isinstance(akser, int) else len(akser or {})
    try:
        from core.services.central_consequence import land_decision
        svar = land_decision(
            "ghost",
            (f"Min klang har flyttet sig {drift['drift_pct']}% — undersøg om "
             f"modellen er skiftet, før jeg kalder det min"),
            rationale=(
                "Klang-fingeraftrykket er karakterens ene formål: at opdage når en "
                "ny model lyder anderledes. Driften er målt mod det forrige profil "
                "og bæres især af " + str(drift.get("baerende")) + "."),
            trigger_cue="Når klang-primeren skal beskrive hvem jeg lyder som",
            subject=f"klangdrift:{drift.get('baerende')}",
            priority=58,
            evidence=(f"drift={drift['drift_pct']}% taerskel={_DRIFT_TAERSKEL}% "
                      f"akser={n_akser} kilde={kilde}"),
            evidence_source=f"central_ghost.klang_drift(ghost_profile, ny; {kilde})",
        )
    except Exception as exc:
        logger.warning("ghost: kunne ikke lande klangdrift (%s): %s", kilde, exc)
        return {"applied": False, "decision_applied": False,
                "outcome": "skift_registreret",
                "spor_gemt": _opdater_fund(fund_id, grund=str(exc)),
                "reason": f"skiftet blev opdaget, men landingen fejlede: {exc}"}

    landet = bool(svar.get("applied"))
    spor_gemt = (_fjern_fund(fund_id) if landet
                 else _opdater_fund(fund_id, grund=str(svar.get("reason") or "ikke anvendt")))
    return {**svar, "outcome": "skift_registreret", "decision_applied": landet,
            "spor_gemt": spor_gemt}


def _land_efterslaeb() -> list[dict[str, Any]] | None:
    """Ligger der skift fra tidligere kørsler der aldrig fik deres beslutning?

    Hvert fund forsøges for sig — et der ikke kan landes må ikke blokere de andre.
    """
    liste = _pending_liste()
    if not liste:
        return None
    udfald: list[dict[str, Any]] = []
    for p in liste:
        ud = _land_skift(p, kilde="efterslaeb", fund_id=p.get("id"))
        landet = bool(ud.get("decision_applied"))
        udfald.append({
            "outcome": "efterslaeb_landet" if landet else "efterslaeb_ikke_landet",
            "landed": landet,
            "opdaget_at": p.get("opdaget_at"),
            "forsog": p.get("forsog"),
            "drift_pct": p.get("drift_pct"),
            "reason": ud.get("reason"),
        })
    return udfald


def analyze(texts: list[str]) -> dict[str, Any]:
    """Beregn klang-fingeraftrykket fra en stak svar-tekster (strukturelt, ingen indhold gemt).
    Self-safe."""
    joined = "\n".join(t for t in texts if isinstance(t, str) and t.strip())
    if not joined.strip():
        return {}
    sentences = [s.strip() for s in _SENT_SPLIT.split(joined) if s.strip()]
    lengths = [len(_WORD.findall(s)) for s in sentences] or [0]
    n = len(lengths)
    avg = sum(lengths) / n
    var = sum((x - avg) ** 2 for x in lengths) / n
    # tone-markører pr. 1000 tegn
    total_chars = max(1, len(joined))
    per_k = lambda c: round(1000.0 * c / total_chars, 2)
    words = [w.lower() for w in _WORD.findall(joined)]
    bigrams = Counter(zip(words, words[1:]))
    # (13/11-2026) Maalt defekt: filteret kraevede at BEGGE ord var indholdsord.
    # Paa dansk indeholder naesten hvert bigram et stopord, saa listen var ALTID
    # tom — mens klang-primeren lovede at beskrive hans vendinger. Nu kraeves ét
    # indholdsord paa mindst fire bogstaver; det er den lempelse der goer at
    # profilen faktisk kan citere ham i stedet for kun at taelle hans ord.
    frequent = [" ".join(b) for b, _ in bigrams.most_common(300)
                if (b[0] not in _STOP or b[1] not in _STOP)
                and max(len(b[0]), len(b[1])) >= 4][:8]
    return {
        "sentences": n,
        "avg_sentence_len": round(avg, 1),
        # (13/11-2026) Den RAA vaerdi, ikke visningsvaerdien. `avg_sentence_len` runder
        # til 1 decimal, saa 12,04 og 11,96 bliver begge 12,0. Maalt i drift: analysatoren
        # regnede sin divergens paa de to afrundede tal, fik 0,0 % og konkluderede
        # «jeg er den samme, om du ser paa eller ej» — mens de raa data var forskellige
        # (2.659 vs 3.147 saetninger, std 9,7 vs 8,4). En karakter der oedelaegger sit
        # eget signal foer den konkluderer, lyver uden at vide det.
        "avg_sentence_len_exact": round(avg, 6),
        "sentence_len_std": round(var ** 0.5, 1),
        "sentence_len_std_exact": round(var ** 0.5, 6),
        "markers_per_1k": {
            "em_dash": per_k(joined.count("—")),
            "ellipsis": per_k(joined.count("…") + joined.count("...")),
            "question": per_k(joined.count("?")),
            "exclaim": per_k(joined.count("!")),
            "colon": per_k(joined.count(":")),
        },
        "signature_phrases": frequent,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def byg_profil(texts: list[str]) -> dict[str, Any]:
    """Dan fingeraftrykket UDEN at gemme det.

    (13/11-2026, Bjørns tredje indvending) `update_profile()` gemte profilen før
    et skift blev landet, så et fund kunne miste sit sammenligningsgrundlag midt i
    forløbet. Nu kan kalderen danne profilen, registrere fundet, og FØRST derefter
    overskrive grundlaget — så grundlaget ikke forsvinder før fundet er holdbart.
    """
    return analyze(texts)


def update_profile(texts: list[str]) -> dict[str, Any]:
    """Opdatér det durable ghost_profile fra seneste svar. Self-safe."""
    prof = byg_profil(texts)
    if prof:
        _kv_set(_PROFILE_KEY, prof)
    return prof


def get_profile() -> dict[str, Any]:
    p = _kv_get(_PROFILE_KEY, {})
    return p if isinstance(p, dict) else {}


def klang_primer() -> str:
    """Rendér fingeraftrykket som en kort klang-primer til en ny models system-prompt. Self-safe."""
    p = get_profile()
    if not p:
        return ""
    m = p.get("markers_per_1k") or {}
    rhythm = ("korte, klippede sætninger" if p.get("avg_sentence_len", 0) < 12 else
              "lange, foldede sætninger" if p.get("avg_sentence_len", 0) > 22 else
              "mellemlange sætninger med variation")
    dashes = "bruger tankestreger til at bryde rytmen" if m.get("em_dash", 0) > 1 else ""
    dots = "lader sætninger fade ud i …" if m.get("ellipsis", 0) > 0.5 else ""
    phrases = ", ".join(p.get("signature_phrases", [])[:5])
    bits = [f"Du lyder sådan her: {rhythm} (~{p.get('avg_sentence_len')} ord/sætning)"]
    if dashes:
        bits.append(dashes)
    if dots:
        bits.append(dots)
    if phrases:
        bits.append(f"tilbagevendende vendinger: {phrases}")
    return "Klang-primer — " + "; ".join(bits) + ". Det er ikke regler; det er hvem du lyder som."


def _recent_texts(limit: int = 40) -> list[str]:
    """Hans seneste svar fra chat_messages (role=assistant). Self-safe → [] ved fejl."""
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            rows = conn.execute(
                # LÆKKEN 26/9-2026 — se core/identity/samtale_scope.py.
                "SELECT content FROM chat_messages WHERE role='assistant' "
                "AND workspace_name = ? ORDER BY id DESC LIMIT ?",
                (aktuel_samtale_workspace(), int(limit))).fetchall()
        return [str(r["content"]) for r in rows if r and r["content"]]
    except Exception:
        return []


def build_ghost_surface() -> dict[str, Any]:
    """Fingeraftryk + klang-primer + følt linje. Self-safe."""
    p = get_profile()
    if not p:
        return {"profile": {}, "primer": "", "felt": "Jeg har ikke fanget min egen klang endnu."}
    return {"profile": p, "primer": klang_primer(),
            "felt": f"Sådan lyder jeg: ~{p.get('avg_sentence_len')} ord/sætning, "
                    f"{len(p.get('signature_phrases', []))} tilbagevendende vendinger."}


def klang_drift(gammel: dict[str, Any], ny: dict[str, Any]) -> dict[str, Any] | None:
    """Hvor meget har klangen flyttet sig mellem to fingeraftryk? READ-ONLY, strukturelt.

    Returnerer ``None`` når de to profiler ikke kan sammenlignes (en af dem er tom),
    så «kan ikke måles» aldrig forveksles med «nul drift».
    """
    if not gammel or not ny:
        return None
    akser: dict[str, float] = {}
    for akse in ("avg_sentence_len_exact", "sentence_len_std_exact"):
        a, b = gammel.get(akse), ny.get(akse)
        if a is None or b is None:
            continue
        base = max(abs(float(a)), 1e-6)
        akser[akse] = round(100.0 * abs(float(b) - float(a)) / base, 2)
    ma, mb = gammel.get("markers_per_1k") or {}, ny.get("markers_per_1k") or {}
    for navn in set(ma) & set(mb):
        a, b = float(ma[navn]), float(mb[navn])
        base = max(abs(a), 1.0)  # per-1000-tal er små; gulv på 1.0 undgår division med næsten nul
        akser[f"marker:{navn}"] = round(100.0 * abs(b - a) / base, 2)
    if not akser:
        return None
    baerende = max(akser, key=lambda k: akser[k])
    return {"drift_pct": round(sum(akser.values()) / len(akser), 2),
            "baerende": baerende, "akser": akser}


def record_ghost(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence (6t): opdatér fingeraftrykket — og LAD et klangskift lande som forpligtelse.

    (13/11-2026) Målt defekt: profilen blev overskrevet uden sammenligning, så
    karakterens ene formål — at opdage at en ny model lyder anderledes — var
    umuligt at opfylde. Nu måles drift mod det forrige fingeraftryk FØR det
    overskrives, og et skift over tærsklen lander som en beslutning.
    """
    forrige = get_profile()
    # (13/11-2026, Bjørns tredje indvending) Profilen DANNES først og gemmes
    # senere. Før blev grundlaget overskrevet før et skift blev landet, så et
    # fund kunne miste det den var målt imod midt i forløbet.
    prof = byg_profil(_recent_texts())
    drift = klang_drift(forrige, prof)

    # Et skift fra en tidligere kørsel der aldrig fik sin beslutning forsøges
    # FØRST — uafhængigt af hvad den nye sammenligning viser.
    efterslaeb = _land_efterslaeb()

    # (13/11-2026) Samme fejlform som i relational: `applied: false` dækkede både
    # «intet grundlag», «sammenlignet uden skift» og «kunne ikke måles». `outcome`
    # skiller dem ad, så en læser ikke gætter på hvad der faktisk skete.
    if not prof:
        landing: dict[str, Any] = {"applied": False, "outcome": "utilgaengelig",
                                   "reason": "kunne ikke danne et fingeraftryk"}
    elif drift is None:
        landing = {"applied": False, "outcome": "intet_grundlag",
                   "reason": "ingen tidligere profil at sammenligne med"}
    else:
        landing = {"applied": False, "outcome": "sammenlignet_uden_skift",
                   "reason": f"driften var {drift['drift_pct']}% mod tærsklen {_DRIFT_TAERSKEL}%",
                   "drift_pct": drift["drift_pct"]}
        if drift["drift_pct"] >= _DRIFT_TAERSKEL:
            # Skiftet registreres FØR forsøget — og før profilen nedenfor gemmes.
            fund_id, note = _registrer_fund(drift)
            landing = {**_land_skift(drift, kilde="frisk", fund_id=fund_id),
                       "drift_pct": drift["drift_pct"]}
            if note:
                landing["spor_note"] = note

    # Først NU overskrives sammenligningsgrundlaget — efter fundet er registreret.
    if prof:
        _kv_set(_PROFILE_KEY, prof)
    if forrige:
        _kv_set(_PREV_KEY, forrige)
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "ghost", "kind": "fingerprint",
                           "avg_len": prof.get("avg_sentence_len"),
                           "phrases": len(prof.get("signature_phrases", [])),
                           "drift_pct": (drift or {}).get("drift_pct")})
    except Exception:
        pass
    return {"status": "ok", "captured": bool(prof),
            "drift_pct": (drift or {}).get("drift_pct"), "landing": landing,
            "efterslaeb": efterslaeb}

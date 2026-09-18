"""Kontekst-komprimering: ÉN sti, med de garantier den manglede.

Bjoerns spec 18/9-2026 («luk hullet mellem spec og drift»). Plan og maalinger:
docs/superpowers/plans/2026-09-18-kompaktering-en-sti.md.

## Hvorfor ét modul

Der var fire veje ind i `compact_session_history`, med fire forskellige
opsummeringer: den strukturerede baggrunds-komprimering, `/compact`-kommandoen
og to vaerktoejer. Kun den ene havde kvalitets-gate og mekanisk fallback; de
tre andre gemte `[Kontekst komprimeret — detaljer ikke tilgaengelige]` som
markoer naar udbyderen fejlede — en markoer uden indhold. Og ved siden af laa
`core/services/compaction_runtime.py` med 28 tests og nul kaldere: ren
token-aritmetik, der aldrig kunne komprimere noget, men som formulerede de
regler den koerende sti manglede. Reglerne er bragt hertil; modulet er slettet.

Alle kaldere gaar nu gennem `komprimer_session`.

## Garantierne

1. **Opsummeringen bygger videre paa den forrige.** Foer laeste hver
   komprimering de seneste 500 raekker og ERSTATTEDE den forrige markoer —
   alt aeldre forsvandt fra hans kontekst. Sessioner paa CT105 18/9: 8.344
   raekker/29 markoerer. Nu: den forrige markoer + beskederne efter den, dvs.
   praecis det Jarvis ser. (Se `session_compact._get_all_session_messages`.)
2. **Fremdrift eller intet.** En komprimering der ikke goer overfladen
   mindre, gemmes ikke (`NotAdvancing`). Den logges, og sessionen komprimeres
   ikke igen foer der er kommet nye beskeder. Manglende fremdrift er
   terminalt, ikke et retry — ellers bygges prompten, komprimeres og bygges
   igen uden at noget flyttede sig.
3. **En aegte timeout.** `with ThreadPoolExecutor(...)` venter paa det haengende
   kald ved exit. Maalt: timeout 1 s, kalderen blokeret 4,0 s. Nu
   `shutdown(wait=False)`.
4. **Et maskinlaesbart spor.** Hver komprimering skriver en raekke i
   `compaction_log` med `vej` ∈ {`llm`, `mekanisk`} og foer/efter-tokens.

## Overflow

Der findes ingen retry efter context-overflow: `HTTP_400_OVERFLOW` er
klassificeret ikke-retrybar (`stream_failure_kind`). Det er med vilje, og det
er pinnet i tests — et overflow er terminalt for turen.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_TIMEOUT_SEK = 45


class NotAdvancing(RuntimeError):
    """Komprimeringen gjorde ikke overfladen mindre. Et genforsoeg ville vaere
    samme kald med samme udfald — en loekke. (Navnet er arvet fra
    compaction_runtime, hvor reglen blev formuleret.)"""


# ── Den strukturerede opsummering ─────────────────────────────────────────

class StruktureretOpsummering:
    """summarise_fn til `compact_session_history`, med sporet `vej` bagefter.

    To trin: foerst foldes gamle tool-resultater til stubbe (deterministisk,
    gratis), SAA opsummeres der (et modelkald der kan tage fejl). Beskaering
    foer opsummering er ikke en optimering — den goer modelkaldet mindre og
    billigere at tage fejl i.

    Kvalitets-gaten afviser tomme, for korte og fejl-lignende svar; saa tager
    den mekaniske fallback over. Den kan ikke vaere tom.
    """

    def __init__(self, focus: str | None = None, *, session_id: str | None = None) -> None:
        self.focus = focus
        self.session_id = session_id
        #: 'llm' eller 'mekanisk' efter kaldet; '' foer.
        self.vej = ""
        self._gt = _ground_truth_for(session_id) if session_id else ""

    def __call__(self, old_msgs: list[dict]) -> str:
        from core.context.compact_llm import call_compact_llm
        from core.context.compaction_policy import (
            build_structured_summary_prompt,
            extract_summary,
            fold_old_tool_results,
            summary_looks_valid,
        )

        folded, _ = fold_old_tool_results(old_msgs, keep=0)
        prompt = build_structured_summary_prompt(
            folded, focus=self.focus, ground_truth=self._gt, max_transcript_chars=60_000,
        )
        # tillad_betalt: Bjoerns valg 19/8 — et compact-resumé ER Jarvis'
        # hukommelse om et helt forloeb, saa det maa koere paa primaer-modellen.
        # Da standarden blev vendt til gratis 14/9, fik de fire ANDRE
        # komprimerings-kaldere flaget — ikke denne, der er den der faktisk
        # koerer. Den har vaeret gratis-only siden.
        raw = _kald_med_timeout(call_compact_llm, prompt, max_tokens=2500, tillad_betalt=True)
        text = extract_summary(raw)
        if summary_looks_valid(text):
            self.vej = "llm"
            return text
        self.vej = "mekanisk"
        return mekanisk_opsummering(old_msgs)


def _kald_med_timeout(fn, *args, **kwargs) -> str:
    """Kald `fn` med en timeout der FAKTISK afbryder ventetiden.

    `with ThreadPoolExecutor(...)` kalder `shutdown(wait=True)` ved exit og
    venter dermed alligevel paa det haengende kald. Her lukkes eksekutoren uden
    at vente; traaden faar lov at doe af sig selv.
    """
    import concurrent.futures as cf

    ex = cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix="kompakt-llm")
    try:
        fut = ex.submit(fn, *args, **kwargs)
        return str(fut.result(timeout=_TIMEOUT_SEK) or "")
    except cf.TimeoutError:
        logger.warning("kompaktering: opsummering over %ds — mekanisk fallback", _TIMEOUT_SEK)
        return ""
    except Exception as exc:
        logger.warning("kompaktering: opsummering kastede (%s) — mekanisk fallback", exc)
        return ""
    finally:
        ex.shutdown(wait=False, cancel_futures=True)


def mekanisk_opsummering(old_msgs: list[dict]) -> str:
    """Deterministisk opsummering naar modellen ikke leverede. Aldrig tom.

    Den forrige opsummering baeres med i fuld laengde (op til 12.000 tegn):
    den er selv allerede komprimeret, og klippede vi den til 400 tegn som en
    almindelig besked, ville en fejlende udbyder slette alt aeldre.
    """
    dele: list[str] = []
    for m in old_msgs:
        rolle = str(m.get("role", "?"))
        c = " ".join(str(m.get("content") or "").split())
        if rolle == TIDLIGERE_RESUME:
            dele.append(f"[tidligere resumé] {c[:12_000]}")
            continue
        loft = 800 if rolle == "user" else 400
        dele.append(f"[{rolle}] {c[:loft]}{'…' if len(c) > loft else ''}")
    samlet = "\n".join(d for d in dele if d.strip()) or "[ingen beskeder at opsummere]"
    return (
        "<summary>[Mechanical fallback — the summariser model returned nothing usable, "
        "so this is a truncated but faithful record of the arc (user turns kept fuller). "
        "Full raw messages remain in the session DB under the compact marker.]\n"
        + samlet[:30_000] + "</summary>"
    )


# Rollen den forrige markoer faar som input. Egen rolle, saa den renderes med
# sit eget navn og ikke forveksles med noget Bjoern eller Jarvis sagde.
TIDLIGERE_RESUME = "tidligere_resume"


def _ground_truth_for(session_id: str) -> str:
    try:
        from core.context.compact_ground_truth import (
            collect_compact_ground_truth, format_ground_truth_block,
        )
        return format_ground_truth_block(collect_compact_ground_truth(session_id))
    except Exception:
        return ""


# ── Loggen: spor og fremdrift ─────────────────────────────────────────────

def _sikr_tabel(conn: Any) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS compaction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            udloeser TEXT NOT NULL DEFAULT '',
            vej TEXT NOT NULL DEFAULT '',
            tokens_foer INTEGER NOT NULL DEFAULT 0,
            tokens_efter INTEGER NOT NULL DEFAULT 0,
            fremdrift INTEGER NOT NULL DEFAULT 0,
            marker_id TEXT NOT NULL DEFAULT '',
            sidste_besked_id INTEGER NOT NULL DEFAULT 0,
            fejl TEXT NOT NULL DEFAULT ''
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_compaction_log_session ON compaction_log(session_id, id)"
    )


def _sidste_besked_id(conn: Any, session_id: str) -> int:
    row = conn.execute(
        "SELECT MAX(id) FROM chat_messages WHERE session_id = ? AND role != 'compact_marker'",
        (session_id,),
    ).fetchone()
    return int((row[0] if row else 0) or 0)


def log_komprimering(
    session_id: str, *, udloeser: str, vej: str, tokens_foer: int, tokens_efter: int,
    fremdrift: bool, marker_id: str = "", fejl: str = "",
) -> None:
    from datetime import UTC, datetime

    from core.runtime.db import connect
    try:
        with connect() as conn:
            _sikr_tabel(conn)
            conn.execute(
                "INSERT INTO compaction_log (session_id, created_at, udloeser, vej, tokens_foer,"
                " tokens_efter, fremdrift, marker_id, sidste_besked_id, fejl)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (session_id, datetime.now(UTC).isoformat(), udloeser, vej, int(tokens_foer),
                 int(tokens_efter), 1 if fremdrift else 0, marker_id,
                 _sidste_besked_id(conn, session_id), fejl[:500]),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("kompaktering: kunne ikke logge (%s)", exc)
    # Centralens maalepunkt — flyttet hertil fra visible_runs, hvor det kun
    # kunne fyre fra den slukkede komprimator og derfor aldrig gjorde det.
    try:
        from core.services import central_timeseries as _cts
        _cts.record("context", "run_compaction", 1.0 if fremdrift else 0.0,
                    meta={"session_id": session_id, "vej": vej, "udloeser": udloeser,
                          "tokens_foer": int(tokens_foer), "tokens_efter": int(tokens_efter)})
    except Exception:
        pass


def staar_fast(session_id: str) -> bool:
    """Sidste forsoeg gav ingen fremdrift, og der er ikke kommet noget nyt siden.

    Saa er et nyt forsoeg samme kald med samme udfald. Overfladen skal flytte
    sig — en ny besked — foer der proeves igen.
    """
    from core.runtime.db import connect
    try:
        with connect() as conn:
            _sikr_tabel(conn)
            row = conn.execute(
                "SELECT fremdrift, sidste_besked_id FROM compaction_log"
                " WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if not row or int(row[0]):
                return False
            return int(row[1]) == _sidste_besked_id(conn, session_id)
    except Exception:
        return False


def seneste_log(session_id: str) -> dict[str, Any] | None:
    from core.runtime.db import connect
    try:
        with connect() as conn:
            _sikr_tabel(conn)
            cur = conn.execute(
                "SELECT * FROM compaction_log WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {d[0]: row[i] for i, d in enumerate(cur.description)}
    except Exception:
        return None


# ── Indgangen ──────────────────────────────────────────────────────────────

def komprimer_session(
    session_id: str,
    *,
    udloeser: str,
    focus: str | None = None,
    low_water_tokens: int = 15_000,
) -> Any:
    """Komprimér sessionen. Returnerer `CompactResult`, eller None hvis der
    intet var at goere, sessionen staar fast, eller der ikke var fremdrift.

    `udloeser` siger hvem der bad om det (`auto`, `kommando`, `vaerktoej`) og
    staar i loggen.
    """
    from core.context.session_compact import compact_session_history

    sid = (session_id or "").strip()
    if not sid:
        return None
    if staar_fast(sid):
        logger.info("kompaktering: %s staar fast uden fremdrift — venter paa nye beskeder", sid)
        return None

    # Halen: lidt under low-water, saa resumé + hale ≈ low-water.
    hale = max(int(low_water_tokens * 0.8), 4_000)
    opsummering = StruktureretOpsummering(focus, session_id=sid)
    try:
        res = compact_session_history(
            sid, keep_recent_tokens=hale, summarise_fn=opsummering, kraev_fremdrift=True,
        )
    except NotAdvancing as exc:
        foer, efter = getattr(exc, "tokens", (0, 0))
        log_komprimering(sid, udloeser=udloeser, vej=opsummering.vej, tokens_foer=foer,
                         tokens_efter=efter, fremdrift=False, fejl=str(exc))
        logger.warning("kompaktering: %s — ingen fremdrift (%d → %d); terminalt", sid, foer, efter)
        return None
    if res is None:
        return None
    log_komprimering(sid, udloeser=udloeser, vej=opsummering.vej or "llm",
                     tokens_foer=res.tokens_foer, tokens_efter=res.tokens_efter,
                     fremdrift=True, marker_id=res.marker_id)
    res.vej = opsummering.vej or "llm"
    return res

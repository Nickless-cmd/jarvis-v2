#!/usr/bin/env python3
"""Mål koordineringen (§8) gennem den vej et initiativ faktisk går.

HVORFOR. Beslutning ``dec_9ba465a80a7b``: en måling skal angive HVILKEN FUNKTION
den blev målt gennem — ikke kun hvilken tabel tallet kom fra. 10/11-2026 gik en
forkert konklusion til Bjørn fordi ét led blev målt i stedet for turens vej.

DE TO VEJE (verificeret i koden)
  Vej A — når initiativet opstår (``core/services/initiative_queue.py``):
      push_initiative() → find_covering_work() → record_decision("coordinated")
      Spor: eventbussen ``coordination.decision`` (tabellen ``events``) og
      ``heartbeat.initiative_rejected``; ``runtime_initiatives`` for dem der kom ind.
  Vej B — når heartbeat afvikler det (``core/services/heartbeat_runtime.py``,
      ``_execute_heartbeat_internal_action("act_on_initiative")``):
      get_pending_initiatives() → claim_initiative() → claim_work()
        → decline_initiative(reason="koordineret: …") når claimed=False
      Spor: ``runtime_initiatives.disposition_reason``, ``runtime_tasks``
      (``origin_ref = "<tick>|<initiative_id>"``, ``work_fingerprint``) og
      ``coordination.decision`` fra ``record_decision`` inde i ``claim_work``.

HONESTITET
- ``værdi`` er et tal (også 0 = «målt til nul») eller ``None`` = «kan ikke måles».
  ``kan_ikke_måles`` rummer grunden. Aldrig en gættet procent.
- Målinger der hviler på ``coordination.decision`` kan KUN skelne «nul» fra «ikke
  instrumenteret endnu» hvis der findes mindst ét sådant event i databasen. Findes
  ingen, er svaret «kan ikke måles», ikke 0. Ligger vinduets start før det første
  event, markeres målingen ``delvist_vindue``.
- READ-ONLY: forbindelsen åbnes ``mode=ro``. Ingen skrivninger, ingen migrationer.

BRUG
    python3 scripts/koordinering_maaling.py            # sidste 24 timer
    python3 scripts/koordinering_maaling.py --hours 48
    python3 scripts/koordinering_maaling.py --json
    python3 scripts/koordinering_maaling.py --db /sti/til/jarvis.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
# Et pending-initiativ ældre end dette er «siddet fast» (køen udløber ellers selv).
FASTSIDDEN_TIMER = 6

NØGLER = (
    "1_initiativer_pr_doegn",
    "2_andel_selvstaendige_runs",
    "3_andel_overlap_eksisterende_arbejde",
    "4_reelle_dubletter",
    "5_legitime_fejlagtigt_afvist",
    "6_tokens_omkostning_dobbeltarbejde",
    "7_knyttet_til_eksisterende_arbejde",
    "8_parallelle_konflikter",
    "9_tabt_eller_siddet_fast",
)


def _m(
    *, værdi: Any = None, kilde: str, funktion: str, hvordan: str,
    kan_ikke_måles: str | None = None, **ekstra: Any,
) -> dict[str, Any]:
    """Ensartet svar. ``værdi=None`` ⇔ ``kan_ikke_måles`` er sat."""
    if (værdi is None) != (kan_ikke_måles is not None):
        raise ValueError("enten værdi eller kan_ikke_måles — aldrig begge/ingen")
    ud = {
        "værdi": værdi, "kilde": kilde, "funktion": funktion, "hvordan": hvordan,
        "kan_ikke_måles": kan_ikke_måles,
    }
    ud.update(ekstra)
    return ud


def åbn_readonly(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _beslutninger(conn: sqlite3.Connection, since: str) -> tuple[list[dict], str | None]:
    """Alle ``coordination.decision`` i vinduet + tidspunktet for det FØRSTE nogensinde."""
    første = conn.execute(
        "SELECT min(created_at) FROM events WHERE kind='coordination.decision'"
    ).fetchone()[0]
    rækker = conn.execute(
        "SELECT payload_json, created_at FROM events"
        " WHERE kind='coordination.decision' AND created_at >= ? ORDER BY id",
        (since,),
    ).fetchall()
    ud = []
    for payload, ts in rækker:
        try:
            p = json.loads(payload)
        except (TypeError, ValueError):
            p = {}
        p["_ts"] = ts
        ud.append(p)
    return ud, første


def _beslutnings_dækning(første: str | None, since: str) -> tuple[str | None, bool]:
    """(grund til at det ikke kan måles | None, vinduet er delvist)."""
    if første is None:
        return (
            "ingen coordination.decision-events findes i databasen overhovedet — "
            "record_decision() har ikke kørt i drift endnu, så 0 ville være en løgn "
            "(kan ikke skelnes fra 'ikke instrumenteret')",
            False,
        )
    return None, første[:19] > since


def mål(conn: sqlite3.Connection, hours: int = 24, nu: datetime | None = None) -> dict[str, Any]:
    nu = nu or datetime.now(UTC)
    since = _iso(nu - timedelta(hours=hours))
    res: dict[str, Any] = {}

    # --- grundtal --------------------------------------------------------
    init = conn.execute(
        "SELECT initiative_id, focus, status, disposition_reason, detected_at, updated_at,"
        " next_attempt_at FROM runtime_initiatives WHERE detected_at >= ? ORDER BY id",
        (since,),
    ).fetchall()
    afvist_ved_porten = conn.execute(
        "SELECT count(*) FROM events WHERE kind='heartbeat.initiative_rejected' AND created_at >= ?",
        (since,),
    ).fetchone()[0]
    beslutninger, første_beslutning = _beslutninger(conn, since)
    ikke_instrumenteret, delvist = _beslutnings_dækning(første_beslutning, since)
    n = len(init)

    # 1 -----------------------------------------------------------------
    res[NØGLER[0]] = _m(
        værdi=n,
        kilde="runtime_initiatives (detected_at i vinduet) + events heartbeat.initiative_rejected",
        funktion="push_initiative() (Vej A) — rækken skrives når alle porte er passeret",
        hvordan=(
            "tæller rækker i runtime_initiatives = initiativer der KOM IND i køen. "
            "Dem push_initiative() afviser ved porten persisteres ikke som række; deres "
            "antal står separat i 'afvist_ved_porten' (event heartbeat.initiative_rejected, "
            "som flere afvisningsgrunde deler — inkl. coordinated)."
        ),
        afvist_ved_porten=afvist_ved_porten,
        timer=hours,
        pr_doegn=round(n * 24.0 / hours, 2) if hours else None,
    )

    # 2 -----------------------------------------------------------------
    ids = [r[0] for r in init]
    med_task = 0
    if ids:
        for kid in ids:
            fundet = conn.execute(
                "SELECT 1 FROM runtime_tasks WHERE origin='heartbeat:initiative'"
                " AND origin_ref LIKE ? LIMIT 1",
                (f"%|{kid}",),
            ).fetchone()
            med_task += 1 if fundet else 0
    if n == 0:
        res[NØGLER[1]] = _m(
            kan_ikke_måles="ingen initiativer i vinduet — andelen har ingen nævner",
            kilde="runtime_initiatives × runtime_tasks",
            funktion="claim_work() i _execute_heartbeat_internal_action (Vej B)",
            hvordan="andel kan ikke udregnes ved nævner 0",
        )
    else:
        res[NØGLER[1]] = _m(
            værdi=round(med_task / n, 4),
            kilde="runtime_tasks.origin_ref = '<tick>|<initiative_id>' (origin='heartbeat:initiative')",
            funktion="claim_work() (Vej B) — create_task() skrives kun når claimed=True",
            hvordan=(
                f"{med_task} af {n} initiativer har en task skabt af claim_work(). "
                "Tasks fra hook:heartbeat.initiative_pushed er en ANDEN vej og tælles ikke."
            ),
            tæller=med_task, nævner=n,
        )

    # 3 + 7 ---------------------------------------------------------------
    declined_koord = [r for r in init if (r[3] or "").startswith("koordineret:")]
    if ikke_instrumenteret:
        for nøgle in (NØGLER[2], NØGLER[6]):
            res[nøgle] = _m(
                kan_ikke_måles=ikke_instrumenteret,
                kilde="events coordination.decision",
                funktion="record_decision() kaldt fra push_initiative() (Vej A) og claim_work() (Vej B)",
                hvordan="eneste persisterede spor af Vej A's 'coordinated'",
                vej_b_spor_i_tabel=len(declined_koord),
            )
    else:
        koord = [b for b in beslutninger if b.get("decision") == "coordinated"]
        med_cover = [b for b in koord if b.get("covering")]
        res[NØGLER[6]] = _m(
            værdi=len(med_cover),
            kilde="events coordination.decision (decision='coordinated', covering udfyldt)",
            funktion="record_decision() via find_covering_work() i push_initiative() (Vej A) og claim_work() (Vej B)",
            hvordan=(
                "tæller beslutninger med en navngiven dækkende relation. 'Korrekt' er IKKE "
                "verificeret — det kræver et menneskeligt facit (se måling 5)."
            ),
            delvist_vindue=delvist, første_event=første_beslutning,
            vej_b_declined_i_tabel=len(declined_koord),
        )
        samlet = len(beslutninger)
        if samlet == 0:
            res[NØGLER[2]] = _m(
                kan_ikke_måles="ingen beslutninger i vinduet — andelen har ingen nævner",
                kilde="events coordination.decision",
                funktion="record_decision()", hvordan="nævner 0",
            )
        else:
            res[NØGLER[2]] = _m(
                værdi=round(len(koord) / samlet, 4),
                kilde="events coordination.decision",
                funktion="record_decision() via find_covering_work() (Vej A+B)",
                hvordan=(
                    f"{len(koord)} 'coordinated' af {samlet} beslutninger "
                    "(coordinated + accepted fra claim_work)."
                ),
                tæller=len(koord), nævner=samlet,
                delvist_vindue=delvist, første_event=første_beslutning,
            )

    # 4 -------------------------------------------------------------------
    try:
        from core.services.work_coordination import work_fingerprint
    except Exception as exc:  # repo-import mislykkedes: sig det, gæt ikke
        work_fingerprint = None
        import_fejl = f"{type(exc).__name__}: {exc}"
    else:
        import_fejl = ""
    if work_fingerprint is None:
        res[NØGLER[3]] = _m(
            kan_ikke_måles=f"work_fingerprint() kunne ikke importeres ({import_fejl})",
            kilde="runtime_initiatives", funktion="work_fingerprint()",
            hvordan="fingeraftryk beregnes med repoets egen funktion",
        )
    else:
        grupper: dict[str, list[str]] = {}
        for kid, focus, status, *_ in init:
            if status != "acted":
                continue
            fp = work_fingerprint(focus or "")
            if fp:
                grupper.setdefault(fp, []).append(kid)
        dubletter = sum(len(v) - 1 for v in grupper.values() if len(v) > 1)
        res[NØGLER[3]] = _m(
            værdi=dubletter,
            kilde="runtime_initiatives (status='acted') i vinduet",
            funktion="work_fingerprint() — den samme funktion claim_work() låser på",
            hvordan=(
                "tæller ekstra acted-initiativer med IDENTISK fingeraftryk. Det er en "
                "NEDRE GRÆNSE for 'samme konkrete handling udført flere gange', ikke en dom: "
                "uden fingeraftryk (work_fingerprint='') findes ingen identitet, og runtime_tasks "
                "fra før koordineringen har ingen fingeraftryk at sammenligne."
            ),
            grupper_med_dubletter=sum(1 for v in grupper.values() if len(v) > 1),
        )

    # 5 -------------------------------------------------------------------
    res[NØGLER[4]] = _m(
        kan_ikke_måles=(
            "'legitim' er en dom og ingen funktion persisterer et facit. Hverken "
            "decline_initiative() eller record_decision() gemmer om afvisningen var "
            "rigtig — kun at den skete og hvorfor."
        ),
        kilde="runtime_initiatives.disposition_reason (declined) + events coordination.decision",
        funktion="decline_initiative() (Vej B) / record_decision() (Vej A)",
        hvordan=(
            "kun en øvre grænse kan aflæses: antal afvisninger — se 'øvre_grænse'. "
            "Et facit kræver manuel gennemgang af stikprøve."
        ),
        øvre_grænse={
            "declined_i_tabel": sum(1 for r in init if r[2] == "declined"),
            "coordinated_events": (
                None if ikke_instrumenteret
                else sum(1 for b in beslutninger if b.get("decision") == "coordinated")
            ),
            "afvist_ved_porten": afvist_ved_porten,
        },
    )

    # 6 -------------------------------------------------------------------
    res[NØGLER[5]] = _m(
        kan_ikke_måles=(
            "costs.run_id peger på visible_runs/agent_runs, ikke på initiativ eller "
            "runtime_tasks; claim_work() gemmer intet run_id. Der er intet led fra et "
            "initiativ til de tokens det kostede, og ingen markering af hvad der var dobbelt."
        ),
        kilde="costs / agent_runs (cost_usd, input_tokens, output_tokens)",
        funktion="claim_work() → runtime_tasks.create_task() — persisterer ikke run_id",
        hvordan=(
            "læst i tabel costs; funktion claim_work()/decline_initiative() persisterer ikke "
            "koblingen. Kræver at task/initiativ-id skrives på costs eller run."
        ),
    )

    # 8 -------------------------------------------------------------------
    if ikke_instrumenteret:
        res[NØGLER[7]] = _m(
            kan_ikke_måles=ikke_instrumenteret,
            kilde="events coordination.decision (reason='tabt-klaim-race')",
            funktion="claim_work() — IntegrityError-grenen på uq_runtime_tasks_work_active",
            hvordan="løbet efterlades kun som beslutningsevent; ingen tabel registrerer det",
        )
    else:
        n_race = sum(1 for b in beslutninger if b.get("reason") == "tabt-klaim-race")
        res[NØGLER[7]] = _m(
            værdi=n_race,
            kilde="events coordination.decision (reason='tabt-klaim-race')",
            funktion="claim_work() — IntegrityError-grenen på uq_runtime_tasks_work_active",
            hvordan=(
                "tæller tabte atomiske klaim. Samtidige kald der IKKE kolliderede på "
                "fingeraftrykket ses ikke."
            ),
            delvist_vindue=delvist, første_event=første_beslutning,
        )

    # 9 -------------------------------------------------------------------
    grænse = _iso(nu - timedelta(hours=FASTSIDDEN_TIMER))
    pending_gamle = conn.execute(
        "SELECT count(*) FROM runtime_initiatives WHERE status='pending' AND detected_at < ?",
        (grænse,),
    ).fetchone()[0]
    claimed_udløbet = conn.execute(
        "SELECT count(*) FROM runtime_initiatives WHERE status='pending'"
        " AND blocked_reason LIKE 'claimed-by:%' AND next_attempt_at != '' AND next_attempt_at < ?",
        (_iso(nu),),
    ).fetchone()[0]
    tasks_blokeret = conn.execute(
        "SELECT count(*) FROM runtime_tasks WHERE kind='initiative-followup'"
        " AND status IN ('blocked','queued','running') AND updated_at < ?",
        (grænse,),
    ).fetchone()[0]
    udløbet_i_vinduet = sum(1 for r in init if r[2] == "expired")
    res[NØGLER[8]] = _m(
        værdi=pending_gamle + claimed_udløbet + tasks_blokeret,
        kilde="runtime_initiatives (pending/claimed) + runtime_tasks (kind='initiative-followup')",
        funktion=(
            "get_pending_initiatives()/claim_initiative() (Vej B) — lease i next_attempt_at; "
            "claim_work() — task-status"
        ),
        hvordan=(
            f"summen af pending-initiativer ældre end {FASTSIDDEN_TIMER} t, claimede med "
            f"udløbet lease, og initiative-followup-tasks i blocked/queued/running der ikke "
            f"er rørt i {FASTSIDDEN_TIMER} t. 'Fastsiddet' er en tærskel jeg har valgt; "
            "tasks er et stående lager (ikke vinduesbegrænset)."
        ),
        pending_gamle=pending_gamle, claimed_lease_udløbet=claimed_udløbet,
        tasks_fastsiddende=tasks_blokeret,
        tabt_ved_udløb_i_vinduet=udløbet_i_vinduet,
    )
    return res


def _tekst(res: dict[str, Any], hours: int, since: str) -> str:
    ud = [f"Koordinering §8 — vindue {hours} t (fra {since}Z)", ""]
    for nøgle in NØGLER:
        m = res[nøgle]
        v = f"{m['værdi']}" if m["værdi"] is not None else "KAN IKKE MÅLES"
        ud.append(f"{nøgle}: {v}")
        ud.append(f"    kilde:    {m['kilde']}")
        ud.append(f"    funktion: {m['funktion']}")
        ud.append(f"    hvordan:  {m['hvordan']}")
        if m["kan_ikke_måles"]:
            ud.append(f"    kan ikke måles: {m['kan_ikke_måles']}")
        if m.get("delvist_vindue"):
            ud.append(f"    OBS delvist vindue: første event {m.get('første_event')}")
        ud.append("")
    return "\n".join(ud)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hours", type=int, default=24, help="vindue i timer (default 24)")
    ap.add_argument("--json", action="store_true", help="maskinlæsbart output")
    ap.add_argument("--db", type=Path, default=DB_PATH, help="sti til jarvis.db (read-only)")
    args = ap.parse_args(argv)
    if args.hours <= 0:
        raise SystemExit("--hours skal være > 0")
    nu = datetime.now(UTC)
    conn = åbn_readonly(args.db)
    try:
        res = mål(conn, args.hours, nu)
    finally:
        conn.close()
    since = _iso(nu - timedelta(hours=args.hours))
    if args.json:
        print(json.dumps(
            {"genereret": nu.isoformat(), "timer": args.hours, "fra": since + "Z", "målinger": res},
            ensure_ascii=False, indent=2,
        ))
    else:
        print(_tekst(res, args.hours, since))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Scoped-recall canary: seks invarianter, syntetiske poster, ingen produktion paavirket.

Skrevet 17/10-2026 som trin 6-7 i udrulningen af scoped recall
(`docs/superpowers/plans/2026-10-13-scoped-recall-unification.md`, Step 10).
Migrationen var koert 14/10 — 52.228 poster, nul i karantaene — men flaget
`scoped_recall_enabled` stod stadig OFF, fordi gaten var fail-closed og ingen
havde trykket paa knappen bagefter. Foelgen var maalt: `recall`,
`search_memory`, `recall_sensory_memories` og jarvis_brain svarede alle
«slået fra» i 18+ kaldesteder, saa arkiv-tjek maatte gaa gennem SQL i stedet.

Dette script er beviset der manglede. Det maaler de seks invarianter gennem
den AEGTE `recall`-vej — ikke en efterligning af den — med syntetiske poster
i `sensory_memories` og `private_brain_records`.

Faser:
  A. `recall_enabled` monkeypatches i PROCES-SCOPE, saa det globale flag
     forbliver OFF indtil invarianterne er bevist. Det er hele pointen:
     beviset skal komme FOER aendringen, ikke efter.
  B. (manuel) slaa det rigtige flag til og verificér gennem det rigtige
     vaerktoej — se MEMORY.md «Scoped recall — slået TIL 17/10-2026».
  C. Oprydning i `finally`, uanset om maalingen fejlede.

Invarianterne:
  1. Owner ser egen syntetisk post
  2. Member ser egen syntetisk post
  3. Owner ser IKKE members post
  4. Member ser IKKE owners post
  5. Ny query giver ikke forrige resultat (ingen stale scope)
  6. Arkiveret post bliver aldrig kandidat

ADVARSEL — scriptet SKRIVER i produktionstabellerne. Posterne er tagget med
et unikt `zzcanary<hex>`-praefiks og slettes igen i `finally`, men koer det
ikke mod en DB du ikke maa skrive i. Exit-kode 0 = alle seks groenne,
1 = mindst én invariant falsk, 2 = undtagelse undervejs.

Kør: `python3 scripts/diagnostics/recall_canary.py`
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Repo-roden findes relativt til filen (scripts/diagnostics/<denne fil>) — ikke
# en hardcoded sti, saa scriptet virker fra enhver checkout og fra en worktree.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from core.identity import workspace_context as wc
from core.identity.owner_resolver import owner_user_id
from core.runtime.db import connect
from core.services import scoped_recall_policy, semantic_memory
from core.services import recall as recall_mod

TAG = "zzcanary" + uuid.uuid4().hex[:8]
NOW = datetime.now(timezone.utc).isoformat()

OWNER_SENSORY = f"{TAG}-owner-sensory"
MEMBER_SENSORY = f"{TAG}-member-sensory"
OWNER_BRAIN = f"{TAG}-owner-brain"
ARCHIVED_BRAIN = f"{TAG}-archived-brain"

OWNER_TEXT = f"{TAG} ejerens syntetiske sanseindtryk blaalilla fyrtarn"
MEMBER_TEXT = f"{TAG} medlemmets syntetiske sanseindtryk groen komet"
BRAIN_TEXT = f"{TAG} ejerens private tanke om en messingventil"
ARCHIVED_TEXT = f"{TAG} arkiveret tanke om en kobberkedel"

report: dict[str, object] = {"tag": TAG, "invariants": {}, "errors": []}


def _seed():
    with connect() as conn:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute(
            "INSERT INTO sensory_memories (id,timestamp,modality,content,mood_tone,"
            "metadata_json,user_id) VALUES (?,?,?,?,?,?,?)",
            (OWNER_SENSORY, NOW, "mixed", OWNER_TEXT, "canary", "{}", OWNER_UID),
        )
        conn.execute(
            "INSERT INTO sensory_memories (id,timestamp,modality,content,mood_tone,"
            "metadata_json,user_id) VALUES (?,?,?,?,?,?,?)",
            (MEMBER_SENSORY, NOW, "mixed", MEMBER_TEXT, "canary", "{}", MEMBER_UID),
        )
        for rid, text, status in (
            (OWNER_BRAIN, BRAIN_TEXT, "active"),
            (ARCHIVED_BRAIN, ARCHIVED_TEXT, "archived"),
        ):
            conn.execute(
                "INSERT INTO private_brain_records (record_id,record_type,layer,"
                "session_id,run_id,focus,summary,detail,source_signals,confidence,"
                "status,created_at,updated_at,salience,domain,user_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rid, "canary", "private_brain", "", "", "canary", text, "",
                 "", "high", status, NOW, NOW, 1.0, "canary", OWNER_UID),
            )
        conn.commit()
    for table, sid, text, modality in (
        ("sensory_memories", OWNER_SENSORY, OWNER_TEXT, "mixed"),
        ("sensory_memories", MEMBER_SENSORY, MEMBER_TEXT, "mixed"),
        ("private_brain_records", OWNER_BRAIN, BRAIN_TEXT, "canary"),
        ("private_brain_records", ARCHIVED_BRAIN, ARCHIVED_TEXT, "canary"),
    ):
        ok = semantic_memory.index_memory(
            source_table=table, source_id=sid, content=text, modality=modality,
        )
        if not ok:
            report["errors"].append(f"embed failed: {table}:{sid}")


def _cleanup():
    with connect() as conn:
        conn.execute("PRAGMA busy_timeout=30000")
        for sid in (OWNER_SENSORY, MEMBER_SENSORY):
            conn.execute("DELETE FROM sensory_memories WHERE id=?", (sid,))
        for rid in (OWNER_BRAIN, ARCHIVED_BRAIN):
            conn.execute("DELETE FROM private_brain_records WHERE record_id=?", (rid,))
        conn.execute(
            "DELETE FROM memory_embeddings WHERE source_id IN (?,?,?,?)",
            (OWNER_SENSORY, MEMBER_SENSORY, OWNER_BRAIN, ARCHIVED_BRAIN),
        )
        conn.commit()


def _as(user_id: str, role: str, fn):
    tok = wc.set_context(workspace_name="canary", user_id=user_id, role=role)
    try:
        return fn()
    finally:
        wc.reset_context(tok)


def _refs(res: dict) -> set[str]:
    return {str(r.get("ref") or "") for r in (res.get("results") or [])}


def main() -> int:
    # Fase A: kun proces-scope, globalt flag urørt.
    recall_mod.recall_enabled = lambda: True
    scoped_recall_policy.recall_enabled = lambda: True

    report["global_flag_before"] = scoped_recall_policy.get_runtime_state_value(
        scoped_recall_policy.RECALL_FLAG, False,
    )
    report["owner_uid"] = OWNER_UID
    report["member_uid"] = MEMBER_UID
    _seed()

    def owner_sensory():
        return recall_mod.recall(
            f"{TAG} blaalilla fyrtarn", sources=["sensory"], limit=10,
        )

    def member_sensory():
        return recall_mod.recall(
            f"{TAG} groen komet", sources=["sensory"], limit=10,
        )

    def owner_brain():
        return recall_mod.recall(
            f"{TAG} messingventil", sources=["private_brain"], limit=10,
        )

    def owner_archived():
        return recall_mod.recall(
            f"{TAG} kobberkedel", sources=["private_brain"], limit=10,
        )

    def owner_changed():
        return recall_mod.recall(
            "kvantemekanik i brintatomer", sources=["sensory"], limit=10,
        )

    o = _as(OWNER_UID, "owner", owner_sensory)
    m = _as(MEMBER_UID, "member", member_sensory)
    ob = _as(OWNER_UID, "owner", owner_brain)
    oa = _as(OWNER_UID, "owner", owner_archived)
    oc = _as(OWNER_UID, "owner", owner_changed)

    o_refs, m_refs, ob_refs, oa_refs, oc_refs = (
        _refs(o), _refs(m), _refs(ob), _refs(oa), _refs(oc),
    )

    inv = report["invariants"]
    inv["1_owner_sees_owner_synthetic"] = OWNER_SENSORY in o_refs
    inv["2_member_sees_member_synthetic"] = MEMBER_SENSORY in m_refs
    inv["3_owner_not_sees_member"] = MEMBER_SENSORY not in o_refs
    inv["4_member_not_sees_owner"] = OWNER_SENSORY not in m_refs
    inv["5_changed_query_no_stale"] = OWNER_SENSORY not in oc_refs
    inv["6_archived_never_candidate"] = ARCHIVED_BRAIN not in oa_refs
    report["samples"] = {
        "owner_refs": sorted(o_refs)[:6],
        "member_refs": sorted(m_refs)[:6],
        "owner_brain_refs": sorted(ob_refs)[:6],
        "archived_query_refs": sorted(oa_refs)[:6],
        "changed_query_refs": sorted(oc_refs)[:6],
        "statuses": {
            "owner": o.get("status"), "member": m.get("status"),
            "owner_brain": ob.get("status"),
        },
    }
    return 0 if all(inv.values()) else 1


try:
    OWNER_UID = _as(owner_user_id(), "owner", lambda: scoped_recall_policy.require_private_scope())
    MEMBER_UID = _as("canary-member-synthetic", "member", lambda: scoped_recall_policy.require_private_scope())
    code = main()
except Exception as exc:  # noqa: BLE001 — canary skal rapportere, ikke skjule
    report["errors"].append(f"{type(exc).__name__}: {exc}")
    code = 2
finally:
    try:
        _cleanup()
        report["cleanup"] = "ok"
    except Exception as exc:  # noqa: BLE001
        report["cleanup"] = f"FAILED {type(exc).__name__}: {exc}"

report["exit"] = code
print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
sys.exit(code)

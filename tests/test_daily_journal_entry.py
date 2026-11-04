"""Dagbøgerne skal være RIGTIGE brain-poster, ikke filer indekset må springe over.

Målt 4/11-2026: alle 147 `*-daily.md` manglede frontmatter, og brain-indekset havde
0 af dem — den hukommelse de blev bygget til (6/6-2026, «han husker ikke en
halvdags arbejde») kunne aldrig genfindes.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from core.services import daily_journal_entry as je
from core.services import jarvis_brain

_STEMPEL = "2026-07-04T20:08:31.928524+00:00"
_KROP = (
    "# Daily journal — 2026-07-04\n\n"
    f"_Synthesized {_STEMPEL} — 80 chat-msgs, 20 carries._\n\n"
    "# 4. juli — En tænkning der kredsede\n\nBjørn og jeg talte om cachen.\n"
)


@pytest.fixture
def hjerne(tmp_path, monkeypatch):
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    obs = jarvis_brain.brain_dir() / "observation"
    obs.mkdir(parents=True)
    return obs


def _dagbog(obs, dag="2026-07-04", tekst=_KROP):
    p = obs / f"{dag}-daily.md"
    p.write_text(tekst, encoding="utf-8")
    return p


def test_en_dagbog_faar_frontmatter_der_kan_laeses_af_hjernen(hjerne):
    p = _dagbog(hjerne)
    assert je.ensure_frontmatter(p) == "added"

    fm, body = jarvis_brain.parse_frontmatter(p)
    e = jarvis_brain.entry_from_frontmatter(fm, body)
    assert (e.kind, e.visibility, e.domain) == ("observation", "intimate", "self")
    assert e.title == "Daily journal — 2026-07-04"
    assert e.tags == ["daily-journal"] and e.status == "active"
    assert e.id.startswith("brn_")
    assert e.created_at == datetime.fromisoformat(_STEMPEL)  # dagens egen stempel, ikke i dag


def test_kroppen_er_uaendret_ord_for_ord(hjerne):
    p = _dagbog(hjerne)
    je.ensure_frontmatter(p)
    _fm, body = jarvis_brain.parse_frontmatter(p)
    assert body.strip() == _KROP.strip()


def test_uden_stempel_bruges_filens_aendringstid(hjerne):
    import os
    p = _dagbog(hjerne, tekst="# Daily journal — 2026-07-04\n\nIngen stempel her.\n")
    os.utime(p, (1_783_000_000, 1_783_000_000))
    je.ensure_frontmatter(p)
    fm, body = jarvis_brain.parse_frontmatter(p)
    e = jarvis_brain.entry_from_frontmatter(fm, body)
    assert e.created_at == datetime.fromtimestamp(1_783_000_000, UTC)


def test_andet_kald_aendrer_intet_og_beholder_id(hjerne):
    p = _dagbog(hjerne)
    je.ensure_frontmatter(p)
    for_ = p.read_bytes()
    assert je.ensure_frontmatter(p) == "present"
    assert p.read_bytes() == for_


@pytest.mark.parametrize("navn, forventet", [
    ("2026-07-04-skift-fra-analyse-1PP1SAM5.md", "skipped:not-a-daily-journal"),
    ("2026-7-4-daily.md", "skipped:not-a-daily-journal"),
    ("notes-daily.md", "skipped:not-a-daily-journal"),
    ("2026-02-31-daily.md", "skipped:not-a-daily-journal"),
])
def test_kun_dagbogsfiler_roeres(hjerne, navn, forventet):
    p = hjerne / navn
    p.write_text("# noget andet\n", encoding="utf-8")
    assert je.ensure_frontmatter(p) == forventet
    assert p.read_text(encoding="utf-8") == "# noget andet\n"


def test_en_uskrivbar_fil_giver_et_resultat_ikke_et_nedbrud(hjerne):
    assert je.ensure_frontmatter(hjerne / "2026-07-05-daily.md") == "skipped:unreadable"


def test_backfill_taeller_hver_udfald_og_er_idempotent(hjerne):
    _dagbog(hjerne, "2026-07-04")
    _dagbog(hjerne, "2026-07-05", tekst="# Daily journal — 2026-07-05\n\nKort.\n")
    with_fm = _dagbog(hjerne, "2026-07-06")
    je.ensure_frontmatter(with_fm)
    (hjerne / "2026-07-04-andet-ABCDEFGH.md").write_text("x", encoding="utf-8")

    assert je.backfill() == {"added": 2, "present": 1, "skipped": 0, "total": 3}
    assert je.backfill() == {"added": 0, "present": 3, "skipped": 0, "total": 3}


def test_hver_dagbog_faar_sit_eget_id(hjerne):
    for d in ("2026-07-04", "2026-07-05", "2026-07-06"):
        _dagbog(hjerne, d)
    je.backfill()
    ids = {jarvis_brain.parse_frontmatter(p)[0]["id"] for p in hjerne.glob("*-daily.md")}
    assert len(ids) == 3


def test_efter_backfill_optager_indekset_dagbogen_uden_at_springe_den_over(hjerne, caplog):
    _dagbog(hjerne)
    je.backfill()
    with caplog.at_level("WARNING"):
        assert jarvis_brain.rebuild_index_from_files() == 1
    assert "kunne ikke parses" not in caplog.text
    conn = jarvis_brain.connect_index()
    try:
        raekke = conn.execute(
            "SELECT kind, visibility, domain, path FROM brain_index WHERE title LIKE 'Daily journal%'"
        ).fetchone()
    finally:
        conn.close()
    assert raekke[:3] == ("observation", "intimate", "self")
    assert raekke[3].endswith("observation/2026-07-04-daily.md")


def test_en_dagbog_uden_frontmatter_blev_sprunget_over_foer_rettelsen(hjerne, caplog):
    """Målingen af fejlen: uden frontmatter indekseres den ikke — og det logges."""
    _dagbog(hjerne)
    with caplog.at_level("WARNING"):
        assert jarvis_brain.rebuild_index_from_files() == 0
    assert "kunne ikke parses" in caplog.text


def test_dagbogen_er_kun_synlig_med_ejerens_loft(hjerne):
    """intimate: et medlems loft (public_safe) og personal-recall ser den ikke."""
    _dagbog(hjerne)
    je.backfill()
    jarvis_brain.rebuild_index_from_files()
    conn = jarvis_brain.connect_index()
    try:
        vis = conn.execute("SELECT visibility FROM brain_index WHERE title LIKE 'Daily journal%'").fetchone()[0]
    finally:
        conn.close()
    niveau = jarvis_brain._VIS_LEVEL
    assert vis == "intimate"
    assert niveau[vis] > niveau["personal"] > niveau["public_safe"]


def test_synthesize_skriver_nu_en_post_med_frontmatter(hjerne, monkeypatch):
    from core.services import daily_journal

    dag = date(2026, 7, 4)
    monkeypatch.setattr(daily_journal, "OBSERVATION_DIR", hjerne)
    monkeypatch.setattr(daily_journal, "_fetch_chat_pairs_for_day",
                        lambda d: [{"role": "user", "content": "x" * 30, "created_at": "t"}])
    monkeypatch.setattr(daily_journal, "_fetch_brain_carries_for_day", lambda d: [])
    monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                        lambda prompt, max_tokens=0: "Dagen handlede om cachen. " * 6)

    res = daily_journal.synthesize_daily_journal(dag)
    assert res["status"] == "written"

    fm, body = jarvis_brain.parse_frontmatter(hjerne / "2026-07-04-daily.md")
    assert fm["kind"] == "observation" and fm["visibility"] == "intimate"
    assert "# Daily journal — 2026-07-04" in body and "Dagen handlede om cachen." in body
    assert daily_journal.journal_exists_for(dag) is True
    assert jarvis_brain.rebuild_index_from_files() == 1


def test_overskrivning_med_force_beholder_id_saa_indekset_ikke_dobbelt(hjerne):
    dag = date(2026, 7, 4)
    p = hjerne / "2026-07-04-daily.md"
    je.write_journal(p, dag, _KROP)
    foer = jarvis_brain.parse_frontmatter(p)[0]["id"]
    jarvis_brain.rebuild_index_from_files()

    je.write_journal(p, dag, _KROP + "\nEn ny linje fra en gensyntese.\n")
    efter, body = jarvis_brain.parse_frontmatter(p)
    assert efter["id"] == foer and "en gensyntese" in body

    jarvis_brain.rebuild_index_from_files()
    conn = jarvis_brain.connect_index()
    try:
        raekker = conn.execute("SELECT id FROM brain_index WHERE path LIKE '%2026-07-04-daily.md'").fetchall()
    finally:
        conn.close()
    assert raekker == [(foer,)]

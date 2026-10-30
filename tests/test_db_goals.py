"""`last_progress_map` — sidste REELLE fremskridt, ikke sidste rørelse.

BAGGRUND (28/10-2026). `detect_stale_goals` målte `updated_at`, altså
RØRELSE. Jeg skrev en statusnote på tre forladte mål — noten SAGDE at de
var forladte — `updated_at` blev rørt, og vagten svarede pludselig 0.
En vagt der kan gøres blind ved at skrive til den måler ikke det den hedder.

`last_progress_map` er svaret: kun opdateringer hvor `progress_delta` er
sat flyttede noget. En note uden delta er en kommentar, ikke et skridt.

Testen kører mod rigtig sqlite via `isolated_runtime` — ikke en mock. En
mock på DB-laget kan ikke se om SQL'en faktisk filtrerer på delta.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=UTC)


@pytest.fixture
def goals(isolated_runtime):
    import core.runtime.db_goals as G

    class H:
        db = G

        def goal(self, title="et mål", **kw):
            return G.create_goal(title=title, description=kw.pop("description", None), **kw)

        def note(self, goal_id, *, delta=None, when=NOW, text="note"):
            """Skriv en opdatering. delta=None = ren kommentar, intet skridt."""
            return G.append_goal_update(
                goal_id=goal_id,
                note=text,
                progress_delta=delta,
                source="test",
            )

    return H()


def test_ren_note_taeller_ikke_som_fremskridt(goals):
    """Kernen i fejlen: en note uden delta må IKKE give et fremskridt."""
    g = goals.goal()
    goals.note(g["goal_id"], delta=None)

    assert goals.db.last_progress_map([g["goal_id"]]) == {}


def test_note_med_delta_taeller(goals):
    g = goals.goal()
    goals.note(g["goal_id"], delta=1)

    m = goals.db.last_progress_map([g["goal_id"]])
    assert g["goal_id"] in m
    assert m[g["goal_id"]]


def test_seneste_delta_vinder_over_tidligere(goals):
    """MAX(created_at) blandt delta-rækker — ikke første, ikke tilfældig."""
    g = goals.goal()
    goals.note(g["goal_id"], delta=1, text="først")
    goals.note(g["goal_id"], delta=1, text="sidst")

    m = goals.db.last_progress_map([g["goal_id"]])
    rows = goals.db.list_goal_updates(g["goal_id"], limit=10)
    med_delta = [r for r in rows if r.get("progress_delta") is not None]
    assert len(med_delta) == 2
    assert m[g["goal_id"]] == max(r["created_at"] for r in med_delta)


def test_delta_0_taeller_som_fremskridt(goals):
    """`progress_delta = 0` er en MÅLT opdatering, ikke en kommentar.

    SQL'en filtrerer på `IS NOT NULL`, ikke på `> 0`. Det er bevidst: en
    måling der viser nul fremgang er stadig en måling, og skal ikke gøre
    målet «forladt».
    """
    g = goals.goal()
    goals.note(g["goal_id"], delta=0)

    assert g["goal_id"] in goals.db.last_progress_map([g["goal_id"]])


def test_mål_uden_opdateringer_er_ikke_i_kortet(goals):
    """Intet fremskridt = ikke i map'en. Kalderen må selv vælge fødslen."""
    g = goals.goal()

    assert goals.db.last_progress_map([g["goal_id"]]) == {}


def test_tom_og_none_giver_tomt_kort(goals):
    """Skal ikke kaste — en tom forespørgsel er et gyldigt svar."""
    assert goals.db.last_progress_map([]) == {}
    assert goals.db.last_progress_map(None) == {}


def test_kun_de_spurgte_mål_kommer_med(goals):
    """Forespørgslen må ikke lække andre måls fremskridt ind i svaret."""
    a = goals.goal(title="a")
    b = goals.goal(title="b")
    goals.note(a["goal_id"], delta=1)
    goals.note(b["goal_id"], delta=1)

    m = goals.db.last_progress_map([a["goal_id"]])
    assert list(m) == [a["goal_id"]]


def test_ukendt_goal_id_giver_intet(goals):
    """Et id der ikke findes må give tomt, ikke en fejl eller en gættet række."""
    assert goals.db.last_progress_map(["goal_findes_ikke"]) == {}


def test_vagten_kan_ikke_goeres_blind_af_en_note(goals):
    """Hele pointen, målt ende-til-ende gennem vagten selv.

    Et mål der er gammelt, men får en frisk note UDEN delta, skal stadig
    være stale. Det er præcis den manøvre jeg lavede ved uheld i går.
    """
    from core.services.agent_self_evaluation import detect_stale_goals

    g = goals.goal(title="forladt mål")
    goals.note(g["goal_id"], delta=None, text="dette mål er forladt")

    # Gør målet kunstigt gammelt: fødslen er det ærlige udgangspunkt når
    # der aldrig har været et fremskridt. Tiden sættes direkte i basen fordi
    # `update_goal_fields` selv skriver `updated_at = nu` — og det er netop
    # hele pointen: `updated_at` er RØRELSE, `created_at` er FØDSEL.
    with goals.db.connect() as conn:
        goals.db._ensure_tables(conn)
        conn.execute(
            "UPDATE long_horizon_goals SET created_at = ?, updated_at = ? "
            "WHERE goal_id = ?",
            (
                (NOW - timedelta(days=40)).isoformat(),
                NOW.isoformat(),
                g["goal_id"],
            ),
        )

    ids = {s["goal_id"] for s in detect_stale_goals(stale_days=14)}
    assert g["goal_id"] in ids

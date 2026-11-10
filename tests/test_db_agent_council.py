"""F5: raadets sammenhaeng i DB. Rigtig sqlite."""
from __future__ import annotations

import pytest

O, S = "u1", "s1"


@pytest.fixture
def cdb(isolated_runtime):
    import core.runtime.db_agent_council as C

    class H:
        C_ = C

        def make(self, owner=O, key="", topic="t"):
            return C.create(owner_user_id=owner, origin_session_id=S, parent_run_id="pr", parent_agent_id="jarvis",
                            topic=topic, facts="f", synthesis_role="synthesizer", budget_tokens=0,
                            idempotency_key=key)
    return H()


def test_a_council_starts_provisioning_with_no_members_and_is_owner_scoped(cdb):
    """R0: raekken maa IKKE starte som ``gathering``.

    ``advance()`` behandler et raad i ``gathering`` som et raad hvis medlemmer arbejder.
    Bliver raekken indsat saadan med ``members_json='[]'``, ser supervisoren nul medlemmer
    der alle er "terminale" - og skriver en syntese over et tomt grundlag. Derfor starter
    den i ``provisioning``, som ingen supervisor maa avancere.
    """
    c = cdb.make()
    assert (c["status"], c["members"], c["synthesis_assignment_id"], c["topic"]) == ("provisioning", [], "", "t")
    assert cdb.C_.get(c["council_id"], O)["council_id"] == c["council_id"]
    assert cdb.C_.get(c["council_id"], "u2") is None
    with pytest.raises(cdb.C_.ContractError):
        cdb.C_.require(c["council_id"], "u2")


def test_set_members_moves_provisioning_to_gathering_and_is_idempotent(cdb):
    """Medlemmerne skrives ind foerst, og FOERST da bliver raadet et arbejdende raad."""
    c = cdb.make()
    cid = c["council_id"]
    cdb.C_.set_members(cid, [{"index": 1, "role": "critic", "task": "x", "assignment_id": "a", "agent_id": "g"}])
    assert cdb.C_.get(cid, O)["status"] == "gathering"
    # En retry maa ikke fejle paa at raadet allerede er flyttet.
    cdb.C_.set_members(cid, [{"index": 1, "role": "critic", "task": "x", "assignment_id": "a", "agent_id": "g"}])
    assert cdb.C_.get(cid, O)["status"] == "gathering"


def test_members_roundtrip_and_the_idempotency_key_is_unique_per_owner_and_session(cdb):
    c = cdb.make(key="k1")
    cdb.C_.set_members(c["council_id"], [{"index": 1, "role": "critic", "task": "x", "assignment_id": "a", "agent_id": "g"}])
    assert cdb.C_.get(c["council_id"], O)["members"][0]["role"] == "critic"
    assert cdb.C_.find_by_key(O, S, "k1")["council_id"] == c["council_id"]
    assert cdb.C_.find_by_key("u2", S, "k1") is None and cdb.C_.find_by_key(O, S, "") is None
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        cdb.make(key="k1")
    assert cdb.make(owner="u2", key="k1")["owner_user_id"] == "u2"


def test_transitions_are_compare_and_swap_and_only_open_councils_are_listed(cdb):
    c = cdb.make()
    cid = c["council_id"]
    assert cdb.C_.transition(cid, frm="synthesizing", to="done") is False          # forkert udgangspunkt
    cdb.C_.set_members(cid, [{"index": 1, "role": "critic", "task": "x", "assignment_id": "a", "agent_id": "g"}])
    assert cdb.C_.transition(cid, frm="gathering", to="synthesizing", synthesis_assignment_id="asg-9") is True
    assert cdb.C_.transition(cid, frm="gathering", to="synthesizing", synthesis_assignment_id="asg-X") is False
    assert cdb.C_.get(cid, O)["synthesis_assignment_id"] == "asg-9"
    assert [x["council_id"] for x in cdb.C_.open_councils()] == [cid]
    assert cdb.C_.transition(cid, frm="synthesizing", to="done") is True
    assert cdb.C_.open_councils() == [] and cdb.C_.get(cid, O)["synthesis_assignment_id"] == "asg-9"


def test_open_statuses_is_the_single_source_for_which_councils_are_open(cdb):
    """``open_councils()`` bygges fra ``OPEN_STATUSES`` - ikke fra en haandskrevet literal.

    En ny aaben status skal derfor kunne tilfoejes i maengden. Testen beviser baade at
    maengden er den forventede, og at alle dens statusser faktisk bliver fundet.
    """
    assert cdb.C_.OPEN_STATUSES == frozenset({"provisioning", "gathering", "synthesizing"})
    ids = {}
    for status in sorted(cdb.C_.OPEN_STATUSES):
        c = cdb.make(key=f"k-{status}")
        if status != "provisioning":
            cdb.C_.set_members(c["council_id"], [{"index": 1, "role": "critic", "task": "x",
                                                 "assignment_id": "a", "agent_id": "g"}])
        if status == "synthesizing":
            assert cdb.C_.transition(c["council_id"], frm="gathering", to="synthesizing") is True
        assert cdb.C_.get(c["council_id"], O)["status"] == status
        ids[status] = c["council_id"]
    assert {x["council_id"] for x in cdb.C_.open_councils()} == set(ids.values())
    # En terminal status er ikke aaben.
    done_id = ids["gathering"]
    assert cdb.C_.transition(done_id, frm="gathering", to="done") is True
    assert done_id not in {x["council_id"] for x in cdb.C_.open_councils()}


def test_advance_never_creates_a_synthesis_for_a_council_without_members(cdb, monkeypatch):
    """R0-racen: nul medlemmer, alle "terminale" -> syntese over et tomt grundlag.

    To veje skal vaere lukket: raadet staar i ``provisioning`` (medlemmerne er ikke skrevet
    ind endnu), eller det staar i ``gathering`` med en tom liste (en gammel raekke fra foer
    tilstanden fandtes). Ingen af dem maa naa dispatch.
    """
    import core.services.agent_council as ac
    calls = []
    monkeypatch.setattr(ac.svc, "dispatch_agent", lambda **kw: calls.append(kw) or {"status": "accepted"})

    fresh = cdb.make(key="k-fresh")
    assert fresh["status"] == "provisioning"
    assert ac.advance() == []

    stale = cdb.make(key="k-stale")
    conn = cdb.C_._conn()
    conn.execute("UPDATE agent_councils SET status='gathering', members_json='[]' WHERE council_id=?",
                 (stale["council_id"],))
    conn.commit()
    assert ac.advance() == [{"council_id": stale["council_id"], "action": "cancelled_empty"}]
    assert calls == [], f"syntese blev dispatchet over et tomt grundlag: {calls}"
    # Den gamle raekke skal ikke bare springes over - den kan aldrig blive faerdig, saa den
    # lukkes. Ellers laa den i open_councils() for evigt med en advarsel ved hvert tick.
    assert cdb.C_.get(stale["council_id"], O)["status"] == "cancelled"
    # Den friske raekke er legitimt aaben (den er midt i en samling); den gamle er lukket.
    assert stale["council_id"] not in {x["council_id"] for x in cdb.C_.open_councils()}


def test_set_members_with_an_empty_list_cannot_open_a_council(cdb):
    """Et raad i ``gathering`` uden medlemmer ER fejlen. Lageret maa ikke kunne skabe den."""
    c = cdb.make(key="k-empty")
    cid = c["council_id"]
    cdb.C_.set_members(cid, [])
    assert cdb.C_.get(cid, O)["status"] == "provisioning"      # ikke flyttet
    cdb.C_.set_members(cid, [{"index": 1, "role": "critic", "task": "x", "assignment_id": "a", "agent_id": "g"}])
    assert cdb.C_.get(cid, O)["status"] == "gathering"


def test_a_synthesizing_council_is_still_closed_when_its_member_list_is_empty(cdb):
    """Regression: vagt mod tomme medlemslister maa ikke ramme ``synthesizing``.

    En raekke i ``synthesizing`` har en syntese der skal lukkes. Bliver den sprunget over
    fordi medlemslisten er tom, kan den aldrig naa ``done`` - den laa fast foer rettelsen.
    """
    import core.services.agent_council as ac
    c = cdb.make(key="k-synth")
    cid = c["council_id"]
    conn = cdb.C_._conn()
    conn.execute(
        "UPDATE agent_councils SET status='synthesizing', members_json='[]', "
        "synthesis_assignment_id='asg-none' WHERE council_id=?", (cid,))
    conn.commit()
    ac.advance()
    assert cdb.C_.get(cid, O)["status"] == "synthesizing"      # syntesen findes ikke endnu
    conn.execute(
        "INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id, origin_session_id, goal, status, "
        "created_at, updated_at) VALUES ('asg-none','g1',?,'s1','syntese','completed','2026-01-01','2026-01-01')",
        (O,))
    conn.commit()
    ac.advance()
    assert cdb.C_.get(cid, O)["status"] == "done"


def test_abandon_from_provisioning_cancels_instead_of_stranding_the_council(cdb):
    """Et afbrudt raad skal ende i ``cancelled`` - ikke staa fast i en status ingen sweep ser."""
    import core.services.agent_council as ac
    c = cdb.make(key="k-abandon")
    cid = c["council_id"]
    ac._abandon(O, S, cid, [], cdb.C_.PROVISIONING)
    assert cdb.C_.get(cid, O)["status"] == "cancelled"
    assert cdb.C_.open_councils() == []


def test_advance_lukker_et_raad_efterladt_i_provisioning_og_frigiver_noeglen(cdb):
    """Genstart midt i samlingen: raekken staar i provisioning uden medlemmer.

    Foer rettelsen kunne den hverken blive faerdig eller forsvinde: ``advance()`` sprang
    den over for evigt, og dens idempotensnoegle laaste en retry ude med
    IDEMPOTENCY_CONFLICT — permanent.
    """
    import core.services.agent_council as ac

    c = cdb.make(key="k-left")
    cid = c["council_id"]
    conn = cdb.C_._conn()
    conn.execute("UPDATE agent_councils SET created_at=? WHERE council_id=?",
                 ("2026-01-01T00:00:00+00:00", cid))
    conn.commit()

    assert ac.advance() == [{"council_id": cid, "action": "abandoned_provisioning"}]
    row = cdb.C_.get(cid, O)
    assert row["status"] == "cancelled"
    assert row["idempotency_key"] == "", "noeglen skal vaere frigivet til et nyt forsoeg"
    assert cdb.C_.open_councils() == []
    assert cdb.C_.find_by_key(O, S, "k-left") is None


def test_en_samling_der_lige_er_startet_maa_ikke_lukkes(cdb):
    """Grace-vinduet: en aktiv ``convene()``-loekke skriver medlemmerne ind inden for sekunder."""
    import core.services.agent_council as ac

    c = cdb.make(key="k-fresh")
    assert ac.advance() == []
    assert cdb.C_.get(c["council_id"], O)["status"] == "provisioning"
    assert cdb.C_.get(c["council_id"], O)["idempotency_key"] == "k-fresh"


def test_et_raad_med_medlemmer_lukkes_ikke_som_forladt(cdb):
    """Kun TOMME provisioning-raekker er forladte — er listen skrevet ind, er samlingen naaet videre."""
    import core.services.agent_council as ac

    c = cdb.make(key="k-has-members")
    cid = c["council_id"]
    conn = cdb.C_._conn()
    conn.execute("UPDATE agent_councils SET created_at=? WHERE council_id=?",
                 ("2026-01-01T00:00:00+00:00", cid))
    conn.commit()
    cdb.C_.set_members(cid, [{"index": 1, "role": "critic", "task": "x", "assignment_id": "a", "agent_id": "g"}])
    assert cdb.C_.get(cid, O)["status"] == "gathering"
    assert cdb.C_.abandon_stale_provisioning(cid) is False

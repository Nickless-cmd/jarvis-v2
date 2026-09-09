"""Godkendelses-broen — én beslutning, bundet til ÉT kald, brugt ÉN gang.

Fase 3, K4 og K5:
    «approval claim and `dispatching` commit in one transaction before crossing
     the provider boundary»
    «it stores the exact invocation digest and atomically consumes one decision»

Den fejl broen findes for: i dag er en godkendelse nøglet på `approval_id`
alene. Ændrede argumenterne sig mellem at kortet blev vist og at der blev
klikket ja, ville godkendelsen stadig gælde — man sagde ja til «slet /tmp/x»
og fik «slet /». Ingen kode ville opdage det, fordi ingen gemte hvad man sagde
ja TIL.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.runtime import db_approval_bridge as B
from core.runtime.db_approval_bridge import ApprovalRefused


@pytest.fixture
def aid(isolated_runtime):
    return "appr-" + datetime.now(UTC).strftime("%H%M%S%f")


ARGS = {"command": "rm -rf /tmp/x"}


def _bed(aid, args=None, **kw):
    return B.request(aid, tool_name="bash", arguments=args or ARGS, **kw)


# ── digesten er bundet til KALDET ────────────────────────────────────────

def test_samme_kald_giver_samme_digest():
    a = B.invocation_digest("bash", {"command": "ls", "cwd": "/x"})
    b = B.invocation_digest("bash", {"cwd": "/x", "command": "ls"})
    assert a == b, "nøglerækkefølge må ikke ændre digesten"


def test_ET_ANDET_kald_giver_en_anden_digest():
    assert B.invocation_digest("bash", {"command": "ls"}) != \
           B.invocation_digest("bash", {"command": "rm -rf /"})


def test_et_andet_VAERKTOEJ_giver_en_anden_digest():
    assert B.invocation_digest("bash", ARGS) != B.invocation_digest("operator_bash", ARGS)


def test_runtime_plumbing_taeller_IKKE_med():
    """`_runtime_trust_all` og `_runtime_session_id` er ikke noget brugeren så
    på kortet — de må ikke kunne ugyldiggøre en godkendelse."""
    a = B.invocation_digest("bash", {"command": "ls"})
    b = B.invocation_digest("bash", {"command": "ls", "_runtime_trust_all": True,
                                     "_runtime_session_id": "s1"})
    assert a == b


# ── livscyklussen ────────────────────────────────────────────────────────

def test_den_normale_vej(aid):
    _bed(aid)
    assert B.state(aid)["state"] == B.PENDING
    assert B.decide(aid, approved=True) is True
    assert B.state(aid)["state"] == B.APPROVED
    c = B.claim(aid, tool_name="bash", arguments=ARGS)
    assert c["state"] == B.DISPATCHING
    assert B.settle(aid, ok=True) is True
    assert B.state(aid)["state"] == B.COMPLETED


def test_dispatching_staar_i_databasen_FOER_udbyder_graensen(aid):
    """Det er hele pointen: tilstanden er committet, ikke kun i hukommelsen."""
    _bed(aid); B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS)
    assert B.state(aid)["state"] == B.DISPATCHING
    assert B.state(aid)["claimed_at"]


# ── den fejl broen findes for ────────────────────────────────────────────

def test_ANDRE_argumenter_kan_ikke_overtage_godkendelsen(aid):
    """«Man sagde ja til slet /tmp/x og fik slet /.»"""
    _bed(aid, {"command": "rm -rf /tmp/x"})
    B.decide(aid, approved=True)
    with pytest.raises(ApprovalRefused, match="et ANDET kald"):
        B.claim(aid, tool_name="bash", arguments={"command": "rm -rf /"})


def test_afslaget_siger_HVAD_der_blev_sagt_ja_til(aid):
    _bed(aid, {"command": "a"}); B.decide(aid, approved=True)
    with pytest.raises(ApprovalRefused) as e:
        B.claim(aid, tool_name="bash", arguments={"command": "b"})
    assert "sagt ja til" in str(e.value)


def test_et_andet_VAERKTOEJ_kan_heller_ikke_overtage(aid):
    _bed(aid); B.decide(aid, approved=True)
    with pytest.raises(ApprovalRefused, match="ANDET kald"):
        B.claim(aid, tool_name="operator_bash", arguments=ARGS)


def test_tilstanden_er_UROERT_efter_et_afvist_forsoeg(aid):
    """Et forkert forsøg må ikke bruge godkendelsen op."""
    _bed(aid); B.decide(aid, approved=True)
    with pytest.raises(ApprovalRefused):
        B.claim(aid, tool_name="bash", arguments={"command": "andet"})
    assert B.state(aid)["state"] == B.APPROVED
    assert B.claim(aid, tool_name="bash", arguments=ARGS)["state"] == B.DISPATCHING


# ── nøjagtig ÉN overtagelse ──────────────────────────────────────────────

def test_godkendelsen_gaelder_EN_gang(aid):
    _bed(aid); B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS)
    with pytest.raises(ApprovalRefused, match="allerede overtaget"):
        B.claim(aid, tool_name="bash", arguments=ARGS)


def test_to_samtidige_overtagelser_giver_EN_vinder(aid):
    """Vinduet mellem pop og eksekvering var der to arbejdere begge kunne nå
    frem. Nu er det én sætning."""
    import threading
    _bed(aid); B.decide(aid, approved=True)
    vundet, tabt = [], []
    def _proev():
        try:
            B.claim(aid, tool_name="bash", arguments=ARGS); vundet.append(1)
        except ApprovalRefused:
            tabt.append(1)
    traade = [threading.Thread(target=_proev) for _ in range(8)]
    for t in traade: t.start()
    for t in traade: t.join()
    assert len(vundet) == 1 and len(tabt) == 7


def test_et_NEJ_kan_ikke_overtages(aid):
    _bed(aid); B.decide(aid, approved=False)
    with pytest.raises(ApprovalRefused, match="afsluttet"):
        B.claim(aid, tool_name="bash", arguments=ARGS)


def test_en_UBESLUTTET_kan_ikke_overtages(aid):
    _bed(aid)
    with pytest.raises(ApprovalRefused, match="ingen har besluttet"):
        B.claim(aid, tool_name="bash", arguments=ARGS)


def test_en_ukendt_godkendelse_afvises(isolated_runtime):
    with pytest.raises(ApprovalRefused, match="ukendt"):
        B.claim("findes-ikke", tool_name="bash", arguments=ARGS)


def test_der_kan_ikke_klikkes_TO_gange(aid):
    _bed(aid)
    assert B.decide(aid, approved=True) is True
    assert B.decide(aid, approved=False) is False
    assert B.state(aid)["state"] == B.APPROVED


# ── K6: aborted_before_dispatch ≠ outcome_unknown ────────────────────────

def test_doede_FOER_afsendelse_betyder_handlingen_skete_ALDRIG(aid):
    _bed(aid); B.decide(aid, approved=True)
    assert B.abandon(aid) == B.ABORTED_BEFORE_DISPATCH


def test_doede_UNDER_afsendelse_betyder_vi_ved_det_IKKE(aid):
    """K7 forbyder et automatisk genforsøg i netop den tilstand."""
    _bed(aid); B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS)
    assert B.abandon(aid) == B.OUTCOME_UNKNOWN


def test_de_to_er_FORSKELLIGE_tilstande(aid):
    assert B.ABORTED_BEFORE_DISPATCH != B.OUTCOME_UNKNOWN


def test_en_allerede_afsluttet_roeres_ikke(aid):
    _bed(aid); B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS); B.settle(aid, ok=True)
    assert B.abandon(aid) == B.COMPLETED


# ── udløb ────────────────────────────────────────────────────────────────

def test_en_udloebet_godkendelse_kan_ikke_overtages(aid):
    _bed(aid, ttl_s=1)
    B.decide(aid, approved=True)
    import time; time.sleep(1.2)
    with pytest.raises(ApprovalRefused):
        B.claim(aid, tool_name="bash", arguments=ARGS)


def test_udloeb_roerer_ALDRIG_en_igangvaerende_afsendelse(aid):
    """En afsendelse der er i gang, udløber ikke — dens udfald er stadig ukendt."""
    _bed(aid, ttl_s=1); B.decide(aid, approved=True)
    B.claim(aid, tool_name="bash", arguments=ARGS)
    import time; time.sleep(1.2)
    B.expire_stale()
    assert B.state(aid)["state"] == B.DISPATCHING


def test_udloeb_markerer_ubesluttede(aid):
    _bed(aid, ttl_s=1)
    import time; time.sleep(1.2)
    assert B.expire_stale() >= 1
    assert B.state(aid)["state"] == B.EXPIRED


# ── settle ───────────────────────────────────────────────────────────────

def test_settle_virker_kun_fra_dispatching(aid):
    _bed(aid); B.decide(aid, approved=True)
    assert B.settle(aid, ok=True) is False        # ikke overtaget endnu
    B.claim(aid, tool_name="bash", arguments=ARGS)
    assert B.settle(aid, ok=True) is True
    assert B.settle(aid, ok=True) is False        # kun én gang

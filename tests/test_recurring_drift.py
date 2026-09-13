"""En forsinket affyring maa ikke flytte planen permanent.

MAALT 13/9-2026: Bjoerns morgenbrief (`rec-2a7fcce8e0`, interval 1440 min) var
planlagt 05:40, blev foerst plukket 07:40:54 — og stod bagefter til **07:40
naeste dag**. Det samme for Mikkels morgenvejr (`rec-d2dcc1007f`).

Aarsagen var én linje:

    next_fire = (now + timedelta(minutes=interval_minutes)).isoformat()

`now` er det tidspunkt opgaven FAKTISK fyrede. Driften kan derfor kun gaa én
vej — senere — og et dagligt morgenbrev vandrer mod middag, én travl morgen ad
gangen.
"""
from datetime import UTC, datetime, timedelta

from core.services.recurring_tasks import _naeste_tid

DAGLIGT = 1440
PLANLAGT = "2026-09-13T03:40:00+00:00"          # 05:40 dansk


def _nu(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def test_to_timers_forsinkelse_flytter_IKKE_morgenbrevet():
    """Selve tilfaeldet fra produktionen."""
    næste = _naeste_tid(PLANLAGT, DAGLIGT, _nu("2026-09-13T05:40:54+00:00"))
    assert næste.isoformat() == "2026-09-14T03:40:00+00:00"


def test_tidspunktet_paa_dagen_holder_over_mange_forsinkede_dage():
    """Driften er kumulativ: det er DEN egenskab der goer den farlig."""
    planlagt = PLANLAGT
    for dag in range(30):
        # Hver dag plukkes den halvanden time for sent.
        nu = datetime.fromisoformat(planlagt) + timedelta(minutes=90)
        planlagt = _naeste_tid(planlagt, DAGLIGT, nu).isoformat()
    assert planlagt.endswith("T03:40:00+00:00"), f"drev til {planlagt}"


def test_lang_nedetid_giver_ÉT_spring_ikke_en_byge():
    """Tre doegn nede = tre forfaldne tidspunkter. Saettes naeste tid til det
    foerste af dem, skal alle tre indhentes."""
    næste = _naeste_tid(PLANLAGT, DAGLIGT, _nu("2026-09-16T09:00:00+00:00"))
    assert næste.isoformat() == "2026-09-17T03:40:00+00:00"
    assert næste > _nu("2026-09-16T09:00:00+00:00")


def test_affyring_foer_tid_roerer_ikke_planen():
    """Gaar uret baglaens, eller plukkes den et sekund for tidligt, maa planen
    ikke skride af den grund."""
    næste = _naeste_tid(PLANLAGT, DAGLIGT, _nu("2026-09-13T03:39:00+00:00"))
    assert næste.isoformat() == "2026-09-14T03:40:00+00:00"


def test_affyring_LANGT_foer_tid_traekker_ikke_planen_BAGUD():
    """Et minut for tidligt giver samme svar med og uden vagten — derfor saa
    mutations-proeven den ikke. Et DOEGN for tidligt goer ikke:

        med vagt:  14/9 03:40      uden vagt:  13/9 03:40   (et doegn bagud)
        to doegn:  14/9 03:40      uden vagt:  12/9 03:40   (i FORTIDEN)

    En naeste-tid i fortiden fyrer med det samme, traekker planen endnu laengere
    bagud, og saa loeber den.
    """
    for dage_for_tidligt in (1, 2, 3):
        nu = _nu(PLANLAGT) - timedelta(days=dage_for_tidligt)
        næste = _naeste_tid(PLANLAGT, DAGLIGT, nu)
        assert næste.isoformat() == "2026-09-14T03:40:00+00:00", \
            f"{dage_for_tidligt} doegn for tidligt flyttede planen til {næste}"
        assert næste > nu, "naeste tid landede i fortiden — den ville loebe"


def test_ukendt_planlagt_tid_falder_tilbage_paa_det_gamle():
    """Self-safe: en raekke uden brugbar tid maa ikke kunne stoppe planlaeggeren."""
    nu = _nu("2026-09-13T05:00:00+00:00")
    assert _naeste_tid("", DAGLIGT, nu) == nu + timedelta(minutes=DAGLIGT)
    assert _naeste_tid("noget-vaas", 60, nu) == nu + timedelta(minutes=60)


def test_naiv_tid_uden_zone_behandles_som_UTC():
    """Aeldre raekker er gemt uden zone. Uden dette kaster sammenligningen."""
    næste = _naeste_tid("2026-09-13T03:40:00", DAGLIGT, _nu("2026-09-13T05:40:00+00:00"))
    assert næste.isoformat() == "2026-09-14T03:40:00+00:00"


def test_kalderen_sender_den_planlagte_tid_med():
    """Uden den er hele regnestykket blindt — og faldbacken bliver den gamle
    fejl igen, tavst."""
    import inspect

    import core.services.recurring_tasks as rt
    kilde = inspect.getsource(rt)
    assert "_advance(task_id, interval_minutes, now,\n" in kilde
    assert "next_fire_at" in kilde.split("_advance(task_id, interval_minutes, now,")[1][:120]

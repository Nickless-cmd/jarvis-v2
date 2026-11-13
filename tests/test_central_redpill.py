"""Red Pill — dagens ubehagelige sandhed, og striben der tæller DAGE.

Målt 13/11-2026, to fejl i samme funktion:

1. **Striben talte KALD, ikke dage.** Nøglen hed «consecutive_days_deferred»,
   men hvert kald lagde 1 til. Den stod på 43 — ikke 43 dage, men 43 kald.
2. **Surfacen MUTEREDE.** `build_redpill_surface()` skrev til runtime-state ved
   hvert kald. Da Matrix-ensemblet nu læser surfacen ved HVER prompt-assembly,
   ville hvert prompt puste til præcis den tæller karakteren selv læser. Det er
   samme fejlform som et panel der skaber det det påstår at observere.
"""
from datetime import UTC, datetime, timedelta
from unittest import mock

from core.services import central_redpill as rp

_SANDHED = [{"key": "bloat:db.py", "kind": "bloat", "truth": "db.py er stor", "score": 33}]


def _kør(kv: dict, *, advance: bool = True, dag: str | None = None) -> dict:
    """Kald todays_truth med en isoleret KV-store og en fastsat dato."""
    with mock.patch("core.services.central_redpill._candidates", return_value=_SANDHED), \
            mock.patch("core.services.central_redpill._kv_get", side_effect=lambda k, d: kv.get(k, d)), \
            mock.patch("core.services.central_redpill._kv_set", side_effect=lambda k, v: kv.__setitem__(k, v)), \
            mock.patch("core.services.central_redpill._observe"):
        if dag is None:
            return rp.todays_truth(advance=advance)
        with mock.patch("core.services.central_redpill.datetime") as dt:
            dt.now.return_value = datetime.fromisoformat(dag + "T12:00:00+00:00")
            return rp.todays_truth(advance=advance)


def test_striben_taeller_hoejst_en_gang_pr_dag():
    kv: dict = {}
    i_dag = datetime.now(UTC).date().isoformat()
    i_morgen = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()

    t1 = _kør(kv, advance=True, dag=i_dag)
    t2 = _kør(kv, advance=True, dag=i_dag)      # samme dag → ingen vækst
    t3 = _kør(kv, advance=True, dag=i_morgen)   # ny dag, samme undgåede sandhed

    assert t1["blue_streak"] == 1
    assert t2["blue_streak"] == 1, "to kald samme dag må ikke give to dage"
    assert t3["blue_streak"] == 2, "en ny dag med samme undgåede sandhed giver +1"


def test_en_laesning_taeller_ikke_og_skriver_ikke():
    """Surfacen læses ved hvert prompt-build — den må ikke røre striben."""
    kv: dict = {}
    _kør(kv, advance=True)
    foer = dict(kv)
    with mock.patch("core.services.central_redpill._candidates", return_value=_SANDHED), \
            mock.patch("core.services.central_redpill._kv_get",
                       side_effect=lambda k, d: kv.get(k, d)), \
            mock.patch("core.services.central_redpill._kv_set") as skriv:
        s = rp.build_redpill_surface()
    assert skriv.call_count == 0, "en læsning må ikke skrive"
    assert kv == foer, "en læsning må ikke ændre striben"
    assert s["blue_streak"] == 1


def test_ingen_sandhed_er_aerlig_og_giver_nul():
    with mock.patch("core.services.central_redpill._candidates", return_value=[]), \
            mock.patch("core.services.central_redpill._kv_get", return_value={}), \
            mock.patch("core.services.central_redpill._kv_set"), \
            mock.patch("core.services.central_redpill._observe"):
        r = rp.todays_truth(advance=True)
    assert r["truth"] is None and r["blue_streak"] == 0
    assert "blind" in r["felt"]


def test_ny_sandhed_nulstiller_striben():
    """Skifter den undgåede sandhed, er det en NY undgåelse — ikke en fortsættelse."""
    kv: dict = {}
    _kør(kv, advance=True)
    anden = [{"key": "incident:17079", "kind": "incident", "truth": "gammel incident", "score": 9}]
    with mock.patch("core.services.central_redpill._candidates", return_value=anden), \
            mock.patch("core.services.central_redpill._kv_get", side_effect=lambda k, d: kv.get(k, d)), \
            mock.patch("core.services.central_redpill._kv_set", side_effect=lambda k, v: kv.__setitem__(k, v)), \
            mock.patch("core.services.central_redpill._observe"):
        r = rp.todays_truth(advance=True)
    assert r["blue_streak"] == 1

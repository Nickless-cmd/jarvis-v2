"""Godkendelses-kortets frist — den må ikke kunne hænge i UI'et.

## Bug'en (målt 25/10-2026)

`StreamContext` holder op med at spørge serveren så snart den HAR et kort
(``if (pendingApproval) return``). Det er med vilje — ellers ville den banke på
hvert andet sekund for et kort den godt kender. Prisen var at et udløb der skete
på SERVEREN aldrig blev opdaget i klienten: kortet blev stående, og både
«Godkend» og «Afvis» ville fejle, fordi posten for længst var for gammel.

Bjørns opgave siger det direkte: *«approval cards må ikk kunne dø et run … eller
approval card bliver afvist eller godkendt.»* Et kort der hverken kan afvises
eller godkendes er præcis det der ikke må findes.

Fixet er at sende fristen med, så klienten kan vise en nedtælling og rydde sig
selv. Testen her værner den ene ting der ellers smuldrer stille: at fristen
klienten får, er **den samme grænse serveren håndhæver**. Regner de to hver sit,
viser kortet en nedtælling der ikke passer med hvornår svaret faktisk afvises.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services.approval_runtime import udloeb_tid
from core.services.visible_runs_approvals import _er_udloebet


def _kort(**over) -> dict:
    grund = {"created_at": datetime.now(UTC).isoformat()}
    grund.update(over)
    return grund


class TestFristen:
    def test_frist_er_created_at_plus_ttl(self):
        from core.runtime.db_approval_bridge import DEFAULT_TTL_S

        start = datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)
        svar = udloeb_tid({"created_at": start.isoformat()})
        assert svar == (start + timedelta(seconds=DEFAULT_TTL_S)).isoformat()

    def test_frist_og_haandhaevet_graense_er_den_samme(self):
        """Den ægte vagt: klientens nedtælling og serverens afvisning.

        Et kort der lige AKkurat er inden for fristen skal være gyldigt, og et
        der er lige over skal være dødt. Er de to uenige, viser kortet «0s
        tilbage» mens serveren stadig tager imod svaret — eller omvendt: det
        viser tid tilbage på et kort der allerede er dødt.

        Målt mod den RIGTIGE funktion (`_er_udloebet`), ikke mod en kopi af
        dens formel: en test der gentager formlen kan ikke fælde at formlen
        ændrer sig.
        """
        from core.runtime.db_approval_bridge import DEFAULT_TTL_S

        nu = datetime.now(UTC)

        # Inden for fristen: serveren tager imod det.
        frisk = {"created_at": (nu - timedelta(seconds=DEFAULT_TTL_S - 30)).isoformat()}
        assert _er_udloebet(frisk) == ""

        # Over fristen: serveren afviser det — og det er PRÆCIS det tidspunkt
        # `udloeb_tid` peger på.
        gammel_start = nu - timedelta(seconds=DEFAULT_TTL_S + 30)
        gammel = {"created_at": gammel_start.isoformat()}
        assert _er_udloebet(gammel) != ""
        assert datetime.fromisoformat(udloeb_tid(gammel)) < nu

    def test_manglende_created_at_giver_ingen_frist(self):
        # Et kort uden tidsstempel skal stadig kunne VISES — men uden
        # nedtælling. En opdigtet frist ville være værre end ingen.
        assert udloeb_tid({}) == ""
        assert udloeb_tid({"created_at": ""}) == ""
        assert udloeb_tid({"created_at": None}) == ""

    def test_ugyldig_created_at_giver_ingen_frist(self):
        assert udloeb_tid({"created_at": "i morgen"}) == ""
        assert udloeb_tid({"created_at": "2026-13-45"}) == ""

    def test_naiv_tid_laeses_som_utc(self):
        """Et tidsstempel uden zone er husets egen form nogle steder.

        Læses det som lokal tid, forskubber fristen sig med op til to timer —
        og kortet ville dø for tidligt eller for sent afhængigt af maskinens
        zone. Vi vælger UTC, som resten af huset gør.
        """
        svar = udloeb_tid({"created_at": "2026-10-25T12:00:00"})
        assert svar.startswith("2026-10-25T13:00:00")

    def test_fristen_er_i_fremtiden_for_et_friskt_kort(self):
        frist = datetime.fromisoformat(udloeb_tid(_kort()))
        assert frist > datetime.now(UTC)

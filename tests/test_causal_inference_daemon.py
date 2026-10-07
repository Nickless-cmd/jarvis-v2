"""De to skrivere til `causal_edges` skal skrive samme tidsformat.

29/9-2026: `eventbus.bus` skrev de eksplicitte kanter som
`2026-07-31T20:03:30.596145+00:00`, mens `causal_inference_daemon` skrev de
udledte som `...Z`. Samme kolonne, to sandheder — 107.121 af 140.178 raekker
stod med `Z`.

Det var ikke kosmetik. Skema-vagten klassificerer en tabel ud fra de tre
aeldste og tre nyeste raekker, saa hvilken skriver der tilfaeldigvis skrev
sidst afgjorde dens svar: den blokerede Jarvis' commit kl. 11:21 og
passerede paa den samme uaendrede base kl. 17:55.
"""
import re

from core.services import causal_inference_daemon as d
from core.eventbus.events import Event
from scripts.verify_sqlite_schema import timestamp_format


def test_daemonens_stempel_har_SAMME_form_som_bussens():
    """Den maaling der afgoer sagen: begge skal klassificeres ens af vagten."""
    fra_daemon = d._now_iso()
    fra_bussen = Event(kind="x", payload={}).ts.isoformat()
    assert timestamp_format(fra_daemon) == timestamp_format(fra_bussen)
    assert timestamp_format(fra_daemon) == "iso_utc_offset", fra_daemon


def test_stemplet_er_ikke_laengere_Z_formet():
    """Selve regressionen, sagt uden om vagtens klassifikation."""
    stempel = d._now_iso()
    assert not stempel.endswith("Z"), stempel
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+00:00", stempel), stempel


def test_de_107000_gamle_Z_raekker_kan_stadig_laeses():
    """`.replace` blev FJERNET, ikke erstattet — de gamle raekker staar der
    stadig, og en laeser der ikke kan tage dem ville vaere en vaerre fejl end
    den vi retter."""
    gammel = d._parse_iso("2026-09-29T17:47:16.929006Z")
    ny = d._parse_iso("2026-07-31T20:03:30.596145+00:00")
    assert gammel is not None and ny is not None
    assert gammel.tzinfo is not None and ny.tzinfo is not None
    assert gammel > ny

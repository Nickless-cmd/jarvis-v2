"""MÅLING 16/10-2026: kæmper desk og mobil om det samme forslag?

Bjørn spurgte om to flader (desk + mobil) kan komme i konflikt om ét
forslag. Spørgsmålet er ikke teoretisk: begge flader henter fra samme
session, og begge kan melde `vist` og et terminalt valg tilbage.

Målt: de kæmper ikke — de DELER én række. Filen pinner de fire steder hvor
de mødes, så en senere ændring ikke kan indføre en konflikt i det stille.
"""
from __future__ import annotations

import pytest

from core.runtime import db_composer_choice as dc
from core.runtime import db_composer_jarvis as dj
from core.services import composer_suggest as cs

_ASSISTENT_SVAR = (
    "Jeg har målt det og fundet at rækken deles. Næste skridt er at bekræfte "
    "det med et rigtigt samtaleforløb, så tallet ikke hviler på et gæt."
)


@pytest.fixture()
def flade(isolated_runtime):
    """En rigtig session med et svar — og ét forslag begge flader kan hente.

    Forslaget skrives EFTER assistent-svaret, så `_svar_efter` er 0 og det
    ikke er forældet. Uden svaret ville hentningen falde tilbage til tomt
    (ingen samtale at bygge på), og målingen ville måle ingenting.
    """
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sid = str(create_chat_session(title="to-flader")["id"])
    append_chat_message(session_id=sid, role="assistant", content=_ASSISTENT_SVAR)
    fid = dj.gem_forslag(session_id=sid, forslag="Mål om desk og mobil kæmper")
    assert fid
    return sid, fid


def _hent(sid: str):
    """Det én flade får ud af at kalde /composer/suggest."""
    return cs.foreslaa_naeste_detaljer(sid)


def test_begge_flader_faar_SAMME_id(flade):
    """Hentning forbruger ikke — begge flader ser samme række."""
    sid, fid = flade
    a = _hent(sid)
    b = _hent(sid)
    assert a["forslag_id"] == fid
    assert b["forslag_id"] == fid, "flade B må ikke få et andet (eller intet) forslag"


def test_hentning_sletter_INTET(flade):
    """Forslaget skal overleve at blive hentet — også to gange."""
    sid, _ = flade
    _hent(sid)
    _hent(sid)
    assert dj.kig_forslag(session_id=sid) is not None


def test_vist_fra_begge_flader_giver_EN_raekke(flade):
    """noter_vist er idempotent: to flader der melder vist tælles én gang."""
    sid, fid = flade
    assert dc.noter_vist(forslag_id=fid, session_id=sid, forslag="x") is True
    assert dc.noter_vist(forslag_id=fid, session_id=sid, forslag="x") is True
    assert len(dc.seneste_valg(session_id=sid)) == 1


def test_foerste_terminale_valg_vinder(flade):
    """Desk trykker Tab → accepteret. Mobilen trykker afvis → må ikke overskrive."""
    sid, fid = flade
    dc.noter_vist(forslag_id=fid, session_id=sid, forslag="x")
    assert dc.noter_valg(forslag_id=fid, valg="accepteret") is True
    dc.noter_valg(forslag_id=fid, valg="afvist")
    assert dc.seneste_valg(session_id=sid)[0]["valg"] == "accepteret"


def test_noter_valg_melder_True_paa_et_no_op_MAALT(flade):
    """MÅLT 16/10-2026 — en unøjagtighed uden konsekvens i dag.

    Melder den anden flade tilbage på en allerede afsluttet række, rammer
    `UPDATE ... WHERE valg = 'vist'` nul rækker. Funktionen svarer alligevel
    True. Testen her CELEBRERER det ikke — den fastholder hvad der er målt,
    og fejler hvis svaret ændrer sig, så nogen må tage stilling.

    Harmløst fordi `meldValg` i desk sender med `void fetch(...)` og en tom
    `catch`: svaret læses ikke af nogen flade. Rettes den dag et svar skal
    BRUGES til noget.
    """
    sid, fid = flade
    dc.noter_vist(forslag_id=fid, session_id=sid, forslag="x")
    dc.noter_valg(forslag_id=fid, valg="accepteret")

    svar = dc.noter_valg(forslag_id=fid, valg="afvist")

    assert dc.seneste_valg(session_id=sid)[0]["valg"] == "accepteret", \
        "første terminale valg skal stå"
    assert svar is True, (
        "målt adfærd ændret: noter_valg svarede ikke længere True på et no-op. "
        "Er det en bevidst rettelse, opdatér denne test og `meldValg`."
    )


def test_ukendt_forslag_id_melder_ogsaa_True_MAALT(flade):
    """Samme familie: et id der slet ikke findes giver også True."""
    assert dc.noter_valg(forslag_id="cj-findes-ikke", valg="accepteret") is True


def test_er_vist_er_den_sikre_side_ved_ukendt_id(flade):
    """Skellet bag ryd-ved-ny-tur: et ukendt id behandles som USET."""
    assert dc.er_vist(forslag_id="cj-findes-ikke") is False
    assert dc.er_vist(forslag_id="") is False

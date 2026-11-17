"""Forslag i komponisten — et bud på den NÆSTE besked.

## Hvem der foreslår (ændret 28/9-2026)

Forslaget kommer udelukkende fra Jarvis selv, gennem værktøjet
`suggest_next_task`. Den lokale model (qwen3:4b) skrev tidligere et bud når
han ikke selv lagde et ned; den blev droppet efter Bjørns måling og dom: «drop
den anden models forslag og kun bruge dine... den anden model viser lorte
forslag». Af 428 viste forslag kom 411 fra modellen, og de blev valgt 2,9 % af
gangene mod 23,5 % for hans egne.

Den anden vej — fortsættelsen af en halvskreven sætning — er også fjernet
(28/9-2026): ingen flade brugte den. Modulet kalder derfor ikke længere nogen
model, og der findes ikke en eneste test her der patcher et model-kald: der er
intet kald at patche.
"""
from __future__ import annotations

import pytest

from core.runtime import db_composer_choice as dc
from core.runtime import db_composer_jarvis as dj
from core.services import composer_suggest as cs


# ──────────────────────────────────────────────── der kaldes INGEN model

def test_modulet_kalder_INGEN_model():
    """Kilde-vagt. Både den lokale models forslag og fortsættelses-formen er
    væk; tilbage står Jarvis' eget forslag. Der må ikke ligge et model-kald
    eller en model-adresse tilbage — heller ikke en betalt lane."""
    import inspect
    kilde = inspect.getsource(cs)
    assert "urllib" not in kilde
    assert "11434" not in kilde        # ingen ollama-adresse
    assert "deepseek" not in kilde     # ingen betalt lane
    assert "openai" not in kilde


# ──────────────────────────────────── forslag til den NAESTE besked (17/9)
#
# Bjoern: «det kommer dumpende mens jeg skriver, det er virkelig traels» — og
# «auto suggest skal jo vaere ud fra konteksten af DIN besked». Forslaget er
# altsaa ikke resten af hans saetning, men et bud paa hvad han kunne sige nu,
# vist dér hvor pladsholderen staar. Kilden er samtalen, ikke tastetrykkene.


def _samtale(*par):
    return [{"role": r, "content": c} for r, c in par]


def test_uden_SESSION_spoerges_der_ikke():
    assert cs.foreslaa_naeste("") == ""
    assert cs.foreslaa_naeste("   ") == ""


def test_en_TOM_samtale_giver_intet_forslag(monkeypatch):
    """Foerste besked i en ny samtale er hans egen. Der er intet at foreslaa
    ud fra, og GreetingHero staar der i forvejen."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [])
    assert cs.foreslaa_naeste("s1") == ""


def test_mens_HANS_besked_venter_paa_svar_foreslaas_intet(monkeypatch):
    """Sidste besked er hans egen → turen er i gang. At foreslaa den naeste
    besked dér er at tale i munden paa et svar der er paa vej."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", "Det er rettet."), ("user", "og deploy det"),
    ))
    assert cs.foreslaa_naeste("s1") == ""


def test_en_DB_fejl_giver_tomt_og_kaster_ikke(monkeypatch):
    monkeypatch.setattr(cs, "_samtale",
                        lambda sid: (_ for _ in ()).throw(RuntimeError("laast")))
    assert cs.foreslaa_naeste("s1") == ""


# ───────────────────────────── en STUMP giver intet forslag (17/9-2026)
#
# Maalt paa ti aegte samtaler: assistentens sidste besked kan vaere en stump —
# «4.», «OK», «Generation cancelled.» — og der er intet naeste skridt at bygge
# paa. Det gaelder ogsaa et forslag fra Jarvis selv: uden noget at bygge paa
# ville det vaere et bud uden grundlag.

@pytest.mark.parametrize("stump", ["4.", "OK", "Generation cancelled.", "Ja."])
def test_en_STUMP_til_sidst_giver_intet_forslag(monkeypatch, stump):
    """Der er intet naeste skridt at bygge paa — heller ikke for Jarvis selv."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", stump)))
    assert cs.foreslaa_naeste("s1") == ""


# ─────────────────────────────────────────────────── fladen skal kunne NAAS

def test_ruten_er_MONTERET_i_appen():
    """En flade ingen kan naa er husets hyppigste fejl. `_runtime_work_surface`
    var korrekt, komplet og usynlig i maanedsvis af praecis den grund."""
    from apps.api.jarvis_api.app import app
    stier = {getattr(r, "path", "") for r in app.routes}
    assert "/composer/suggest" in stier


def test_ruten_svarer_TOMT_frem_for_at_fejle(monkeypatch):
    """Et forslag er en bekvemmelighed. En klient der skulle haandtere
    fejlkoder for at kunne skrive videre, ville holde op med at virke af en
    grund der ikke rager den."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa_naeste_detaljer",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert r.suggest(r.Udkast(session_id="s1")) == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_ruten_baerer_forslaget_igennem(monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa_naeste_detaljer", lambda s: {
        "forslag": "naeste til " + s, "forslag_id": "cs-x", "kilde_besked_id": "m1"})
    assert r.suggest(r.Udkast(session_id="s1"))["forslag"] == "naeste til s1"


def test_ruten_taaler_en_tom_krop():
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    assert r.suggest(r.Udkast()) == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_et_GAMMELT_kald_med_udkast_ignoreres(monkeypatch):
    """Feltet `udkast` stod i kontrakten indtil 28/9-2026. En klient der ikke
    er opdateret sender det stadig — det skal ignoreres, ikke fejle, og svaret
    skal vaere praecis det samme som uden."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa_naeste_detaljer", lambda s: {
        "forslag": "naeste til " + s, "forslag_id": "cs-x", "kilde_besked_id": "m1"})
    svar = r.suggest(r.Udkast(**{"udkast": "kan du lige", "session_id": "s1"}))
    assert svar["forslag"] == "naeste til s1"


# ─────────────────────────────────────────────── valget (fase 2, 20/9-2026)
#
# Bjoern: «vi skal gemme brugerens valg, dvs. om de brugte den suggested (tab)
# i composer eller skrev der egen besked saa naeste forslag bliver mere
# mig/maalrettet». Forslaget skal derfor baere et id ud til klienten, saa
# klienten kan melde tilbage hvad der skete med netop DET forslag.


def test_INTET_forslag_giver_tomme_id(monkeypatch):
    """Der er ikke noget at melde tilbage om — og en klient der fik et id uden
    et forslag, ville oprette en raekke for noget der aldrig blev vist."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [])
    d = cs.foreslaa_naeste_detaljer("s1")
    assert d == {"forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_ruten_registrerer_VIST_og_derefter_valget(isolated_runtime, monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute
    from core.runtime import db_composer_choice as dc

    rute.choice(rute.Valg(forslag_id="cs-9", session_id="s1",
                          forslag="Ret det og koer testene igen",
                          kilde_besked_id="message-3", valg="vist"))
    assert dc.seneste_valg()[0]["valg"] == "vist"
    rute.choice(rute.Valg(forslag_id="cs-9", valg="accepteret"))
    assert dc.seneste_valg()[0]["valg"] == "accepteret"


def test_ruten_fejler_ALDRIG(isolated_runtime, monkeypatch):
    """Komponisten maa ikke kunne gaa i stykker af en telemetri-skrivning."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute
    from core.runtime import db_composer_choice as dc

    monkeypatch.setattr(dc, "noter_vist",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("basen er nede")))
    assert rute.choice(rute.Valg(forslag_id="cs-1", session_id="s1",
                                 forslag="x", valg="vist")) == {"ok": True}


# ──────────────────────────────── Jarvis' EGET forslag (24/9-2026)
#
# Bjoern: «i chatview er det dig selv der saetter ord paa runderne... det
# burde endelig osse vaere dig der kommer med forslag i composer?» Raekke-
# foelgen er hele pointen:
#
#   Jarvis' eget forslag (hvis det findes)  ->  ellers staar feltet TOMT
#
# Lageret selv (gem/tag/kig/forbrug) er testet i test_db_composer_jarvis.py,
# og vaerktoejet han kalder i test_composer_suggest_tools.py. Her proves KUN
# hvornaar hans forslag vinder — og hvornaar feltet staar tomt.


_ASSISTENT_SVAR = "Det er rettet og verificeret — testene er groenne igen."


def _med_svar(monkeypatch, session: str = "s1"):
    """En samtale der slutter med et rigtigt svar fra Jarvis."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [{
        "role": "assistant", "message_id": "message-42", "content": _ASSISTENT_SVAR}])


def test_JARVIS_forslag_vinder(isolated_runtime, monkeypatch):
    """Kernetesten. Ligger der et forslag fra Jarvis, er det HANS ord der
    moeder brugeren — og id'et baerer hans praefiks, saa telemetrien kan se
    hvor det kom fra."""
    _med_svar(monkeypatch)
    dj.gem_forslag(session_id="s1", forslag="Vis mig de to der står i karantaene")

    d = cs.foreslaa_naeste_detaljer("s1")
    assert d["forslag"] == "Vis mig de to der står i karantaene"
    # Id'et baerer Jarvis' praefiks, saa telemetrien kan se hvor det kom fra.
    assert d["forslag_id"].startswith("cj-")
    # Kilde-beskeden er den FAKTISKE sidste besked — ikke noget Jarvis gættede.
    assert d["kilde_besked_id"] == "message-42"


def test_uden_hans_forslag_staar_FELTET_TOMT(isolated_runtime, monkeypatch):
    """Den lokale model blev droppet 28/9-2026: «drop den anden models forslag
    og kun bruge dine». Uden et eget forslag er der intet bud — og et tomt felt
    er aerligere end et daarligt forslag."""
    _med_svar(monkeypatch)
    assert cs.foreslaa_naeste_detaljer("s1") == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_forslaget_OVERLEVER_en_ny_hentning(isolated_runtime, monkeypatch):
    """Bjoern 6/10-2026: forslaget skal overleve en app-genstart.

    Foer slettede hentningen raekken, saa klienten der hentede holdt den eneste
    kopi — en genstart tabte baade hukommelsen og raekken, og forslaget var vaek
    uden at nogen havde set det. En genstart er praecis en ny hentning.
    """
    _med_svar(monkeypatch)
    dj.gem_forslag(session_id="s1", forslag="fra Jarvis")

    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == "fra Jarvis"
    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == "fra Jarvis"
    assert dj.kig_forslag(session_id="s1") is not None


def test_forslaget_overlever_at_samtalen_koerer_videre(isolated_runtime, monkeypatch):
    """To eller flere svar efter forslaget rydder det IKKE længere (17/11-2026).

    Reglen var «2+ assistent-svar → forældet, ryd». Målt i drift: et forslag
    vist 11:30:31 og taget med Tab 11:31:00 var ryddet ved turstart 11:31 —
    58 minutter før Bjørn kiggede, og han kaldte det en genstart der spiste
    det. Reglen målte «samtalen er kørt videre» og ramte dermed også et
    forslag han lige havde taget. Nu afgør BRUG og ALDER, ikke ture.
    """
    _med_svar(monkeypatch)
    fid = dj.gem_forslag(session_id="s1", forslag="fra Jarvis")
    dc.noter_vist(forslag_id=fid, session_id="s1", forslag="fra Jarvis")
    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == "fra Jarvis"
    assert dj.kig_forslag(session_id="s1") is not None


def test_et_GAMMELT_forslag_ryddes_paa_alder(isolated_runtime, monkeypatch):
    """Alders-loftet er det eneste der rydder et ubrugt forslag.

    Uden det ville et bud kunne hænge for evigt i en session ingen rører.
    """
    _med_svar(monkeypatch)
    monkeypatch.setattr(cs, "_foraeldet", lambda skrevet: True)
    dj.gem_forslag(session_id="s1", forslag="fra Jarvis")
    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == ""
    assert dj.kig_forslag(session_id="s1") is None, "det gamle forslag skal ryddes"


def test_forslaget_hentes_igen_EFTER_han_har_taget_det(isolated_runtime, monkeypatch):
    """`accepteret` er Tab — teksten lægges i feltet, den sendes ikke.

    Målt 17/11-2026: netop det skete. Forslaget blev taget 11:31:00, han
    skrev noget andet, og forslaget var væk. Et forslag han tog men ikke
    sendte, skal stadig kunne hentes.
    """
    _med_svar(monkeypatch)
    fid = dj.gem_forslag(session_id="s1", forslag="fra Jarvis")
    dc.noter_vist(forslag_id=fid, session_id="s1", forslag="fra Jarvis")
    dc.noter_valg(forslag_id=fid, valg="accepteret")

    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == "fra Jarvis"
    assert dj.kig_forslag(session_id="s1") is not None


def test_hans_forslag_bruges_ikke_naar_turen_IKKE_er_faerdig(isolated_runtime, monkeypatch):
    """Står der en ubesvaret besked fra Bjørn, er turen i gang. Så er der
    ingen «naeste besked» at foreslå — og forslaget skal blive liggende."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", _ASSISTENT_SVAR), ("user", "og hvad med den anden?")))
    dj.gem_forslag(session_id="s1", forslag="fra Jarvis")

    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == ""
    assert dj.kig_forslag(session_id="s1") is not None, "forslaget skal vente, ikke forbruges"


def test_et_gemt_forslag_vises_OGSAA_naar_sidste_svar_er_en_STUMP(isolated_runtime, monkeypatch):
    """En stump til sidst stopper ikke et forslag Jarvis selv har lagt ned.

    Reglen om `MIN_SVAR_TEGN` gjaldt et forslag bygget PAA samtalen: «OK.» er
    intet at bygge videre på. Et gemt forslag blev skrevet mens Jarvis kendte
    turen og bærer sin egen kontekst — og efter en genstart er det sidste svar
    ofte kort netop fordi samtalen lige er genåbnet. Reglen stoppede derfor
    forslaget dér hvor det skulle vises.
    """
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", "OK.")))
    dj.gem_forslag(session_id="s1", forslag="fra Jarvis")
    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == "fra Jarvis"


# ─────────── tællingen maa ikke komme fra et vindue (maalt 7/10-2026) ───────────
#
# `_samtale` henter SEKS raekker, og de seks raekker blev brugt til at afgoere
# foraeldelsen. I en tool-tung session er de seks nyeste raekker `tool`-raekker,
# saa tællingen kunne kun se ÉT assistent-svar efter forslaget — og kaldte
# derfor et foraeldet bud for aktuelt.
#
# Maalt i drift samme aften: et forslag skrevet 18:23 blev returneret som
# «aktuelt» efter hver tur resten af aftenen, og raekken laa stadig i basen 3,5
# time senere. Bjørn: «dine suggested next task skal altid nulstilles i composer
# naar en ny tur starter, ellers haenger gamle ved over mange beskeder».
#
# Testen her bygger den praecise form op i en RIGTIG base. Den FEJLER paa den
# gamle tælling: vinduet ser [assistent, tool, tool, tool, tool, tool] og tæller
# ét svar, hvor der er to.


def test_tool_raekker_skjuler_ikke_forslaget(isolated_runtime):
    """Fem `tool`-raekker og to svar efter forslaget maa ikke gøre det usynligt.

    Testen bevogtede oprindeligt at forældelses-tællingen kom fra SQL og ikke
    fra et vindue paa seks rækker. Den regel er væk (17/11-2026) — men kravet
    er det samme: vinduets form maa ikke afgøre om forslaget kan hentes.
    """
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sid = str(create_chat_session(title="tool-tung")["id"])
    fid = dj.gem_forslag(session_id=sid, forslag="fra Jarvis")
    dc.noter_vist(forslag_id=fid, session_id=sid, forslag="fra Jarvis")
    append_chat_message(session_id=sid, role="assistant", content=_ASSISTENT_SVAR,
                        created_at="2026-10-07T18:24:00+00:00")
    for i in range(5):
        append_chat_message(session_id=sid, role="tool",
                            content=f"[tool_result:tool-result-abc{i}] svar {i}",
                            created_at=f"2026-10-07T18:25:0{i}+00:00")
    append_chat_message(session_id=sid, role="assistant", content=_ASSISTENT_SVAR,
                        created_at="2026-10-07T18:26:00+00:00")

    assert cs.foreslaa_naeste_detaljer(sid)["forslag"] == "fra Jarvis"
    assert dj.kig_forslag(session_id=sid) is not None


def test_en_ny_tur_rydder_IKKE_et_forslag_der_bare_blev_set(isolated_runtime):
    """En ny tur rydder ikke et forslag blot fordi det kom på skærmen (17/11-2026).

    Bjoern 7/10-2026 bad om at gamle forslag nulstilles ved en ny tur — og det
    blev implementeret som «blev det SET, ryddes det». Målt i drift 17/11:
    forslaget blev vist 11:30:31, taget med Tab 11:31:00 og ryddet ved turstart
    11:31, 58 minutter før han kiggede. Han kaldte det en genstart der spiste
    forslaget. Et forslag der er set er ikke forældet — det er kun set.
    """
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sid = str(create_chat_session(title="ny tur")["id"])
    fid = dj.gem_forslag(session_id=sid, forslag="fra Jarvis")
    assert dj.kig_forslag(session_id=sid) is not None
    dc.noter_vist(forslag_id=fid, session_id=sid, forslag="fra Jarvis")

    append_chat_message(session_id=sid, role="user", content="naeste opgave, tak")

    assert dj.kig_forslag(session_id=sid) is not None, (
        "et SET forslag maa ikke ryddes blot fordi en ny tur begynder — det "
        "skal kunne hentes igen efter en genstart"
    )


def test_en_ny_tur_rydder_forslaget_naar_hans_besked_BRUGER_det(isolated_runtime):
    """Brugte han forslaget, er det brugt op — så ryddes det ved turstart."""
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sid = str(create_chat_session(title="brugt")["id"])
    dj.gem_forslag(session_id=sid, forslag="Ret forslaget så det overlever en genstart")

    append_chat_message(
        session_id=sid, role="user",
        content="Ret forslaget så det overlever en genstart",
    )

    assert dj.kig_forslag(session_id=sid) is None, "et brugt forslag skal ryddes"


def test_ESCAPE_rydder_forslaget(isolated_runtime):
    """`afvist` er et nej. Så skal forslaget ikke tilbydes igen."""
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sid = str(create_chat_session(title="afvist")["id"])
    fid = dj.gem_forslag(session_id=sid, forslag="fra Jarvis")
    dc.noter_vist(forslag_id=fid, session_id=sid, forslag="fra Jarvis")
    dc.noter_valg(forslag_id=fid, valg="afvist")

    append_chat_message(session_id=sid, role="user", content="noget helt andet")

    assert dj.kig_forslag(session_id=sid) is None, "et afvist forslag skal ryddes"


def test_en_ny_tur_rydder_IKKE_et_forslag_der_aldrig_blev_set(isolated_runtime):
    """Et USET forslag er ikke foraeldet — det er ubesvaret (maalt 16/10-2026).

    Rydningen var ubetinget, og et forslag der aldrig naaede skaermen forsvandt
    med den: lagt 15:55, ryddet 16:15 — tyve minutter senere, uden at klienten
    nogensinde havde hentet det (nul raekker i `composer_choices` for
    sessionen). Bjørn spurgte selv efter hvad det havde vaeret.

    Uden en `vist`-raekke skal forslaget derfor OVERLEVE turen. Det hober sig
    ikke op: `gem_forslag` holder hoejst ét pr. session, og foraeldelses-reglen
    i `foreslaa_naeste_detaljer` spoerger nu OGSAA `er_vist` (rettet samme dag,
    se `test_TO_svar_efter_et_USET_forslag_rydder_det_IKKE`), saa et uset
    forslag ryddes hverken ved ny tur eller ved foraeldelse.
    """
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sid = str(create_chat_session(title="uset")["id"])
    dj.gem_forslag(session_id=sid, forslag="fra Jarvis")
    assert dc.optaelling(session_id=sid)["vist"] == 0, "ingen vist-raekke endnu"

    append_chat_message(session_id=sid, role="user", content="naeste opgave, tak")

    assert dj.kig_forslag(session_id=sid) is not None, (
        "et forslag der ALDRIG kom paa skaermen maa ikke ryddes af en ny tur"
    )

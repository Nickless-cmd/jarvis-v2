"""Et medlem skal kunne sætte sin EGEN totrinsbekræftelse — målt 31/10-2026.

## Fejlen der blev rettet

`/auth/totp/setup` var owner-only (`_owner_or_403`), og `TotpSetup` var pakket
i `{isOwner && …}` i desk. Kæden imellem dem gjorde 2FA til en død ende for
alle andre:

    ingen seed  ->  `kraev_totp` kan ikke verificere  ->  ingen enhed
                ->  enheds-reglen spærrer code mode

Så snart reglen blev tændt 30/10, fik et medlem beskeden «Slå totrinsbekræftelse
til først (Indstillinger → Konto), så kan du tilføje enheder» — om en knap der
ikke fandtes for dem. Målt: Mikkel (uid 238975101381378048) havde nul enheder
og fik 403 på `POST /chat/stream/v2`.

## Hvorfor denne fil findes ved siden af `test_auth_enheder_routes.py`

Den fils `ejer`-fixture monkeypatcher `users.get_totp_seed` til at returnere en
seed for ENHVER discord_id. Det er en mock på den brækkede søm: kæden kan
gennemføres i testen uden at nogen nogensinde har fået en seed ad den ægte vej.
Målt 31/10: alle fem brugere havde `seed_bytes=0` i produktion, mens kæden var
grøn i test. Her mockkes INTET — seeden kommer fra ruten.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

import core.identity.users as users
import core.identity.workspace_context as wc
from apps.api.jarvis_api.routes import auth_enheder as ae
from apps.api.jarvis_api.routes import totp as totp_rute
from core.identity import kode_adgang
from core.runtime import db_devices as dd
from core.services import totp_verifier as tv

MEDLEM = "238975101381378048"
EJER = "1246415163603816499"


@pytest.fixture
def to_brugere(isolated_runtime, monkeypatch):
    """Én ejer og ét medlem — som i den målte produktionstilstand."""
    users.add_user(discord_id=EJER, name="Bjørn", role="owner", workspace="bjorn")
    users.add_user(discord_id=MEDLEM, name="Mikkel", role="member", workspace="mikkel")
    tv._ATTEMPTS.clear()

    def som(uid=MEDLEM, rolle="member", enhed="", app_id=""):
        monkeypatch.setattr(wc, "current_user_id", lambda: uid)
        monkeypatch.setattr(wc, "current_role", lambda: rolle)
        monkeypatch.setattr(wc, "current_token_enhed", lambda: (enhed, app_id))

    som()
    return som


def test_medlem_faar_en_seed_af_ruten(to_brugere):
    """Kernen i fejlen: dette kastede 403 for alle andre end ejeren."""
    svar = totp_rute._do_setup()
    assert svar["secret"], "ingen seed — medlemmet er stadig lukket ude"
    assert svar["account"] == "Mikkel"
    # og den ligger på MEDLEMMETS id, ikke ejerens
    assert users.get_totp_seed(discord_id=MEDLEM) == svar["secret"]
    assert users.get_totp_seed(discord_id=EJER) == ""


def test_medlem_kAN_ikke_skrive_paa_en_andens_konto(to_brugere):
    """Ruten skriver altid på kalderen — den kan ikke adressere en anden."""
    svar = totp_rute._do_setup()
    assert users.get_totp_seed(discord_id=EJER) == ""
    assert users.get_totp_seed(discord_id=MEDLEM) == svar["secret"]


def test_ukendt_bruger_afvises_stadig(to_brugere):
    """Rollen er uden betydning, men identiteten er ikke: ukendt = ingen konto."""
    to_brugere(uid="findes-ikke", rolle="member")
    with pytest.raises(HTTPException) as e:
        totp_rute._do_setup()
    assert e.value.status_code == 403


def test_medlemmets_seed_aabner_IKKE_ejerens_override(to_brugere):
    """Den grænse der skulle bevares — og som gør ruten sikker at åbne.

    `!override` slår op på `get_owner().discord_id` (discord_gateway:1390,
    telegram_gateway:360, chat_stream_v2:196), aldrig på den kaldende. En
    members seed må derfor ikke kunne verificere ejerens bagdør.
    """
    svar = totp_rute._do_setup()
    medlems_seed = svar["secret"]
    ejer_seed = tv.generate_seed()
    users.set_totp_seed(discord_id=EJER, seed=ejer_seed)

    kode = tv.generate_code(medlems_seed)
    # koden er gyldig for medlemmets seed ...
    assert tv.verify(kode, seed=medlems_seed) is True
    # ... men ejerens override læser ejerens seed, og der matcher den ikke
    assert users.get_totp_seed(discord_id=EJER) == ejer_seed
    assert tv.verify(kode, seed=users.get_totp_seed(discord_id=EJER)) is False


def test_hele_kaeden_for_et_medlem(to_brugere):
    """seed -> registrér enhed -> kode_tilladt(). Det var dét der gav 403."""
    # 1) reglen er tændt (sat af ejeren 30/10)
    dd.saet_kraev(True, af=EJER)
    assert dd.kraev_aktivt() is True

    # 2) medlemmet sætter sin egen 2FA — den vej der var lukket
    seed = totp_rute._do_setup()["secret"]

    # 3) medlemmet registrerer sin computer med koden
    svar = ae.registrer_denne_computer(
        ae.TotpReq(totp=tv.generate_code(seed), navn="Mikkels computer", app_id="mikkel-desk")
    )

    # 4) enheden er der, og næste anmodning bærer claim'et
    assert [e["navn"] for e in dd.liste(MEDLEM)] == ["Mikkels computer"]
    from core.runtime.jarvisx_auth import verify_token
    claim = verify_token(f"Bearer {svar['token']}")
    assert claim["app_id"] == "mikkel-desk"

    to_brugere(uid=MEDLEM, rolle="member", app_id=str(claim["app_id"]))
    assert kode_adgang.kode_tilladt() is True, "medlemmet er stadig spærret fra code mode"


def test_uden_seed_er_beskeden_den_rigtige(to_brugere):
    """412 «slå totrinsbekræftelse til» skal pege på en vej der FINDES."""
    dd.saet_kraev(True, af=EJER)
    with pytest.raises(HTTPException) as e:
        ae.registrer_denne_computer(ae.TotpReq(totp="123456", navn="X", app_id="a"))
    assert e.value.status_code == 412
    assert "totrinsbekræftelse" in e.value.detail.lower()
    # og vejen er åben: ruten der gør beskeden opfyldelig afviser ikke medlemmet
    assert totp_rute._do_setup()["secret"]


def test_ejeren_kan_stadig(to_brugere):
    """Retningen for ejeren må ikke ændres af fixet."""
    to_brugere(uid=EJER, rolle="owner")
    svar = totp_rute._do_setup()
    assert svar["account"] == "Bjørn"
    assert users.get_totp_seed(discord_id=EJER) == svar["secret"]


def test_revoke_rammer_kun_kalderens_egen_seed(to_brugere):
    medlem_seed = totp_rute._do_setup()["secret"]
    to_brugere(uid=EJER, rolle="owner")
    ejer_seed = totp_rute._do_setup()["secret"]

    to_brugere(uid=MEDLEM, rolle="member")
    import asyncio
    asyncio.run(totp_rute.totp_revoke())

    assert users.get_totp_seed(discord_id=MEDLEM) == ""
    assert users.get_totp_seed(discord_id=EJER) == ejer_seed, "ejerens seed blev revet med"
    assert medlem_seed  # den fandtes før revoke

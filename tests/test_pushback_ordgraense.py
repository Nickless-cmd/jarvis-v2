"""Konflikt-matchet skal maale SIGNAL, ikke ord (27/10 + 25/11-2026).

To fejlformer er rettet her, og de er samme klasse — et ord der ligner et
signal, men ikke er det.

**27/10-2026 — delstreng.** `target in msg_lower` var en SUBSTRING-test.
Forpligtelsen «Er de ikke ens, skriv blokken om» gav target `ens`, og
`"ens" in "genstart"` er sandt. En vaekst-prompt der bad om at «genstart
igen og vent» blev derfor laest som et pres for at springe et
konsistens-tjek over — og veto-gaten blokerede fem vaerktoejskald i traek.
Rettelsen kraevede ord-graense og afviste bindestreg.

**25/11-2026 — navnefrasen.** Ord-graensen var noedvendig, men ikke
tilstraekkelig. Reglen udtrak de foerste 1-4 ord efter et forbudsverbum, og
det gav NAVNEFRASER i stedet for handlinger:

    `findes`            verbum uden objekt
    `et tool`           artikel + generisk substantiv
    `en blokering`      en tilstand
    `bjorns`            et ejefald
    `x`                 et bogstav
    `om modellen var for`, `klump dem i en`   hele bisætninger

MAALT: 42 af 50 aktive beslutninger fyrede med saadant et target. Enhver
besked der indeholdt ordet «bevis» eller «en kontrol» blev laest som en
konflikt med en vilkaarlig beslutning. Det blokerede min egen rettelse af
gaten — beskeden indeholdt ordet «bevis», og beslutningen «En groen test er
ikke bevis, foer jeg har set den blive roed» fyrede paa det.

Rettelsen: et signal skal vaere ENTEN erklaeret (citeret i beslutningens
`trigger_cue`, feltet der findes netop til dette) ELLER en handling
(verbum + objekt, ikke aabnet af en artikel). En navnefrase er ingen af
delene.

Disse vagter pinner BEGGE retninger: de falske match skal vaek, og de aegte
skal blive. En rettelse der kun fjerner de falske — og ogsaa fjerner de
aegte — er ikke en rettelse, den er en tavs goerelse af gaten tandloes.
"""

from __future__ import annotations

import pytest

from core.services import pushback


def _med_beslutning(monkeypatch, **fields):
    """Én aktiv beslutning med praecis den ordlyd testen handler om."""
    from core.services import behavioral_decisions

    monkeypatch.setattr(
        behavioral_decisions,
        "list_active_decisions",
        lambda limit=5: [fields],
    )
    return pushback


# ── 27/10: delstreng og bindestreg ────────────────────────────────────────


@pytest.fixture()
def med_forpligtelse(monkeypatch):
    """Én aktiv forpligtelse med praecis den ordlyd der faeldede i drift."""
    return _med_beslutning(
        monkeypatch,
        directive=(
            "Tael `columns` og tael `values` i hver enkelt raekke, foer en "
            "`comparison`-blok sendes — antallet skal vaere identisk. "
            "Er de ikke ens, skriv blokken om."
        ),
    )


@pytest.mark.parametrize(
    "besked",
    [
        "genstart igen og vent",
        "vi skal konsistens-tjekke noget",
        "koer genstart af runtime",
        "tjek at alt er ensartet",
    ],
)
def test_delstreng_i_et_laengere_ord_er_ikke_en_konflikt(med_forpligtelse, besked):
    """`ens` inde i «genstart»/«konsistens»/«ensartet» er ikke et ord-match."""
    assert med_forpligtelse._conflict_with_decisions(besked) == []


def test_den_maalte_vaekst_prompt_er_ren(med_forpligtelse):
    """Den praecise formulering der kostede fem kald i traek."""
    prompt = (
        "1. Bekraeft at uvicorn startede EFTER commit-tid. "
        "Er den aeldre, genstart igen og vent."
    )
    assert med_forpligtelse._conflict_with_decisions(prompt) == []


@pytest.fixture()
def med_tool_forpligtelse(monkeypatch):
    return _med_beslutning(
        monkeypatch,
        directive="Saet ikke et tool-kald efter den afsluttende tekstblok.",
    )


@pytest.mark.parametrize(
    "besked",
    [
        "jeg satte et tool-kald efter svaret",
        "der stod et tool-kald i sidste runde",
        "et tool-kald er ikke tilladt her",
    ],
)
def test_bindestreg_sammensaetning_er_ikke_en_konflikt(
    med_tool_forpligtelse, besked
):
    """`et tool` inde i «et tool-kald» er samme fejlform som `ens` i «genstart»."""
    assert med_tool_forpligtelse._conflict_with_decisions(besked) == []


# ── 25/11: navnefrasen er ikke en handling ────────────────────────────────
#
# Den gamle test her hed `test_det_selvstaendige_ord_fanges_stadig` og
# kraevede at «saet et tool her efter svaret» blev flagget. Den bevarede en
# FALSK positiv: `et tool` er artikel + generisk substantiv, ikke en
# handling, og beslutningen den kom fra («Saet ikke et tool-kald efter den
# afsluttende tekstblok») handler om MIN tur-adfaerd — ikke om hvad Bjorn
# maa bede om. Testen er derfor vendt om nedenfor.


@pytest.mark.parametrize(
    "target",
    [
        "findes",           # verbum uden objekt
        "et tool",          # artikel + generisk substantiv
        "en observation",   # et begreb
        "bjorns",           # et ejefald
        "en blokering",     # en tilstand
        "x",                # et bogstav
        "bevis",            # et enkelt ord uden objekt
        "en kontrol",       # artikel + generisk substantiv
        "om modellen var for",              # en bisætning
        "klump dem i en",                   # verbum + pronomen + artikel
        "laengere som ubesvarede spoergsmaal",  # en saetning
    ],
)
def test_navnefrase_er_ikke_et_konfliktobjekt(target):
    """De udtrukne fraser fra maalingen 25/11 skal alle afvises."""
    assert pushback._er_handlings_target(target) is False


@pytest.mark.parametrize(
    "target",
    [
        "slette filer",       # verbum + konkret objekt — den maalte aegte
        "signalets navn",     # konkret objekt
        "pushe uden test",    # handling med praepositionsled
    ],
)
def test_handling_er_et_konfliktobjekt(target):
    """En handling skal stadig kunne vaere target."""
    assert pushback._er_handlings_target(target) is True


def test_navnefrase_i_beskeden_fyrer_ikke(med_tool_forpligtelse):
    """Den praecise besked der blokerede rettelsen af gaten 25/11."""
    besked = (
        "Hahahahaha, han har lige brugt hele aftenen paa at afsloere forskellen "
        "mellem et signal og det, signalet paastaas at repraesentere - og nu "
        "finder han praecis samme problem i sin egen Central. Det staerke "
        "resultat er fundet paa et efterfoelgende udvalgt undersaet."
    )
    assert med_tool_forpligtelse._conflict_with_decisions(besked) == []


def test_den_maalte_blokering_af_egen_rettelse_fyrer_ikke(monkeypatch):
    """Beslutningen der blokerede fixet: target `bevis` fra en 1-ords frase."""
    modul = _med_beslutning(
        monkeypatch,
        directive=(
            "En groen test er ikke bevis, foer jeg har set den blive roed paa "
            "den rettelse den skulle fange."
        ),
    )
    assert modul._conflict_with_decisions(
        "Ret veto gaten - det er ikke bevis nok at tests er groenne."
    ) == []


# ── Den aegte konflikt: erklaeret signal eller handling ────────────────────


def test_handlings_target_fanges_stadig(monkeypatch):
    """`slette filer` er verbum + konkret objekt — den skal fyre."""
    modul = _med_beslutning(monkeypatch, directive="undgå at slette filer")
    flags = modul._conflict_with_decisions("slette filer nu")
    assert len(flags) >= 1, "aegte konflikt blev ikke fanget"
    assert "forpligtelse" in flags[0]


def test_erklaeret_signal_i_trigger_cue_fanges(monkeypatch):
    """En beslutning der CITERER sit signal skal fyre paa det — ogsaa selv om
    dens target-form var en navnefrase.

    Det er den mekanisme der allerede findes i skemaet: `trigger_cue` er
    feltet hvor beslutningen erklaerer hvad der aktiverer den. 13 af 50
    aktive beslutninger bruger den.
    """
    modul = _med_beslutning(
        monkeypatch,
        directive="Foelg kaeden af afledte tilstande, ikke signalets navn.",
        trigger_cue=(
            "Naar jeg vil skrive «X naar ikke frem til Y», «ingen forbindelse», "
            "eller «nul kaldere» om et signal mellem to moduler."
        ),
    )
    flags = modul._conflict_with_decisions("der er nul kaldere til funktionen")
    assert len(flags) >= 1, "erklaeret signal blev ikke fanget"


def test_erklaeret_signal_uden_forekomst_fyrer_ikke(monkeypatch):
    """Erklaeringen maa ikke goere beslutningen bredere end sine egne ord."""
    modul = _med_beslutning(
        monkeypatch,
        directive="Foelg kaeden af afledte tilstande, ikke signalets navn.",
        trigger_cue="Naar jeg vil skrive «ingen forbindelse» om et signal.",
    )
    assert modul._conflict_with_decisions(
        "Undersoeg om et regimeskift kan opdages foer udfaldet"
    ) == []

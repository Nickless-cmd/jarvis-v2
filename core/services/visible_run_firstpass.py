"""Ventetiden foer modellens FOERSTE element — livstegn, sandhed og et loft.

Udskilt fra ``visible_runs.py`` (7.485 linjer) efter Boy Scout-reglen, fordi
det er praecis den enhed der skulle aendres. Den er holdt som rene
beslutnings-funktioner uden async-rammeverk, saa loftet kan proeves uden at
rejse en hel stroem.

## Hvorfor den findes (14/9-2026)

Bjoern: «Den haenger bar på tænker..». Fire synlige koersler doede den aften
uden ét eneste tegn paa skaermen:

    20:31:57 → 20:47:04   907 s
    20:35:52 → 20:51:00   908 s
    21:59:21 → 22:14:45   924 s
    22:08:43 → 22:24:23   940 s

`py-spy` viste traaden blokeret i ``ssl.read`` under ``iter_lines``, og
``ss -tin`` viste at der KOM bytes — ca. 41 hvert 8. sekund. Det var
keepalive, ikke tekst: sporet sagde «FIRST item efter 905.6s:
VisibleModelStreamDone», altsaa en stroem der lukkede helt uden indhold.

Derfor kunne httpx' 60-sekunders laese-timeout aldrig fyre. Den maaler om der
kommer BYTES. Ingen maalte om der kom FREMDRIFT.

## Loftet er sat paa data, ikke paa en fornemmelse

227 foerste-elementer over tre doegn. De 222 sunde:

    p95  25,3 s
    p99  27,2 s
    max  40,0 s     (de seks langsomste: 26,7 27,0 27,2 30,0 33,3 40,0)

De fem syge laa alle paa 900+. Der er over tyve gange mellem den vaerste
sunde koersel og den hurtigste syge, saa taersklen er ikke et skoen — den
ligger midt i et tomrum. 120 sekunder giver tre gange luft over den vaerste
maalte sunde koersel og fanger haenget 7,5 gange hurtigere end i aften.

## Fase-navnet loej

Hjerteslaget sendte ``phase: "prompt_assembly"`` hele vejen. Kommentaren i
den gamle kode gaettede paa at ventetiden var prompt-bygning, og det var
rimeligt da den blev skrevet. Men medianen for foerste element er 6,8 s, saa
efter et halvt minut er den paastand forkert — og efter ni minutter er den
grov. Den narrede mig selv under fejlsoegningen i aften: jeg gaettede foerst
paa prompt-bygning, fordi serveren sagde det.

Loopet kan ikke se HVOR ventetiden ligger. Saa nu paastaar den det ikke;
den siger hvad den ved.
"""
from __future__ import annotations

# Hvor laenge vi venter paa koeen ad gangen foer vi sender livstegn. Klienten
# river forbindelsen efter ~20 s uden bytes (Bjoern 17/6: «spinner drejer
# ~20s → død»), saa der skal vaere rigeligt mellemrum til at naa flere.
KEEPALIVE_S = 6.0

# ── De tre tal og hvordan de haenger sammen ──────────────────────────────
#
# STALL_UDEN_DATA_S  <  STALL * 2  <  FOERSTE_ELEMENT_LOFT_S
#        60                120              240
#
# Den INDRE vagt (60 s) sidder i selve laese-loopet og kan se forskel paa
# «der kommer keepalive-linjer» og «der kommer indhold». Den fyrer foerst, og
# den kan noejes med ét nyt forsoeg.
#
# Det YDRE loft (240 s) sidder i stroem-generatoren og kan kun se at der intet
# er kommet. Det er et bagstop for alt den indre vagt ikke kan se, og det skal
# derfor ligge over to fulde indre forsoeg (2 x 60 = 120) plus den langsomste
# sunde koersel vi har maalt (40 s) med rigelig luft.
#
# Loftet stod paa 120 s da det blev bygget, foer der fandtes et genforsoeg.
# Med et genforsoeg nedenunder ville 120 slaa netop det forsoeg ihjel som var
# ved at lykkes. Seks gange den vaerste maalte sunde koersel er stadig knap
# fire gange hurtigere end de 906-940 sekunder det kostede 14/9.
FOERSTE_ELEMENT_LOFT_S = 240.0

# Hvor laenge der maa komme linjer UDEN indhold foer vi opgiver forsoeget.
# 14/9 kom der ca. 41 bytes hvert 8. sekund i femten minutter — keepalive,
# ikke tekst. httpx' laese-timeout saa bytes og var derfor tilfreds.
STALL_UDEN_DATA_S = 60.0

# Fejlkoden der betyder «udbyderen tav FOER sit foerste event». Kun den maa
# udloese et nyt forsoeg: er der allerede streamet tekst, ville et genforsoeg
# gentage den paa skaermen.
STALL_KODE = "stalled-before-first-event"

# Ét. Samme regel som bro-failoveren: en aerlig fejl er bedre end en langsom.
MAKS_GENFORSOEG = 1

# Under dette er ventetiden helt normal (p90 = 22,3 s), og der er ingen grund
# til at goere en bruger nervoes.
USAEDVANLIG_EFTER_S = 45.0


def hjerteslag_fase(ventet_s: float) -> str:
    """Hvad hjerteslaget skal sige at den laver.

    Den gamle kode sagde «prompt_assembly» uanset hvor laenge der var gaaet.
    Loopet kan ikke se om ventetiden ligger i prompt-bygningen eller i
    udbyderens socket, saa det rigtige er at sige det den VED: at der ventes
    paa foerste svar — og at sige til naar det er unormalt.
    """
    if ventet_s >= USAEDVANLIG_EFTER_S:
        return "afventer_foerste_svar_usaedvanlig_laenge"
    return "afventer_foerste_svar"


def loft_naaet(ventet_s: float) -> bool:
    """Har vi ventet laengere end nogen sund koersel nogensinde har gjort?"""
    return ventet_s >= FOERSTE_ELEMENT_LOFT_S


def opgiv_tekst(ventet_s: float, *, provider: str, model: str) -> str:
    """Den besked brugeren faar. Den skal sige HVAD der skete og HVOR.

    En tavs fejl er det hele denne fil handler om at undgaa, saa beskeden
    naevner baade udbyderen og ventetiden — ellers kan man ikke skelne «min
    prompt var for stor» fra «udbyderen svarede aldrig».
    """
    return (
        f"{provider}/{model} tog imod kaldet og sendte intet svar i "
        f"{int(ventet_s)} sekunder. Kørslen blev stoppet, så den ikke hænger. "
        f"Ingen sund kørsel har været over {int(FOERSTE_ELEMENT_LOFT_S)} sekunder om "
        f"det første svar."
    )

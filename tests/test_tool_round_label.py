"""Etiketten over en værktøjs-runde — «Rettede NPE i UserService».

Budgetterne og formen stammer fra Claude Codes egen kilde, læst af Jarvis
14/9-2026 (`src/services/toolUseSummary/toolUseSummaryGenerator.ts`): 300 tegn
pr. værktøj, brugerens hensigt som kontekst, og en prompt der siger
*«single-line row in a mobile app … truncates around 30 characters … think
git-commit-subject, not sentence»*.

Det er den ene af TO linjer om en runde. Den mekaniske («Kørte en kommando og
redigerede 2 filer +12 −4») siger hvad der SKETE og bygges af værktøjernes egne
resultater. Denne siger hvad runden UDRETTEDE.
"""
from __future__ import annotations

import pytest

from core.services import tool_round_label as trl


def _v(navn: str, inp: object = None, res: object = None, id_: str = "") -> dict:
    return {"name": navn, "input": inp, "result": res, "id": id_}


# ────────────────────────────────────────────────────────── hvad modellen ser

def test_hvert_kald_klippes_FOR_SIG():
    """Klippedes hele blokken under ét, ville ét stort bash-output skubbe de
    oevrige kald ud af billedet — og etiketten ville beskrive én tilfaeldig del
    af runden som om den var det hele."""
    p = trl.byg_prompt([_v("bash", {"command": "ls"}, "x" * 5000),
                        _v("read_file", {"path": "vigtig.py"}, "indhold")])
    assert "vigtig.py" in p, "det andet kald forsvandt bag det foerstes output"
    # Maal afkortningen DIREKTE. Foerste udgave taalte «hoejst ét hundrede
    # x'er i traek», hvilket er noget andet: 300 tegn rummer tre af dem.
    langt = max(len(s) for s in p.split("Output: ")[1].split("\n"))
    assert langt == trl.MAKS_PR_VAERKTOEJ, f"output klippet til {langt}"


def test_budgettet_pr_vaerktoej_er_kildens():
    assert trl.MAKS_PR_VAERKTOEJ == 300


def test_brugerens_HENSIGT_kommer_med():
    """Etiketten skal beskrive hvad runden udrettede I FORHOLD TIL det der blev
    bedt om — ikke bare hvad vaerktoejet gjorde."""
    p = trl.byg_prompt([_v("bash", {"command": "pytest"})], hensigt="ret den fejl i login")
    assert "ret den fejl i login" in p


def test_en_tom_hensigt_fylder_ingenting():
    p = trl.byg_prompt([_v("bash", {"command": "ls"})], hensigt="   ")
    assert "Brugeren bad om" not in p


def test_et_kald_UDEN_navn_springes_over():
    """En halvt streamet raekke har ikke noget navn endnu. «Vaerktoej: » med
    ingenting efter ville faa modellen til at digte."""
    p = trl.byg_prompt([_v("", {"a": 1}), _v("bash", {"command": "ls"})])
    assert p.count("Værktøj:") == 1


def test_None_bliver_TOMT_og_ikke_teksten_None():
    p = trl.byg_prompt([_v("bash", None, None)])
    assert "None" not in p


def test_nylinjer_i_output_braekker_ikke_billedet():
    """Et bash-output med linjeskift ville ellers se ud som flere felter."""
    p = trl.byg_prompt([_v("bash", {"command": "ls"}, "a\nb\nc")])
    assert "Output: a b c" in p


# ─────────────────────────────────────────────────────────────── selve etiketten

def test_etiketten_er_KORT(monkeypatch):
    monkeypatch.setattr(trl, "_kald_model", lambda p: "ord " * 40)
    ud = trl.etiket([_v("bash", {"command": "ls"})])
    assert len(ud) <= trl.MAKS_ETIKET
    assert not ud.endswith("or"), "klippet midt i et ord"


def test_punktum_og_anfoerselstegn_fjernes(monkeypatch):
    """Det er et commit-emne, ikke en saetning."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: '«Rettede NPE i UserService.»')
    assert trl.etiket([_v("bash")]) == "Rettede NPE i UserService"


def test_kun_FOERSTE_linje(monkeypatch):
    """Fiksturen baerer stien, fordi opdigt-vagten ellers — med rette —
    kasserer en etiket der naevner en fil kaldet aldrig roerte. Den fangede
    denne test da vagten kom til, og fiksturen var det der ikke lignede
    virkeligheden."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Læste config.json\n\nHer er hvorfor:")
    assert trl.etiket([_v("read_file", {"path": "config.json"})]) == "Læste config.json"


def test_INGEN_vaerktoejer_giver_intet_kald(monkeypatch):
    kaldt: list[int] = []
    monkeypatch.setattr(trl, "_kald_model", lambda p: kaldt.append(1) or "x")
    assert trl.etiket([]) == ""
    assert trl.etiket([_v("")]) == ""
    assert kaldt == []


def test_en_MODELFEJL_giver_tomt_og_kaster_ikke(monkeypatch):
    """En etiket er en overskrift. En tur maa aldrig vaelte fordi overskriften
    ikke kunne skrives — CC's egen kilde loggger og lader kaldet passere."""
    monkeypatch.setattr(trl, "_kald_model",
                        lambda p: (_ for _ in ()).throw(RuntimeError("nede")))
    assert trl.etiket([_v("bash", {"command": "ls"})]) == ""


def test_et_TOMT_modelsvar_giver_tomt(monkeypatch):
    monkeypatch.setattr(trl, "_kald_model", lambda p: "   ")
    assert trl.etiket([_v("bash")]) == ""


# ────────────────────────────────────────── etiketten haefter paa SIT batch

def test_tool_use_ids_baeres_med():
    """CC baerer det samme som `preceding_tool_use_ids`, og det er ikke pynt:
    uden det haefter etiketten sig paa en PLADS i stroemmen i stedet for paa
    sit batch, og en sen etiket ville saette sig over de forkerte kald."""
    assert trl.tool_use_ids([_v("bash", id_="a"), _v("read_file", id_="b")]) == ["a", "b"]


def test_kald_uden_id_udelades_frem_for_at_faa_en_tom_plads():
    assert trl.tool_use_ids([_v("bash", id_=""), _v("read_file", id_="b")]) == ["b"]


def test_tool_use_id_accepteres_ogsaa_som_navn():
    """Serveren og klienten kalder feltet hver sit."""
    assert trl.tool_use_ids([{"name": "bash", "tool_use_id": "z"}]) == ["z"]


# ──────────────────────────────────────────── den betalte lane er FORBUDT

def test_der_bruges_en_LOKAL_model():
    """CC bruger Haiku — den lille hjaelpe-model — netop fordi det er
    nyttearbejde. CLAUDE.md siger det samme: billige modeller maa STOETTE ham,
    ikke definere ham. En etiket er ikke hans samtale, den er en overskrift
    over den."""
    import inspect
    kilde = inspect.getsource(trl)
    assert "127.0.0.1" in kilde
    assert "deepseek.com" not in kilde


def test_ventetiden_har_et_loft():
    """Et loefte der ikke er indfriet inden da, er uinteressant.

    Loftet blev haevet fra 3 til 6 s 17/9-2026, fordi maalingen viste hvad det
    KOSTEDE: paa aegte runder ramte de lange kald loftet og gav TOM etiket.
    Ingen venter paa den — traaden er daemon, og etiketten baerer sine
    tool_use_ids, saa den finder sine kald uanset hvornaar den lander. Loftet
    findes stadig, fordi et kald der haenger, ikke maa haenge for evigt.
    """
    assert trl.TIMEOUT_S <= 8.0


def test_prompten_vokser_ikke_med_en_KAEMPE_runde():
    """En runde paa 50 kald gav 15.000 tegns prompt og dermed timeout. De
    foerste kald siger hvad runden handlede om; resten taelles."""
    kald = [{"name": f"vaerktoej_{i}", "input": {"x": "y" * 200}} for i in range(50)]
    p = trl.byg_prompt(kald)
    assert p.count("Værktøj: ") == trl.MAKS_KALD
    assert "(og 42 kald mere i samme runde)" in p


# ────────────────────────────── serverens EGEN form (14/9-2026)
#
# Runde-løkken i `visible_runs` holder kaldene i OpenAI-form:
# `{id, type, function: {name, arguments}}` — og UDEN resultater. Målt: det
# koster næsten ingenting. Samme fire runder med og uden outputs gav
# «Rettede fejl i login» begge gange, og «Søgte i heartbeat_model_provider»
# uden outputs mod «Søgte i heartbeat_runtime» med — den uden er endda mere
# præcis. Derfor kobles den på den form serveren HAR, frem for at vente på en
# den ikke har.

def test_openai_formen_forstaas():
    p = trl.byg_prompt([{"id": "a", "type": "function",
                         "function": {"name": "bash", "arguments": '{"command": "ls"}'}}])
    assert "Værktøj: bash" in p
    assert '"command": "ls"' in p


def test_id_hentes_ogsaa_fra_openai_formen():
    kald = [{"id": "call_1", "function": {"name": "bash", "arguments": "{}"}}]
    assert trl.tool_use_ids(kald) == ["call_1"]


def test_de_to_former_kan_BLANDES():
    """En runde kan indeholde begge, og en etiket der tier om halvdelen er
    værre end ingen."""
    p = trl.byg_prompt([
        {"id": "a", "function": {"name": "bash", "arguments": "{}"}},
        {"name": "read_file", "input": {"path": "x.py"}},
    ])
    assert p.count("Værktøj:") == 2


def test_et_openai_kald_UDEN_navn_springes_over():
    p = trl.byg_prompt([{"id": "a", "function": {"name": "", "arguments": "{}"}},
                        {"name": "bash", "input": {}}])
    assert p.count("Værktøj:") == 1


# ───────────────────────────── opdigt kasseres (14/9-2026, maalt i produktion)
#
# Foerste ægte etiketter: «Kørte ssh og hentede logfiler» (god) og
# «Søgte i bash/» (opdigt). Den anden er modellen der efteraber promptens eget
# eksempel «Søgte i auth/» og opfinder et bibliotek `bash/` der ikke findes.
#
# En strammere prompt er et haab. Huset har et bedre greb: `explore_claim_check`
# slaar paastande op i kilden. Samme princip her — en etiket der naevner en sti
# eller et navn der ikke staar i kaldene, er opdigt. En kedelig etiket er
# harmloes; en der lyver om hvad der skete, er ikke.

def test_en_opdigtet_sti_kasseres(monkeypatch):
    """Det ægte fund fra produktion."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Søgte i bash/")
    assert trl.etiket([_v("bash", {"command": "ssh bs@10.0.0.39 'journalctl -n 50'"})]) == ""


def test_en_sti_der_FAKTISK_staar_i_kaldet_slipper_igennem(monkeypatch):
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Læste config.json")
    assert trl.etiket([_v("read_file", {"path": "apps/config.json"})]) == "Læste config.json"


def test_et_navn_med_understreg_efterproeves_ogsaa(monkeypatch):
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Søgte i heartbeat_model_provider")
    kald = [_v("grep", {"pattern": "heartbeat_model_provider"})]
    assert trl.etiket(kald) == "Søgte i heartbeat_model_provider"
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Søgte i noget_der_ikke_findes")
    assert trl.etiket(kald) == ""


def test_almindelige_ORD_efterproeves_ikke(monkeypatch):
    """«Kørte ssh og hentede logfiler» skal igennem. Kraevede vi at hvert ord
    stod i kaldet, ville enhver omskrivning blive kasseret — og en etiket der
    kun maa gentage input er ikke en etiket."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Kørte ssh og hentede logfiler")
    ud = trl.etiket([_v("bash", {"command": "ssh bs@10.0.0.39 'journalctl -n 50'"})])
    assert ud == "Kørte ssh og hentede logfiler"


def test_tal_og_korte_stumper_udloeser_ikke_vagten(monkeypatch):
    """«2 filer» og «v2» maa ikke se ud som opdigtede stier."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Rettede 2 fejl")
    assert trl.etiket([_v("edit_file", {"path": "a.py"})]) == "Rettede 2 fejl"


# ──────────────────────────── etiketten maa ikke VAERE kommandoen (17/9-2026)
#
# Maalt paa 45 aegte etiketter i produktion: «Sed 645 700p chatview tsx», «cd
# /media/projects/jarvis-v2 && grep -n», «Grep -rn instrument_fix core»,
# «Grepede approved i core apps py», «Sættede maksimum til 5 kald». Etiketten
# blev kommandolinjen igen — praecis det den mekaniske linje viser i forvejen —
# eller et engelsk kommandonavn boejet som et dansk verbum.

@pytest.mark.parametrize("raa", [
    "Sed 645 700p chatview tsx",
    "cd /media/projects/jarvis-v2 && grep -n",
    "Grep -rn instrument_fix core",
    "Grepede approved i core apps py",
    "CD'et til projects jarvis v2",
    "git log for de sidste 25",
])
def test_en_etiket_der_bare_gentager_kommandoen_kasseres(monkeypatch, raa):
    monkeypatch.setattr(trl, "_kald_model", lambda p: raa)
    assert trl.etiket([_v("bash", {"command": "cd /media/projects/jarvis-v2 && grep -rn x core"})]) == ""


@pytest.mark.parametrize("raa", [
    "Søgte efter instrument_fix i core",
    "Læste linjerne i chatview",
    "Hentede historikken fra repoet",
])
def test_en_RIGTIG_etiket_om_de_samme_kald_slipper_igennem(monkeypatch, raa):
    """Vagten maa ikke ramme etiketter der BESKRIVER en kommando i stedet for
    at gentage den — det er hele den form vi beder om."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: raa)
    kald = [_v("bash", {"command": "cd /repo && grep -rn instrument_fix core chatview historikken"})]
    assert trl.etiket(kald) == raa


def test_et_naeget_verbum_er_ikke_en_etiket(monkeypatch):
    """Maalt: modellen svarede «Søgte agent-21cc158c0a274d98ae2e4c0fb56bb57»,
    og klipningen ved 40 tegn aad hele objektet. Tilbage stod «Søgte», som
    ikke siger mere end den mekaniske linje."""
    monkeypatch.setattr(trl, "_kald_model",
                        lambda p: "Søgte agent-21cc158c0a274d98ae2e4c0fb56bb57xyz")
    assert trl.etiket([_v("bash", {"command": "grep agent-21cc158c0a274d98ae2e4c0fb56bb57xyz x"})]) == ""


def test_efterproevningen_ser_bort_fra_KASSE(monkeypatch):
    """Modellen retter gerne begyndelsesbogstavet. Et match der kraevede samme
    kasse ville kassere en RIGTIG etiket."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Læste Config.json")
    assert trl.etiket([_v("read_file", {"path": "apps/config.json"})]) == "Læste Config.json"


# ──────── to fejl fra anden produktions-runde (14/9-2026)
#
# Fem ægte etiketter efter opdigt-vagten. Tre var gode. To var ikke:
#
#   «Skriv etiketten: Kørte beacon scriptet»  — modellen skrev min INSTRUKTION
#                                               med som en del af svaret
#   «Restartede crash-beacon og hentede»      — klippet ved 40 tegn og efterlod
#                                               et hængende bindeord
#
# Begge er mekaniske. En etiket der bærer sin egen prompt, og en der slutter
# på «og», ligner begge en fejl i appen — og de ER det.

def test_en_laekket_instruktion_fjernes(monkeypatch):
    """Det ægte fund. Modellen skrev prompten med."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Skriv etiketten: Kørte beacon scriptet")
    assert trl.etiket([_v("bash", {"command": "./beacon.sh"})]) == "Kørte beacon scriptet"


def test_flere_former_for_instruktion(monkeypatch):
    for raa in ("Etiket: Læste loggen", "etiketten: Læste loggen",
                "Svar: Læste loggen", "Etiket - Læste loggen"):
        monkeypatch.setattr(trl, "_kald_model", lambda p, r=raa: r)
        assert trl.etiket([_v("bash", {"command": "cat log"})]) == "Læste loggen", raa


def test_et_almindeligt_kolon_MIDT_i_etiketten_roeres_ikke(monkeypatch):
    """«Kørte: ls» ville vaere en anden sag — men kun et kendt instruktions-ord
    foran kolonet maa udloese det. Ellers ville vi klippe i rigtige etiketter."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Kørte ls: fandt 3 filer")
    assert trl.etiket([_v("bash", {"command": "ls"})]) == "Kørte ls: fandt 3 filer"


def test_en_KLIPPET_etiket_slutter_hvor_et_led_slutter(monkeypatch):
    """Det ægte fund: «Restartede crash-beacon og hentede».

    Den ender IKKE paa et bindeord — den ender paa et VERBUM hvis objekt blev
    klippet vaek, og derfor kunne en liste over bindeord aldrig fange den.
    Foerste udgave af den her test proevede netop for et haengende bindeord og
    bestod TOMT: to mutationer overlevede den.

    Reglen er en anden: er teksten klippet, ryger det sidste led med.
    """
    monkeypatch.setattr(
        trl, "_kald_model",
        lambda p: "Restartede crash-beacon og hentede logfilerne bagefter ogsaa")
    ud = trl.etiket([_v("bash", {"command": "systemctl restart crash-beacon"})])
    assert ud == "Restartede crash-beacon", ud


def test_en_KORT_etiket_med_og_klippes_IKKE(monkeypatch):
    """Var den ikke klippet, er «og» forfatterens egen saetning."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Læste og rettede filen")
    assert trl.etiket([_v("edit_file", {"path": "filen.py"})]) == "Læste og rettede filen"


def test_klipning_efterlader_ikke_et_haengende_ord(monkeypatch):
    """Uden led-skel, men med et forholdsord til sidst efter klipningen.

    Foerste udgave brugte en tekst med «og» i — og saa var det LED-reglen der
    ryddede op, ikke den her loekke. Testen bestod uden loekken, og mutationen
    overlevede. Inputtet er nu valgt saa KUN loekken kan redde den: klippet
    ved 40 tegn ender den paa «til».
    """
    monkeypatch.setattr(trl, "_kald_model",
                        lambda p: "Læste beskeden fra brugeren til systemet med")
    ud = trl.etiket([_v("read_file", {"path": "a.py"})])
    assert ud == "Læste beskeden fra brugeren", ud


def test_et_forholdsord_til_sidst_ryger_ogsaa_UDEN_klipning(monkeypatch):
    """«Skrev den nye fil til disken som» er en braekket saetning uanset om den
    blev klippet. Loekken koerer derfor altid."""
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Skrev den nye fil til disken som")
    assert trl.etiket([_v("write_file", {"path": "a.py"})]) == "Skrev den nye fil til disken"

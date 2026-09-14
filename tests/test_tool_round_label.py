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
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Læste config.json\n\nHer er hvorfor:")
    assert trl.etiket([_v("read_file")]) == "Læste config.json"


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
    """Et loefte der ikke er indfriet inden da, er uinteressant."""
    assert trl.TIMEOUT_S <= 5.0

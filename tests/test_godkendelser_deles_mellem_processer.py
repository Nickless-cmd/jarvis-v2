"""Et godkendelses-kort skal kunne ses af den proces der ikke lavede det.

Bjørns symptom, gentaget over måneder: «jeg kan sidde i en samtale i desk og tro
han er stået af, fordi mobilen har overtaget og approval-kortet er landet der».

Det er ikke mobilen der overtager. `_PENDING_APPROVALS` blev indlæst ÉN gang —
ved modul-import — og gemt ved hver ændring, men aldrig genindlæst. `jarvis-api`
og `jarvis-runtime` kører samme kode i hver sin proces og deler filen, så et kort
skabt i den ene var usynligt i den anden indtil en genstart.

Kortet var aldrig ét sted.

Jarvis fandt selv formen samme aften, mens han læste hvordan Anthropic og OpenAI
gør det: «det svære er at to flader SKRIVER i én session uden at træde på
hinanden». Han foreslog en tabel. Det her er det samme svar i det mindre: én
sandhed på disken, læst hver gang, skrevet under lås.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import core.services.visible_runs as vr

ROD = Path(__file__).resolve().parents[1]


def _skriv_i_anden_proces(hjem: str, praefiks: str, antal: int) -> int:
    """Skriv kort fra en RIGTIG anden proces. Giver exit-koden tilbage.

    **HOME, ikke JARVIS_HOME.** `state_store._STATE_DIR` er
    ``Path.home() / ".jarvis-v2" / "state"`` — en modul-konstant. Foerste udgave
    af denne test satte `JARVIS_HOME`, som INTET styrer her, saa subprocessen
    skrev i den rigtige state-mappe paa maskinen. Den skrev 27 test-kort derind
    foer jeg opdagede det.

    `subprocess` frem for `multiprocessing`: en `fork` ville arve vores
    allerede indlaeste moduler og dermed skjule netop den fejl vi tester — at
    hver proces har sin egen kopi.
    """
    kode = (
        "import sys; sys.path.insert(0, '.');"
        "import core.services.visible_runs as v;"
        f"[v.saet_godkendelse('{praefiks}-%d' % i, {{"
        "'tool_name': 'bash', 'arguments': {}, 'run_id': 'r',"
        "'session_id': 's1', 'status': 'pending',"
        "'created_at': '2026-09-24T22:00:00+00:00'})"
        f" for i in range({antal})]"
    )
    miljoe = {**os.environ, "HOME": hjem}
    return subprocess.run([sys.executable, "-c", kode], cwd=str(ROD),
                          env=miljoe, capture_output=True, timeout=180).returncode


def _samme_mappe(monkeypatch, tmp_path) -> str:
    """Peg BEGGE processer paa det samme midlertidige state-dir."""
    import core.runtime.state_store as ss
    hjem = tmp_path / "hjem"
    (hjem / ".jarvis-v2" / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ss, "_STATE_DIR", hjem / ".jarvis-v2" / "state")
    return str(hjem)


def _kort(session_id: str = "s1", **ekstra) -> dict:
    return {"tool_name": "bash", "arguments": {"command": "ls"},
            "run_id": "r1", "session_id": session_id, "status": "pending",
            "created_at": "2026-09-24T22:00:00+00:00", **ekstra}


def test_en_anden_proces_ser_kortet(tmp_path, monkeypatch) -> None:
    """KERNEN. Skrives kortet i én proces, skal det kunne læses i en anden.

    Før: det kunne det ikke, og der var ingen fejl — kun et kort ingen kunne se.
    """
    hjem = _samme_mappe(monkeypatch, tmp_path)

    kode = _skriv_i_anden_proces(hjem, "fra-anden-proces", 1)
    assert kode == 0, "skrive-processen fejlede"

    assert "fra-anden-proces-0" in vr.godkendelser_nu(), (
        "kortet fra den anden proces er usynligt — præcis den fejl der fik "
        "Bjørn til at tro Jarvis var stået af"
    )


def test_to_skrivere_sletter_ikke_hinandens_kort(tmp_path, monkeypatch) -> None:
    """Hver gemning skriver HELE filen. Uden lås taber den ene den andens kort.

    Det er den fejl der bliver VÆRRE af at rette læsningen alene: før ville den
    skrivende proces i det mindste selv se sit kort; med læsning fra disk ville
    et tabt kort være usynligt for alle.
    """
    hjem = _samme_mappe(monkeypatch, tmp_path)

    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        ka = ex.submit(_skriv_i_anden_proces, hjem, "a", 12)
        kb = ex.submit(_skriv_i_anden_proces, hjem, "b", 12)
        assert ka.result() == 0 and kb.result() == 0

    alle = vr.godkendelser_nu()
    fra_a = [k for k in alle if k.startswith("a-")]
    fra_b = [k for k in alle if k.startswith("b-")]
    assert len(fra_a) == 12 and len(fra_b) == 12, (
        f"kort gik tabt under samtidig skrivning: a={len(fra_a)} b={len(fra_b)} "
        f"— to processer skrev oven i hinanden"
    )


def test_et_fjernet_kort_bliver_vaek(tmp_path, monkeypatch) -> None:
    """Og den modsatte vej: svarer den ene proces, må den anden ikke vise kortet.

    Et kort der er besvaret ét sted og stadig lyser et andet, er samme
    forvirring set fra den anden side.
    """
    hjem = _samme_mappe(monkeypatch, tmp_path)

    vr.saet_godkendelse("a1", _kort())
    assert "a1" in vr.godkendelser_nu()
    assert vr.fjern_godkendelse("a1") is not None
    assert "a1" not in vr.godkendelser_nu(), "kortet blev liggende efter svar"
    assert vr.fjern_godkendelse("a1") is None, "det blev fjernet to gange"


def test_laesningen_kasserer_ikke_udloebne_kort(tmp_path, monkeypatch) -> None:
    """Et udløbet kort skal AFVISES, ikke forsvinde.

    Første udgave kørte `_friske_godkendelser` ved hver læsning. Den hører til
    opstart (hvor et dødt kort ikke skal genoplives); brugt ved hver læsning
    ville et udløbet kort bare forsvinde — og et kort der forsvinder uden svar
    er præcis den forvirring vi fjerner. En test fangede det.
    """
    hjem = _samme_mappe(monkeypatch, tmp_path)

    vr.saet_godkendelse("gammelt", _kort(created_at="2026-01-01T00:00:00+00:00"))
    assert "gammelt" in vr.godkendelser_nu(), (
        "et udløbet kort blev kasseret ved læsning i stedet for at blive afvist "
        "med en grund"
    )

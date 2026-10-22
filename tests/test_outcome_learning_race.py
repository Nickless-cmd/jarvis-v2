"""outcome_learning.json — to skrivere delte én temp-fil.

MÅLT 20/10-2026 17:44:31 (side-9b957af2ea):

    save failed — No such file or directory: outcome_learning.tmp -> outcome_learning.json
    load failed: Extra data: line 21434 column 2 (char 521995)

Begge fejl er samme rod. `_save` brugte en FAST temp-sti
(`path.with_suffix(".tmp")`), så `jarvis-api` og `jarvis-runtime` — der kører
samme kode i hver sin proces og deler filen — skrev til PRÆCIS samme temp-fil:

    A åbner tmp med "w" (trunkerer), skriver
    B åbner SAMME tmp med "w" (trunkerer), skriver ind over A
    A's replace() flytter tmp -> .json
    B's replace()  -> tmp findes ikke længere  -> "No such file or directory"

Og imellem de to skrivninger kunne .json få blandet indhold, hvilket læses som
"Extra data: line 21434".

Derudover var read-modify-write ulåst: begge parter læste N poster, tilføjede
én og skrev N+1 — den enes post forsvandt sporløst (lost update).

Testene her måler ADFÆRDEN, ikke mekanismen: at ingen post tabes, og at en
læser aldrig ser en halv fil.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from core.services import outcome_learning as ol


@pytest.fixture()
def storage(tmp_path, monkeypatch):
    """Isolér storage-filen. Låsen følger husets mønster og ligger i state."""
    fil = tmp_path / "shared" / "runtime" / "outcome_learning.json"
    fil.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ol, "_storage_path", lambda: fil)
    return fil


def test_samtidige_skrivninger_taber_ikke_poster(storage):
    """Kernen i den målte fejl: read-modify-write uden lås.

    Uden låsen læser to parter samme N poster og skriver hver N+1 — så den ene
    post forsvinder. Med låsen serialiseres hele læs-ændr-skriv, og alle
    poster overlever.

    MUTATION: fjern `med_laas` omkring læs/skriv i record_outcome -> fejler.
    """
    antal = 24
    barrier = threading.Barrier(antal)
    fejl: list[BaseException] = []
    id_liste: list[str] = []
    id_lock = threading.Lock()

    def skriv(_i: int) -> None:
        try:
            barrier.wait(timeout=10)
            rid = ol.record_outcome(context="race-test", outcome="success")
            with id_lock:
                id_liste.append(rid)
        except BaseException as exc:  # pragma: no cover - rapporteres nedenfor
            fejl.append(exc)

    tråde = [threading.Thread(target=skriv, args=(i,)) for i in range(antal)]
    for t in tråde:
        t.start()
    for t in tråde:
        t.join(timeout=30)

    assert not fejl, f"skrivninger kastede: {fejl!r}"
    assert len(id_liste) == antal

    gemt = json.loads(storage.read_text(encoding="utf-8"))
    gemte_id = {p["record_id"] for p in gemt}
    manglende = set(id_liste) - gemte_id
    assert not manglende, (
        f"{len(manglende)} af {antal} poster forsvandt — read-modify-write er "
        f"ikke serialiseret")


def test_laeseren_ser_aldrig_en_halv_fil(storage):
    """Den anden halvdel af den målte fejl: "Extra data: line 21434".

    En læser der rammer midt i en skrivning må aldrig se trunkeret eller
    blandet JSON. Med en unik temp-fil pr. skrivning er `replace()` atomisk,
    så læseren ser enten den gamle eller den nye fil — aldrig en blanding.

    MUTATION: gå tilbage til den faste `with_suffix(".tmp")`-sti -> fejler.
    """
    ol.record_outcome(context="basis", outcome="success")

    stop = threading.Event()
    set_under_skrivning: list[str] = []

    def skriv_løbende() -> None:
        while not stop.is_set():
            ol.record_outcome(context="race-test", outcome="success")

    def laes_løbende() -> None:
        while not stop.is_set():
            raa = storage.read_text(encoding="utf-8") if storage.exists() else "[]"
            try:
                json.loads(raa)
            except ValueError as exc:
                set_under_skrivning.append(f"{exc}: {raa[:80]!r}")
                return

    skrivere = [threading.Thread(target=skriv_løbende) for _ in range(4)]
    læsere = [threading.Thread(target=laes_løbende) for _ in range(2)]
    for t in skrivere + læsere:
        t.start()
    threading.Event().wait(0.6)
    stop.set()
    for t in skrivere + læsere:
        t.join(timeout=30)

    assert not set_under_skrivning, (
        f"læseren så en ugyldig fil: {set_under_skrivning[:2]}")


def test_ingen_delt_temp_fil_bliver_tilbage(storage):
    """En delt temp-fil efterladt på disken er selve mekanismen der gjorde
    skaden mulig. Efter en skrivning må der ikke ligge en `outcome_learning.tmp`
    som den næste skriver kan træde ind i.

    MUTATION: gå tilbage til den faste sti -> fejler (filen bliver tilbage).
    """
    ol.record_outcome(context="basis", outcome="success")
    efterladt = list(Path(storage.parent).glob("*.tmp"))
    assert not efterladt, f"delt temp-fil efterladt: {efterladt}"

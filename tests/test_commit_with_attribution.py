"""Beskeden må kunne afleveres uden at røre skallen.

Målt 11/9-2026: tre backtick-citerede navne i én `--message "..."` blev kørt
som kommando-substitution. `permission_axes` og `--stat` forsvandt HELT,
`4009d48c5` blev halveret (den overlevede ét af sine to steder). Commit'en gik
igennem med exit 0 — fejlen stod kun på stderr — og `--amend` er blokeret af
hookene, så beskeden kan ikke rettes bagefter.

`--message "$(cat fil)"` har virket i 7.951 commits, men det er en omgåelse af
et manglende interface, ikke en kur: prosaen går stadig gennem skallen.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "cwa", Path(__file__).resolve().parents[1] / "scripts" / "commit_with_attribution.py")
cwa = importlib.util.module_from_spec(_SPEC)
sys.modules["cwa"] = cwa
_SPEC.loader.exec_module(cwa)


def _args(**kw):
    class A:
        message = None
        message_file = None
    a = A()
    for k, v in kw.items():
        setattr(a, k, v)
    return a


def test_message_file_laeses_ordret(tmp_path):
    """Præcis den prosa der fejlede: backticks, en flag-lignende streng og
    dobbelt-nævnte navne."""
    tekst = ("fix: `4009d48c5` hedder docs og indfoerer en service.\n"
             "`--stat` retter den; emnelinjen goer ikke. Og `permission_axes`\n"
             "hoerer hjemme paa staerkere grund. Se `4009d48c5` igen.\n")
    f = tmp_path / "besked.txt"
    f.write_text(tekst, encoding="utf-8")
    ud = cwa._laes_besked(_args(message_file=str(f)))
    assert ud == tekst
    assert ud.count("4009d48c5") == 2, "det dobbelt-naevnte navn maa ikke halveres"
    assert "--stat" in ud
    assert "permission_axes" in ud


def test_message_bruges_naar_den_er_der():
    assert cwa._laes_besked(_args(message="almindelig besked")) == "almindelig besked"


def test_utf8_overlever(tmp_path):
    """Beskederne er danske. En kodningsfejl her ville æde æøå i stedet for
    backticks — samme klasse, anden bogstav."""
    f = tmp_path / "b.txt"
    f.write_text("rettelse: æøå «citat» — tankestreg\n", encoding="utf-8")
    assert "æøå «citat» — tankestreg" in cwa._laes_besked(_args(message_file=str(f)))


def test_de_to_veje_udelukker_hinanden():
    """Ellers ville en kalder kunne sende to beskeder og ikke vide hvilken der
    gælder.

    FØR sprang denne test over HVER gang: den slog op efter `build_parser`, og
    funktionen hedder `_parser`. `hasattr` var falsk, `pytest.skip` fyrede, og
    suiten meldte grønt. En test der aldrig har prøvet det den påstår er
    `holder: True` ved nul kontrollerede påstande — i netop den test der skulle
    bære den sætning. (Jarvis' fund, 11/9-2026.)

    Derfor kaldes `_parser` nu DIREKTE. Omdøbes den, fejler testen med
    AttributeError i stedet for at forsvinde i en overspringelse."""
    with pytest.raises(SystemExit):
        cwa._parser().parse_args([
            "--message", "a", "--message-file", "b",
            "--actor", "opus", "--origin", "x", "--approved-by", "y"])


def test_mindst_én_af_de_to_kraeves():
    """`required=True` på gruppen: en commit uden besked må ikke kunne dannes."""
    with pytest.raises(SystemExit):
        cwa._parser().parse_args([
            "--actor", "opus", "--origin", "x", "--approved-by", "y"])


def test_denne_fil_springer_intet_over():
    """Vagten mod at det sker igen — i denne fil OG i resten af suiten.

    En overspringelse er ikke en fejl; den er en test der melder grønt uden at
    have målt noget. Den eneste måde den bliver synlig er hvis nogen spørger."""
    import ast
    traeet = ast.parse(open(__file__, encoding="utf-8").read())
    kald = [n for n in ast.walk(traeet)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "skip"]
    # AST, ikke tekstsøgning: første udgave ledte efter strengen og fangede sin
    # EGEN docstring, hvor ordet står som forklaring. Instrumentet målte sig
    # selv — samme fejl som det vogter imod, ét lag ude.
    assert not kald, f"{len(kald)} overspringelse(r) i denne fil"

"""Heartbeat-levering: udskillelsens kontrakt og vagten foran leveringen.

`heartbeat_delivery.py` blev skilt ud af `heartbeat_runtime.py` (7.432 linjer)
2/10-2026, fordi de to leveringsfunktioner skulle gennem daemon-vagten i
`notification_bridge`. Foer skrev de direkte med `append_chat_message` og kunne
derfor banke paa midt i en saetning.

Testene her daekker to ting som den oprindelige testfil ikke kan se:

1. **Udskillelsens bagudkompatibilitet.** `heartbeat_runtime` skal stadig
   udstille begge navne, og de skal vaere SAMME objekt som i det nye modul —
   ellers rammer en monkeypatch i én af dem ikke den anden. Praecis den fejl
   (`from X import Y` binder en kopi) kostede tre fejlsoegninger paa ét doegn.
2. **At vagten faktisk staar foran.** En kilde-vagt, fordi leveringen ellers
   kraever hele heartbeat-policy-maskineriet: ingen af de to funktioner maa
   kalde `append_chat_message`, og begge skal kalde
   `send_session_notification` med `push=False`.
"""
from __future__ import annotations

import ast
import pathlib

from core.services import heartbeat_delivery as hd
from core.services import heartbeat_runtime as hr

KILDE = pathlib.Path("core/services/heartbeat_delivery.py")
LEVERINGSFUNKTIONER = ("_deliver_heartbeat_proposal", "_deliver_heartbeat_ping_directly")


def _funktion(navn: str) -> ast.FunctionDef:
    tree = ast.parse(KILDE.read_text())
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == navn:
            return n
    raise AssertionError(f"{navn} findes ikke i {KILDE}")


def test_re_eksporten_er_samme_objekt_ikke_en_kopi():
    """`heartbeat_runtime._deliver_...` skal VAERE funktionen fra det nye modul.

    Er de to forskellige objekter, vil en test der patcher det ene se det andet
    koere videre uaendret — og den slags fejl fejler tavst."""
    for navn in LEVERINGSFUNKTIONER:
        assert hasattr(hr, navn), f"{navn} er ikke re-eksporteret fra heartbeat_runtime"
        assert getattr(hr, navn) is getattr(hd, navn), navn


def test_ingen_af_leveringsfunktionerne_skriver_direkte_laengere():
    """Hele formaalet med flytningen. Et `append_chat_message` her ville
    omgaa daemon-vagten og kunne lande midt i Bjoerns saetning."""
    for navn in LEVERINGSFUNKTIONER:
        tekst = ast.unparse(_funktion(navn))
        assert "append_chat_message" not in tekst, (
            f"{navn} skriver stadig direkte i sessionen"
        )


def test_begge_leverer_gennem_vagten_uden_at_tilfoeje_push():
    """`push=False` er ikke pynt: ingen af de to sendte mobil-push foer, og
    flytningen maatte ikke give Bjoern to nye push-kilder."""
    for navn in LEVERINGSFUNKTIONER:
        fn = _funktion(navn)
        kald = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and (getattr(n.func, "attr", None) or getattr(n.func, "id", None))
            == "send_session_notification"
        ]
        assert len(kald) == 1, f"{navn} kalder vagten {len(kald)} gange, forventede én"
        kw = {k.arg: ast.unparse(k.value) for k in kald[0].keywords if k.arg}
        assert kw.get("push") == "False", f"{navn} ville tilfoeje en push: {kw}"
        assert "session_id" in kw, (
            f"{navn} sender ikke sin egen session med — vagten ville saa vaelge "
            "en ANDEN samtale end i dag"
        )


def test_status_laeses_med_hjaelperen_og_ikke_som_lighed_med_ok():
    """«queued» ER en succes. Et `status == "ok"` her ville genindfoere
    dobbelt-leveringen fra 23/9-2026, hvor morgenbriefen blev koeet og
    run'et laeste det som «webchat nede» og tog Discord-noedplanen."""
    for navn in LEVERINGSFUNKTIONER:
        tekst = ast.unparse(_funktion(navn))
        assert "delivery_succeeded" in tekst, f"{navn} tjekker ikke status via hjaelperen"
        assert '== \'ok\'' not in tekst, f"{navn} sammenligner status med 'ok'"


def test_ping_historikken_fejler_mod_tom_og_ikke_mod_en_undtagelse():
    """`_recent_ping_history` slaar op i heartbeat_runtime ved kaldetid (en
    modul-import ville vaere cirkulaer). Fejler opslaget, skal den give en tom
    historik — en undtagelse midt i en levering ville vaere vaerre end et
    manglende dublet-tjek."""
    import core.services.heartbeat_runtime as rigtig

    gammel = rigtig._recent_ping_history

    def _sprael(**_k):
        raise RuntimeError("DB nede")

    rigtig._recent_ping_history = _sprael
    try:
        assert hd._recent_ping_history(limit=3) == []
    finally:
        rigtig._recent_ping_history = gammel

"""Hvem må skrive ind i Bjørns aktive session — og hvem skal gennem vagten.

## Hvad der blev målt 2/10-2026

Bjørn bad om en optælling: hvor mange beskeder sendte Jarvis efter hans sidste?
Svaret var 7 på to timer, hvoraf fem var proaktive — og mødet med Line nævnt
FIRE gange i fire forskellige stemmer. I hans store session (5.521 beskeder
over tre døgn) stod 43 beskeder uden `content_json`, altså indsprøjtet uden om
en egentlig tur.

En AST-gennemgang af hele repoet fandt **to veje ind** i en aktiv session:

* **Vej A** — `notification_bridge.send_session_notification()`: 13 kilder.
  Denne vej HAR vagten (fra 24/5-2026): er sessionen aktiv og `urgent=False`,
  køes beskeden i `session_inbox` og flushes efter turen. To kilder satte
  `urgent=True` og sprang den over.
* **Vej B** — direkte `append_chat_message(role="assistant")`: fire moduler,
  HELT uden vagt. `proactivity_bridge` gjorde det med vilje og skrev det i sin
  egen docstring: «Lander i hans SIDST AKTIVE samtale».

De fire på vej B er flyttet ind gennem vagten. Antallet af filer der skriver
`role="assistant"` gik fra NI til FEM.

## Hvad denne fil vogter

Et skralde-spærre på netop de fem. En ny daemon der vil sige noget til Bjørn
skal gennem `send_session_notification`, så vagten gælder for den. Vil man
tilføje en fil her, skal man kunne skrive HVORFOR den ikke kan gå gennem vagten
— og det er svaret på det spørgsmål, ikke listen, der er pointen.
"""
from __future__ import annotations

import ast
import pathlib

#: Hvem der må skrive en assistent-besked direkte, og hvorfor netop de.
TILLADTE: dict[str, str] = {
    # De ægte svarveje: her ER beskeden Jarvis' svar på noget Bjørn skrev.
    "apps/api/jarvis_api/routes/chat.py":
        "svarvejen — beskeden er turens eget svar",
    "apps/api/jarvis_api/routes/chat_stream_v2.py":
        "den streamende svarvej — samme sag",
    "core/services/client_turn_absorb.py":
        "absorberer en tur en klient allerede har vist; ikke en indsprøjtning",
    # Vagten selv og køens udløb — de ER mekanismen.
    "core/services/notification_bridge.py":
        "vagten selv: den skriver først EFTER at have spurgt om sessionen er aktiv",
    "core/services/session_inbox.py":
        "køens udløb: flusher det vagten holdt tilbage, efter Bjørns tur",
}

RODMAPPER = ("core", "apps/api")


def _filer_der_skriver_assistent() -> dict[str, list[int]]:
    """Alle kaldesteder der kalder `append_chat_message(role="assistant")`."""
    ud: dict[str, list[int]] = {}
    for rod in RODMAPPER:
        for p in sorted(pathlib.Path(rod).rglob("*.py")):
            if "__pycache__" in str(p):
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                navn = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                if navn != "append_chat_message":
                    continue
                for kw in n.keywords:
                    if kw.arg == "role" and "assistant" in ast.unparse(kw.value):
                        ud.setdefault(str(p), []).append(n.lineno)
    return ud


def test_kun_de_fem_tilladte_skriver_direkte_i_en_session():
    """Skralde-spærren. En ny fil her betyder en ny kilde der kan banke på
    midt i en sætning — præcis det Bjørn bad om at få skilt fra."""
    fundet = _filer_der_skriver_assistent()
    nye = {f: linjer for f, linjer in fundet.items() if f not in TILLADTE}
    assert not nye, (
        "nye direkte skrivere uden daemon-vagten — send dem gennem "
        f"notification_bridge.send_session_notification() i stedet: {nye}"
    )


def test_listen_er_ikke_raadnet():
    """En tilladelse til en fil der ikke længere skriver er en tilladelse der
    stille dækker noget andet næste gang filen vokser."""
    fundet = _filer_der_skriver_assistent()
    foraeldede = sorted(set(TILLADTE) - set(fundet))
    assert not foraeldede, (
        f"disse står på listen men skriver ikke længere: {foraeldede}"
    )


def test_de_fire_flyttede_gaar_gennem_vagten():
    """De fire fra vej B, navngivet. Et nyt `append_chat_message` i en af dem
    ville ikke blive fanget af spærren ovenfor hvis nogen samtidig føjede filen
    til TILLADTE — så de nævnes her, hvor begrundelsen ikke kan skrives væk."""
    flyttede = {
        "core/services/proactivity_bridge.py": "proactivity-bridge",
        "core/services/autonomous_run_digest.py": "autonomous-run-digest",
        "core/services/heartbeat_delivery.py": "heartbeat-propose-bridge",
        "core/services/tiny_webchat_execution_pilot.py": "proactive-execution-pilot",
    }
    for sti, kilde in flyttede.items():
        kode = pathlib.Path(sti).read_text()
        assert sti not in TILLADTE, f"{sti} må ikke få en tilladelse"
        assert "send_session_notification" in kode, (
            f"{sti} går ikke gennem vagten længere"
        )
        assert kilde in kode, (
            f"{sti} mistede sit source-mærke '{kilde}' — uden det kan en "
            "levering ikke spores tilbage til sin kilde i journalen"
        )


def test_ingen_af_de_fire_tilfoejede_en_mobil_push():
    """Vagten pusher som standard. De fire pushede IKKE før, og flytningen må
    ikke give Bjørn fire nye push-kilder — det var det modsatte af formålet."""
    for sti in (
        "core/services/proactivity_bridge.py",
        "core/services/autonomous_run_digest.py",
        "core/services/heartbeat_delivery.py",
        "core/services/tiny_webchat_execution_pilot.py",
    ):
        tree = ast.parse(pathlib.Path(sti).read_text())
        kald = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and (getattr(n.func, "attr", None) or getattr(n.func, "id", None))
            == "send_session_notification"
        ]
        assert kald, f"{sti} kalder ikke vagten"
        for k in kald:
            kw = {a.arg: ast.unparse(a.value) for a in k.keywords if a.arg}
            assert kw.get("push") == "False", (
                f"{sti} ville tilføje en mobil-push: {kw}"
            )

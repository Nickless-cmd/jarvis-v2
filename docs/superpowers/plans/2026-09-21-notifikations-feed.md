# Notifikations-feed og push — implementeringsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Klokken i desk og mobil bliver et notifikations-feed med tæller, hvor man kan se, holde musen over, og godkende eller afvise direkte — med push per slags.

**Architecture:** En tynd tabel `notifikationer` hvor hver række PEGER på sin ejer (`kilde` + `ref`) frem for at kopiere ham. Ved læsning hydreres rækken hos ejeren, og en godkendelse der er afgjort et andet sted lukker sig selv. Push genbruger `notification_router` (stilletimer og kanaler findes dér); kun præference-modellen laves om fra kolonner til rækker, så den kan bære «per slags».

**Tech Stack:** Python 3.11 + FastAPI + SQLite (server), React + TypeScript + Vitest (desk), React Native + Jest (mobil).

**Spec:** `docs/superpowers/specs/2026-09-21-notifikations-feed-design.md`

## Global Constraints

- Python køres ALTID med `/opt/conda/envs/ai/bin/python`. Aldrig bart `python`.
- Commits går gennem repoets wrapper, aldrig `git commit`:
  `/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus --origin interactive --approved-by bjorn --message-file <fil> --path <sti>` — én `--path` pr. rørt sti. Brug `--message-file`, ALDRIG `--message`. `--amend` er blokeret.
- Beskeden skrives til en fil FØRST. Prosa må aldrig gennem skallen.
- Al brugervendt tekst er på dansk.
- Ingen fil over 1500 linjer; ingen core-runtime-fil over 2000.
- Rører du en fil over 2000 linjer, skal du først udskille den nærmeste naturlige enhed (Boy Scout-reglen i CLAUDE.md).
- Fejl må aldrig se ud som tomhed: kan en liste ikke hentes, siger fladen det — den viser ikke «ingen notifikationer».
- Ingen bare `except:` uden at fejlen navngives — `scripts/verify_silent_except.py` blokerer commit'en.
- Desk-tests: `cd apps/jarvis-desk && npx vitest run <sti>`. Typecheck: `npx tsc --noEmit -p tsconfig.json`.

---

### Task 1: Tabellen og lageret

**Files:**
- Modify: `core/runtime/db_schema.py` — funktionen `_ensure_notification_tables` (linje 238)
- Create: `core/services/notifikationer.py`
- Test: `tests/test_notifikationer_lager.py`

**Interfaces:**
- Consumes: `core.runtime.db.connect()`
- Produces:
  - `opret(*, user_id: str, slags: str, kilde: str, titel: str, tekst: str = "", ref: str | None = None, session_id: str | None = None) -> str` — returnerer id; ved dublet-`ref` returneres den eksisterende rækkes id uden at skrive.
  - `aabne(user_id: str, *, er_owner: bool) -> list[dict]` — rå rækker, IKKE hydreret (Task 2 lægger hydreringen ovenpå).
  - `luk(notif_id: str, udfald: str) -> None`
  - `ryd_gamle(dage: int = 7) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikationer_lager.py
from __future__ import annotations


def test_opret_og_aabne(isolated_runtime) -> None:
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="Vil du tillade bash?")
    raekker = n.aabne("bjorn", er_owner=True)
    assert [r["id"] for r in raekker] == [nid]
    assert raekker[0]["slags"] == "approval"
    assert raekker[0]["klaret"] is None


def test_samme_ref_lander_kun_een_gang(isolated_runtime) -> None:
    """En gen-udsendt haendelse maa ikke give to rakker for samme godkendelse."""
    from core.services import notifikationer as n

    a = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    b = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X igen")
    assert a == b
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_uden_ref_maa_gerne_ligne_hinanden(isolated_runtime) -> None:
    """To paamindelser er to paamindelser — kun ejede raekker afdubleres."""
    from core.services import notifikationer as n

    n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Husk mælk")
    n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Husk mælk")
    assert len(n.aabne("bjorn", er_owner=True)) == 2


def test_luk_fjerner_fra_feeden_men_beholder_raekken(isolated_runtime) -> None:
    """To-do-listen tommes i fladen; raekken bliver for at en gen-udsendt
    haendelse ikke kan genaabne noget der lige er klaret."""
    from core.services import notifikationer as n
    from core.runtime.db import connect

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    n.luk(nid, "approved")
    assert n.aabne("bjorn", er_owner=True) == []
    with connect() as conn:
        raekke = conn.execute("SELECT udfald FROM notifikationer WHERE id=?", (nid,)).fetchone()
    assert raekke[0] == "approved"
    # Og den kan ikke genaabnes af den samme ref.
    igen = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    assert igen == nid
    assert n.aabne("bjorn", er_owner=True) == []


def test_ryd_gamle_fjerner_kun_klarede(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.services import notifikationer as n
    from core.runtime.db import connect

    aaben = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Aaben")
    gammel = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Gammel")
    n.luk(gammel, "seen")
    for_laenge_siden = (datetime.now(UTC) - timedelta(days=9)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET klaret=? WHERE id=?", (for_laenge_siden, gammel))
        conn.commit()

    assert n.ryd_gamle(dage=7) == 1
    with connect() as conn:
        tilbage = [r[0] for r in conn.execute("SELECT id FROM notifikationer").fetchall()]
    assert tilbage == [aaben]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikationer_lager.py -q`
Expected: FAIL med `ModuleNotFoundError: No module named 'core.services.notifikationer'`

- [ ] **Step 3: Tilføj tabellen**

I `core/runtime/db_schema.py`, inde i `_ensure_notification_tables(conn)`, efter `delayed_notifications`-blokken:

```python
    # Notifikations-feeden (spec 2026-09-21). Raekken PEGER paa sin ejer gennem
    # kilde+ref og kopierer ham ikke: en godkendelse har sin egen livscyklus, og
    # en kopi her ville kunne staa og lyve om at noget stadig venter.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifikationer (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            slags       TEXT NOT NULL,
            kilde       TEXT NOT NULL,
            ref         TEXT,
            session_id  TEXT,
            titel       TEXT NOT NULL,
            tekst       TEXT NOT NULL DEFAULT '',
            oprettet    TEXT NOT NULL,
            klaret      TEXT,
            udfald      TEXT
        )""")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_notif_aaben "
        "ON notifikationer(user_id, klaret, oprettet)")
    # Delvist indeks: kun raekker MED en ejer afdubleres. To paamindelser uden
    # ref er to paamindelser.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_notif_ref "
        "ON notifikationer(slags, ref) WHERE ref IS NOT NULL")
```

- [ ] **Step 4: Skriv lageret**

```python
# core/services/notifikationer.py
"""Notifikations-feedens lager (spec docs/superpowers/specs/2026-09-21-...).

Raekken PEGER paa sin ejer gennem `kilde` + `ref`; den kopierer ham ikke.
Hydreringen (notifikationer_hydrering.py) slaar op hos ejeren ved laesning, og
det er DEN der lukker en raekke hvis ejeren er faerdig. Dette modul kender kun
tabellen.

Feeden er en to-do-liste: `klaret` sat = vaek fra fladen. Raekken slettes ikke
med det samme, for uden den ville en gen-udsendt haendelse kunne genaabne noget
der lige er klaret. `ryd_gamle()` fjerner dem efter en uge.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect

_log = logging.getLogger(__name__)

#: Systemraekker hoerer til ejeren — de handler om maskinen, ikke om en samtale.
SYSTEM_SLAGS = {"release", "incident", "quota"}


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def opret(*, user_id: str, slags: str, kilde: str, titel: str,
          tekst: str = "", ref: str | None = None,
          session_id: str | None = None) -> str:
    """Laeg en notifikation. Returnerer id.

    Findes samme (slags, ref) i forvejen — ogsaa en KLARET — returneres den
    eksisterende raekkes id uden at skrive. Det er hele grunden til at klarede
    raekker bliver liggende.
    """
    with connect() as conn:
        if ref is not None:
            fundet = conn.execute(
                "SELECT id FROM notifikationer WHERE slags=? AND ref=?",
                (slags, ref)).fetchone()
            if fundet:
                return str(fundet[0])
        nid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO notifikationer"
            " (id, user_id, slags, kilde, ref, session_id, titel, tekst, oprettet)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (nid, user_id, slags, kilde, ref, session_id, titel, tekst, _nu()))
        conn.commit()
        return nid


def aabne(user_id: str, *, er_owner: bool) -> list[dict[str, Any]]:
    """Aabne raekker for denne bruger. RAA — se hydreringen for den rigtige feed.

    Owner ser sine egne raekker. Systemraekker faar `user_id` = owner ved
    oprettelse, saa de er allerede med. Owner ser IKKE andre brugeres
    personlige raekker: deres indhold er krypteret og ikke ment til ejeren.
    `er_owner` er derfor ikke et filter i dag, men staar i signaturen fordi
    kaldestedet SKAL tage stilling, og fordi en fremtidig systemraekke uden
    ejer ville skulle bruge den.
    """
    del er_owner  # se docstring
    with connect() as conn:
        raekker = conn.execute(
            "SELECT id, user_id, slags, kilde, ref, session_id, titel, tekst,"
            " oprettet, klaret, udfald"
            " FROM notifikationer WHERE user_id=? AND klaret IS NULL"
            " ORDER BY oprettet DESC",
            (user_id,)).fetchall()
    kolonner = ("id", "user_id", "slags", "kilde", "ref", "session_id",
                "titel", "tekst", "oprettet", "klaret", "udfald")
    return [dict(zip(kolonner, r)) for r in raekker]


def luk(notif_id: str, udfald: str) -> None:
    """Klaret — vaek fra fladen. Raekken bliver liggende til `ryd_gamle`."""
    with connect() as conn:
        conn.execute(
            "UPDATE notifikationer SET klaret=?, udfald=? WHERE id=? AND klaret IS NULL",
            (_nu(), udfald, notif_id))
        conn.commit()


def ryd_gamle(dage: int = 7) -> int:
    """Fjern KLAREDE raekker aeldre end `dage`. Returnerer antal fjernede."""
    graense = (datetime.now(UTC) - timedelta(days=dage)).isoformat()
    with connect() as conn:
        markoer = conn.execute(
            "DELETE FROM notifikationer WHERE klaret IS NOT NULL AND klaret < ?",
            (graense,))
        conn.commit()
        return int(markoer.rowcount or 0)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikationer_lager.py -q`
Expected: PASS, 5 tests

- [ ] **Step 6: Commit**

```bash
cat > /tmp/notif1.txt <<'EOF'
feat(notifikationer): lageret — en raekke der peger paa sin ejer

Feedens tabel. Raekken baerer kilde+ref og kopierer ikke ejeren: en
godkendelse har sin egen livscyklus, og en kopi her kunne staa og lyve om at
noget stadig venter.

Feeden er en to-do-liste, men raekken slettes ikke naar den er klaret. Uden
den ville en gen-udsendt haendelse kunne genaabne noget der lige er klaret —
derfor returnerer opret() den eksisterende raekkes id ogsaa naar den er
lukket. ryd_gamle() fjerner dem efter en uge.

Det delvise unikke indeks gaelder KUN raekker med en ref: to paamindelser
uden ejer er to paamindelser, ikke en dublet.
EOF
git add -- core/runtime/db_schema.py core/services/notifikationer.py tests/test_notifikationer_lager.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif1.txt \
  --path core/runtime/db_schema.py --path core/services/notifikationer.py \
  --path tests/test_notifikationer_lager.py
```

---

### Task 2: Hydrering — designets kerne

**Files:**
- Create: `core/services/notifikationer_hydrering.py`
- Test: `tests/test_notifikationer_hydrering.py`

**Interfaces:**
- Consumes: `notifikationer.aabne()`, `notifikationer.luk()`, `approval_runtime.state(approval_id) -> dict | None`
- Produces: `feed(user_id: str, *, er_owner: bool) -> list[dict]` — hver post har `id, slags, titel, tekst, session_id, oprettet, kan_afgoere: bool, forældet: bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikationer_hydrering.py
from __future__ import annotations


def test_godkendelse_afgjort_et_andet_sted_lukker_sig_selv(isolated_runtime, monkeypatch) -> None:
    """Godkender man paa telefonen, skal desk-feeden helbrede sig selv."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1",
            titel="Vil du tillade bash?")
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "approved"})

    assert h.feed("bjorn", er_owner=True) == []
    assert n.aabne("bjorn", er_owner=True) == []


def test_ventende_godkendelse_bliver_staaende_og_kan_afgoeres(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="Gammel titel")
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "pending", "tool_name": "bash_session"})

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["kan_afgoere"] is True
    # Ejeren er sandheden: titlen kommer fra ham, ikke fra den gemte kopi.
    assert "bash_session" in poster[0]["titel"]


def test_hydrering_der_fejler_lukker_IKKE_raekken(isolated_runtime, monkeypatch) -> None:
    """En utilgaengelig ejer maa ikke se ud som en klaret opgave."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="Gemt titel")

    def sprang(_aid):
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(approval_runtime, "state", sprang)

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["titel"] == "Gemt titel"
    assert poster[0]["foraeldet"] is True
    assert poster[0]["kan_afgoere"] is False
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_egen_raekke_er_sin_egen_sandhed(isolated_runtime) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    n.opret(user_id="bjorn", slags="reminder", kilde="egen",
            titel="Husk mælk", tekst="Du bad mig minde dig om det i morges.")
    poster = h.feed("bjorn", er_owner=True)
    assert poster[0]["titel"] == "Husk mælk"
    assert poster[0]["kan_afgoere"] is False


def test_anden_brugers_raekke_naar_aldrig_owners_feed(isolated_runtime) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    n.opret(user_id="mikkel", slags="reminder", kilde="egen", titel="Mikkels ting")
    assert h.feed("bjorn", er_owner=True) == []
    assert len(h.feed("mikkel", er_owner=False)) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikationer_hydrering.py -q`
Expected: FAIL med `ModuleNotFoundError: No module named 'core.services.notifikationer_hydrering'`

- [ ] **Step 3: Skriv hydreringen**

```python
# core/services/notifikationer_hydrering.py
"""Feedens laesning — den slaar op hos EJEREN, ikke i sin egen kopi.

Det er designets kerne. En godkendelse der er afgjort paa telefonen lukker sig
selv her, og desk-feeden helbreder sig selv ved naeste laesning. En kopi ville
have det spoegelse indbygget: man kunne staa og godkende noget der var vaek.

En hydrering der FEJLER lukker ikke raekken. En utilgaengelig ejer maa ikke se
ud som en klaret opgave — saa ville en nedetid tomme feeden.
"""
from __future__ import annotations

import logging
from typing import Any

from core.services import notifikationer as _lager

_log = logging.getLogger(__name__)

#: Slags man kan svare paa direkte i fladen.
#:
#: KUN `approval`. `question` (pause_and_ask) besvares med en TEKST eller et af
#: Jarvis' egne valg, sendt som en besked i samtalen — der findes ingen
#: server-side afgoerelse at kalde. Spoergsmaals-raekken foerer i stedet hen til
#: samtalen. Specen sagde oprindeligt begge; kaldestedet sagde noget andet.
AFGOERBARE = {"approval"}


def _hydrer_approval(raekke: dict[str, Any]) -> dict[str, Any] | None:
    """None = ejeren er faerdig, luk raekken. Kaster = ejeren er utilgaengelig."""
    from core.services import approval_runtime
    kort = approval_runtime.state(str(raekke["ref"] or ""))
    if not kort:
        return None
    if str(kort.get("status") or "") != "pending":
        return None
    vaerktoej = str(kort.get("tool_name") or "et værktøj")
    return {"titel": f"Vil du tillade {vaerktoej}?",
            "tekst": str(kort.get("summary") or raekke["tekst"] or "")}


def _hydrer(raekke: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    """(felter, foraeldet). felter=None betyder «luk raekken»."""
    kilde = str(raekke["kilde"])
    if kilde == "egen":
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, False
    try:
        if kilde == "approval":
            return _hydrer_approval(raekke), False
        # `run` og `event` hydreres i Task 6, hvor deres emittere bygges. Indtil
        # da staar de paa deres gemte tekst frem for at forsvinde.
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, False
    except Exception:
        _log.warning("notifikation %s: ejeren (%s) kunne ikke naas",
                     raekke["id"], kilde, exc_info=True)
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, True


def feed(user_id: str, *, er_owner: bool) -> list[dict[str, Any]]:
    """Aabne notifikationer, hydreret hos deres ejere."""
    ud: list[dict[str, Any]] = []
    for raekke in _lager.aabne(user_id, er_owner=er_owner):
        felter, foraeldet = _hydrer(raekke)
        if felter is None:
            _lager.luk(str(raekke["id"]), "superseded")
            continue
        ud.append({
            "id": raekke["id"],
            "slags": raekke["slags"],
            "titel": felter["titel"],
            "tekst": felter["tekst"],
            "session_id": raekke["session_id"],
            "oprettet": raekke["oprettet"],
            "kan_afgoere": raekke["slags"] in AFGOERBARE and not foraeldet,
            "foraeldet": foraeldet,
        })
    return ud
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikationer_hydrering.py -q`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
cat > /tmp/notif2.txt <<'EOF'
feat(notifikationer): hydreringen — feeden laeser hos ejeren, ikke i sin kopi

Designets kerne. En godkendelse der er afgjort paa telefonen lukker sig selv
ved naeste laesning, og desk-feeden helbreder sig selv. En kopi ville have det
spoegelse indbygget: man kunne staa og godkende noget der var vaek.

Den vigtigste enkeltregel er at en hydrering der FEJLER ikke lukker raekken.
En utilgaengelig ejer maa ikke se ud som en klaret opgave — saa ville en
nedetid tomme feeden. Raekken viser i stedet sin gemte tekst og markeres
foraeldet, og den kan ikke afgoeres imens.
EOF
git add -- core/services/notifikationer_hydrering.py tests/test_notifikationer_hydrering.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif2.txt \
  --path core/services/notifikationer_hydrering.py \
  --path tests/test_notifikationer_hydrering.py
```

---

### Task 3: Hændelses-familien — så live-vejen ikke er stum

**Files:**
- Modify: `core/eventbus/events.py` — `ALLOWED_EVENT_FAMILIES` (linje 5)
- Modify: `core/services/notifikationer.py` — publish i `opret`/`luk`
- Test: `tests/test_notifikationer_haendelser.py`

**Interfaces:**
- Consumes: `core.eventbus.bus.event_bus.publish(kind, payload)`
- Produces: hændelserne `notifikation.ny` og `notifikation.klaret` med payload `{"id": str, "user_id": str, "slags": str}`

**Hvorfor det er sit eget trin:** en familie der ikke står i `ALLOWED_EVENT_FAMILIES` får hvert `publish` til at kaste, og fejlen bliver slugt af kaldestedet. Det er sket mindst fem gange i dette repo (prompt 4/9, tool_discovery 6/9, r2_5_gate 19/9, app 20/9). Familien registreres og efterprøves FØR nogen bygger oven på den.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikationer_haendelser.py
from __future__ import annotations


def test_familien_er_registreret(isolated_runtime) -> None:
    """Femte gang samme moenster: en uregistreret familie faar publish til at
    kaste, kaldestedet sluger det, og hverken feed eller klient ser noget."""
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES
    assert "notifikation" in ALLOWED_EVENT_FAMILIES


def test_opret_lander_paa_bussen(isolated_runtime) -> None:
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    event_bus.flush()
    with connect() as conn:
        raekker = conn.execute(
            "SELECT payload_json FROM events WHERE kind=?",
            ("notifikation.ny",)).fetchall()
    assert any(nid in r[0] for r in raekker)


def test_luk_lander_paa_bussen(isolated_runtime) -> None:
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="X")
    n.luk(nid, "seen")
    event_bus.flush()
    with connect() as conn:
        raekker = conn.execute(
            "SELECT payload_json FROM events WHERE kind=?",
            ("notifikation.klaret",)).fetchall()
    assert any(nid in r[0] for r in raekker)


def test_dublet_udsender_ikke_igen(isolated_runtime) -> None:
    """Ellers ville en gen-udsendt haendelse faa klokken til at blinke igen."""
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    event_bus.flush()
    with connect() as conn:
        antal = conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", ("notifikation.ny",)).fetchone()[0]
    assert antal == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikationer_haendelser.py -q`
Expected: FAIL på `test_familien_er_registreret` med `AssertionError`

- [ ] **Step 3: Registrér familien**

I `core/eventbus/events.py`, i `ALLOWED_EVENT_FAMILIES`, efter linjen med `"composite",`:

```python
    # ── 21. sep 2026: notifikations-feeden (spec 2026-09-21). Femte gang samme
    #    moenster ville have ramt: uden denne linje kaster hvert publish, og
    #    kaldestedet sluger det — klokken ville staa stille uden at noget fejlede.
    "notifikation",      # notifikation.{ny,klaret} — feedens live-vej til desk og mobil
```

- [ ] **Step 4: Udsend fra lageret**

I `core/services/notifikationer.py`, tilføj øverst efter `_log`:

```python
def _udsend(slags_haendelse: str, nid: str, user_id: str, slags: str) -> None:
    """Live-vejen til klokken. Fejler den, skal FEEDEN stadig virke — men den
    skal siges hoejt, ikke sluges: en tavs bus er praecis den fejl der har
    ramt dette repo fem gange."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"notifikation.{slags_haendelse}",
                          {"id": nid, "user_id": user_id, "slags": slags})
    except Exception:
        _log.warning("notifikation.%s kunne ikke udsendes for %s",
                     slags_haendelse, nid, exc_info=True)
```

I `opret()`, ERSTAT `return str(fundet[0])` og den afsluttende `return nid`:

```python
            if fundet:
                # Dublet: ingen ny haendelse. Ellers ville en gen-udsendt
                # haendelse faa klokken til at blinke for noget gammelt.
                return str(fundet[0])
```

og efter `conn.commit()`:

```python
        conn.commit()
    _udsend("ny", nid, user_id, slags)
    return nid
```

I `luk()`, efter `conn.commit()`:

```python
        raekke = conn.execute(
            "SELECT user_id, slags FROM notifikationer WHERE id=?", (notif_id,)).fetchone()
    if raekke:
        _udsend("klaret", notif_id, str(raekke[0]), str(raekke[1]))
```

Bemærk: `_udsend` kaldes UDEN for `with connect()`, så bussens egen skrivning ikke sidder og venter på vores forbindelse.

- [ ] **Step 5: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikationer_haendelser.py tests/test_notifikationer_lager.py -q`
Expected: PASS, 9 tests

- [ ] **Step 6: Commit**

```bash
cat > /tmp/notif3.txt <<'EOF'
feat(notifikationer): live-vejen — og familien registreret FOERST

`notifikation.{ny,klaret}` paa bussen, saa klokken kan opdatere sig uden at
man gaar ud og ind af appen.

Familien er registreret i ALLOWED_EVENT_FAMILIES i samme commit, og det er
hele pointen med at det er sit eget trin. En uregistreret familie faar hvert
publish til at kaste, og kaldestedet sluger det: klokken ville staa stille
uden at noget som helst fejlede. Det er sket mindst fem gange i dette repo —
prompt 4/9, tool_discovery 6/9, r2_5_gate 19/9, app 20/9. En test hoelder nu
fast i at familien staar der.

En dublet udsender ikke igen. Ellers ville en gen-udsendt haendelse faa
klokken til at blinke for noget gammelt.
EOF
git add -- core/eventbus/events.py core/services/notifikationer.py tests/test_notifikationer_haendelser.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif3.txt \
  --path core/eventbus/events.py --path core/services/notifikationer.py \
  --path tests/test_notifikationer_haendelser.py
```

---

### Task 4: Ruterne

**Files:**
- Create: `apps/api/jarvis_api/routes/notifikationer.py`
- Modify: `apps/api/jarvis_api/app.py` — import + `include_router`
- Test: `tests/test_notifikationer_rute.py`

**Interfaces:**
- Consumes: `notifikationer_hydrering.feed()`, `notifikationer.luk()`, `approval_runtime.decide(approval_id, approved=..., answered_by=...)`
- Produces:
  - `GET /notifikationer` → `{"poster": [...], "antal": int}`
  - `POST /notifikationer/{id}/afgoer` body `{"approved": bool}` → `{"ok": bool, "fejl": str}`
  - `POST /notifikationer/{id}/set` → `{"ok": bool}`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikationer_rute.py
from __future__ import annotations

import pytest


@pytest.fixture()
def klient(isolated_runtime, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api.jarvis_api.routes import notifikationer as rute

    monkeypatch.setattr(rute, "_nuvaerende_bruger", lambda: ("bjorn", True))
    app = FastAPI()
    app.include_router(rute.router)
    return TestClient(app)


def test_feed_returnerer_aabne_med_antal(klient, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Husk mælk")
    monkeypatch.setattr(approval_runtime, "state", lambda aid: None)

    svar = klient.get("/notifikationer").json()
    assert svar["antal"] == 1
    assert svar["poster"][0]["titel"] == "Husk mælk"


def test_afgoer_en_godkendelse_kalder_decide(klient, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    kaldt = {}
    monkeypatch.setattr(approval_runtime, "decide",
                        lambda aid, **kw: kaldt.update({"id": aid, **kw}) or {"ok": True})

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True})
    assert svar.json()["ok"] is True
    assert kaldt["id"] == "a-1"
    assert kaldt["approved"] is True
    assert kaldt["answered_by"] == "bjorn"


def test_ruten_lukker_IKKE_raekken_selv(klient, monkeypatch) -> None:
    """Hydreringen bestemmer. Lukkede ruten ogsaa, kunne den lukke en raekke
    hvis ejer stadig venter — og saa var kortet vaek uden at vaere besvaret."""
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    monkeypatch.setattr(approval_runtime, "decide", lambda aid, **kw: {"ok": True})
    klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True})
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_afgoer_afviser_en_raekke_der_ikke_kan_afgoeres(klient) -> None:
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="X")
    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False
    assert "kan ikke" in svar["fejl"]


def test_afgoer_afviser_en_anden_brugers_raekke(klient, monkeypatch) -> None:
    """Ellers kunne et id gaettet fra en anden bruger afgoeres herfra."""
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="mikkel", slags="approval", kilde="approval", ref="a-9", titel="X")
    monkeypatch.setattr(approval_runtime, "decide",
                        lambda aid, **kw: pytest.fail("maatte ikke kaldes"))
    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False


def test_set_lukker_en_uden_handling(klient) -> None:
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="X")
    assert klient.post(f"/notifikationer/{nid}/set").json()["ok"] is True
    assert n.aabne("bjorn", er_owner=True) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikationer_rute.py -q`
Expected: FAIL med `ModuleNotFoundError: No module named 'apps.api.jarvis_api.routes.notifikationer'`

- [ ] **Step 3: Skriv ruten**

```python
# apps/api/jarvis_api/routes/notifikationer.py
"""Notifikations-feeden. Scoper til den auth'ede bruger.

Ruten LUKKER ikke selv en raekke naar den er afgjort — det goer hydreringen
ved naeste laesning. Ét sted der bestemmer: lukkede ruten ogsaa, kunne den
lukke en raekke hvis ejer stadig venter, og saa var kortet vaek uden at vaere
besvaret.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from core.services import notifikationer as _lager
from core.services import notifikationer_hydrering as _hyd

router = APIRouter(prefix="/notifikationer", tags=["notifikationer"])


class AfgoerBody(BaseModel):
    approved: bool


def _nuvaerende_bruger() -> tuple[str | None, bool]:
    """(user_id, er_owner)."""
    from core.identity.workspace_context import current_user_id, current_user_role
    return current_user_id() or None, (current_user_role() or "") == "owner"


def _min_raekke(notif_id: str, user_id: str) -> dict | None:
    """Raekken — kun hvis den er brugerens egen. Et gaettet id fra en anden
    bruger maa ikke kunne afgoeres herfra."""
    for r in _lager.aabne(user_id, er_owner=False):
        if str(r["id"]) == notif_id:
            return r
    return None


@router.get("")
async def feed() -> dict:
    uid, er_owner = _nuvaerende_bruger()
    if not uid:
        return {"poster": [], "antal": 0}
    poster = _hyd.feed(uid, er_owner=er_owner)
    return {"poster": poster, "antal": len(poster)}


@router.post("/{notif_id}/afgoer")
async def afgoer(notif_id: str, body: AfgoerBody) -> dict:
    uid, _ = _nuvaerende_bruger()
    if not uid:
        return {"ok": False, "fejl": "Ikke logget ind."}
    raekke = _min_raekke(notif_id, uid)
    if raekke is None:
        return {"ok": False, "fejl": "Notifikationen findes ikke."}
    slags = str(raekke["slags"])
    if slags not in _hyd.AFGOERBARE:
        # Herunder `question`: et pause_and_ask besvares med en tekst i
        # samtalen, ikke med ja/nej. Fladen sender dig derhen i stedet.
        return {"ok": False, "fejl": "Den slags kan ikke godkendes eller afvises."}
    ref = str(raekke["ref"] or "")
    try:
        from core.services import approval_runtime
        approval_runtime.decide(ref, approved=body.approved, answered_by=uid)
    except Exception as fejl:
        return {"ok": False, "fejl": f"Svaret kunne ikke sendes: {fejl}"}
    # Raekken lukkes af hydreringen ved naeste laesning — ikke her.
    return {"ok": True, "fejl": ""}


@router.post("/{notif_id}/set")
async def set_(notif_id: str) -> dict:
    uid, _ = _nuvaerende_bruger()
    if not uid:
        return {"ok": False}
    if _min_raekke(notif_id, uid) is None:
        return {"ok": False}
    _lager.luk(notif_id, "seen")
    return {"ok": True}
```

- [ ] **Step 4: Registrér ruten**

I `apps/api/jarvis_api/app.py`, ved siden af de andre `include_router`-kald (omkring linje 842):

```python
    from apps.api.jarvis_api.routes.notifikationer import router as notifikationer_router
    app.include_router(notifikationer_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikationer_rute.py -q`
Expected: PASS, 6 tests

- [ ] **Step 6: Efterprøv at ruten er registreret i den rigtige app**

Run:
```bash
/opt/conda/envs/ai/bin/python -c "
from apps.api.jarvis_api.app import app
stier = sorted({r.path for r in app.routes if 'notifikation' in r.path})
print(stier)
assert '/notifikationer' in stier, 'ruten er ikke registreret'
"
```
Expected: listen indeholder `/notifikationer`, `/notifikationer/{notif_id}/afgoer`, `/notifikationer/{notif_id}/set`

Dette trin er ikke pynt: en rute der virker i sin egen test og ikke er hængt på appen er præcis det mønster der har kostet mest tid i dette repo.

- [ ] **Step 7: Commit**

```bash
cat > /tmp/notif4.txt <<'EOF'
feat(api): notifikations-ruterne — og ruten lukker ikke raekken selv

GET /notifikationer, POST /{id}/afgoer og POST /{id}/set.

To ting er med vilje:

Ruten lukker IKKE raekken naar den er afgjort. Det goer hydreringen ved naeste
laesning. Lukkede ruten ogsaa, kunne den lukke en raekke hvis ejer stadig
venter, og saa var kortet vaek uden at vaere besvaret. Ét sted bestemmer.

`approval` og `question` gaar ad HVER SIN vej. De ligner hinanden i fladen,
men er ikke samme mekanisme — en rute der kaldte decide() for begge ville
svare det forkerte sted.

Og en raekke kan kun afgoeres af sin egen ejer: et gaettet id fra en anden
bruger naar ikke igennem.

Efterproevet at ruten faktisk er haengt paa app'en, ikke kun paa sin egen
test-app.
EOF
git add -- apps/api/jarvis_api/routes/notifikationer.py apps/api/jarvis_api/app.py tests/test_notifikationer_rute.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif4.txt \
  --path apps/api/jarvis_api/routes/notifikationer.py --path apps/api/jarvis_api/app.py \
  --path tests/test_notifikationer_rute.py
```

---

### Task 5: Push-valg per slags

**Files:**
- Modify: `core/runtime/db_schema.py` — `_ensure_notification_tables`
- Create: `core/services/notifikations_valg.py`
- Modify: `core/services/notification_router.py` — læs rækker med kolonner som fald-tilbage
- Test: `tests/test_notifikations_valg.py`

**Interfaces:**
- Consumes: `core.runtime.db.connect()`
- Produces:
  - `kanal_for(user_id: str, slags: str) -> str` — `auto | mobile | desktop | push | ingen`
  - `saet(user_id: str, slags: str, kanal: str) -> None`
  - `alle(user_id: str) -> dict[str, str]`
  - `migrer_kolonner() -> int` — antal overførte valg

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikations_valg.py
from __future__ import annotations


def test_standard_er_tavs_undtagen_det_der_haster(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    assert v.kanal_for("bjorn", "approval") == "auto"
    assert v.kanal_for("bjorn", "question") == "auto"
    assert v.kanal_for("bjorn", "run_failed") == "auto"
    assert v.kanal_for("bjorn", "release") == "ingen"
    assert v.kanal_for("bjorn", "run_done") == "ingen"


def test_eget_valg_slaar_standarden(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    v.saet("bjorn", "release", "push")
    assert v.kanal_for("bjorn", "release") == "push"
    assert v.alle("bjorn")["release"] == "push"


def test_migreringen_baerer_de_fem_kolonner_over(isolated_runtime) -> None:
    """En halvvejs migreret base maa ikke tabe nogens valg."""
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder, briefing)"
            " VALUES (?,?,?,?)", ("bjorn", "auto", "mobile", "ingen"))
        conn.commit()

    assert v.migrer_kolonner() == 2
    assert v.kanal_for("bjorn", "reminder") == "mobile"
    assert v.kanal_for("bjorn", "briefing") == "ingen"


def test_migreringen_overskriver_ikke_et_nyere_valg(isolated_runtime) -> None:
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder)"
            " VALUES (?,?,?)", ("bjorn", "auto", "mobile"))
        conn.commit()
    v.saet("bjorn", "reminder", "ingen")
    v.migrer_kolonner()
    assert v.kanal_for("bjorn", "reminder") == "ingen"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_valg.py -q`
Expected: FAIL med `ModuleNotFoundError: No module named 'core.services.notifikations_valg'`

- [ ] **Step 3: Tilføj tabellen**

I `core/runtime/db_schema.py`, i `_ensure_notification_tables(conn)`, efter `notifikationer`-blokken fra Task 1:

```python
    # Push-valg PER SLAGS. notification_preferences har én kolonne pr. type og
    # kan ikke baere en ny slags uden en ny kolonne hver gang.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifikations_valg (
            user_id TEXT NOT NULL,
            slags   TEXT NOT NULL,
            kanal   TEXT NOT NULL,
            PRIMARY KEY (user_id, slags)
        )""")
```

- [ ] **Step 4: Skriv valg-modulet**

```python
# core/services/notifikations_valg.py
"""Push-valg per slags (spec 2026-09-21).

`notification_preferences` har én kolonne pr. type (briefing, reminder, …) og
kan ikke baere en ny slags uden en ny kolonne hver gang. Valgene bor nu i
raekker. Kolonnerne bliver staaende indtil alle kaldesteder laeser den nye
tabel, og `notification_router` laeser raekker MED kolonnerne som fald-tilbage,
saa en halvvejs migreret base ikke taber nogens valg.
"""
from __future__ import annotations

import logging

from core.runtime.db import connect

_log = logging.getLogger(__name__)

GYLDIGE_KANALER = {"auto", "mobile", "desktop", "push", "ingen"}

#: Standard naar brugeren ikke har valgt. Kun det der HASTER pusher.
#: «auto» lader notification_router vaelge kanal efter enhed og stilletimer.
STANDARD: dict[str, str] = {
    "approval": "auto",
    "question": "auto",
    "run_failed": "auto",
    "run_done": "ingen",
    "briefing": "ingen",
    "reminder": "ingen",
    "reach_out": "ingen",
    "initiative": "ingen",
    "release": "ingen",
    "incident": "ingen",
    "quota": "ingen",
}

#: Kolonnenavn i notification_preferences -> slags i den nye tabel.
_GAMLE_KOLONNER = {
    "briefing": "briefing",
    "reminder": "reminder",
    "reach_out": "reach_out",
    "team_invite": "initiative",
    "wakeup": "initiative",
}


def kanal_for(user_id: str, slags: str) -> str:
    with connect() as conn:
        raekke = conn.execute(
            "SELECT kanal FROM notifikations_valg WHERE user_id=? AND slags=?",
            (user_id, slags)).fetchone()
    if raekke:
        return str(raekke[0])
    return STANDARD.get(slags, "ingen")


def saet(user_id: str, slags: str, kanal: str) -> None:
    if kanal not in GYLDIGE_KANALER:
        raise ValueError(f"ukendt kanal: {kanal}")
    with connect() as conn:
        conn.execute(
            "INSERT INTO notifikations_valg (user_id, slags, kanal) VALUES (?,?,?)"
            " ON CONFLICT(user_id, slags) DO UPDATE SET kanal=excluded.kanal",
            (user_id, slags, kanal))
        conn.commit()


def alle(user_id: str) -> dict[str, str]:
    """Alle slags med brugerens valg lagt oven paa standarden."""
    ud = dict(STANDARD)
    with connect() as conn:
        for slags, kanal in conn.execute(
                "SELECT slags, kanal FROM notifikations_valg WHERE user_id=?",
                (user_id,)).fetchall():
            ud[str(slags)] = str(kanal)
    return ud


def migrer_kolonner() -> int:
    """Baer de gamle kolonner over som raekker. Idempotent.

    `INSERT OR IGNORE`: har brugeren allerede valgt noget nyere for den slags,
    roeres det ikke. Ellers ville en genstart rulle et valg tilbage.
    """
    flyttet = 0
    with connect() as conn:
        try:
            raekker = conn.execute(
                "SELECT user_id, " + ", ".join(_GAMLE_KOLONNER) +
                " FROM notification_preferences").fetchall()
        except Exception:
            _log.warning("notification_preferences kunne ikke laeses; "
                         "ingen valg migreret", exc_info=True)
            return 0
        for raekke in raekker:
            user_id = str(raekke[0])
            for i, slags in enumerate(_GAMLE_KOLONNER.values(), start=1):
                vaerdi = raekke[i]
                if not vaerdi:
                    continue
                markoer = conn.execute(
                    "INSERT OR IGNORE INTO notifikations_valg (user_id, slags, kanal)"
                    " VALUES (?,?,?)", (user_id, slags, str(vaerdi)))
                flyttet += int(markoer.rowcount or 0)
        conn.commit()
    return flyttet
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_valg.py -q`
Expected: PASS, 4 tests

- [ ] **Step 6: Lad routeren læse rækkerne**

I `core/services/notification_router.py`, i `_route_proactive_notification_impl`, dér hvor brugerens kanal slås op, læg rækkerne FØR kolonnerne:

I `_route_proactive_notification_impl`, ERSTAT linjen
`    channel = resolve_channel(prefs, notification_type)` (linje 224) med:

```python
    # Raekker foerst, kolonner som fald-tilbage. En halvvejs migreret base maa
    # ikke tabe nogens valg (spec 2026-09-21).
    from core.services.notifikations_valg import kanal_for as _kanal_for
    valgt = _kanal_for(uid, notification_type)
    if valgt == "ingen":
        # Brugeren har selv slaaet den slags fra. Returformen er den samme som
        # alle andre udgange — kalderne laeser `delivered` og `channel`, og en
        # ny form her ville braekke dem.
        return {"delivered": False, "channel": "fravalgt", "target": uid,
                "fallback_used": False}
    channel = valgt if valgt != "auto" else resolve_channel(prefs, notification_type)
```

Bemærk at `uid` (den rensede) bruges, ikke `user_id` — det er den variabel
funktionen selv arbejder videre med.

- [ ] **Step 7: Kør hele notifikations-suiten**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_valg.py tests/test_notification_router.py -q`
Expected: PASS — ingen eksisterende router-test må bryde

- [ ] **Step 8: Commit**

```bash
cat > /tmp/notif5.txt <<'EOF'
feat(notifikationer): push-valg per slags, med kolonnerne som fald-tilbage

notification_preferences har én kolonne pr. type og kan ikke baere en ny slags
uden en ny kolonne hver gang. Valgene bor nu i raekker.

Kolonnerne bliver staaende, og routeren laeser raekker MED dem som
fald-tilbage: en halvvejs migreret base maa ikke tabe nogens valg. Og
migreringen bruger INSERT OR IGNORE, saa en genstart ikke ruller et nyere valg
tilbage.

Standard: kun approval, question og run_failed naar telefonen. Resten staar
stille i feeden til man selv kigger — et push skal betyde at noget venter.
EOF
git add -- core/runtime/db_schema.py core/services/notifikations_valg.py core/services/notification_router.py tests/test_notifikations_valg.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif5.txt \
  --path core/runtime/db_schema.py --path core/services/notifikations_valg.py \
  --path core/services/notification_router.py --path tests/test_notifikations_valg.py
```

---

### Task 6: Emitterne — hvor notifikationer fødes

**Files:**
- Create: `core/services/notifikations_emittere.py`
- Modify: `core/services/notifikationer_hydrering.py` — rigtig `run`- og `event`-hydrering
- Test: `tests/test_notifikations_emittere.py`

**Interfaces:**
- Consumes: `notifikationer.opret()`, `notifikations_valg.kanal_for()`, `notification_router.route_proactive_notification()`
- Produces:
  - `paa_godkendelse(approval_id: str, *, user_id: str, session_id: str, vaerktoej: str) -> None`
  - `paa_koersel_fejlet(run_id: str, *, user_id: str, session_id: str, titel: str) -> None`
  - `paa_koersel_faerdig(run_id: str, *, user_id: str, session_id: str, titel: str) -> None`
  - `fra_jarvis(user_id: str, slags: str, titel: str, tekst: str = "") -> None`
  - `system(slags: str, titel: str, tekst: str = "") -> None` — finder owner selv

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikations_emittere.py
from __future__ import annotations


def test_godkendelse_giver_en_raekke_OG_et_push(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e
    from core.services import notification_router

    sendt = []
    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: sendt.append((a, kw)) or {"ok": True})

    e.paa_godkendelse("a-1", user_id="bjorn", session_id="s-1", vaerktoej="bash_session")

    raekker = n.aabne("bjorn", er_owner=True)
    assert len(raekker) == 1
    assert raekker[0]["ref"] == "a-1"
    assert sendt, "en godkendelse skal ogsaa naa telefonen"


def test_faerdigt_svar_giver_en_raekke_men_INTET_push(isolated_runtime, monkeypatch) -> None:
    """Standarden er at kun det der haster afbryder."""
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e
    from core.services import notification_router

    sendt = []
    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: sendt.append(a) or {"ok": True})

    e.paa_koersel_faerdig("r-1", user_id="bjorn", session_id="s-1", titel="Kæledyret")
    assert len(n.aabne("bjorn", er_owner=True)) == 1
    assert sendt == []


def test_eget_valg_kan_taende_for_pushet(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikations_emittere as e
    from core.services import notifikations_valg as v
    from core.services import notification_router

    sendt = []
    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: sendt.append(a) or {"ok": True})
    v.saet("bjorn", "run_done", "push")

    e.paa_koersel_faerdig("r-1", user_id="bjorn", session_id="s-1", titel="Kæledyret")
    assert sendt, "har man selv taendt for den slags, skal den pushe"


def test_systemraekke_havner_hos_owner(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e

    monkeypatch.setattr(e, "_owner_id", lambda: "bjorn")
    e.system("release", "Ny version 0.6.70 er klar")
    raekker = n.aabne("bjorn", er_owner=True)
    assert len(raekker) == 1
    assert raekker[0]["slags"] == "release"


def test_push_der_fejler_maa_ikke_tabe_raekken(isolated_runtime, monkeypatch) -> None:
    """Feeden er den paalidelige del. Telefonen er den upaalidelige."""
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e
    from core.services import notification_router

    def sprang(*a, **kw):
        raise RuntimeError("ingen forbindelse")
    monkeypatch.setattr(notification_router, "route_proactive_notification", sprang)

    e.paa_godkendelse("a-1", user_id="bjorn", session_id="s-1", vaerktoej="bash_session")
    assert len(n.aabne("bjorn", er_owner=True)) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_emittere.py -q`
Expected: FAIL med `ModuleNotFoundError: No module named 'core.services.notifikations_emittere'`

- [ ] **Step 3: Skriv emitterne**

```python
# core/services/notifikations_emittere.py
"""Hvor notifikationer foedes (spec 2026-09-21).

Ét sted der baade laegger raekken og — hvis brugerens valg siger det — sender
pushet. Uden det ville hver kilde skulle huske begge dele, og den ene ville
blive glemt.

Feeden er den PAALIDELIGE del; telefonen er den upaalidelige. Et push der
fejler maa aldrig tage raekken med sig.
"""
from __future__ import annotations

import logging

from core.services import notifikationer as _lager
from core.services import notifikations_valg as _valg

_log = logging.getLogger(__name__)


def _owner_id() -> str | None:
    """Ejeren. Systemraekker hoerer til ham — de handler om maskinen."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            raekke = conn.execute(
                "SELECT user_id FROM users WHERE role='owner' LIMIT 1").fetchone()
        return str(raekke[0]) if raekke else None
    except Exception:
        _log.warning("kunne ikke finde owner til en systemnotifikation", exc_info=True)
        return None


def _maaske_push(user_id: str, slags: str, titel: str, tekst: str) -> None:
    kanal = _valg.kanal_for(user_id, slags)
    if kanal == "ingen":
        return
    try:
        from core.services import notification_router
        notification_router.route_proactive_notification(
            user_id, slags, {"titel": titel, "tekst": tekst},
            importance="high" if slags in ("approval", "question") else "normal")
    except Exception:
        # Raekken staar allerede i feeden. Et brudt push maa ikke tage den med.
        _log.warning("push for %s til %s fejlede", slags, user_id, exc_info=True)


def _foed(*, user_id: str, slags: str, kilde: str, titel: str,
          tekst: str = "", ref: str | None = None,
          session_id: str | None = None) -> None:
    _lager.opret(user_id=user_id, slags=slags, kilde=kilde, titel=titel,
                 tekst=tekst, ref=ref, session_id=session_id)
    _maaske_push(user_id, slags, titel, tekst)


def paa_godkendelse(approval_id: str, *, user_id: str, session_id: str,
                    vaerktoej: str) -> None:
    _foed(user_id=user_id, slags="approval", kilde="approval", ref=approval_id,
          session_id=session_id, titel=f"Vil du tillade {vaerktoej}?")


def paa_koersel_fejlet(run_id: str, *, user_id: str, session_id: str,
                       titel: str) -> None:
    _foed(user_id=user_id, slags="run_failed", kilde="run", ref=run_id,
          session_id=session_id, titel=f"Noget gik galt i «{titel}»")


def paa_koersel_faerdig(run_id: str, *, user_id: str, session_id: str,
                        titel: str) -> None:
    _foed(user_id=user_id, slags="run_done", kilde="run", ref=run_id,
          session_id=session_id, titel=f"Svar klar i «{titel}»")


def fra_jarvis(user_id: str, slags: str, titel: str, tekst: str = "") -> None:
    """Det Jarvis selv sender. Har ingen ejer — raekken ER sandheden."""
    _foed(user_id=user_id, slags=slags, kilde="egen", titel=titel, tekst=tekst)


def system(slags: str, titel: str, tekst: str = "") -> None:
    uid = _owner_id()
    if not uid:
        return
    _foed(user_id=uid, slags=slags, kilde="egen", titel=titel, tekst=tekst)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_emittere.py -q`
Expected: PASS, 5 tests

- [ ] **Step 5: Kobl den rigtige run-hydrering på**

I `core/services/notifikationer_hydrering.py`, ERSTAT kommentaren om at `run` og `event` hydreres senere:

Der FINDES ikke et opslag på en kørsels status i dag — `core/runtime/opmaerksomhed.py:153`
læser `SELECT status, error FROM visible_runs WHERE run_id = ?` direkte. Læg
et opslag hvor statussen SKRIVES, så læsning og skrivning bor sammen, i
`core/services/visible_runs_sections/run_finalization.py` ved siden af
`finalize_run`:

```python
def status_for_run(run_id: str) -> str:
    """Koerslens status, eller "" hvis den ikke findes.

    Laesningen laa foer inline i opmaerksomhed.py. Feeden skal ogsaa bruge
    den, og to steder der laeser samme tabel paa hver sin maade er den slags
    der skrider fra hinanden.
    """
    from core.runtime.db import connect
    with connect() as conn:
        raekke = conn.execute(
            "SELECT status FROM visible_runs WHERE run_id = ?", (run_id,)).fetchone()
    return str(raekke[0] or "") if raekke else ""
```

og hydreringen:

```python
def _hydrer_run(raekke: dict[str, Any]) -> dict[str, Any] | None:
    """None = koerslen er ikke laengere i den tilstand der skabte raekken."""
    from core.services.visible_runs_sections.run_finalization import status_for_run
    tilstand = status_for_run(str(raekke["ref"] or ""))
    slags = str(raekke["slags"])
    if slags == "run_failed" and tilstand not in ("failed", "interrupted"):
        return None
    if slags == "run_done" and tilstand not in ("completed", "done"):
        return None
    return {"titel": raekke["titel"], "tekst": raekke["tekst"]}
```

og i `_hydrer`, efter `approval`-grenen:

```python
        if kilde == "run":
            return _hydrer_run(raekke), False
```

- [ ] **Step 6: Test at en genåbnet kørsel lukker rækken**

Føj til `tests/test_notifikations_emittere.py`:

```python
def test_faerdig_koersel_der_koerer_igen_lukker_raekken(isolated_runtime, monkeypatch) -> None:
    """Startede den forfra, er «svar klar» ikke sandt laengere."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import notifikations_emittere as e
    from core.services import notification_router
    from core.services.visible_runs_sections import run_finalization

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    e.paa_koersel_faerdig("r-1", user_id="bjorn", session_id="s-1", titel="X")
    monkeypatch.setattr(run_finalization, "status_for_run", lambda rid: "running")

    assert h.feed("bjorn", er_owner=True) == []
    assert n.aabne("bjorn", er_owner=True) == []
```

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_emittere.py -q`
Expected: PASS, 6 tests

- [ ] **Step 7: Commit**

```bash
cat > /tmp/notif6.txt <<'EOF'
feat(notifikationer): emitterne — ét sted der baade laegger raekken og pusher

Uden dem skulle hver kilde huske begge dele, og den ene ville blive glemt.

Feeden er den PAALIDELIGE del; telefonen er den upaalidelige. Et push der
fejler tager aldrig raekken med sig — den staar der stadig naar man kigger.

Run-hydreringen er koblet paa: en «svar klar»-raekke lukker sig selv hvis
koerslen er startet forfra. Ellers stod der en paastand om noget der ikke var
sandt laengere.
EOF
git add -- core/services/notifikations_emittere.py core/services/notifikationer_hydrering.py core/services/visible_runs_sections/run_finalization.py tests/test_notifikations_emittere.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif6.txt \
  --path core/services/notifikations_emittere.py \
  --path core/services/notifikationer_hydrering.py \
  --path core/services/visible_runs_sections/run_finalization.py \
  --path tests/test_notifikations_emittere.py
```

---

### Task 7: Kobl emitterne på — afstemning frem for fødsels-kroge

**Files:**
- Modify: `core/services/notifikations_emittere.py` — `afstem_godkendelser()`
- Modify: `core/services/notifikationer_hydrering.py` — kald afstemningen i `feed()`
- Modify: `core/services/visible_runs_sections/run_finalization.py` — `finalize_in_flight`
- Modify: `apps/api/jarvis_api/routes/app_release.py`
- Test: `tests/test_notifikations_kobling.py`

**Interfaces:**
- Consumes: `approval_runtime.pending_for_owner(user_id)`, `notifikations_emittere.*`
- Produces: `afstem_godkendelser(user_id: str) -> int` — antal nye rækker

**Hvorfor afstemning og ikke en krog ved fødslen:** godkendelses-kortet fødes
TO steder i `core/services/visible_runs.py` (linje 2228 og 4601) — en fil på
7.290 linjer, hvor Boy Scout-reglen kræver en udskilning før man rører den.
Vigtigere: en overset krog betyder en notifikation der ALDRIG findes, og det
ville man ikke opdage. Afstemningen kan ikke glemme noget: den spørger
`pending_for_owner` hver gang feeden læses, og lægger en række for det der
mangler. Den virker også for godkendelser der fandtes før feeden blev bygget.

Den blokerende vej er i forvejen dækket uafhængigt af feeden: desk poller
`/chat/approvals/pending` hvert 4. sekund og rejser selve godkendelseskortet.
Feeden er en ANDEN flade på samme sandhed, og et par sekunders forsinkelse dér
koster ikke noget.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikations_kobling.py
from __future__ import annotations

import inspect


def test_afstemning_laegger_en_raekke_for_en_ventende_godkendelse(isolated_runtime, monkeypatch) -> None:
    from core.services import approval_runtime, notification_router
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    monkeypatch.setattr(approval_runtime, "pending_for_owner", lambda uid: {
        "approval_id": "a-1", "tool_name": "bash_session", "session_id": "s-1"})

    assert e.afstem_godkendelser("bjorn") == 1
    raekker = n.aabne("bjorn", er_owner=True)
    assert [r["ref"] for r in raekker] == ["a-1"]


def test_afstemning_er_idempotent(isolated_runtime, monkeypatch) -> None:
    """Den koerer ved HVER laesning. Anden gang maa den intet goere."""
    from core.services import approval_runtime, notification_router
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    monkeypatch.setattr(approval_runtime, "pending_for_owner", lambda uid: {
        "approval_id": "a-1", "tool_name": "bash_session", "session_id": "s-1"})

    e.afstem_godkendelser("bjorn")
    assert e.afstem_godkendelser("bjorn") == 0
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_afstemning_der_fejler_tommer_ikke_feeden(isolated_runtime, monkeypatch) -> None:
    from core.services import approval_runtime
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Husk mælk")

    def sprang(_uid):
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(approval_runtime, "pending_for_owner", sprang)

    assert len(h.feed("bjorn", er_owner=True)) == 1


def test_feeden_afstemmer_selv(isolated_runtime, monkeypatch) -> None:
    """Uden dette kald ville afstemningen vaere kode ingen kalder."""
    from core.services import approval_runtime, notification_router
    from core.services import notifikationer_hydrering as h

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    monkeypatch.setattr(approval_runtime, "pending_for_owner", lambda uid: {
        "approval_id": "a-1", "tool_name": "bash_session", "session_id": "s-1"})
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "pending", "tool_name": "bash_session"})

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["kan_afgoere"] is True


def test_en_fejlet_koersel_giver_en_raekke(isolated_runtime, monkeypatch) -> None:
    """KALDER finalize_in_flight rigtigt. En kilde-vagt der greber efter en
    streng maaler naesten ingenting — den ville vaere groen ogsaa hvis kaldet
    stod i en gren der aldrig naas."""
    from core.runtime.db import connect
    from core.services import notification_router
    from core.services import notifikationer as n
    from core.services.visible_runs_sections.run_finalization import finalize_in_flight

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"delivered": True, "channel": "push",
                                          "target": "bjorn", "fallback_used": False})
    with connect() as conn:
        conn.execute("INSERT INTO chat_sessions (id, user_id, title) VALUES (?,?,?)",
                     ("s-1", "bjorn", "Kæledyret"))
        conn.commit()

    finalize_in_flight(run_id="r-1", session_id="s-1", status="failed_terminal",
                       error="noget braekkede")

    raekker = n.aabne("bjorn", er_owner=True)
    assert [r["slags"] for r in raekker] == ["run_failed"]
    assert "Kæledyret" in raekker[0]["titel"]


def test_en_faerdig_koersel_giver_den_anden_slags(isolated_runtime, monkeypatch) -> None:
    from core.runtime.db import connect
    from core.services import notification_router
    from core.services import notifikationer as n
    from core.services.visible_runs_sections.run_finalization import finalize_in_flight

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"delivered": False, "channel": "none",
                                          "target": "", "fallback_used": False})
    with connect() as conn:
        conn.execute("INSERT INTO chat_sessions (id, user_id, title) VALUES (?,?,?)",
                     ("s-1", "bjorn", "Kæledyret"))
        conn.commit()

    finalize_in_flight(run_id="r-2", session_id="s-1", status="completed")
    assert [r["slags"] for r in n.aabne("bjorn", er_owner=True)] == ["run_done"]


def test_release_vagten_kalder_emitteren() -> None:
    """Denne ENE er en kilde-vagt med vilje: at koere vagten rigtigt kraever et
    kald ud af huset til GitHub. Den maaler kun at ledningen findes — selve
    adfaerden er daekket af emitter-testene."""
    import apps.api.jarvis_api.routes.app_release as m
    assert "notifikations_emittere" in inspect.getsource(m)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_kobling.py -q`
Expected: FAIL — `afstem_godkendelser` findes ikke

- [ ] **Step 3: Skriv afstemningen**

I `core/services/notifikations_emittere.py`:

```python
def afstem_godkendelser(user_id: str) -> int:
    """Laeg raekker for ventende godkendelser der mangler. Returnerer antal nye.

    Afstemning frem for en krog ved foedslen: kortet foedes to steder i
    visible_runs.py, og en overset krog ville betyde en notifikation der ALDRIG
    fandtes — uden at nogen opdagede det. Den her kan ikke glemme noget, og den
    virker ogsaa for godkendelser der fandtes foer feeden blev bygget.

    `opret()` afdublerer paa (slags, ref), saa den er idempotent af sig selv.
    """
    from core.services import approval_runtime
    kort = approval_runtime.pending_for_owner(user_id)
    if not kort:
        return 0
    aid = str(kort.get("approval_id") or "")
    if not aid:
        return 0
    foer = {str(r["ref"]) for r in _lager.aabne(user_id, er_owner=False)}
    if aid in foer:
        return 0
    paa_godkendelse(aid, user_id=user_id,
                    session_id=str(kort.get("session_id") or ""),
                    vaerktoej=str(kort.get("tool_name") or "et værktøj"))
    return 1
```

- [ ] **Step 4: Lad feeden afstemme**

I `core/services/notifikationer_hydrering.py`, i `feed()`, FØRST i funktionen:

```python
def feed(user_id: str, *, er_owner: bool) -> list[dict[str, Any]]:
    """Aabne notifikationer, hydreret hos deres ejere."""
    # Afstemningen foerst: en ventende godkendelse uden raekke skal med i
    # SAMME laesning, ellers ville den foerst dukke op naeste gang.
    try:
        from core.services.notifikations_emittere import afstem_godkendelser
        afstem_godkendelser(user_id)
    except Exception:
        # En afstemning der fejler maa ikke tomme feeden for alt det andet.
        _log.warning("godkendelser kunne ikke afstemmes for %s", user_id, exc_info=True)
    ud: list[dict[str, Any]] = []
```

- [ ] **Step 5: Hæng den på kørslens udfald**

I `core/services/visible_runs_sections/run_finalization.py`, i `finalize_in_flight`
(den har både `run_id`, `session_id` og `status`), efter den eksisterende krop:

```python
    # Feeden (spec 2026-09-21). Fejler den, skal koerslen stadig afsluttes:
    # afslutningen er den vigtige del.
    try:
        from core.services import notifikations_emittere
        from core.services.visible_runs_sections.run_finalization import _ejer_og_titel
        ejer, titel = _ejer_og_titel(session_id)
        if ejer:
            if status in ("failed", "failed_terminal", "interrupted"):
                notifikations_emittere.paa_koersel_fejlet(
                    run_id, user_id=ejer, session_id=session_id, titel=titel)
            elif status == "completed":
                notifikations_emittere.paa_koersel_faerdig(
                    run_id, user_id=ejer, session_id=session_id, titel=titel)
    except Exception:
        _log.warning("koersel %s naaede ikke feeden", run_id, exc_info=True)
```

og hjælperen i samme fil:

```python
def _ejer_og_titel(session_id: str) -> tuple[str, str]:
    """(ejer, samtale-titel). Tomme strenge hvis samtalen ikke kan laeses."""
    from core.runtime.db import connect
    try:
        with connect() as conn:
            raekke = conn.execute(
                "SELECT user_id, title FROM chat_sessions WHERE id = ?",
                (session_id,)).fetchone()
    except Exception:
        return "", ""
    if not raekke:
        return "", ""
    return str(raekke[0] or ""), str(raekke[1] or "samtalen")
```

Har filen ikke en `_log` i forvejen, så tilføj `import logging` og
`_log = logging.getLogger(__name__)` øverst.

- [ ] **Step 6: Hæng den på release-vagten**

I `apps/api/jarvis_api/routes/app_release.py`, umiddelbart efter at
`app.release.available` publiceres:

```python
    try:
        from core.services import notifikations_emittere
        notifikations_emittere.system("release", f"Ny version {version} er klar")
    except Exception:
        _log.warning("release %s naaede ikke feeden", version, exc_info=True)
```

Brug det variabelnavn versionen har på stedet — find det med
`grep -n "app.release.available" -B8 apps/api/jarvis_api/routes/app_release.py`.

- [ ] **Step 7: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_kobling.py -q`
Expected: PASS, 7 tests

- [ ] **Step 8: Kør HELE suiten — `finalize_in_flight` er en meget varm sti**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q`
Expected: PASS. Ca. 13 minutter. Bryder noget, er det fordi run-afslutningen nu
gør mere end før — ret det, baselinér det ikke.

- [ ] **Step 9: Commit**

```bash
cat > /tmp/notif7.txt <<'EOF'
feat(notifikationer): koblingen — afstemning frem for kroge ved foedslen

Godkendelses-kortet foedes TO steder i visible_runs.py (2228 og 4601) — en
fil paa 7.290 linjer. Planen var at saette en krog begge steder. Det ville
have vaeret forkert paa to maader: Boy Scout-reglen kraever en udskilning
foerst, og vigtigere, en overset krog betyder en notifikation der ALDRIG
findes — uden at nogen opdager det.

Feeden afstemmer i stedet mod pending_for_owner hver gang den laeses. Den kan
ikke glemme noget, og den virker ogsaa for godkendelser der fandtes foer
feeden blev bygget. opret() afdublerer paa (slags, ref), saa den er idempotent
af sig selv.

Den blokerende vej er i forvejen daekket uafhaengigt: desk poller
/chat/approvals/pending hvert 4. sekund og rejser selve kortet. Feeden er en
anden flade paa samme sandhed.

Koerslens udfald haenger paa finalize_in_flight — den ene funktion der har
baade run_id, session_id og status. En afstemning eller en notifikation der
fejler maa aldrig vaelte det den haenger paa.
EOF
git add -- core/services/notifikations_emittere.py core/services/notifikationer_hydrering.py core/services/visible_runs_sections/run_finalization.py apps/api/jarvis_api/routes/app_release.py tests/test_notifikations_kobling.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif7.txt \
  --path core/services/notifikations_emittere.py \
  --path core/services/notifikationer_hydrering.py \
  --path core/services/visible_runs_sections/run_finalization.py \
  --path apps/api/jarvis_api/routes/app_release.py \
  --path tests/test_notifikations_kobling.py
```

---

### Task 8: Desk — klokken med tæller

**Files:**
- Create: `apps/jarvis-desk/src/lib/notifikationerApi.ts`
- Create: `apps/jarvis-desk/src/components/shell/Klokke.tsx`
- Create: `apps/jarvis-desk/src/components/shell/Klokke.test.tsx`
- Modify: `apps/jarvis-desk/src/components/shell/Sidebar.tsx` — erstat klokke-knappen
- Modify: `apps/jarvis-desk/src/styles/app.css`

**Interfaces:**
- Consumes: `GET /notifikationer`, `apiFetch` fra `../lib/api`, `maaPolle` fra `../lib/ro`
- Produces:
  - `hentNotifikationer(config): Promise<{poster: Notifikation[], antal: number}>`
  - `afgoerNotifikation(config, id, approved): Promise<{ok: boolean, fejl: string}>`
  - `setNotifikation(config, id): Promise<void>`
  - `<Klokke config={...} onAaben={() => void} />`

- [ ] **Step 1: Write the failing test**

```tsx
// apps/jarvis-desk/src/components/shell/Klokke.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const hent = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
}))

import { Klokke } from './Klokke'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('Klokke', () => {
  beforeEach(() => hent.mockReset())

  it('viser ingen taeller naar der intet er', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalled())
    expect(screen.queryByTestId('klokke-taeller')).toBeNull()
  })

  it('taeller ALLE aabne, ikke kun dem der kraever et svar', async () => {
    hent.mockResolvedValue({
      poster: [
        { id: '1', slags: 'approval', titel: 'A', tekst: '', kan_afgoere: true, foraeldet: false, oprettet: '', session_id: null },
        { id: '2', slags: 'run_failed', titel: 'B', tekst: '', kan_afgoere: false, foraeldet: false, oprettet: '', session_id: null },
      ],
      antal: 2,
    })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    expect(await screen.findByTestId('klokke-taeller')).toHaveTextContent('2')
  })

  it('siger fra naar listen ikke kunne hentes — og skjuler IKKE bare taelleren', async () => {
    hent.mockRejectedValue(new Error('offline'))
    render(<Klokke config={cfg} onAaben={() => {}} />)
    const knap = await screen.findByRole('button', { name: /Notifikationer/ })
    await waitFor(() => expect(knap.getAttribute('title')).toMatch(/kunne ikke hentes/i))
  })

  it('viser 9+ i stedet for et tal der sprænger prikken', async () => {
    hent.mockResolvedValue({ poster: [], antal: 14 })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    expect(await screen.findByTestId('klokke-taeller')).toHaveTextContent('9+')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/components/shell/Klokke.test.tsx`
Expected: FAIL — `Failed to resolve import "./Klokke"`

- [ ] **Step 3: Skriv api-klienten**

```ts
// apps/jarvis-desk/src/lib/notifikationerApi.ts
import { apiFetch, type ApiConfig } from './api'

export interface Notifikation {
  id: string
  slags: string
  titel: string
  tekst: string
  session_id: string | null
  oprettet: string
  kan_afgoere: boolean
  foraeldet: boolean
}

export interface Feed { poster: Notifikation[]; antal: number }

export async function hentNotifikationer(config: ApiConfig): Promise<Feed> {
  return apiFetch<Feed>(config, '/notifikationer')
}

export async function afgoerNotifikation(
  config: ApiConfig, id: string, approved: boolean,
): Promise<{ ok: boolean; fejl: string }> {
  return apiFetch(config, `/notifikationer/${encodeURIComponent(id)}/afgoer`, {
    method: 'POST',
    body: JSON.stringify({ approved }),
  })
}

export async function setNotifikation(config: ApiConfig, id: string): Promise<void> {
  await apiFetch(config, `/notifikationer/${encodeURIComponent(id)}/set`, { method: 'POST' })
}
```

- [ ] **Step 4: Skriv klokken**

```tsx
// apps/jarvis-desk/src/components/shell/Klokke.tsx
import { useCallback, useEffect, useState } from 'react'
import { Bell } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { hentNotifikationer } from '../../lib/notifikationerApi'
import { maaPolle } from '../../lib/ro'

/**
 * Notifikations-klokken med sin taeller.
 *
 * Taelleren er antal AABNE — alle slags, ikke kun dem der kraever et svar.
 * Det foelger af at feeden er en to-do-liste: staar noget der, er det ikke
 * klaret. En taeller der kun talte godkendelser ville lade et fejlet run staa
 * usynligt bag et tomt tal.
 *
 * Kan listen ikke hentes, skjules taelleren ikke bare — knappen siger det.
 * En tom klokke og en brudt klokke maa ikke ligne hinanden.
 */
export function Klokke({ config, onAaben }: {
  config: ApiConfig | null
  onAaben: () => void
}) {
  const [antal, setAntal] = useState(0)
  const [fejl, setFejl] = useState(false)

  const hent = useCallback(() => {
    if (!config) return
    if (!maaPolle('notifikationer', 8000)) return
    void hentNotifikationer(config)
      .then((f) => { setAntal(f.antal); setFejl(false) })
      .catch(() => setFejl(true))
  }, [config])

  useEffect(() => {
    hent()
    const id = window.setInterval(hent, 8000)
    return () => window.clearInterval(id)
  }, [hent])

  const titel = fejl
    ? 'Notifikationer — listen kunne ikke hentes'
    : antal > 0 ? `Notifikationer — ${antal} åbne` : 'Notifikationer'

  return (
    <button type="button" className="icon-btn klokke" title={titel}
            aria-label={titel} onClick={onAaben}>
      <Bell size={15} />
      {antal > 0 && (
        <span className="klokke-taeller" data-testid="klokke-taeller">
          {antal > 9 ? '9+' : antal}
        </span>
      )}
      {fejl && <span className="klokke-fejl" aria-hidden="true" />}
    </button>
  )
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/components/shell/Klokke.test.tsx`
Expected: PASS, 4 tests

- [ ] **Step 6: Sæt den i sidepanelet**

I `apps/jarvis-desk/src/components/shell/Sidebar.tsx`, ERSTAT hele `<button>`-blokken med `aria-label="Notifikationer"` (den med `<Bell size={15} />`) med:

```tsx
          <Klokke
            config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : null}
            onAaben={() => setFeedAaben(true)}
          />
```

Tilføj importen og tilstanden:

```tsx
import { Klokke } from './Klokke'
```
```tsx
  const [feedAaben, setFeedAaben] = useState(false)
```

- [ ] **Step 7: Styl tælleren**

I `apps/jarvis-desk/src/styles/app.css`, efter `.icon-btn`-reglerne:

```css
/* Klokken baerer sin taeller i hjoernet. `position: relative` paa knappen, saa
   prikken foelger ikonet og ikke sidepanelets kant. */
.klokke { position: relative; }
.klokke-taeller {
  position: absolute; top: 1px; right: 0;
  min-width: 14px; height: 14px; padding: 0 3px;
  border-radius: 7px; background: var(--accent); color: #fff;
  font-size: 9.5px; line-height: 14px; text-align: center;
  font-variant-numeric: tabular-nums;
}
/* En brudt klokke og en tom klokke maa ikke ligne hinanden. */
.klokke-fejl {
  position: absolute; bottom: 2px; right: 2px;
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--error-fg, #ff6b6b);
}
```

- [ ] **Step 8: Typecheck og kør desk-suiten**

Run:
```bash
cd apps/jarvis-desk && npx tsc --noEmit -p tsconfig.json && npx vitest run
```
Expected: tsc uden output, alle testfiler grønne

- [ ] **Step 9: Commit**

```bash
cat > /tmp/notif8.txt <<'EOF'
feat(desk): klokken med taeller

Taelleren er antal AABNE — alle slags, ikke kun dem der kraever et svar. Det
foelger af at feeden er en to-do-liste: staar noget der, er det ikke klaret.
En taeller der kun talte godkendelser ville lade et fejlet run staa usynligt
bag et tomt tal.

Kan listen ikke hentes, skjules taelleren ikke bare — knappen siger det og
faar en lille roed prik. En tom klokke og en brudt klokke maa ikke ligne
hinanden; det er hele lektien fra de fjorten ruder 21/9.
EOF
git add -- apps/jarvis-desk/src/lib/notifikationerApi.ts apps/jarvis-desk/src/components/shell/Klokke.tsx apps/jarvis-desk/src/components/shell/Klokke.test.tsx apps/jarvis-desk/src/components/shell/Sidebar.tsx apps/jarvis-desk/src/styles/app.css
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif8.txt \
  --path apps/jarvis-desk/src/lib/notifikationerApi.ts \
  --path apps/jarvis-desk/src/components/shell/Klokke.tsx \
  --path apps/jarvis-desk/src/components/shell/Klokke.test.tsx \
  --path apps/jarvis-desk/src/components/shell/Sidebar.tsx \
  --path apps/jarvis-desk/src/styles/app.css
```

---

### Task 9: Desk — selve feeden

**Files:**
- Create: `apps/jarvis-desk/src/components/shell/NotifikationsFeed.tsx`
- Create: `apps/jarvis-desk/src/components/shell/NotifikationsFeed.test.tsx`
- Modify: `apps/jarvis-desk/src/components/shell/Sidebar.tsx` — vis feeden når `feedAaben`
- Modify: `apps/jarvis-desk/src/styles/app.css`

**Interfaces:**
- Consumes: `hentNotifikationer`, `afgoerNotifikation`, `setNotifikation`, `SettingsState` fra `../settings/SettingsState`
- Produces: `<NotifikationsFeed config={...} onLuk={() => void} onAabnSession={(id: string) => void} />`

- [ ] **Step 1: Write the failing test**

```tsx
// apps/jarvis-desk/src/components/shell/NotifikationsFeed.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hent = vi.fn()
const afgoer = vi.fn()
const set = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
  afgoerNotifikation: (...a: unknown[]) => afgoer(...a),
  setNotifikation: (...a: unknown[]) => set(...a),
}))

import { NotifikationsFeed } from './NotifikationsFeed'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const post = (o: Partial<Record<string, unknown>> = {}) => ({
  id: '1', slags: 'approval', titel: 'Vil du tillade bash?',
  tekst: 'Jarvis vil køre en kommando.', session_id: 's-1',
  oprettet: new Date().toISOString(), kan_afgoere: true, foraeldet: false, ...o,
})

describe('NotifikationsFeed', () => {
  beforeEach(() => { hent.mockReset(); afgoer.mockReset(); set.mockReset() })

  it('en fejl ser IKKE ud som en tom feed', async () => {
    hent.mockRejectedValue(new Error('offline'))
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/kunne ikke hentes/i)
    expect(screen.queryByText(/Ingen notifikationer/)).toBeNull()
  })

  it('siger det pænt naar der faktisk ikke er noget', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByText(/Ingen notifikationer/)).toBeInTheDocument()
  })

  it('godkender og fjerner posten fra listen', async () => {
    hent.mockResolvedValueOnce({ poster: [post()], antal: 1 })
       .mockResolvedValue({ poster: [], antal: 0 })
    afgoer.mockResolvedValue({ ok: true, fejl: '' })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Godkend' }))
    await waitFor(() => expect(afgoer).toHaveBeenCalledWith(cfg, '1', true))
    await waitFor(() => expect(screen.queryByText('Vil du tillade bash?')).toBeNull())
  })

  it('siger det hoejt naar et svar ikke kunne sendes — og beholder posten', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1 })
    afgoer.mockResolvedValue({ ok: false, fejl: 'Kørslen er væk.' })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Afvis' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Kørslen er væk.')
    expect(screen.getByText('Vil du tillade bash?')).toBeInTheDocument()
  })

  it('en foraeldet post kan ikke afgoeres', async () => {
    hent.mockResolvedValue({ poster: [post({ foraeldet: true, kan_afgoere: false })], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByText('Vil du tillade bash?')
    expect(screen.queryByRole('button', { name: 'Godkend' })).toBeNull()
    expect(screen.getByText(/kunne ikke opdateres/i)).toBeInTheDocument()
  })

  it('baerer den fulde tekst som hover-information', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    const raekke = await screen.findByTestId('notif-1')
    expect(raekke.getAttribute('title')).toBe('Jarvis vil køre en kommando.')
  })

  it('et spoergsmaal foerer hen til samtalen — det kan ikke svares her', async () => {
    hent.mockResolvedValue({
      poster: [post({ slags: 'question', kan_afgoere: false, titel: 'Hvilken fil?' })],
      antal: 1,
    })
    set.mockResolvedValue(undefined)
    const aabn = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabn} />)
    await screen.findByText('Hvilken fil?')
    expect(screen.queryByRole('button', { name: 'Godkend' })).toBeNull()
    fireEvent.click(screen.getByTestId('notif-1'))
    expect(aabn).toHaveBeenCalledWith('s-1')
  })

  it('aabner samtalen naar man trykker paa en post uden handling', async () => {
    hent.mockResolvedValue({ poster: [post({ slags: 'run_done', kan_afgoere: false })], antal: 1 })
    set.mockResolvedValue(undefined)
    const aabn = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabn} />)
    fireEvent.click(await screen.findByTestId('notif-1'))
    expect(aabn).toHaveBeenCalledWith('s-1')
    await waitFor(() => expect(set).toHaveBeenCalledWith(cfg, '1'))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/components/shell/NotifikationsFeed.test.tsx`
Expected: FAIL — `Failed to resolve import "./NotifikationsFeed"`

- [ ] **Step 3: Skriv feeden**

```tsx
// apps/jarvis-desk/src/components/shell/NotifikationsFeed.tsx
import { useCallback, useEffect, useState } from 'react'
import { X, ShieldAlert, CircleAlert, CircleCheck, Bell, Package } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import {
  hentNotifikationer, afgoerNotifikation, setNotifikation, type Notifikation,
} from '../../lib/notifikationerApi'
import { SettingsState, SettingsActionError } from '../settings/SettingsState'

const IKON: Record<string, typeof Bell> = {
  approval: ShieldAlert, question: ShieldAlert,
  run_failed: CircleAlert, run_done: CircleCheck,
  release: Package,
}

/** «for 3 min siden» — et klokkeslaet siger mindre end et interval her. */
function siden(iso: string): string {
  const ms = Date.now() - Date.parse(iso)
  if (!Number.isFinite(ms) || ms < 0) return ''
  const min = Math.floor(ms / 60_000)
  if (min < 1) return 'lige nu'
  if (min < 60) return `${min} min siden`
  const timer = Math.floor(min / 60)
  if (timer < 24) return `${timer} t siden`
  return `${Math.floor(timer / 24)} d siden`
}

/**
 * Notifikations-feeden — en to-do-liste, ikke en journal.
 *
 * Har man handlet, er posten vaek. Derfor er en tom feed en GOD nyhed, og
 * derfor maa en fejlet hentning aldrig ligne den: de to staar som hver sin
 * besked.
 */
export function NotifikationsFeed({ config, onLuk, onAabnSession }: {
  config: ApiConfig | null
  onLuk: () => void
  onAabnSession: (sessionId: string) => void
}) {
  const [poster, setPoster] = useState<Notifikation[] | null>(null)
  const [fejl, setFejl] = useState(false)
  const [handlingFejl, setHandlingFejl] = useState('')
  const [travl, setTravl] = useState('')

  const hent = useCallback(() => {
    if (!config) return
    void hentNotifikationer(config)
      .then((f) => { setPoster(f.poster); setFejl(false) })
      .catch(() => setFejl(true))
  }, [config])

  useEffect(() => { hent() }, [hent])

  const afgoer = async (p: Notifikation, godkendt: boolean) => {
    if (!config) return
    setTravl(p.id); setHandlingFejl('')
    try {
      const svar = await afgoerNotifikation(config, p.id, godkendt)
      if (!svar.ok) { setHandlingFejl(svar.fejl || 'Svaret kunne ikke sendes.'); return }
      hent()
    } catch {
      setHandlingFejl('Svaret kunne ikke sendes. Prøv igen.')
    } finally { setTravl('') }
  }

  const aabn = (p: Notifikation) => {
    if (p.session_id) onAabnSession(p.session_id)
    if (config) void setNotifikation(config, p.id).then(hent).catch(() => undefined)
  }

  return (
    <div className="notif-feed" role="dialog" aria-label="Notifikationer">
      <div className="notif-head">
        <span>Notifikationer</span>
        <button type="button" className="jobs-close" onClick={onLuk} aria-label="Luk">
          <X size={14} />
        </button>
      </div>

      <SettingsActionError message={handlingFejl} />

      {fejl ? (
        <SettingsState status="error" label="notifikationerne" onRetry={hent} />
      ) : poster === null ? (
        <SettingsState status="loading" label="notifikationerne" onRetry={() => {}} />
      ) : poster.length === 0 ? (
        <p className="notif-tom">Ingen notifikationer — alt er klaret.</p>
      ) : (
        <ul className="notif-liste">
          {poster.map((p) => {
            const Ikon = IKON[p.slags] ?? Bell
            return (
              <li key={p.id}>
                <div
                  className={`notif-post${p.foraeldet ? ' er-foraeldet' : ''}`}
                  data-testid={`notif-${p.id}`}
                  title={p.tekst || p.titel}
                  role="button"
                  tabIndex={0}
                  onClick={() => { if (!p.kan_afgoere) aabn(p) }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !p.kan_afgoere) aabn(p) }}
                >
                  <Ikon size={14} className="notif-ikon" aria-hidden="true" />
                  <span className="notif-titel">{p.titel}</span>
                  <span className="notif-tid">{siden(p.oprettet)}</span>
                </div>
                {p.foraeldet && (
                  <p className="notif-foraeldet">Kunne ikke opdateres — det viste er sidste nyt.</p>
                )}
                {p.kan_afgoere && (
                  <div className="notif-handlinger">
                    <button type="button" disabled={travl === p.id}
                            onClick={() => void afgoer(p, true)}>Godkend</button>
                    <button type="button" disabled={travl === p.id}
                            onClick={() => void afgoer(p, false)}>Afvis</button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/components/shell/NotifikationsFeed.test.tsx`
Expected: PASS, 8 tests

- [ ] **Step 5: Vis feeden fra sidepanelet**

I `Sidebar.tsx`, lige efter `</div>` der lukker knap-rækken øverst:

```tsx
      {feedAaben && (
        <NotifikationsFeed
          config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : null}
          onLuk={() => setFeedAaben(false)}
          onAabnSession={(id) => { select(id); setFeedAaben(false); onSurface('chat') }}
        />
      )}
```

og importen:

```tsx
import { NotifikationsFeed } from './NotifikationsFeed'
```

- [ ] **Step 6: Styl feeden**

I `app.css`, efter `.klokke-fejl`:

```css
/* Feeden haenger under klokken, ikke i sidepanelets flow: den maa ikke skubbe
   samtalelisten ned hver gang den aabnes. */
.notif-feed {
  position: absolute; top: 46px; left: 10px; right: 10px; z-index: 70;
  max-height: min(60vh, 520px); overflow-y: auto;
  padding: 10px 12px; border-radius: 12px;
  background: var(--bg-2); border: 1px solid var(--line);
  box-shadow: 0 10px 30px rgba(0,0,0,.34);
}
.notif-head {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 13px; color: var(--fg-3); margin-bottom: 8px;
}
.notif-tom { margin: 8px 2px; color: var(--fg-3); font-size: 12.5px; }
.notif-liste { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.notif-post {
  display: flex; align-items: center; gap: 8px; width: 100%;
  padding: 7px 9px; border-radius: 8px; background: var(--bg-1);
  border: 1px solid var(--line); cursor: pointer; text-align: left;
}
.notif-post:hover { background: var(--bg-3, var(--bg-2)); }
.notif-post:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.notif-ikon { flex: none; color: var(--fg-3); }
.notif-titel { flex: 1; min-width: 0; color: var(--fg-1); font-size: 12.5px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notif-tid { flex: none; color: var(--fg-3); font-size: 11px; }
.notif-post.er-foraeldet { opacity: .7; }
.notif-foraeldet { margin: 4px 0 0 9px; font-size: 11.5px; color: var(--error-fg, #ff8e8e); }
.notif-handlinger { display: flex; gap: 6px; margin: 6px 0 0 9px; }
.notif-handlinger button {
  background: none; border: 1px solid var(--line); border-radius: 7px;
  color: var(--fg-2); font-size: 11.5px; padding: 3px 10px; cursor: pointer;
}
.notif-handlinger button:hover:not(:disabled) { color: var(--fg-1); background: var(--bg-2); }
.notif-handlinger button:disabled { opacity: .5; cursor: default; }
```

- [ ] **Step 7: Typecheck og kør desk-suiten**

Run:
```bash
cd apps/jarvis-desk && npx tsc --noEmit -p tsconfig.json && npx eslint src/ && npx vitest run
```
Expected: tsc uden output, eslint 0 errors, alle testfiler grønne

- [ ] **Step 8: Commit**

```bash
cat > /tmp/notif9.txt <<'EOF'
feat(desk): notifikations-feeden — se, hold musen over, godkend eller afvis

En to-do-liste, ikke en journal. Har man handlet, er posten vaek.

Netop derfor er en tom feed en GOD nyhed — og derfor maa en fejlet hentning
aldrig ligne den. De staar som hver sin besked, med «Proev igen» paa fejlen.

Et svar der ikke kunne sendes beholder posten og siger hvorfor. Ellers ville
man tro man havde godkendt noget man ikke havde.

En post hvis ejer ikke kunne naas kan ikke afgoeres — den siger «kunne ikke
opdateres» i stedet for at lade som om den er frisk.
EOF
git add -- apps/jarvis-desk/src/components/shell/NotifikationsFeed.tsx apps/jarvis-desk/src/components/shell/NotifikationsFeed.test.tsx apps/jarvis-desk/src/components/shell/Sidebar.tsx apps/jarvis-desk/src/styles/app.css
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif9.txt \
  --path apps/jarvis-desk/src/components/shell/NotifikationsFeed.tsx \
  --path apps/jarvis-desk/src/components/shell/NotifikationsFeed.test.tsx \
  --path apps/jarvis-desk/src/components/shell/Sidebar.tsx \
  --path apps/jarvis-desk/src/styles/app.css
```

---

### Task 10: Desk — live uden at gå ud og ind

**Files:**
- Modify: `apps/jarvis-desk/src/components/shell/Klokke.tsx` — lyt på WS
- Modify: `apps/jarvis-desk/src/components/shell/Klokke.test.tsx`

**Interfaces:**
- Consumes: `openEventSocket(config)` fra `../../lib/api`
- Produces: ingen nye

**Hvorfor:** hele klagen bag denne opgave er at man skal ud og ind af appen før noget nyt viser sig. En feed med et 8-sekunders poll er ikke godt nok når en godkendelse holder en kørsel.

- [ ] **Step 1: Write the failing test**

```tsx
// tilfoejes Klokke.test.tsx
const sockets: { onmessage: ((e: { data: string }) => void) | null; close: () => void }[] = []
vi.mock('../../lib/api', () => ({
  openEventSocket: () => {
    const s = { onmessage: null, onerror: null, close: vi.fn() }
    sockets.push(s as never)
    return s
  },
}))

it('opdaterer taelleren paa en haendelse — uden at man gaar ud og ind', async () => {
  hent.mockResolvedValueOnce({ poster: [], antal: 0 })
     .mockResolvedValue({ poster: [], antal: 3 })
  render(<Klokke config={cfg} onAaben={() => {}} />)
  await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
  expect(screen.queryByTestId('klokke-taeller')).toBeNull()

  const s = sockets[sockets.length - 1]
  s.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })

  expect(await screen.findByTestId('klokke-taeller')).toHaveTextContent('3')
})

it('ignorerer haendelser der ikke er vores', async () => {
  hent.mockResolvedValue({ poster: [], antal: 0 })
  render(<Klokke config={cfg} onAaben={() => {}} />)
  await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
  const s = sockets[sockets.length - 1]
  s.onmessage?.({ data: JSON.stringify({ kind: 'runtime.tick' }) })
  await new Promise((r) => setTimeout(r, 30))
  expect(hent).toHaveBeenCalledTimes(1)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/components/shell/Klokke.test.tsx`
Expected: FAIL — tælleren bliver ved at være tom, fordi ingen lytter

- [ ] **Step 3: Lyt på hændelsen**

I `Klokke.tsx`, tilføj efter poll-effekten:

```tsx
  // Live-vejen. Pollet er sikkerhedsnettet; DETTE er grunden til at man ikke
  // skal ud og ind af appen for at se en ny godkendelse. `hentNu` gaar uden om
  // `maaPolle`: en haendelse ER signalet, og et ro-loft ville sluge den.
  useEffect(() => {
    if (!config) return
    let ws: WebSocket | null = null
    try {
      ws = openEventSocket(config)
      ws.onmessage = (e) => {
        try {
          const kind = String(JSON.parse(String(e.data))?.kind || '')
          if (kind.startsWith('notifikation.')) hentNu()
        } catch { /* ikke-JSON paa bussen er ikke vores */ }
      }
      ws.onerror = () => { /* pollet daekker */ }
    } catch { /* pollet daekker */ }
    return () => { try { ws?.close() } catch { /* noop */ } }
  }, [config, hentNu])
```

og splid hentningen, så hændelsen ikke bremses af ro-loftet:

```tsx
  const hentNu = useCallback(() => {
    if (!config) return
    void hentNotifikationer(config)
      .then((f) => { setAntal(f.antal); setFejl(false) })
      .catch(() => setFejl(true))
  }, [config])

  const hent = useCallback(() => {
    if (!maaPolle('notifikationer', 8000)) return
    hentNu()
  }, [hentNu])
```

Tilføj importen: `import { openEventSocket } from '../../lib/api'`

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/components/shell/Klokke.test.tsx`
Expected: PASS, 6 tests

- [ ] **Step 5: Commit**

```bash
cat > /tmp/notif10.txt <<'EOF'
feat(desk): klokken opdaterer sig live — uden at man gaar ud og ind

Hele klagen bag denne opgave er at man skal ud og ind af appen foer noget nyt
viser sig. Et 8-sekunders poll er ikke godt nok naar en godkendelse holder en
koersel.

Klokken lytter nu paa `notifikation.*` og henter med det samme. Pollet er
sikkerhedsnettet hvis forbindelsen er nede.

Haendelses-hentningen gaar UDEN OM ro-loftet. En haendelse ER signalet, og
`maaPolle` ville sluge den — saa var vi tilbage ved at vente.
EOF
git add -- apps/jarvis-desk/src/components/shell/Klokke.tsx apps/jarvis-desk/src/components/shell/Klokke.test.tsx
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif10.txt \
  --path apps/jarvis-desk/src/components/shell/Klokke.tsx \
  --path apps/jarvis-desk/src/components/shell/Klokke.test.tsx
```

---

### Task 11: Mobil — klokke og feed

**Files:**
- Modify: `apps/mobile/src/lib/apiClient.ts` — de tre kald
- Modify: `apps/mobile/src/screens/ActivityCenterScreen.tsx` — feed-sektion
- Modify: `apps/mobile/src/screens/ChatScreen.tsx` — tæller på Aktivitet-knappen
- Test: `apps/mobile/src/screens/ActivityCenterScreen.test.tsx`

**Interfaces:**
- Consumes: samme tre ruter som desk
- Produces:
  - `hentNotifikationer(config: ApiConfig): Promise<{poster: Notifikation[]; antal: number}>`
  - `afgoerNotifikation(config: ApiConfig, id: string, approved: boolean): Promise<{ok: boolean; fejl: string}>`

**Hvorfor i ActivityCenterScreen og ikke en ny skærm:** mobilen har allerede «Aktivitet», og den viser netop aktive runs. Feeden hører til dér. En ny skærm ville give to steder at kigge efter det samme.

- [ ] **Step 1: Write the failing test**

```tsx
// apps/mobile/src/screens/ActivityCenterScreen.test.tsx — tilfoejes
it('viser notifikationer og kan godkende', async () => {
  const afgoer = jest.fn().mockResolvedValue({ ok: true, fejl: '' })
  const { findByText, getByText } = render(
    <ActivityCenterScreen
      onClose={() => {}}
      runs={[]}
      notifikationer={[{
        id: '1', slags: 'approval', titel: 'Vil du tillade bash?', tekst: '',
        session_id: 's-1', oprettet: new Date().toISOString(),
        kan_afgoere: true, foraeldet: false,
      }]}
      onAfgoer={afgoer}
    />,
  )
  await findByText('Vil du tillade bash?')
  fireEvent.press(getByText('Godkend'))
  expect(afgoer).toHaveBeenCalledWith('1', true)
})

it('en fejl ser ikke ud som en tom liste', async () => {
  const { findByText, queryByText } = render(
    <ActivityCenterScreen onClose={() => {}} runs={[]} notifikationer={null} notifFejl />,
  )
  await findByText(/kunne ikke hentes/i)
  expect(queryByText(/Ingen notifikationer/)).toBeNull()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/mobile && npx jest src/screens/ActivityCenterScreen.test.tsx`
Expected: FAIL — props findes ikke

- [ ] **Step 3: Tilføj kaldene i apiClient**

I `apps/mobile/src/lib/apiClient.ts`, ved siden af de andre kald:

```ts
export interface Notifikation {
  id: string
  slags: string
  titel: string
  tekst: string
  session_id: string | null
  oprettet: string
  kan_afgoere: boolean
  foraeldet: boolean
}

export async function hentNotifikationer(
  config: ApiConfig,
): Promise<{ poster: Notifikation[]; antal: number }> {
  return apiFetch(config, '/notifikationer')
}

export async function afgoerNotifikation(
  config: ApiConfig, id: string, approved: boolean,
): Promise<{ ok: boolean; fejl: string }> {
  return apiFetch(config, `/notifikationer/${encodeURIComponent(id)}/afgoer`, {
    method: 'POST',
    body: JSON.stringify({ approved }),
  })
}
```

`apiFetch<T>(config, path, options)` er filens egen hjælper (linje 41) — den
tager `config` som FØRSTE argument, præcis som desk-siden.

- [ ] **Step 4: Tilføj feeden i ActivityCenterScreen**

Udvid props:

```tsx
  notifikationer?: Notifikation[] | null
  notifFejl?: boolean
  onAfgoer?: (id: string, approved: boolean) => Promise<{ ok: boolean; fejl: string }>
  onGenhent?: () => void
```

og indsæt en sektion øverst i `<ScrollView>`, før run-listen:

```tsx
        <Text style={styles.sektion}>Notifikationer</Text>
        {notifFejl ? (
          <View style={styles.card}>
            <Text style={styles.fejl}>Notifikationerne kunne ikke hentes.</Text>
            {onGenhent ? (
              <Pressable onPress={onGenhent} accessibilityRole="button">
                <Text style={styles.linkTekst}>Prøv igen</Text>
              </Pressable>
            ) : null}
          </View>
        ) : notifikationer === null || notifikationer === undefined ? (
          <Text style={styles.muted}>Henter notifikationer…</Text>
        ) : notifikationer.length === 0 ? (
          <Text style={styles.muted}>Ingen notifikationer — alt er klaret.</Text>
        ) : notifikationer.map((p) => (
          <View key={p.id} style={styles.card}>
            <Text style={styles.value}>{p.titel}</Text>
            {p.tekst ? <Text style={styles.muted}>{p.tekst}</Text> : null}
            {p.foraeldet ? (
              <Text style={styles.fejl}>Kunne ikke opdateres — det viste er sidste nyt.</Text>
            ) : null}
            {p.kan_afgoere && onAfgoer ? (
              <View style={styles.knapRaekke}>
                <Pressable accessibilityRole="button" onPress={() => { void onAfgoer(p.id, true) }}>
                  <Text style={styles.linkTekst}>Godkend</Text>
                </Pressable>
                <Pressable accessibilityRole="button" onPress={() => { void onAfgoer(p.id, false) }}>
                  <Text style={styles.linkTekst}>Afvis</Text>
                </Pressable>
              </View>
            ) : null}
          </View>
        ))}
```

Tilføj `sektion`, `fejl`, `linkTekst` og `knapRaekke` til `makes`-stilarket ved siden af de eksisterende, i samme stil.

- [ ] **Step 5: Tæller på Aktivitet-knappen**

I `ChatScreen.tsx`, hent feeden med samme 8-sekunders interval som desk, og vis `antal` som et lille tal på den knap der åbner `ActivityCenterScreen`. Brug den eksisterende badge-stil (`styles.badge` bruges allerede i skærmen).

- [ ] **Step 6: Run test to verify it passes**

Run: `cd apps/mobile && npx jest src/screens/ActivityCenterScreen.test.tsx`
Expected: PASS

- [ ] **Step 7: Kør hele mobil-suiten**

Run: `cd apps/mobile && npx jest`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
cat > /tmp/notif11.txt <<'EOF'
feat(mobil): notifikationer i Aktivitet, med taeller

Feeden bor i den eksisterende «Aktivitet»-skaerm frem for i en ny. Den viser
allerede aktive runs; en ny skaerm ville give to steder at kigge efter det
samme.

Samme regel som paa desk: en fejlet hentning ser ikke ud som en tom liste. De
to staar som hver sin besked.

Desk og mobil bygges i samme omgang med vilje. De er gledet fra hinanden foer
— tool-linjens tekst stod to dage bagud paa mobilen — og en delt server goer
det billigt at goere samtidig.
EOF
git add -- apps/mobile/src/lib/apiClient.ts apps/mobile/src/screens/ActivityCenterScreen.tsx apps/mobile/src/screens/ActivityCenterScreen.test.tsx apps/mobile/src/screens/ChatScreen.tsx
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif11.txt \
  --path apps/mobile/src/lib/apiClient.ts \
  --path apps/mobile/src/screens/ActivityCenterScreen.tsx \
  --path apps/mobile/src/screens/ActivityCenterScreen.test.tsx \
  --path apps/mobile/src/screens/ChatScreen.tsx
```

---

### Task 12: Indstillinger — push per slags

**Files:**
- Create: `apps/api/jarvis_api/routes/notifikations_valg.py`
- Modify: `apps/api/jarvis_api/app.py`
- Create: `apps/jarvis-desk/src/components/settings/NotifikationsValg.tsx`
- Create: `apps/jarvis-desk/src/components/settings/NotifikationsValg.test.tsx`
- Modify: `apps/jarvis-desk/src/components/settings/NotificationsSection.tsx`
- Test: `tests/test_notifikations_valg_rute.py`

**Interfaces:**
- Consumes: `notifikations_valg.alle()`, `notifikations_valg.saet()`
- Produces:
  - `GET /notifikations-valg` → `{"valg": {slags: kanal}}`
  - `POST /notifikations-valg` body `{"slags": str, "kanal": str}` → `{"ok": bool, "fejl": str}`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikations_valg_rute.py
from __future__ import annotations

import pytest


@pytest.fixture()
def klient(isolated_runtime, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api.jarvis_api.routes import notifikations_valg as rute

    monkeypatch.setattr(rute, "_bruger", lambda: "bjorn")
    app = FastAPI()
    app.include_router(rute.router)
    return TestClient(app)


def test_henter_alle_slags_med_standarden_lagt_i(klient) -> None:
    valg = klient.get("/notifikations-valg").json()["valg"]
    assert valg["approval"] == "auto"
    assert valg["release"] == "ingen"


def test_saetter_et_valg(klient) -> None:
    assert klient.post("/notifikations-valg",
                       json={"slags": "release", "kanal": "push"}).json()["ok"] is True
    assert klient.get("/notifikations-valg").json()["valg"]["release"] == "push"


def test_afviser_en_ukendt_kanal(klient) -> None:
    svar = klient.post("/notifikations-valg",
                       json={"slags": "release", "kanal": "duer-ikke"}).json()
    assert svar["ok"] is False
    assert "kanal" in svar["fejl"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_valg_rute.py -q`
Expected: FAIL med `ModuleNotFoundError`

- [ ] **Step 3: Skriv ruten**

```python
# apps/api/jarvis_api/routes/notifikations_valg.py
"""Push-valg per slags. Scoper til den auth'ede bruger."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from core.services import notifikations_valg as _valg

router = APIRouter(prefix="/notifikations-valg", tags=["notifikationer"])


class SaetBody(BaseModel):
    slags: str
    kanal: str


def _bruger() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


@router.get("")
async def hent() -> dict:
    uid = _bruger()
    return {"valg": _valg.alle(uid) if uid else {}}


@router.post("")
async def saet(body: SaetBody) -> dict:
    uid = _bruger()
    if not uid:
        return {"ok": False, "fejl": "Ikke logget ind."}
    try:
        _valg.saet(uid, body.slags, body.kanal)
    except ValueError:
        return {"ok": False, "fejl": f"Ukendt kanal: {body.kanal}"}
    return {"ok": True, "fejl": ""}
```

I `apps/api/jarvis_api/app.py`, ved siden af `notifikationer_router`:

```python
    from apps.api.jarvis_api.routes.notifikations_valg import router as notifikations_valg_router
    app.include_router(notifikations_valg_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_valg_rute.py -q`
Expected: PASS, 3 tests

- [ ] **Step 5: Skriv desk-testen**

```tsx
// apps/jarvis-desk/src/components/settings/NotifikationsValg.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hent = vi.fn()
const saet = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationsValg: (...a: unknown[]) => hent(...a),
  saetNotifikationsValg: (...a: unknown[]) => saet(...a),
}))

import { NotifikationsValg } from './NotifikationsValg'
const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('NotifikationsValg', () => {
  beforeEach(() => { hent.mockReset(); saet.mockReset() })

  it('en fejl ser ikke ud som tomme valg', async () => {
    hent.mockRejectedValue(new Error('offline'))
    render(<NotifikationsValg config={cfg} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/kunne ikke hentes/i)
  })

  it('gemmer et valg', async () => {
    hent.mockResolvedValue({ valg: { approval: 'auto', release: 'ingen' } })
    saet.mockResolvedValue({ ok: true, fejl: '' })
    render(<NotifikationsValg config={cfg} />)
    const felt = await screen.findByLabelText('Ny app-version')
    fireEvent.change(felt, { target: { value: 'push' } })
    await waitFor(() => expect(saet).toHaveBeenCalledWith(cfg, 'release', 'push'))
  })

  it('ruller valget tilbage og siger det naar det ikke kunne gemmes', async () => {
    hent.mockResolvedValue({ valg: { release: 'ingen' } })
    saet.mockResolvedValue({ ok: false, fejl: 'Kunne ikke gemmes.' })
    render(<NotifikationsValg config={cfg} />)
    const felt = await screen.findByLabelText('Ny app-version') as HTMLSelectElement
    fireEvent.change(felt, { target: { value: 'push' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Kunne ikke gemmes.')
    await waitFor(() => expect(felt.value).toBe('ingen'))
  })
})
```

- [ ] **Step 6: Skriv komponenten**

Tilføj først de to kald i `apps/jarvis-desk/src/lib/notifikationerApi.ts`:

```ts
export async function hentNotifikationsValg(config: ApiConfig): Promise<{ valg: Record<string, string> }> {
  return apiFetch(config, '/notifikations-valg')
}

export async function saetNotifikationsValg(
  config: ApiConfig, slags: string, kanal: string,
): Promise<{ ok: boolean; fejl: string }> {
  return apiFetch(config, '/notifikations-valg', {
    method: 'POST',
    body: JSON.stringify({ slags, kanal }),
  })
}
```

```tsx
// apps/jarvis-desk/src/components/settings/NotifikationsValg.tsx
import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { hentNotifikationsValg, saetNotifikationsValg } from '../../lib/notifikationerApi'
import { SettingsState, SettingsActionError } from './SettingsState'

/** Brugerens ord for hver slags — ikke systemets. */
const NAVN: Record<string, string> = {
  approval: 'Godkendelser',
  question: 'Spørgsmål fra Jarvis',
  run_failed: 'Når noget går galt',
  run_done: 'Når et svar er klar',
  briefing: 'Morgenbriefing',
  reminder: 'Påmindelser',
  reach_out: 'Når Jarvis selv tager kontakt',
  initiative: 'Initiativer',
  release: 'Ny app-version',
  incident: 'Hændelser i systemet',
  quota: 'Kvote opbrugt',
}

const KANALER: [string, string][] = [
  ['auto', 'Automatisk'],
  ['push', 'Altid på telefonen'],
  ['desktop', 'Kun på computeren'],
  ['ingen', 'Kun i feeden'],
]

export function NotifikationsValg({ config }: { config: ApiConfig | undefined }) {
  const [valg, setValg] = useState<Record<string, string> | null>(null)
  const [fejl, setFejl] = useState(false)
  const [gemFejl, setGemFejl] = useState('')

  const hent = () => {
    if (!config) return
    void hentNotifikationsValg(config)
      .then((d) => { setValg(d.valg); setFejl(false) })
      .catch(() => setFejl(true))
  }
  useEffect(hent, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  const skift = async (slags: string, kanal: string) => {
    if (!config || !valg) return
    const foer = valg[slags]
    setValg({ ...valg, [slags]: kanal })   // optimistisk
    setGemFejl('')
    try {
      const svar = await saetNotifikationsValg(config, slags, kanal)
      if (!svar.ok) {
        // Rul tilbage. Ellers stod der et valg der ikke var gemt, og man ville
        // tro telefonen var slaaet til.
        setValg((v) => (v ? { ...v, [slags]: foer } : v))
        setGemFejl(svar.fejl || 'Valget kunne ikke gemmes.')
      }
    } catch {
      setValg((v) => (v ? { ...v, [slags]: foer } : v))
      setGemFejl('Valget kunne ikke gemmes. Prøv igen.')
    }
  }

  if (fejl) return <SettingsState status="error" label="notifikations-valgene" onRetry={hent} />
  if (!valg) return <SettingsState status="loading" label="notifikations-valgene" onRetry={() => {}} />

  return (
    <div className="settings-section">
      <h3>Hvad må afbryde dig</h3>
      <p className="settings-hint">
        Alt står i feeden under klokken. Her bestemmer du kun hvad der også når telefonen.
      </p>
      <SettingsActionError message={gemFejl} />
      {Object.keys(NAVN).filter((s) => s in valg).map((slags) => (
        <label key={slags} className="settings-row">
          <span>{NAVN[slags]}</span>
          <select aria-label={NAVN[slags]} value={valg[slags]}
                  onChange={(e) => void skift(slags, e.target.value)}>
            {KANALER.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
          </select>
        </label>
      ))}
    </div>
  )
}
```

Sæt den ind i `NotificationsSection.tsx` under det eksisterende indhold:

```tsx
      <NotifikationsValg config={config} />
```

- [ ] **Step 7: Run tests**

Run:
```bash
cd apps/jarvis-desk && npx vitest run src/components/settings/NotifikationsValg.test.tsx
```
Expected: PASS, 3 tests

- [ ] **Step 8: Efterprøv at ruterne hænger på appen**

Run:
```bash
/opt/conda/envs/ai/bin/python -c "
from apps.api.jarvis_api.app import app
stier = sorted({r.path for r in app.routes if 'notifikation' in r.path})
print(stier)
assert '/notifikations-valg' in stier
"
```
Expected: `/notifikations-valg` er med

- [ ] **Step 9: Commit**

```bash
cat > /tmp/notif12.txt <<'EOF'
feat(desk): vaelg selv hvad der maa afbryde dig

Alt staar i feeden under klokken; her bestemmer man kun hvad der ogsaa naar
telefonen. Standarden er at godkendelser, spoergsmaal og fejl pusher — resten
staar stille til man selv kigger.

Valget er optimistisk og RULLES TILBAGE hvis det ikke kunne gemmes. Ellers
stod der et valg der ikke var gemt, og man ville tro telefonen var slaaet til.

Teksterne er brugerens ord, ikke systemets: «Naar noget gaar galt», ikke
«run_failed».
EOF
git add -- apps/api/jarvis_api/routes/notifikations_valg.py apps/api/jarvis_api/app.py apps/jarvis-desk/src/lib/notifikationerApi.ts apps/jarvis-desk/src/components/settings/NotifikationsValg.tsx apps/jarvis-desk/src/components/settings/NotifikationsValg.test.tsx apps/jarvis-desk/src/components/settings/NotificationsSection.tsx tests/test_notifikations_valg_rute.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif12.txt \
  --path apps/api/jarvis_api/routes/notifikations_valg.py --path apps/api/jarvis_api/app.py \
  --path apps/jarvis-desk/src/lib/notifikationerApi.ts \
  --path apps/jarvis-desk/src/components/settings/NotifikationsValg.tsx \
  --path apps/jarvis-desk/src/components/settings/NotifikationsValg.test.tsx \
  --path apps/jarvis-desk/src/components/settings/NotificationsSection.tsx \
  --path tests/test_notifikations_valg_rute.py
```

---

### Task 13: Oprydning og migrering ved opstart

**Files:**
- Modify: `apps/api/jarvis_api/app.py` — lifespan
- Test: `tests/test_notifikations_opstart.py`

**Interfaces:**
- Consumes: `notifikations_valg.migrer_kolonner()`, `notifikationer.ryd_gamle()`
- Produces: ingen nye

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifikations_opstart.py
from __future__ import annotations

import inspect


def test_opstarten_migrerer_og_rydder_op() -> None:
    """Migreringen skal koere, ellers taber den foerste bruger sine valg.
    Oprydningen skal koere, ellers vokser tabellen i det uendelige."""
    import apps.api.jarvis_api.app as m
    kilde = inspect.getsource(m)
    assert "migrer_kolonner" in kilde
    assert "ryd_gamle" in kilde


def test_migreringen_er_idempotent(isolated_runtime) -> None:
    """Den koerer ved HVER opstart — anden gang maa den ikke goere noget."""
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder)"
            " VALUES (?,?,?)", ("bjorn", "auto", "mobile"))
        conn.commit()

    assert v.migrer_kolonner() == 1
    assert v.migrer_kolonner() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_opstart.py -q`
Expected: FAIL på `test_opstarten_migrerer_og_rydder_op`

- [ ] **Step 3: Kør begge ved opstart**

Find lifespan-funktionen: `grep -n "async def lifespan" apps/api/jarvis_api/app.py`

Tilføj i opstarts-grenen, efter at DB-skemaet er sikret:

```python
    # Notifikations-feeden (spec 2026-09-21). Begge er idempotente og maa
    # aldrig kunne vaelte opstarten: en feed der ikke kan rydde op er stadig
    # bedre end en API der ikke starter.
    try:
        from core.services.notifikations_valg import migrer_kolonner
        flyttet = migrer_kolonner()
        if flyttet:
            _log.info("notifikations-valg: %d valg migreret fra kolonner", flyttet)
    except Exception:
        _log.warning("notifikations-valg kunne ikke migreres", exc_info=True)
    try:
        from core.services.notifikationer import ryd_gamle
        fjernet = ryd_gamle()
        if fjernet:
            _log.info("notifikationer: %d klarede raekker ryddet", fjernet)
    except Exception:
        _log.warning("notifikationer kunne ikke ryddes", exc_info=True)
```

Brug det logger-navn filen allerede har — slå det op med `grep -n "^_log\|getLogger" apps/api/jarvis_api/app.py | head -3`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_notifikations_opstart.py -q`
Expected: PASS, 2 tests

- [ ] **Step 5: Kør HELE suiten**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q`
Expected: PASS. Ca. 13 minutter.

- [ ] **Step 6: Commit**

```bash
cat > /tmp/notif13.txt <<'EOF'
feat(notifikationer): migrering og oprydning ved opstart

Migreringen skal koere, ellers taber den foerste bruger sine gamle valg.
Oprydningen skal koere, ellers vokser tabellen i det uendelige — klarede
raekker bliver liggende med vilje i syv dage, men ikke laengere.

Begge er pakket ind og maa aldrig vaelte opstarten. En feed der ikke kan rydde
op er stadig bedre end en API der ikke starter.

Migreringen er efterproevet idempotent: den koerer ved HVER opstart, og anden
gang goer den intet.
EOF
git add -- apps/api/jarvis_api/app.py tests/test_notifikations_opstart.py
/opt/conda/envs/ai/bin/python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message-file /tmp/notif13.txt \
  --path apps/api/jarvis_api/app.py --path tests/test_notifikations_opstart.py
```

---

## Efter planen

- Deploy: push til `origin` OG `ct105`. CT105-genstart kun bag en vagt der tjekker at der er 0 aktive synlige runs, i SAMME kommando.
- Desk-udgivelse: bump `apps/jarvis-desk/package.json`, commit, DEREFTER tag `jarvis-desktop-vX`, `npm run package:linux`, `sudo -n dpkg -i`, genstart med `setsid /opt/J.A.R.V.I.S/jarvis-desktop`.
- Mobil: nyt build efter Task 11.
- Se feeden virke med rigtige data, ikke kun i test — `verify_visual_before_done`.

## Holdt ude med vilje

At app-opdateringer kræver at man går ud og ind af appen. Push-vejen blev bygget 20/9 og er brudt et sted. Det er en fejljagt med måling, ikke et designspørgsmål, og den hører til sin egen opgave med `superpowers:systematic-debugging`.

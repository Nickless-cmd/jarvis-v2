"""Tests for de udskilte fil-tool executors + encryption-aware I/O-helpers."""
from __future__ import annotations

import os

import pytest


def test_ws_helpers_plaintext_roundtrip(tmp_path) -> None:
    from core.tools.file_tools_exec import _ws_read_text, _ws_write_text, _ws_path_exists
    p = tmp_path / "note.md"
    _ws_write_text(p, "hej verden")
    assert _ws_path_exists(p) is True
    assert _ws_read_text(p) == "hej verden"
    assert _ws_read_text(tmp_path / "nope.md") is None


def test_exec_read_file_plaintext(tmp_path) -> None:
    from core.tools.file_tools_exec import _exec_read_file
    p = tmp_path / "f.txt"
    p.write_text("indhold", encoding="utf-8")
    res = _exec_read_file({"path": str(p)})
    assert res["status"] == "ok"
    assert res["text"] == "indhold"


def test_exec_read_file_missing(tmp_path) -> None:
    from core.tools.file_tools_exec import _exec_read_file
    res = _exec_read_file({"path": str(tmp_path / "missing.txt")})
    assert res["status"] == "error"
    assert "not found" in res["error"].lower()


def test_ws_helpers_member_enc_roundtrip(isolated_runtime, tmp_path, monkeypatch) -> None:
    """Member .enc læses/skrives transparent via de udskilte helpers (§16)."""
    from core.identity.users import add_user
    from core.tools import file_tools_exec as fx
    import core.services.keyring_store as ks

    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")

    p = tmp_path / "workspaces" / "mikkel" / "MEMORY.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    fx._ws_write_text(p, "- mikkels note\n")
    assert (tmp_path / "workspaces" / "mikkel" / "MEMORY.md.enc").exists()
    assert not p.exists()
    assert fx._ws_path_exists(p) is True
    assert fx._ws_read_text(p) == "- mikkels note\n"


def test_exec_read_file_decrypts_member_enc(isolated_runtime, tmp_path, monkeypatch) -> None:
    """read_file-toolet dekrypterer en members .enc-fil efter flip (§16)."""
    from core.identity.users import add_user
    from core.tools import file_tools_exec as fx
    import core.services.keyring_store as ks

    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(ks, "_keyring", lambda: None)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVISX_ENCRYPT_WORKSPACES", "1")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")

    p = tmp_path / "workspaces" / "mikkel" / "USER.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    fx._ws_write_text(p, "hemmelig profil")
    res = fx._exec_read_file({"path": str(p)})
    assert res["status"] == "ok"
    assert res["text"] == "hemmelig profil"


# ── Read-back: mutationen skal være selv-bevisende (10. sep 2026) ──────────
#
# Baggrund: R2 heed-rate var 17–26%, median 27 minutter fra advarsel til første
# kig. Hintet («kør verify_file_contains») fandtes allerede og flyttede intet,
# fordi et hint er en OPFORDRING. `edit_file` returnerede en PÅSTAND fra
# værktøjet (`replacements: 1`), ikke et bevis fra disken. Testene her binder
# at resultatet nu bærer filen som den FAKTISK står — og at det siger højt når
# den ikke gør.


def test_edit_file_readback_comes_from_disk(tmp_path) -> None:
    from core.tools import file_tools_exec as fx
    p = tmp_path / "note.txt"
    p.write_text("linje et\nlinje to\nlinje tre\n", encoding="utf-8")

    res = fx._exec_edit_file({
        "path": str(p), "old_text": "linje to", "new_text": "LINJE TO",
    })

    assert res["status"] == "ok"
    assert res["replacements"] == 1
    assert res["readback"] is True
    # Beviset skal komme fra DISKEN, ikke fra argumentet.
    assert "LINJE TO" in p.read_text(encoding="utf-8")
    assert "LINJE TO" in res["text"]
    assert "»" in res["text"], "ændringen skal markeres i udsnittet"


def test_edit_file_readback_flags_a_change_that_never_landed(tmp_path, monkeypatch) -> None:
    """Kernen i fixet: værktøjet kan tro det gik — read-back'en siger sandheden.

    Uden dette ville en tavs skrivefejl blive bygget videre på, og først blive
    opdaget 27 minutter senere (median) eller slet ikke.
    """
    from core.tools import file_tools_exec as fx
    p = tmp_path / "note.txt"
    p.write_text("original\n", encoding="utf-8")
    monkeypatch.setattr(fx, "_ws_write_text", lambda *_a, **_k: None)

    res = fx._exec_edit_file({"path": str(p), "old_text": "original", "new_text": "ændret"})

    assert res["status"] == "ok"       # værktøjet melder succes ...
    assert res["readback"] is False    # ... disken siger nej
    assert "står IKKE" in res["text"]
    assert "original" in res["text"], "readback'en skal vise hvad der FAKTISK står"


def test_edit_file_readback_shows_a_deletion(tmp_path) -> None:
    """En sletning har ingen new_text at søge efter — vinduet rammes via gammel offset."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "note.txt"
    p.write_text("a\nb\nSLET MIG\nc\nd\n", encoding="utf-8")

    res = fx._exec_edit_file({"path": str(p), "old_text": "SLET MIG\n", "new_text": ""})

    assert res["status"] == "ok"
    assert res["readback"] is True
    assert "SLET MIG" not in p.read_text(encoding="utf-8")
    assert "c" in res["text"], "udsnittet skal vise stedet hvor linjen forsvandt"


def test_write_file_readback_from_disk(tmp_path) -> None:
    from core.tools import file_tools_exec as fx
    p = tmp_path / "out.txt"

    res = fx._exec_write_file({"path": str(p), "content": "alpha\nbeta\ngamma\n"})

    assert res["status"] == "ok"
    assert res["readback"] is True
    assert res["line_count"] == 4          # tre linjer + den afsluttende tomme
    assert "alpha" in res["text"]
    assert p.read_text(encoding="utf-8") == "alpha\nbeta\ngamma\n"


def test_write_file_readback_flags_mismatch(tmp_path, monkeypatch) -> None:
    """Filen KAN læses, men indholdet er ikke det vi skrev → sig det højt."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "out.txt"
    monkeypatch.setattr(
        fx, "_ws_write_text",
        lambda path, content: path.write_text("noget ANDET", encoding="utf-8"),
    )

    res = fx._exec_write_file({"path": str(p), "content": "noget"})

    assert res["status"] == "ok"
    assert res["readback"] is False
    assert "afviger" in res["text"], "skal sige at indholdet ikke matcher"


def test_write_file_readback_flags_unreadable_file(tmp_path, monkeypatch) -> None:
    """En tavs skrivefejl må ikke blive tavs: filen findes ikke bagefter.

    Uden dette gren ville `readback`-flaget mangle helt, og et totalt svigt
    ville se ud som en helt almindelig skrivning.
    """
    from core.tools import file_tools_exec as fx
    p = tmp_path / "out.txt"
    monkeypatch.setattr(fx, "_ws_write_text", lambda *_a, **_k: None)

    res = fx._exec_write_file({"path": str(p), "content": "noget"})

    assert res["status"] == "ok"
    assert res["readback"] is False
    assert "kunne IKKE læses" in res["text"]


def test_readback_is_bounded(tmp_path) -> None:
    """Read-back'en må ikke sprænge konteksten på en stor fil."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "big.txt"
    p.write_text("\n".join(f"linje {i} " + "x" * 200 for i in range(200)), encoding="utf-8")

    res = fx._exec_edit_file({
        "path": str(p), "old_text": "linje 100 ", "new_text": "LINJE 100 ",
    })

    assert res["status"] == "ok"
    assert len(res["text"]) < fx._READBACK_MAX_CHARS + 400


def test_verify_hint_points_at_the_readback(monkeypatch) -> None:
    """Hintet må ikke sende Jarvis ud i et ekstra læs for noget han HAR fået."""
    from core.tools.simple_tools import _verify_hint_for
    hint = _verify_hint_for("edit_file", {
        "status": "ok", "path": "/tmp/x.txt", "replacements": 1, "readback": True,
    })
    assert "Readback" in hint
    assert "verify_file_contains" not in hint


# ─────────────────────────────────────────────────────────────────────────
# Linjetallene bag «+12 −4» (14/9-2026)
#
# Bjørn vil have Claude Codes rundelinje: «ran a command, edited 3 files
# +12 −4». Den linje er MEKANISK i CC — den bygges af værktøjernes egne
# resultater, og det er derfor den står der med det samme.
#
# Huset havde allerede en rundelinje i begge apps («Kørte 2 ting»). Det der
# manglede var ikke en model, men TAL: `edit_file` returnerede `path`,
# `match_count` og previews — ingen steder stod hvor meget der blev ændret.
#
# Tallene følger git-diff-semantik: en ændring INDEN i én linje er +1 −1,
# ikke 0. Det er ikke en tilnærmelse — det er sådan en diff tæller.
# ─────────────────────────────────────────────────────────────────────────

from core.tools.file_tools_exec import linjetal  # noqa: E402


def test_en_linje_byttet_er_plus_en_minus_en():
    """git tæller en ændret linje som én slettet og én tilføjet."""
    assert linjetal("gammel", "ny", 1) == (1, 1)


def test_en_aendring_INDEN_i_en_linje_er_ogsaa_plus_en_minus_en():
    """«foo» → «foobar» roerer én linje. Nul ville skjule aendringen helt."""
    assert linjetal("foo", "foobar", 1) == (1, 1)


def test_flere_linjer_taelles_hver_for_sig():
    assert linjetal("a\nb\nc", "x\ny", 1) == (2, 3)


def test_en_ren_SLETNING_tilfoejer_ingenting():
    """Tom ny tekst er en sletning — ikke «én tom linje tilfoejet»."""
    assert linjetal("a\nb", "", 1) == (0, 2)


def test_en_ren_TILFOEJELSE_fjerner_ingenting():
    assert linjetal("", "a\nb\nc", 1) == (3, 0)


def test_replace_all_ganger_med_antal_traef():
    """Tre erstatninger af samme to-linjers blok er seks linjer roert."""
    assert linjetal("a\nb", "x\ny", 3) == (6, 6)


def test_nul_erstatninger_roerer_intet():
    assert linjetal("a", "b", 0) == (0, 0)


def test_taeller_som_claude_desktop():
    """Claude Desktop 1:1 (Bjoern 19/9-2026): linjeskift + 1, saa «a\\n» er
    TO linjer hos dem (c980da984-…js). Testen stod foer paa det modsatte —
    «en afsluttende newline er ikke en linje» — og samme redigering viste ét
    tal her og et andet i Claude Desktop."""
    assert linjetal("a\n", "b\n", 1) == (2, 2)
    assert linjetal("", "", 1) == (0, 0)


def test_edit_resultatet_BAERER_linjetallene(tmp_path) -> None:
    """Kilde-vagten er ikke nok: tallene skal ud i det resultat klienterne ser.

    Et regnestykke ingen kalder er husets hyppigste fejl — og her ville den
    vise sig som en rundelinje der bare siger «redigerede 3 filer» for evigt.
    """
    from core.tools import file_tools_exec as fx
    p = tmp_path / "f.txt"
    p.write_text("a\nb\nc\n", encoding="utf-8")
    res = fx._exec_edit_file({"path": str(p), "old_text": "a\nb", "new_text": "x"})
    assert res["status"] == "ok"
    assert res["linjer_tilfoejet"] == 1
    assert res["linjer_fjernet"] == 2


def test_write_resultatet_BAERER_linjetallene(tmp_path) -> None:
    """En NY fil tilfoejer alt og fjerner intet."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "ny.txt"
    res = fx._exec_write_file({"path": str(p), "content": "en\nto\ntre\n"})
    assert res["status"] == "ok"
    # Claude Desktops regel: linjeskift + 1 — den afsluttende newline taeller.
    assert res["linjer_tilfoejet"] == 4
    assert res["linjer_fjernet"] == 0


def test_write_OVER_en_fil_fjerner_den_gamle(tmp_path) -> None:
    """Overskrivning er ikke en tilfoejelse. Talte vi kun det nye, ville
    linjen sige «+3» om en handling der ogsaa slettede fem linjer."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "f.txt"
    p.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
    res = fx._exec_write_file({"path": str(p), "content": "en\nto\n"})
    assert res["status"] == "ok"
    # Claude Desktops regel: linjeskift + 1 (se test_taeller_som_claude_desktop).
    assert res["linjer_tilfoejet"] == 3
    assert res["linjer_fjernet"] == 6


def test_en_FEJLET_edit_baerer_ingen_tal(tmp_path) -> None:
    """Nul er et tal og ville staa i linjen som «+0 −0» — en handling der ikke
    skete skal slet ikke taelle med."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "f.txt"
    p.write_text("abc", encoding="utf-8")
    res = fx._exec_edit_file({"path": str(p), "old_text": "findes-ikke", "new_text": "x"})
    assert res["status"] == "error"
    assert "linjer_tilfoejet" not in res


# ─────────────────────────────────────────────────────────────────────────
# Linjeinterval i read_file (10/11-2026)
#
# MAALT i drift: en researcher fik opgaven «citer filnavn og linjenummer for
# hvert fund». Den bad om linje 418-650, fik hele filen fra toppen (klippet
# ved MAX_READ_CHARS) og svarede: «jeg kan ikke citere betingelser uden at
# gætte». Værktøjet IGNOREREDE argumentet — skemaet havde kun `path`, og
# ukendte argumenter blev ikke afvist, bare kastet væk.
#
# Det er den samme fejlform som resten af dagen: en kapacitet modellen
# forventer, som værktøjet tier om. Testene her binder BEGGE halvdele —
# at skemaet annoncerer intervallet, og at det bliver laest.
# ─────────────────────────────────────────────────────────────────────────


def test_read_file_honours_a_line_range(tmp_path) -> None:
    """Et interval giver praecis de linjer — ikke hele filen fra toppen."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "f.txt"
    p.write_text("en\nto\ntre\nfire\nfem\n", encoding="utf-8")

    res = fx._exec_read_file({"path": str(p), "start_line": 2, "end_line": 4})

    assert res["status"] == "ok"
    assert res["text"] == "to\ntre\nfire"
    # Agenten skal kunne CITERE det den laeste: linje N i teksten er
    # start_line + N - 1.
    assert res["start_line"] == 2
    assert res["end_line"] == 4
    assert res["total_lines"] == 6  # fem linjer + den afsluttende tomme


def test_read_file_without_a_range_is_unchanged(tmp_path) -> None:
    """Uden interval opfoerer værktøjet sig praecis som før — ingen regression."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "f.txt"
    p.write_text("en\nto\ntre\n", encoding="utf-8")

    res = fx._exec_read_file({"path": str(p)})

    assert res["status"] == "ok"
    assert res["text"] == "en\nto\ntre\n"
    assert "start_line" not in res
    assert "truncated" not in res


def test_read_file_reaches_the_middle_of_a_file_it_could_not_read_whole(tmp_path) -> None:
    """Kernen i fixet: midten af en stor fil var UTILGAENGELIG for en agent.

    Uden intervallet fik den de foerste MAX_READ_CHARS tegn og havde ingen vej
    til resten — praecis den tilstand agenten beskrev som sin blocker.
    """
    from core.tools import file_tools_exec as fx
    from core.tools.simple_tools import MAX_READ_CHARS

    p = tmp_path / "big.txt"
    linjer = [f"linje {i} " + "x" * 100 for i in range(1, 1000)]
    p.write_text("\n".join(linjer), encoding="utf-8")
    assert p.stat().st_size > MAX_READ_CHARS, "testen kraever en fil over graensen"

    hel = fx._exec_read_file({"path": str(p)})
    assert hel["truncated"] is True
    assert "linje 900" not in hel["text"], "hele filen kan pr. definition ikke laeses"

    interval = fx._exec_read_file({"path": str(p), "start_line": 900, "end_line": 902})

    assert interval["status"] == "ok"
    assert "linje 900" in interval["text"]
    assert interval["start_line"] == 900
    assert "truncated" not in interval


def test_read_file_clamps_an_end_line_past_the_file(tmp_path) -> None:
    """En slutlinje forbi filens ende er ikke en fejl — den klippes."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "f.txt"
    p.write_text("en\nto\n", encoding="utf-8")

    res = fx._exec_read_file({"path": str(p), "start_line": 2, "end_line": 9999})

    assert res["status"] == "ok"
    assert res["text"] == "to\n"


def test_read_file_rejects_a_range_that_runs_backwards(tmp_path) -> None:
    """En baglaens interval er en fejl — ikke et tomt svar der ligner «ingen fund»."""
    from core.tools import file_tools_exec as fx
    p = tmp_path / "f.txt"
    p.write_text("en\nto\ntre\n", encoding="utf-8")

    res = fx._exec_read_file({"path": str(p), "start_line": 3, "end_line": 1})

    assert res["status"] == "error"
    assert "after end_line" in res["error"]


def test_the_schema_ANNOUNCES_the_range() -> None:
    """Vagten mod den oprindelige fejl: kapaciteten skal vaere ANNONCERET.

    En implementeret men uannonceret parameter er stadig usynlig for modellen —
    og det var praecis fejlen: agenten bad om et interval, værktøjet tav.
    """
    from core.tools.simple_tools import get_tool_definitions

    katalog = {t["function"]["name"]: t for t in get_tool_definitions()}
    props = katalog["read_file"]["function"]["parameters"]["properties"]

    assert "start_line" in props
    assert "end_line" in props
    assert props["start_line"]["type"] == "integer"
    assert props["end_line"]["type"] == "integer"
    # `path` er stadig det eneste paakraevede felt.
    assert katalog["read_file"]["function"]["parameters"]["required"] == ["path"]



# ── Skrive-stien skal selv registrere filen som læst (14/11-2026) ───────────
#
# Målt 14/11-2026 i events: 50 af 447 `guard_blocked` på `edit_file` kom efter
# en `write_file` med status ok på SAMME absolutte sti i SAMME run. Konkret:
# run `visible-57a5bba8762e4c7cbe3cda3da3b17ef4` skrev
# `tests/test_karakter_levers.py` 19:38:58 og blev afvist 19:39:13 — femten
# sekunder senere, på en fil den lige havde skrevet.
#
# Årsagen var ikke at vagten var for streng. Den var at skrive-stien kun kaldte
# `_record_active_file` (desk-fil-træet) og aldrig `record_read` (vagtens nøgle).
# Vagten spurgte «har du læst den?» om en fil der lige var skrevet af samme
# kalder — et spørgsmål hvis svar var indlysende, men som ingen havde noteret.


def test_en_fil_der_LIGE_er_skrevet_kan_redigeres(tmp_path) -> None:
    """Kernen i fejlen: write_file efterfulgt af edit_file på samme sti.

    `.py` er valgt med vilje — det er en beskyttet endelse, så vagten faktisk
    fyrer. En `.txt` ville passere uanset og gøre testen tom.
    """
    from uuid import uuid4

    from core.services.read_before_write_guard import was_read
    from core.tools import file_tools_exec as fx

    # Unik session pr. kørsel: shared_cache er fælles for hele maskinen, og en
    # fast nøgle ville lade en tidligere kørsel gøre testen grøn.
    sid = f"prove-skrevet-{uuid4().hex[:10]}"
    p = tmp_path / "modul.py"

    foerste = fx._exec_write_file(
        {"path": str(p), "content": "en = 1\nto = 2\n", "_runtime_session_id": sid},
    )
    assert foerste["status"] == "ok", foerste
    assert was_read(str(p), sid) is True, (
        "skrivningen registrerede ikke filen som læst — næste edit vil blive afvist"
    )

    anden = fx._exec_edit_file(
        {
            "path": str(p),
            "old_text": "en = 1",
            "new_text": "en = 9",
            "_runtime_session_id": sid,
        },
    )
    assert anden["status"] == "ok", f"edit blev afvist efter egen skrivning: {anden}"
    assert "en = 9" in p.read_text(encoding="utf-8")


def test_en_FEJLET_skrivning_registreres_ikke_som_laest(tmp_path, monkeypatch) -> None:
    """Den anden halvdel — og den der gør rettelsen sikker.

    Registrerede vi en fejlet eller blokeret skrivning som en læsning, ville den
    NÆSTE skrivning passere uden at nogen havde set filens indhold. Vagten ville
    altså slås til præcis når den skal virke, og grundlaget ville være en
    skrivning der ikke fandt sted.
    """
    from uuid import uuid4

    from core.services.read_before_write_guard import was_read
    from core.tools import file_tools_exec as fx

    sid = f"prove-fejl-{uuid4().hex[:10]}"
    p = tmp_path / "modul.py"

    def _kaster(path, content):
        raise OSError("disken er fuld")

    monkeypatch.setattr(fx, "_ws_write_text", _kaster)

    # Uanset om fejlen propagerer eller fanges og returneres: udfaldet må ikke
    # vaere `ok`, og filen må ikke staa som læst.
    try:
        ud = fx._exec_write_file(
            {"path": str(p), "content": "x = 1\n", "_runtime_session_id": sid},
        )
    except OSError:
        ud = {"status": "error"}
    assert ud.get("status") != "ok", f"skrivningen fejlede men meldte ok: {ud}"
    assert was_read(str(p), sid) is False, (
        "en fejlet skrivning blev registreret som læsning"
    )


def test_to_redigeringer_i_traek_kraever_ingen_kunstig_laesning(tmp_path) -> None:
    """Edit-grenen skal ogsaa efterlade filen læst.

    Samme defekt som write_file-grenen, blot et skridt senere: efter en
    gennemført `edit_file` er filens indhold kendt af den der redigerede den.
    Uden registreringen ville den anden redigering i træk blive afvist, og
    kalderen måtte indsætte en `read_file` hvis eneste formål var at fortælle
    vagten noget den allerede vidste.

    Testen er skrevet fordi mutationen «fjern registreringen fra edit-grenen»
    ellers slap gennem hele suiten — grenen var dekoration.

    Isolationen er nødvendig: `read_file`'s egen nøgle er frisk i 600 s og
    ville maskere fejlen, så testen blev grøn af den forkerte grund. Derfor
    læses filen under sessionen `default` (som `_was_read` falder tilbage til),
    mens redigeringen kører under sin EGEN session. Efter redigeringen slettes
    `default`-nøglen — nu er redigeringens egen registrering den eneste mulige
    kilde til «læst».
    """
    from uuid import uuid4

    from core.services import shared_cache
    from core.services.read_before_write_guard import _cache_key, record_read, was_read
    from core.tools import file_tools_exec as fx

    sid = f"prove-to-edits-{uuid4().hex[:10]}"
    p = tmp_path / "modul.py"
    p.write_text("en = 1\nto = 2\ntre = 3\n", encoding="utf-8")
    abs_sti = str(p.resolve())

    # Læsningen registreres under `default`, så redigeringen under `sid`
    # passerer via vagtens fallback.
    record_read(abs_sti, session_id="default")
    foerste = fx._exec_edit_file(
        {"path": str(p), "old_text": "en = 1", "new_text": "en = 9",
         "_runtime_session_id": sid},
    )
    assert foerste["status"] == "ok", foerste

    # Fjern fallback'en. Tilbage er kun hvad redigeringen selv satte under `sid`.
    shared_cache.delete(_cache_key("default", abs_sti))
    assert was_read(abs_sti, sid) is True, (
        "edit registrerede ikke filen som læst — næste redigering ville blive afvist"
    )

    anden = fx._exec_edit_file(
        {"path": str(p), "old_text": "to = 2", "new_text": "to = 8",
         "_runtime_session_id": sid},
    )
    assert anden["status"] == "ok", f"anden edit blev afvist: {anden}"
    tekst = p.read_text(encoding="utf-8")
    assert "en = 9" in tekst and "to = 8" in tekst


def test_ende_til_ende_gennem_execute_tool(tmp_path) -> None:
    """Den vej runnet faktisk gik — gennem dispatcheren, ikke exec-funktionen.

    Fejlen blev målt i events som `write_file` → `edit_file` gennem
    `execute_tool`, og det er derfor fixet skal bevises dér. En test der kun
    kalder `_exec_edit_file` kan være grøn selv om dispatcheren,
    argument-normaliseringen eller gate-kæden ændrer noget undervejs.
    """
    from uuid import uuid4

    from core.tools.simple_tools import execute_tool

    sid = f"prove-e2e-{uuid4().hex[:10]}"
    p = tmp_path / "karakter_levers.py"

    skriv = execute_tool(
        "write_file",
        {"path": str(p), "content": "LEVER = 1\n", "_runtime_session_id": sid},
    )
    assert skriv.get("status") == "ok", skriv

    rediger = execute_tool(
        "edit_file",
        {"path": str(p), "old_text": "LEVER = 1", "new_text": "LEVER = 2",
         "_runtime_session_id": sid},
    )
    assert rediger.get("status") == "ok", (
        f"edit_file blev afvist efter egen write_file: {rediger}"
    )
    assert "LEVER = 2" in p.read_text(encoding="utf-8")

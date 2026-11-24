"""Test: personality_vector write-guard stripper snake_case maskin-id (Jarvis-spec #2)."""
from __future__ import annotations


def test_human_filter_strips_machine_ids():
    # Genskab _human-filterets logik (samme regel som write-guarden i update-stien):
    # snake_case event-navne droppes, menneskelæsbare (m. mellemrum) består.
    def _human(items):
        out = []
        for x in items:
            s = str(x).strip()
            core = s.split(":", 1)[-1].strip()
            if core and " " not in core and core.count("_") >= 2:
                continue
            out.append(x)
        return out

    strengths = [
        "sensory_archive_analysis",                       # maskin-id → drop
        "plugin_container_process_kill_load_reduction_success",  # maskin-id → drop
        "tålmodig og grundig fejlsøgning",                # menneske → behold
    ]
    mistakes = [
        "forgetting_to_stage_changes_before_commit",      # maskin-id → drop
        "Svar bliver for lange i simple repo-opgaver",    # menneske → behold
        "genstart løste ikke problemet",                  # menneske → behold
    ]
    assert _human(strengths) == ["tålmodig og grundig fejlsøgning"]
    assert _human(mistakes) == [
        "Svar bliver for lange i simple repo-opgaver",
        "genstart løste ikke problemet",
    ]


def test_personality_vector_module_imports():
    # Sikrer write-guarden ikke brød modulet.
    import core.services.personality_vector as pv
    assert hasattr(pv, "_merge_vector")


def test_dommerens_bevis_vindue_viser_den_aegte_slutning():
    """Dommeren må ikke kunne læse et KLIP som et afbrudt svar.

    Målt 20/11-2026: `assistant_response[:400]` blev sendt til dommeren uden
    markering. 59 % af mine svar over 400 tegn (6.214 af 10.494) ender midt i
    et ord ved præcis den grænse, så dommeren skrev «Afbrød sit eget svar midt
    i sætningen» ind som en gentagen fejl — 14 gange — mens beskederne i
    `chat_messages` slutter korrekt. Fejlen var i målingen.
    """
    from core.services.personality_vector import _bevis_vindue

    # Slutningen er det der AFGØR spørgsmålet, og den ligger langt efter 400.
    slutning = "Det er derfor målingen kom først."
    svar = ("og den skal lukkes med et konkret tal. " * 60) + slutning
    assert len(svar) > 2000

    # Forudsætningen for testen: et råt [:400]-klip hugger midt i et ord.
    raat = svar[:400]
    assert raat[-1].isalnum() and raat[-2].isalnum(), "klippet ramte ikke midt i et ord"

    bevis = _bevis_vindue(svar)

    # 1) Den ægte slutning er med — så afbrydelse kan afgøres.
    assert bevis.rstrip().endswith(slutning), bevis[-80:]
    # 2) Klippet er NAVNGIVET, så det ikke læses som Jarvis' eget stop.
    assert "VINDUET" in bevis
    assert "afbryder" in bevis
    # 3) Beviset slutter ikke midt i et ord (det gjorde det rå klip).
    assert not (bevis[-1].isalnum() and bevis[-2].isalnum())


def test_kort_svar_gaar_uaendret_igennem():
    """Under loftet må beviset ikke ændres — ingen støj på korte svar."""
    from core.services.personality_vector import _bevis_vindue

    kort = "Kort og korrekt svar."
    assert _bevis_vindue(kort) == kort


def test_en_bevist_forkert_post_kan_traekkes_tilbage():
    """Selvmodellen skal kunne AFLÆRE, ikke kun lære.

    Målt 20/11-2026: 14 af 20 poster i `recurring_mistakes` var «Afbrød sit
    eget svar midt i sætningen». De kom fra dommerens klippede bevis-vindue —
    de citerede beskeder slutter korrekt i `chat_messages` (fx 885 tegn og et
    fuldstændigt spørgsmål). Men listen kunne kun vokse, så hver falsk post
    blev et læringsmål, som hjerteslaget gjorde til en opgave. Uden denne gren
    er en falsk selvdom evig.
    """
    from core.services.personality_vector import _merge_vector

    falsk = "Afbrød sit eget svar midt i sætningen ('...Den '), så intet blev leveret"
    aegte = "Gættede på kolonnenavne i runtime_tasks før schemaet var læst"
    current = {"recurring_mistakes": [falsk, aegte]}

    merged = _merge_vector(current, {"retire_mistakes": [falsk]})
    assert merged["recurring_mistakes"] == [aegte]

    # En post der ikke findes må ikke gøre noget — en afvigelse i dommerens
    # citat må ikke tømme listen.
    uaendret = _merge_vector(current, {"retire_mistakes": ["findes ikke"]})
    assert uaendret["recurring_mistakes"] == [falsk, aegte]

    # Uden retire-feltet opfører listen sig præcis som før.
    assert _merge_vector(current, {})["recurring_mistakes"] == [falsk, aegte]

    # `retire_mistakes` er en INSTRUKS, ikke et felt der gemmes i vektoren.
    assert "retire_mistakes" not in merged


# ── Tre felter var uopnåelige fra tomme (målt 25/9-2026) ───────────────────
#
# Over ALLE 1007 versioner af vektoren på CT105:
#
#     learned_preferences      ikke-tom i 728 versioner
#     confidence_by_domain     ikke-tom i   1
#     recurring_mistakes       ikke-tom i   0
#     strengths_discovered     ikke-tom i   0
#
# Skrivevejen virkede — samme funktion, samme merge-logik. Forskellen stod i
# PROMPTEN: `learned_preferences` havde en additiv instruktion («tilføj nye,
# behold gamle»), de tre andre havde en betingelse der forudsatte en værdi der
# allerede var der.
#
# «Tilføj kun hvis gentaget» på en TOM liste er en bootstrap-låsning: den
# første forekomst skrives aldrig, så der bliver aldrig en anden. Og
# `_merge_vector` deduplikerer i forvejen (`if item not in merged`), så listen
# kan slet ikke udtrykke «gentaget» ved antal — feltet er strukturelt
# «observerede fejl», ikke «fejl talt mere end én gang».


def _prompt() -> str:
    from core.services.personality_vector import _build_update_prompt
    return _build_update_prompt()


def test_ingen_betingelse_forudsaetter_en_vaerdi_der_ikke_findes():
    """Vagten mod at bootstrap-låsningen sniger sig ind igen."""
    p = _prompt()
    for forbudt in ("kun hvis gentaget", "kun ved tydelig evidens"):
        assert forbudt not in p, (
            f"«{forbudt}» kan ikke opfyldes fra en tom liste — "
            "den første post bliver aldrig skrevet, så der kommer aldrig en anden"
        )


def test_de_tre_felter_har_en_additiv_instruktion():
    """Samme form som `learned_preferences`, der SOM DEN ENESTE virkede."""
    p = _prompt()
    for felt in ("recurring_mistakes", "strengths_discovered"):
        assert felt in p
    # Begge lister skal sige at også første forekomst tæller.
    assert p.count("også første gang du ser den") == 2
    # Og dict'en skal kunne få sit første domæne.
    assert "Et domæne uden et tal kan aldrig justeres senere" in p


def test_konservatismen_gaelder_TAL_ikke_tomme_felter():
    """«Vær konservativ — kun opdatér det der faktisk ændrede sig» ramte også
    et tomt felt: der var jo ikke sket en ændring, kun en begyndelse."""
    p = _prompt()
    assert "et TOMT felt er ikke en værdi der skal bevares" in p


def test_maskin_navne_frarades_i_prompten():
    """Skrive-vagten (`_human`) strippede snake_case — rod-kilden til
    maskin-id-lækken i den synlige prompt. Nu står det også i prompten, så
    modellen ikke producerer det der alligevel bliver kasseret."""
    p = _prompt()
    assert "sensory_archive_analysis" in p and "menneskelig form" in p


def test_merge_deduplikerer_saa_en_gentagelse_ikke_bliver_to_poster():
    """Grunden til at «gentaget» aldrig kunne måles ved antal."""
    from core.services.personality_vector import _merge_vector

    ud = _merge_vector(
        {"recurring_mistakes": '["glemmer at køre suiten"]'},
        {"recurring_mistakes": ["glemmer at køre suiten", "ny fejl"]},
    )
    assert ud["recurring_mistakes"] == ["glemmer at køre suiten", "ny fejl"]


# ── Svaret naaede sjældent frem (målt 26/9-2026) ───────────────────────────


def test_taenkningen_er_slaaet_FRA_og_budgettet_raekker():
    """Ræsonnementet åd svar-budgettet. Målt på CT105 mod
    `deepseek-v4.1-flash:cloud`, samme prompt og input:

        np=200            content=   0  thinking=  910  done=length
        np=600            content= 399  thinking=  263  done=stop
        np=600            content=   0  thinking= 2421  done=length
        np=1500           content=  53  thinking= 3203  done=stop
        np=600 think=off  content= 359  thinking=    0  done=stop  (3 af 3)

    Ræsonnementets længde svinger fra 263 til 3.203 tegn, så ethvert fast loft
    er et gæt — selv 600 slog fejl. Med `think: False` er der intet at betale
    for, og alle tre kald svarede med `recurring_mistakes` udfyldt.

    Det er den egentlige grund til at feltet aldrig har ændret sig. Ikke
    tærsklen i prompten.
    """
    import ast
    import inspect

    from core.services import personality_vector as PV

    traeet = ast.parse(inspect.getsource(PV._call_llm).lstrip())
    fundet = []
    for n in ast.walk(traeet):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value == "num_predict":
                    fundet.append(v.value)
    assert fundet, "num_predict findes ikke længere — er kaldet lagt om?"
    assert all(v >= 600 for v in fundet), (
        f"num_predict={fundet} er for lavt; ræsonnementet tæller med i "
        "budgettet og content kommer tom tilbage"
    )

    # Selve rettelsen: uden denne er ethvert loft et gæt.
    kilde = inspect.getsource(PV._call_llm)
    assert '"think": False' in kilde, (
        "tænkningen er slået til igen — ræsonnementet æder svar-budgettet, og "
        "kaldet falder tilbage på den deterministiske sti"
    )


def test_et_tomt_svar_logges_frem_for_at_tie(monkeypatch, caplog):
    """En tom `content` er ikke «intet at sige» — den er et afkortet svar.

    Uden logningen kunne de to ikke skelnes, og forskellen kostede at feltet
    stod tomt i månedsvis.
    """
    import json
    import logging

    from core.services import personality_vector as PV

    class _Svar:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"message": {"content": "", "thinking": "x" * 910},
                               "done_reason": "length"}).encode()

    monkeypatch.setattr(PV.urllib_request, "urlopen", lambda *a, **k: _Svar())

    with caplog.at_level(logging.WARNING):
        ud = PV._call_llm({"provider": "ollama", "model": "m", "base_url": "http://x"},
                          "system", "user")

    assert ud == ""
    assert any("tomt svar" in r.message for r in caplog.records), \
        "et afkortet svar blev slugt i tavshed"
    assert any("length" in str(r.args) for r in caplog.records), \
        "done_reason skal med — den siger HVORFOR det var tomt"


# ── Dommeren må ikke læse runnets PREVIEW som hele svaret (målt 20/11) ─────
#
# Run 54590 («Hvad siger vejret idag?» 11:53Z): dommeren fik work_preview —
# 320 tegn + dekorativ '…' efter «…knap tre timers dags» — læste klippet som
# afbrydelse og skrev «den ægte slutning klipper midt i ordet 'dags'» ind som
# gentagen fejl, mens den ægte besked (690 tegn) slutter fuldstændigt med
# «…AQI 1, «god».». Og det er ikke ét tilfælde: 19.415 af 26.295 previews i
# den levende base slutter med '…' (320 tegn: 15.359 · 319: 3.016 · 120: 861 ·
# 119: 162 — byte-klip-familier), så signaturen kan ikke være én længde.
# Rettelsen: kalder-kæden træder session_id igennem (den blev smidt væk ved
# kaldet til update_personality_vector_async), og den ægte besked læses med
# husets dekrypterende læser.


def _indsaet_besked(session: str, rolle: str, indhold: str) -> None:
    from core.runtime.db import connect

    with connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages (message_id, session_id, role, content, "
            "created_at, encrypted) VALUES (?, ?, ?, ?, ?, 0)",
            (f"msg-test-{session[-8:]}-{rolle}-{len(indhold)}", session, rolle,
             indhold, "2026-11-20T12:00:00+00:00"),
        )
        conn.commit()


def test_preview_opgraderes_til_den_aegte_besked(isolated_runtime):
    """Den ægte besked i sessionen VINDER over previewet.

    Previewet klippes midt i «dagslys» — præcis «dags…» som i målet — og
    hjælperen skal hente beskeden der slutter med «AQI 1, «god». 🧣».
    """
    from core.services.personality_vector import _hent_rigtigt_svar

    session = "chat-test-preview-aegte"
    aegte = (
        "Vejret bliver klart og køligt i aften — knap tre timers dagslys. "
        "Luftkvaliteten er i øvrigt i top: AQI 1, «god». 🧣"
    )
    _indsaet_besked(session, "user", "Hvad siger vejret idag?")
    _indsaet_besked(session, "assistant", aegte)

    preview = aegte[:aegte.index("dagslys") + 4] + "…"
    assert preview.endswith("dags…"), "testens klip ramte ikke midt i 'dagslys'"

    assert _hent_rigtigt_svar(session, preview) == aegte


def test_uden_session_bevaar_previewet_og_gaetter_ikke(isolated_runtime):
    """Ingen session → intet opslag → intet gæt. Previewet beholdes."""
    from core.services.personality_vector import _hent_rigtigt_svar

    preview = "Vejret bliver klart og køligt i aften — knap tre timers dags…"
    assert _hent_rigtigt_svar(None, preview) == preview
    assert _hent_rigtigt_svar("   ", preview) == preview


def test_preview_som_udklip_midt_i_beskeden_opgraderes(isolated_runtime):
    """Målt 23/11-2026: 230 af 368 previews matcher kun MIDT i beskeden.

    Previewet er arbejdets tekst — her klippet ud af beskedens midte — og
    den ægte besked skal VINDE, selvom den ikke starter med previewet.
    Præfiks-vagten alene fejlede i 86 % af runs og fodrede 17 «slutter
    midt i ordet»-poster i vektoren.
    """
    from core.services.personality_vector import _hent_rigtigt_svar

    session = "chat-test-preview-udklip"
    aegte = (
        "Du vil se den igen — så jeg kører et par kald først, mens du ser "
        "på farven. Alt står rigtigt: PWA'en serverer index-DWKJX0cL.js fra "
        "0.6.409, main er identisk med fjernen, og keyframen læser --accent "
        "ved både 0 % og 70 %, så ordene får farven hele vejen. Teksten her "
        "er skrevet på den kode der ligger live — ikke en jeg håber på."
    )
    _indsaet_besked(session, "assistant", aegte)

    preview = (
        "Alt står rigtigt: PWA'en serverer index-DWKJX0cL.js fra 0.6.409, "
        "main er identisk med fjernen, og keyframen læser …"
    )

    assert _hent_rigtigt_svar(session, preview) == aegte


def test_preview_der_intet_matcher_bliver_en_pladsholder(isolated_runtime):
    """Målt 23/11-2026: 86 af 368 previews matcher slet ingen besked.

    Det klippede preview var kilden til 17 «slutter midt i ordet»-poster.
    Det må ALDRIG vende tilbage som svar — dommeren får pladsholderen,
    der eksplicit siger at der er intet at bedømme.
    """
    from core.services.personality_vector import (
        _SVAR_IKKE_BEVIST,
        _hent_rigtigt_svar,
    )

    session = "chat-test-preview-pladsholder"
    _indsaet_besked(session, "assistant", "Et helt andet svar om noget andet.")
    preview = "Vejret bliver klart og køligt i aften — knap tre timers dags…"

    assert _hent_rigtigt_svar(session, preview) == _SVAR_IKKE_BEVIST


def test_dommerens_prompt_genkender_pladsholderen():
    """Pladsholderen er en MÅLING, ikke et svar — prompten må aldrig give
    dommeren lov til at citere den eller skrive en afbrudt-post ud fra den."""
    assert "SVARET KAN IKKE BEVISES" in _prompt()


# ── Det RÅ snit: `text_preview = text[:140]` uden '…' (målt 23/11-2026) ────
#
# Værnet ovenfor kiggede kun på det dekorative '…'. Men 6.903 af 26.295
# previews (26 %) slutter UDEN '…', og 3.467 af dem slutter uden afsluttende
# tegnsætning — altså midt i et ord eller midt i en sætning. Tre poster i
# vektoren citerer dem ordret: «det slutter med ordet 'en'», «…med 'fil'»,
# «…med 'Det var det ene krav'». Ingen af dem har en ellipse at gribe i.
#
# Signaturen kan ikke være «mangler punktum»: 2.043 previews ≥100 tegn
# slutter med tegnsætning, og mange af de øvrige slutter med en EMOJI
# (👍 🤖 🌙 😊) — de er HELE svar. Derfor: klip-LOFTET, og kun når teksten
# ikke slutter rent af sig selv.


def test_ser_klippet_ud_kender_loftet_men_ikke_emoji():
    """Vagten skal ramme det rå snit — og IKKE et helt svar der slutter med emoji."""
    from core.services.personality_vector import _ser_klippet_ud

    # Råt snit ved et målt loft, der stopper midt i et ord.
    assert _ser_klippet_ud("x" * 139 + "e")
    # Samme længde, men slutter af sig selv med emoji → HEL.
    assert not _ser_klippet_ud("x" * 138 + "e" + "👍")
    # Kort tekst er aldrig et klip, uanset hvad den slutter med.
    assert not _ser_klippet_ud("Kort svar uden punktum")
    # Det dekorative '…' er stadig en signatur.
    assert _ser_klippet_ud("Kort svar…")


def test_kliploftet_indeholder_ikke_chifferlaengder():
    """Loftet må kun komme fra klartekst (målt 24/11-2026).

    170 af 187 `enc:`-previews i `visible_runs` ligger i 483–519 tegn. I
    klartekst findes der nul rækker på 491/495/499 og én hver på 487/503 —
    og begge dem slutter rent. De fem værdier var base64-længder på
    krypterede previews, ikke klip, og de gjorde chiffertekst til «bevis»
    for en afbrydelse.
    """
    from core.services.personality_vector import _KLIP_LOFTER

    assert not (_KLIP_LOFTER & {487, 491, 495, 499, 503})


def test_krypteret_preview_bliver_aldrig_chiffertekst_for_dommeren(isolated_runtime):
    """Uden dekrypterbar nøgle skal dommeren have pladsholderen — ikke base64."""
    from core.services.personality_vector import _SVAR_IKKE_BEVIST, _hent_rigtigt_svar

    chiffer = "enc:v1:" + "QWxsZSBkaW5lIGJlc2tlZGVyIGVy" * 8
    assert _hent_rigtigt_svar("chat-ukendt-session", chiffer) == _SVAR_IKKE_BEVIST
    assert _hent_rigtigt_svar(None, chiffer) == _SVAR_IKKE_BEVIST


def test_raat_snit_uden_ellipse_opgraderes(isolated_runtime):
    """140-tegns-snittet uden '…' skal også opgraderes til den ægte besked."""
    from core.services.personality_vector import _hent_rigtigt_svar, _ser_klippet_ud

    session = "chat-test-raat-snit"
    aegte = (
        "Jeg har målt hele kæden: vagten fyrede aldrig, fordi den kun kiggede "
        "på det dekorative '…' og ikke på det rå snit ved 140 tegn. Nu henter "
        "den den ægte besked i stedet, så dommeren får en slutning der findes "
        "i virkeligheden og ikke et snit midt i et ord."
    )
    _indsaet_besked(session, "assistant", aegte)

    preview = aegte[:140]
    assert len(preview) == 140
    assert not preview.endswith("…"), "testen skal ramme det rå snit, ikke ellipsen"
    assert _ser_klippet_ud(preview)
    assert _hent_rigtigt_svar(session, preview) == aegte


def test_raat_snit_uden_match_bliver_pladsholder(isolated_runtime):
    """Kan det rå snit ikke bevises, må dommeren ikke se det som et svar."""
    from core.services.personality_vector import _SVAR_IKKE_BEVIST, _hent_rigtigt_svar

    session = "chat-test-raat-snit-uden-match"
    _indsaet_besked(session, "assistant", "Et helt andet svar om noget andet.")

    preview = (
        "Fem patches er reelt landet, men jeg mangler stadig at se om den "
        "lovede verifikation faktisk kører på den kode der ligger live nu, "
        "og om den kode er den samme som den jeg har i arbejdstræet her"
    )[:140]
    assert len(preview) == 140
    assert _hent_rigtigt_svar(session, preview) == _SVAR_IKKE_BEVIST


def test_helt_svar_ved_loftet_med_emoji_gaar_urort_igennem(isolated_runtime):
    """Et HELT svar på præcis 140 tegn der slutter med emoji må ikke røres."""
    from core.services.personality_vector import _hent_rigtigt_svar, _ser_klippet_ud

    krop = "Ord-animationen kører nu med 30 ms forskydning pr. ord og 220 ms i alt."
    helt = krop + " " * (139 - len(krop)) + "👍"
    assert len(helt) == 140, "testen skal ramme klip-loftet for at måle noget"
    assert not _ser_klippet_ud(helt)
    assert _hent_rigtigt_svar("chat-uden-opslag", helt) == helt


def test_stilistisk_ellipsis_loeser_sig_selv(isolated_runtime):
    """En ægte besked der stylistisk slutter med '…' må ikke mistænkeliggøres.

    Den brede signatur (endswith '…') rammer også ægte tekst — men beskeden
    matcher sit eget hoved og er ikke længere end inputtet, så den
    returneres uændret. Vagten, ikke signaturen, er sikkerheden.
    """
    from core.services.personality_vector import _hent_rigtigt_svar

    session = "chat-test-stil-ellipsis"
    besked = "Fortsættelsen følger i næste tur…"
    _indsaet_besked(session, "assistant", besked)

    assert _hent_rigtigt_svar(session, besked) == besked


def test_async_wrapperen_baerer_session_id():
    """Kædens søm: visible_runs HAR session_id — wrapperen må ikke smide den
    væk igen (det var præcis dér previewet blev til dommerens eneste bevis)."""
    import inspect

    from core.services.personality_vector import update_personality_vector_async

    params = inspect.signature(update_personality_vector_async).parameters
    assert "session_id" in params, "async wrapperen mistede session_id igen"


def test_dommerens_prompt_ser_den_aegte_slutning(monkeypatch, isolated_runtime):
    """Ende-til-ende: from_run med preview-input → dommerens prompt indeholder
    den ægte slutning («god». 🧣) og IKKE preview-halen («dags…»)."""
    from core.services import personality_vector as PV

    session = "chat-test-prompt-e2e"
    aegte = (
        "Vejret bliver klart og køligt i aften — knap tre timers dagslys. "
        "Luftkvaliteten er i øvrigt i top: AQI 1, «god». 🧣"
    )
    _indsaet_besked(session, "user", "Hvad siger vejret idag?")
    _indsaet_besked(session, "assistant", aegte)
    preview = aegte[:aegte.index("dagslys") + 4] + "…"
    assert preview.endswith("dags…")

    fang = {}
    monkeypatch.setattr(
        PV, "_resolve_local_llm_target", lambda: {"provider": "x", "model": "m"}
    )

    def _fang(target, system, user):
        fang["prompt"] = user
        return "{}"

    monkeypatch.setattr(PV, "_call_llm", _fang)

    PV.update_personality_vector_from_run(
        run_id="r-preview-e2e",
        session_id=session,
        user_message="Hvad siger vejret idag?",
        assistant_response=preview,
        outcome_status="completed",
    )

    prompt = fang["prompt"]
    assert "«god». 🧣" in prompt, "dommeren fik ikke den ægte slutning"
    assert "dags…" not in prompt, "preview-halen nåede dommeren"


# ── Pensionsvej for strengths_discovered og self_model_signals (20/11-2026) ──

_FALSK_DOM = "Afbrød sit eget svar midt i sætningen"


def test_pensioneret_styrke_baeres_ikke_videre_men_uberoerte_goer():
    from core.services.personality_vector import _merge_vector

    aegte = "Grundig fejlsøgning"
    current = {"strengths_discovered": [_FALSK_DOM, aegte]}

    merged = _merge_vector(current, {"retire_strengths": [_FALSK_DOM]})
    assert merged["strengths_discovered"] == [aegte]  # (a)
    assert "retire_strengths" not in merged

    # (b) ikke-pensioneret bæres stadig; ukendt post tømmer intet
    assert _merge_vector(current, {})["strengths_discovered"] == [_FALSK_DOM, aegte]
    assert _merge_vector(current, {"retire_strengths": ["findes ikke"]})[
        "strengths_discovered"
    ] == [_FALSK_DOM, aegte]


def test_styrke_pension_roerer_ikke_recurring_mistakes_og_omvendt():
    from core.services.personality_vector import _merge_vector

    current = {
        "strengths_discovered": [_FALSK_DOM],
        "recurring_mistakes": [_FALSK_DOM],  # identisk tekst i begge felter
    }
    s = _merge_vector(current, {"retire_strengths": [_FALSK_DOM]})
    assert s["strengths_discovered"] == []
    assert s["recurring_mistakes"] == [_FALSK_DOM]  # (c)

    m = _merge_vector(current, {"retire_mistakes": [_FALSK_DOM]})
    assert m["recurring_mistakes"] == []
    assert m["strengths_discovered"] == [_FALSK_DOM]


def _signal(sid: str, key: str, title: str) -> None:
    from core.runtime.db import upsert_runtime_self_model_signal

    upsert_runtime_self_model_signal(
        signal_id=sid, signal_type="strength", canonical_key=key, status="active",
        title=title, summary=title, rationale="t", source_kind="runtime-derived-support",
        confidence="medium", evidence_summary="e", support_summary="s",
        support_count=1, session_count=1,
        created_at="2026-11-20T01:00:00+00:00", updated_at="2026-11-20T01:00:00+00:00",
    )


def test_pensioneret_self_model_signal_forlader_overfladen(isolated_runtime):
    from core.runtime.db import get_runtime_self_model_signal
    from core.services.personality_vector import retire_self_model_signals
    from core.services.self_model_signal_tracking import (
        build_runtime_self_model_signal_surface,
    )

    _signal("sig-falsk", "k-falsk", f"Strength: {_FALSK_DOM}")
    _signal("sig-aegte", "k-aegte", "Strength: grundig fejlsøgning")

    retire_self_model_signals(["sig-falsk"], reason="Bevis-vinduet klippede; målefejl")

    falsk = get_runtime_self_model_signal("sig-falsk")
    assert falsk["status"] == "retired"
    assert "målefejl" in falsk["status_reason"]
    # (b) den uberørte er stadig aktiv og vises
    assert get_runtime_self_model_signal("sig-aegte")["status"] == "active"
    ids = [i["signal_id"] for i in build_runtime_self_model_signal_surface()["items"]]
    assert "sig-aegte" in ids and "sig-falsk" not in ids  # (a)


def test_pension_af_self_model_signal_fejler_hoejt(isolated_runtime):
    import pytest
    from core.runtime.db import get_runtime_self_model_signal
    from core.services.personality_vector import retire_self_model_signals

    _signal("sig-1", "k-1", "Strength: x y")
    with pytest.raises(ValueError):
        retire_self_model_signals(["sig-1"], reason="  ")
    with pytest.raises(ValueError):
        retire_self_model_signals([], reason="r")
    with pytest.raises(ValueError):  # ét ukendt id → intet ændres
        retire_self_model_signals(["sig-1", "findes-ikke"], reason="r")
    assert get_runtime_self_model_signal("sig-1")["status"] == "active"


# ── Skønnet må ikke overskrive en måling (20/11-2026) ───────────────────────


def test_selvrapport_flytter_ikke_en_maalt_vaerdi():
    """Målt 20/11-2026: v55864 bar 0,43 for «souls-build analyse» — skrevet af
    den mekaniske sti efter et run der faktisk gjorde noget. v55865, 3,9 s
    senere, stod der 0,38 igen: LLM-opdateringens eget skøn overskrev målingen.
    Skete det hver gang, kunne confidence aldrig akkumulere noget som helst."""
    from core.services.personality_vector import _merge_vector

    current = {"confidence_by_domain": '{"souls-build analyse": 0.43}'}
    merged = _merge_vector(current, {"confidence_by_domain": {"souls-build analyse": 0.38}})

    assert merged["confidence_by_domain"]["souls-build analyse"] == 0.43, (
        "skønnet overskrev en målt værdi — så kan confidence aldrig flytte sig"
    )


def test_selvrapport_saetter_stadig_et_nyt_domaene():
    """Filteret må ikke gøre vektoren død: et domæne der IKKE står der endnu er
    netop hvad selvrapporten skal kunne tilføje — som startpunkt, ikke som dom."""
    from core.services.personality_vector import _merge_vector

    current = {"confidence_by_domain": '{"python": 0.7}'}
    merged = _merge_vector(
        current, {"confidence_by_domain": {"python": 0.1, "nyt domæne": 0.31}}
    )

    assert merged["confidence_by_domain"]["python"] == 0.7
    assert merged["confidence_by_domain"]["nyt domæne"] == 0.31


# ── Dommen skal bygges på den ægte slutning (20/11-2026) ─────────────────────

def test_prompten_binder_afbrudt_dom_til_den_aegte_slutning():
    """MÅLT 20/11-2026: 255 af 342 poster nogensinde var «afbrudt midt i
    sætningen». Seks af seks efterprøvede citater fortsatte i den faktiske
    besked og sluttede korrekt — fejlen var i dommerens vindue, ikke i
    svaret. En note i dataene blev ikke læst; reglen skal stå i prompten."""
    p = _prompt()
    assert "ÆGTE SLUTNING" in p, "prompten siger ikke hvor dommen må bygges"
    assert "Citér aldrig et sted fra hovedet" in p, "citat-forbuddet mangler"


def test_bevis_vinduet_viser_en_hel_slutning():
    """Et afbrudt hoved må ikke være det eneste dommeren ser."""
    from core.services.personality_vector import _bevis_vindue

    tekst = ("Første sætning her. " * 40) + "Og den ægte slutning er hel og færdig."
    b = _bevis_vindue(tekst)
    assert "Og den ægte slutning er hel og færdig." in b, "slutningen mangler"
    assert "VINDUET der klipper" in b, "klippet er ikke navngivet"
    # den ægte slutning skal stå SIDST — det er den dommen skal læse
    assert b.rstrip().endswith("hel og færdig.")

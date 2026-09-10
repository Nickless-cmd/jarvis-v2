"""Vaernet slaar nu op DÉR HVOR FILERNE BOR — Fase 6.

Jarvis pegede paa `simple_tools_explore.py:126`: `if target == "workstation":
tjek_paastande = None`. Vaernet var slaaet HELT fra netop paa den sti hvor han
undersoeger Bjoerns egen maskine — dér hvor en fabrikeret rapport koster mest.

MEN UNDTAGELSEN VAR RIGTIG som den stod. `_rod()` peger paa CONTAINERENS repo,
saa et opslag dér ville have flaget hver eneste sti paa Bjoerns maskine som
opdigtet. Det er den modsatte fejl: falske anklager i stedet for manglende
vaern.

To ting skulle derfor rettes foer vaernet kunne taendes:

  1. Stierne skal slaas op OVER BROEN, ikke i containeren.
  2. Regexen matchede slet ikke ABSOLUTTE stier. En workstation-rapport skriver
     naturligt `/home/bs/projekt/src/main.ts`, saa vaernet ville have vaeret
     koblet paa og alligevel BLINDT.
"""
from __future__ import annotations

from core.services.explore_claim_check import tjek_paastande


# ── 2: absolutte stier ───────────────────────────────────────────────────

def test_absolutte_stier_efterproeves_nu():
    set_af = []
    tjek_paastande("se /home/bs/p/main.ts",
                   findes_fn=lambda s: set_af.append(s) or True)
    assert set_af == ["/home/bs/p/main.ts"]


def test_absolut_sti_MED_linjenummer():
    set_af = []
    tjek_paastande("se /home/bs/p/main.ts:42",
                   findes_fn=lambda s: set_af.append(s) or True)
    assert set_af == ["/home/bs/p/main.ts"]


def test_relative_stier_virker_stadig():
    d = tjek_paastande("se src/app/main.ts", findes_fn=lambda s: False)
    assert d["kontrolleret"] == 1 and d["holder"] is False


def test_URLer_er_ikke_filstier():
    """`https:` fejler paa kolon, `//host` paa den anden skraastreg."""
    assert tjek_paastande("se https://example.com/a/b.js",
                          findes_fn=lambda s: False)["kontrolleret"] == 0


# ── 1: uafgjort er hverken fund eller fejl ───────────────────────────────

def test_UAFGJORT_taeller_hverken_som_fund_eller_fejl():
    """`_operator_file_exists` svarer `None` naar broen ikke kan afgoere det.
    Et vaern der gaetter er vaerre end intet — det ville anklage aegte filer."""
    d = tjek_paastande("se /home/bs/p/main.ts", findes_fn=lambda s: None)
    # Haevder MENINGEN, ikke den noejagtige dict-form: et vaeltet tjek har
    # ikke doemt noget — og siger det nu ogsaa i `bevis` frem for at lade
    # `holder=True` staa alene og ligne en blaastempling.
    assert d["kontrolleret"] == 0 and d["fejl"] == [] and d["holder"] is True
    assert d["bevis"] == "intet-bevis"


def test_en_tjekker_der_KASTER_doemmer_ikke():
    d = tjek_paastande("se /home/bs/p/main.ts",
                       findes_fn=lambda s: (_ for _ in ()).throw(RuntimeError("bro nede")))
    assert d["kontrolleret"] == 0 and d["holder"] is True


def test_en_FALSK_sti_over_broen_falder():
    d = tjek_paastande("se /home/bs/p/opdigtet.ts", findes_fn=lambda s: False)
    assert d["holder"] is False
    assert "findes ikke" in d["fejl"][0]


def test_linje_indhold_efterproeves_IKKE_over_broen():
    """Det ville kraeve en fuld filhentning pr. citat. Eksistensen er det
    billige og det vigtigste — «filen findes ikke» er den typiske fabrikation.
    """
    d = tjek_paastande("se /home/bs/p/main.ts:9999:noget der ikke staar der",
                       findes_fn=lambda s: True)
    assert d["holder"] is True


# ── koblingen ────────────────────────────────────────────────────────────

def _kode_uden_kommentarer(fn) -> str:
    """Kommentarerne CITERER den gamle kode for at forklare hvorfor den er
    vaek. En ren tekst-soegning falder derfor over sin egen forklaring — samme
    faelde som ramte `as_completed`-testen i raadet."""
    import inspect
    linjer = [ln for ln in inspect.getsource(fn).splitlines()
              if not ln.lstrip().startswith("#")]
    return "\n".join(linjer)


def test_workstation_slaar_ikke_laengere_vaernet_FRA():
    """Foer stod der `tjek_paastande = None` for workstation — vaernet var
    slaaet HELT fra netop dér hvor en fabrikeret rapport koster mest."""
    from core.tools import simple_tools_explore as E
    kode = _kode_uden_kommentarer(E._exec_explore)
    linjer = kode.splitlines()
    for i, ln in enumerate(linjer[:-1]):
        if 'if target == "workstation":' in ln:
            assert "tjek_paastande = None" not in linjer[i + 1], (
                "vaernet slaas stadig helt fra for workstation")
    # Bro-ruten bor nu ÉT sted (`_bro_kontrol`) — se
    # test_begge_grene_spoerger_SAMME_bro for hvorfor det maatte samles.
    assert "_bro_kontrol(args)" in kode
    assert "findes_fn=_bro_tjek" in kode
    assert callable(E._bro_kontrol)


def test_runtime_stien_bruger_stadig_containerens_repo():
    """Broen er KUN for workstation. Et runtime-explore skal slaa op lokalt."""
    from core.tools import simple_tools_explore as E
    kode = _kode_uden_kommentarer(E._exec_explore)
    assert 'if target == "workstation":' in kode
    assert "else tjek_paastande(svar)" in kode


# ── citater efterproeves ogsaa over broen — Jarvis' forslag ─────────────
#
# Han spurgte: «er det dyrere end det er vaerd, eller er det den naeste billige
# sejr?» — og bad udtrykkeligt om at det blev maalt, ikke gaettet.
#
# MAALT 10/9-2026 mod hans egen maskine:
#     _operator_file_exists   0,08 s   (kun eksistens)
#     operator_grep           0,08 s   (fil + linjenummer + tekst)
#
# Samme pris, mere i svaret. Den billige sejr var der.


def test_et_citat_der_PASSER_holder():
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True,
                       linje_fn=lambda s, n, f: True)
    assert d["holder"] is True and d["kontrolleret"] == 1


def test_et_citat_paa_den_FORKERTE_linje_falder():
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True,
                       linje_fn=lambda s, n, f: False)
    assert d["holder"] is False
    assert "indeholder ikke" in d["fejl"][0]


def test_fragmentet_sendes_NOEGENT_videre():
    """Modellen omskriver whitespace og klipper linjen. Vi soeger paa kernen,
    ikke paa en eksakt streng — samme leniens som den lokale sti bruger."""
    set_af = []
    tjek_paastande("se /home/bs/p/main.ts:42:`const foo(bar)` ",
                   findes_fn=lambda s: True,
                   linje_fn=lambda s, n, f: set_af.append(f) or True)
    assert set_af == ["const foo"]


def test_UAFGJORT_citat_doemmes_ikke():
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True,
                       linje_fn=lambda s, n, f: None)
    assert d["holder"] is True


def test_en_linje_tjekker_der_KASTER_doemmer_ikke():
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True,
                       linje_fn=lambda s, n, f: (_ for _ in ()).throw(RuntimeError("bro nede")))
    assert d["holder"] is True


def test_uden_linje_tjekker_efterproeves_kun_eksistensen():
    """Bagudkompatibelt: en kalder der kun giver `findes_fn` faar samme
    opfoersel som foer."""
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True)
    assert d["holder"] is True and d["kontrolleret"] == 1


def test_workstation_stien_giver_BEGGE_tjekkere_med():
    from core.tools import simple_tools_explore as E
    kode = _kode_uden_kommentarer(E._exec_explore)
    assert "linje_fn=_bro_linje" in kode
    assert "_exec_operator_grep" in _kode_uden_kommentarer(E._bro_kontrol)


def test_begge_grene_spoerger_SAMME_bro(monkeypatch):
    """Jarvis' fund, 10/9. `_bro_tjek` sendte brugeren med, `_bro_linje` gjorde
    ikke — saa `_operator_user_id()` udledte selv og faldt gennem session ->
    owner_user_id -> hardkodet Bjoerns-id.

    For EJEREN var det tilfaeldigvis rigtigt. For enhver anden gik
    indholds-tjekket til ejerens bro, fejlede, og gav `None` — et TAVST no-op.
    Ikke en falsk anklage, men den vaerre slags: vaernet er koblet paa, svarer
    korrekt, og ser ingenting, fordi det spoerger den forkerte maskine.

    Testen KALDER begge grene i stedet for at laese kildetekst, og haevder det
    der faktisk betyder noget: samme identitet ud af begge. Kobles en tredje
    gren paa senere, fanger den det.
    """
    import sys, types
    import core.tools.simple_tools_explore as ex

    set_af: dict[str, str] = {}

    falsk = types.ModuleType("core.tools.simple_tools_operator")
    falsk._operator_file_exists = (                       # type: ignore[attr-defined]
        lambda sti, bruger: set_af.__setitem__("eksistens", bruger) or True)

    def _grep(a):
        set_af["grep"] = str(a.get("_runtime_user_id") or "")
        set_af["grep_session"] = str(a.get("_runtime_session_id") or "")
        return {"status": "ok",
                "result": [{"file": a["path"], "line": 42, "text": "x"}]}

    falsk._exec_operator_grep = _grep                    # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "core.tools.simple_tools_operator", falsk)

    findes, linje = ex._bro_kontrol({"_runtime_user_id": "mikkel-123",
                                     "_runtime_session_id": "sess-abc"})
    assert findes("/home/mikkel/x.py") is True
    assert linje("/home/mikkel/x.py", 42, "x") is True

    assert set_af["eksistens"] == "mikkel-123"
    assert set_af["grep"] == "mikkel-123", (
        "indholds-tjekket ruter til en ANDEN bruger end eksistens-tjekket "
        "— for en ikke-ejer bliver citat-efterproevningen et tavst no-op")
    assert set_af["grep_session"] == "sess-abc"


def test_bro_kontrol_domsformer():
    """Tre udfald, og de skal holdes adskilt: `None` = kan ikke afgoere,
    `False` = fragmentet findes ikke (opdigtet citat), `True` = rigtig linje.
    En bro-fejl maa ALDRIG blive til en anklage."""
    import sys, types
    import core.tools.simple_tools_explore as ex

    def _byg(grep_svar):
        m = types.ModuleType("core.tools.simple_tools_operator")
        m._operator_file_exists = lambda sti, bruger: None   # type: ignore[attr-defined]
        m._exec_operator_grep = lambda a: grep_svar          # type: ignore[attr-defined]
        return m

    for svar, ventet, hvorfor in [
        ({"status": "error"}, None, "bro-fejl maa ikke doemme"),
        ({"status": "ok", "result": []}, False, "intet match = opdigtet"),
        ({"status": "ok", "result": [{"line": 9, "text": "x"}]}, False,
         "forkert linjenummer"),
        ({"status": "ok", "result": [{"line": 42, "text": "x"}]}, True,
         "rigtig linje"),
        ({"status": "ok", "result": "ikke-en-liste"}, None, "ukendt form"),
    ]:
        sys.modules["core.tools.simple_tools_operator"] = _byg(svar)
        try:
            _, linje = ex._bro_kontrol({"_runtime_user_id": "u"})
            assert linje("/a/b.py", 42, "x") is ventet, hvorfor
        finally:
            del sys.modules["core.tools.simple_tools_operator"]


# ── «vi doemte intet» maa ikke laese som «vi verificerede alt» ──────────
#
# Jarvis' fund, 10/9. `holder = not fejl` er sandt naar der INGEN fejl er —
# ogsaa naar der ingenting blev efterproevet. En explore-rapport uden en eneste
# kontrolleret paastand kom derfor tilbage som et rent `status: ok`.
#
# Det er PRAECIS den sammenblanding jeg selv navngav og rettede i fase 11 for
# ledgeren, seks timer foer han fandt den her. Samme ordforraad med vilje.

def test_intet_efterproevet_er_ikke_verificeret():
    d = tjek_paastande("en rapport uden en eneste sti eller linjehenvisning")
    assert d["holder"] is True, "der ER ingen fejl — det er stadig sandt"
    assert d["bevis"] == "intet-bevis", (
        "nul kontrollerede paastande blev meldt som verificeret")


def test_en_bekraeftet_paastand_er_verificeret(tmp_path, monkeypatch):
    import core.services.explore_claim_check as c
    monkeypatch.setattr(c, "_rod", lambda: tmp_path)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "rigtig.py").write_text("x = 1\n")
    # `_STI` kraever mindst ét «/» — et bart filnavn matcher aldrig.
    d = tjek_paastande("se sub/rigtig.py for detaljerne")
    assert d["kontrolleret"] >= 1
    # EKSISTENS ER IKKE VERIFIKATION. Denne test haevdede foer «verificeret»
    # for en ren sti-paastand — altsaa den betydning der lod fire fabrikerede
    # citater passere som «4 paastand(e) slaaet op og bekraeftet». Testen
    # kodede fejlen; nu koder den skelnen.
    assert d["bevis"] == "kun-eksistens"
    assert int(d.get("indhold_bekraeftet") or 0) == 0


def test_en_falsk_paastand_er_uenig(tmp_path, monkeypatch):
    import core.services.explore_claim_check as c
    monkeypatch.setattr(c, "_rod", lambda: tmp_path)
    d = tjek_paastande("se sub/findes_slet_ikke.py for detaljerne")
    assert d["holder"] is False
    assert d["bevis"] == "uenig"


def test_explore_baerer_dommen_UD_til_kalderen():
    """Uden dette staar dommen i en dict ingen laeser — og modtageren ser
    `status: ok` og tror rapporten er gennemgaaet."""
    import inspect

    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._exec_explore)
    assert '"bevis":' in kilde
    assert "IKKE verificeret" in kilde


# ── prosa-formen: et opdigtet tal paa en AEGTE fil ──────────────────────
#
# Jarvis' fund. `_STI_LINJE` kraever `sti:linje`, men en model skriver lige saa
# gerne «simple_tools_explore.py line 8: _MAKS = 3». Da fangede kun den
# bare-sti-regex den, saa KUN filens eksistens blev efterproevet — og et
# OPDIGTET tal paa en aegte fil passerede som «holder».
#
# Det er den farligste form, fordi den ser mest overbevisende ud: rigtig sti,
# praecist linjenummer, og en vaerdi ingen har slaaet op. Det var praecis det
# han fik: agenten sagde 7 hvor der staar 3.

def _rod_med(tmp_path, monkeypatch, indhold: str):
    import core.services.explore_claim_check as c
    monkeypatch.setattr(c, "_rod", lambda: tmp_path)
    (tmp_path / "sub").mkdir(exist_ok=True)
    (tmp_path / "sub" / "x.py").write_text(indhold)
    return tmp_path


def test_prosa_paastand_bliver_EFTERPROEVET(tmp_path, monkeypatch):
    _rod_med(tmp_path, monkeypatch, "a = 1\nb = 2\n_MAKS = 3\n")
    d = tjek_paastande("jeg saa sub/x.py line 3: _MAKS = 3")
    assert d["kontrolleret"] >= 1
    assert d["bevis"] == "verificeret", d


def test_et_OPDIGTET_tal_paa_en_aegte_fil_fanges(tmp_path, monkeypatch):
    """Praecis Jarvis' tilfaelde: agenten sagde 7, der staar 3."""
    _rod_med(tmp_path, monkeypatch, "a = 1\nb = 2\n_MAKS = 3\n")
    d = tjek_paastande("jeg saa sub/x.py line 3: _MAKS = 7")
    assert d["holder"] is False, "et opdigtet indhold passerede"
    assert d["bevis"] == "uenig"


def test_forkert_linjenummer_fanges(tmp_path, monkeypatch):
    _rod_med(tmp_path, monkeypatch, "a = 1\nb = 2\n_MAKS = 3\n")
    d = tjek_paastande("se sub/x.py linje 1 — _MAKS = 3")
    assert d["holder"] is False


def test_den_omvendte_ordstilling_fanges_ogsaa(tmp_path, monkeypatch):
    """«linje 8 i core/x.py» — dansk ordstilling, samme paastand."""
    _rod_med(tmp_path, monkeypatch, "a = 1\n")
    d = tjek_paastande("det staar paa linje 1 i sub/x.py")
    assert d["kontrolleret"] >= 1


def test_samme_paastand_i_to_former_taelles_ÉN_gang(tmp_path, monkeypatch):
    """Ellers ville en rapport der gentager sig selv se bedre efterproevet ud
    end den er — samme fejl som emne-tællingen paa world-model-grenen."""
    _rod_med(tmp_path, monkeypatch, "a = 1\n")
    d = tjek_paastande("sub/x.py:1 og ogsaa sub/x.py line 1 — samme sted")
    assert d["kontrolleret"] == 1, d


# ── den FALSKE POSITIV: fire opdigtede citater meldt «verificeret» ──────
#
# Jarvis' anden explore-test mod Bjoerns maskine. Agenten fabrikerede fire
# paastande med linjenumre om en AEGTE fil — dato, to author-vaerdier og en
# traileer der ikke findes — og porten svarede:
#
#     paastande_kontrolleret: 4
#     bevis: "verificeret"
#     bevis_note: "4 paastand(e) slaaet op og bekraeftet."
#
# Det er vaerre end den falske negativ jeg lukkede samme formiddag. Dén sagde
# «vi doemte intet»; denne siger «vi verificerede alt» om ren opdigt.
#
# TO AARSAGER, og begge er lukket her:
#   1. Markdown-formen `sti:12`: indhold — backticken aad indholdet, saa
#      linje-tjekket blev ALDRIG kaldt. Det er den mest naturlige maade at
#      citere paa, saa hullet var normalvejen, ikke en kant.
#   2. «Filen findes» taalte som en bekraeftet paastand.

def test_markdown_formen_kalder_linje_tjekket():
    kaldt = {"n": 0}

    def _linje(sti, nr, frag):
        kaldt["n"] += 1
        return False

    d = tjek_paastande("se `docs/x.md:12`: Etableret 2023-11-15",
                       findes_fn=lambda s: True, linje_fn=_linje)
    assert kaldt["n"] == 1, (
        "backticken aad indholdet — linje-tjekket blev aldrig kaldt")
    assert d["bevis"] == "uenig"


def test_fire_fabrikerede_citater_meldes_UENIG():
    """Praecis hans tilfaelde, i den form agenten skrev det."""
    tekst = ("`docs/git-attribution.md:12`: Etableret 2023-11-15\n"
             "`docs/git-attribution.md:24`: Jarvis Core Team\n"
             "`docs/git-attribution.md:25`: Claude Team\n"
             "`docs/git-attribution.md:38`: Signed-off-by")
    d = tjek_paastande(tekst, findes_fn=lambda s: True,
                       linje_fn=lambda *a: False)
    assert d["bevis"] == "uenig", d
    assert d["holder"] is False
    assert len(d["fejl"]) == 4


def test_kun_eksistens_er_sin_EGEN_dom():
    """Hverken «verificeret» eller «intet-bevis». Vi HAR slaaet noget op — vi
    har bare ikke efterproevet hvad der staar i det."""
    d = tjek_paastande("se a/b.py og c/d.py", findes_fn=lambda s: True)
    assert d["bevis"] == "kun-eksistens"
    assert d["kontrolleret"] == 2
    assert int(d.get("indhold_bekraeftet") or 0) == 0


def test_nul_vaerktoejskald_blaastemples_ikke():
    """Agenten skal LAESE noget for at kunne svare. Udfoerte den ingen kald, er
    svaret gaettet — uanset hvor praecist det lyder. Og foer returnerede
    explore paa runde 0, saa den mekanisme der skulle skifte modellen ud koerte
    ALDRIG: gaten blev sat ud af spil af netop den fejl den skulle fange."""
    import inspect

    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._exec_explore)
    assert "_tomhaendet" in kilde
    assert 'result.get("tool_calls")' in kilde
    assert "if dom.get(\"holder\") and not _tomhaendet:" in kilde, (
        "et tomhaendet svar returneres stadig uden rotation")

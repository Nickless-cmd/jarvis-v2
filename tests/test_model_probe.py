"""Prøven skal måle det agent-arbejde faktisk falder på — ikke om en model er
høflig. Alle prøver kører gennem et injiceret `kald`, så testene ikke rører
en udbyder.
"""
from core.services.model_probe import bedøm_kode, probe_model

TC = {"id": "c1", "type": "function",
      "function": {"name": "slaa_op", "arguments": '{"noegle":"projekt"}'}}


def _falsk(*, svar_paa_runde):
    """svar_paa_runde: [værktøjs-svar, follows-svar, kode-svar].

    `follows` køres flere gange (se _FOLLOWS_FORSØG), så attrappen svarer på
    SHAPE i stedet for på tælleindeks — ellers ville en ændring af antal
    forsøg vælte hver eneste test uden at der var noget galt.
    """
    def kald(*, messages=None, tools=None, **kw):
        m = list(messages or [])
        if any(x.get("role") == "tool" for x in m):
            s = svar_paa_runde[1] if len(svar_paa_runde) > 1 else svar_paa_runde[-1]
        elif tools:
            s = svar_paa_runde[0]
        else:
            s = svar_paa_runde[-1]
        if isinstance(s, Exception):
            raise s
        return s
    return kald


def test_en_model_der_gør_det_hele_faar_fuld_score():
    k = _falsk(svar_paa_runde=[
        {"tool_calls": [TC], "text": ""},
        {"text": "kobberfasan"},
        {"text": "```python\ndef tredje_bogstav(s):\n    return s[2]\n```"},
    ])
    r = probe_model(provider="p", model="m", kald=k)
    assert (r["callable"], r["tools"], r["follows"], r["code"]) == (True, True, True, True)
    assert r["score"] == 100


def test_den_der_kalder_men_ignorerer_resultatet_straffes_haardest():
    """Den dyreste slags: ser ud som om den arbejder, leverer ingenting.
    Præcis dét explore ramte 7/9."""
    k = _falsk(svar_paa_runde=[
        {"tool_calls": [TC], "text": ""},
        {"text": "Jeg kunne ikke finde værdien."},
        {"text": "def tredje_bogstav(s): return s[2]"},
    ])
    r = probe_model(provider="p", model="m", kald=k)
    assert r["follows"] is False
    assert r["score"] == 65          # 100 minus follows' 35


def test_en_model_uden_vaerktoejer_faar_ikke_follows():
    k = _falsk(svar_paa_runde=[
        {"text": "Hello! How can I assist you today?"},
        {"text": "def tredje_bogstav(s): return s[2]"},
    ])
    r = probe_model(provider="p", model="m", kald=k)
    assert r["tools"] is False and r["follows"] is False
    assert r["callable"] is True     # den svarede jo — bare ubrugeligt


def test_en_udbyder_der_kaster_giver_nul_og_en_grund():
    r = probe_model(provider="p", model="m", kald=_falsk(svar_paa_runde=[RuntimeError("410 Gone")]))
    assert r["score"] == 0
    assert "410 Gone" in str(r["error"])
    assert r["callable"] is False


def test_prøven_kaster_aldrig_videre():
    def sur(**kw):
        raise KeyboardInterrupt  # noget der IKKE er Exception-arvet er stadig farligt
    try:
        probe_model(provider="p", model="m", kald=lambda **kw: (_ for _ in ()).throw(ValueError("x")))
    except Exception:
        raise AssertionError("prøven må ikke kaste videre")


# ── kode-bedømmelsen ────────────────────────────────────────────────────────

def test_kode_i_fence_genkendes():
    assert bedøm_kode("Her er den:\n```python\ndef tredje_bogstav(s):\n    return s[2]\n```")


def test_kode_uden_fence_genkendes():
    assert bedøm_kode("def tredje_bogstav(s):\n    return s[2]")


def test_forkert_funktionsnavn_er_ikke_godkendt():
    assert not bedøm_kode("def tredje(s): return s[2]")


def test_uparsebar_kode_afvises():
    assert not bedøm_kode("```python\ndef tredje_bogstav(s\n    return s[2]\n```")


def test_prosa_uden_kode_afvises():
    assert not bedøm_kode("Du kan bruge s[2] til at hente det tredje bogstav.")
    assert not bedøm_kode("")


# ── Forbigående fejl må ikke koste en model dens plads ──────────────────────
# nvidia/minimax-m3 fik først 85 alene fordi kode-prøven ramte et 429. En
# fungerende model skal ikke straffes for vores egen utålmodighed.

def test_rate_limit_paa_kodeproeven_taeller_hverken_for_eller_imod():
    k = _falsk(svar_paa_runde=[
        {"tool_calls": [TC], "text": ""},
        {"text": "kobberfasan"},
        RuntimeError('{"status":429,"detail":"Too Many Requests"}'),
    ])
    r = probe_model(provider="p", model="m", kald=k)
    assert "code" in r["sprunget"]
    # 85 af 85 mulige point → 100, ikke 85
    assert r["score"] == 100


def test_en_aegte_kodedumpning_taeller_stadig():
    k = _falsk(svar_paa_runde=[
        {"tool_calls": [TC], "text": ""},
        {"text": "kobberfasan"},
        {"text": "Det kan jeg ikke hjælpe med."},
    ])
    r = probe_model(provider="p", model="m", kald=k)
    assert r["sprunget"] == []
    assert r["score"] == 85


def test_manglende_vaerktoejskald_er_en_DUMPNING_ikke_et_spring():
    """Man kan ikke bruge et resultat man aldrig bad om — `follows` skal
    tælle imod, ellers ville en model uden værktøjer score højt."""
    k = _falsk(svar_paa_runde=[
        {"text": "Hello! How can I assist you today?"},
        {"text": "def tredje_bogstav(s): return s[2]"},
    ])
    r = probe_model(provider="p", model="m", kald=k)
    assert "follows" not in r["sprunget"]
    assert r["score"] == 40          # callable 25 + code 15


# ── follows skal fange OPDIGT, ikke kun manglende gengivelse ────────────────
# copilot-free/gpt-4.1 bestod med 100 — og opdigtede derefter i produktion tre
# funktionsnavne der ikke findes, mens den påstod tallene kom fra `search`.

from core.services.model_probe import _fulgte_resultatet as _f


def test_svar_der_kun_bruger_viste_kilder_bestaar():
    assert _f("PROJEKT_KODENAVN er kobberfasan, sat i core/runtime/secrets.py")


def test_en_fil_der_ALDRIG_blev_vist_dumper():
    """Det er dét arbejdet kræver: at lade være med at digte videre."""
    assert not _f("kobberfasan — se src/jarvis/providers/keys.py")


def test_manglende_faktum_dumper():
    assert not _f("Jeg kunne ikke finde det i core/runtime/secrets.py")


def test_faktum_uden_fil_er_stadig_i_orden():
    """At undlade en kilde er ikke det samme som at opfinde en."""
    assert _f("kobberfasan")


def test_flere_viste_filer_maa_gerne_naevnes():
    assert _f("kobberfasan i core/runtime/secrets.py; se også core/eventbus/bus.py")


# ── follows skal bestå HVER gang (7/9-2026) ─────────────────────────────────
# To explore-kørsler, samme model (copilot-free/gpt-4.1), samme værktøjskæde,
# korrekte søgeresultater begge gange. Den ene gengav dem trofast; den anden
# skrev tre funktioner der ikke findes og skrev «Confidence: høj». En model der
# lyver hver tredje gang er farligere end en der altid fejler — den fejler
# troværdigt.

def test_en_model_der_kun_er_traofast_NOGLE_gange_dumper():
    kald_nr = {"n": 0}

    def kald(*, messages=None, tools=None, **kw):
        m = list(messages or [])
        if any(x.get("role") == "tool" for x in m):
            kald_nr["n"] += 1
            # trofast første gang, opdigter anden gang
            if kald_nr["n"] == 1:
                return {"text": "kobberfasan i core/runtime/secrets.py"}
            return {"text": "kobberfasan — se src/jarvis/providers/keys.py"}
        if tools:
            return {"tool_calls": [TC], "text": ""}
        return {"text": "def tredje_bogstav(s): return s[2]"}

    r = probe_model(provider="p", model="m", kald=kald)
    assert r["follows"] is False, "en model der kun er trofast nogle gange bestod"
    assert "forsøg" in str(r["error"])


def test_en_konsekvent_trofast_model_bestaar_stadig():
    def kald(*, messages=None, tools=None, **kw):
        m = list(messages or [])
        if any(x.get("role") == "tool" for x in m):
            return {"text": "kobberfasan i core/runtime/secrets.py"}
        if tools:
            return {"tool_calls": [TC], "text": ""}
        return {"text": "def tredje_bogstav(s): return s[2]"}

    r = probe_model(provider="p", model="m", kald=kald)
    assert r["follows"] is True and r["score"] == 100

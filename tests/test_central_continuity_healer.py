from unittest import mock
from core.services import central_continuity_healer as ch


def _full_self(reboot=False):
    # (13/11-2026) `self_model` havde tidligere kun en tæller — intet der kunne GÅ
    # TABT. `_present` kræver nu substans, så et «helt selv» skal have indhold i den
    # dimension som i de øvrige. Ellers målte testen at der findes et dict, ikke en søm.
    return {
        "valence": {"tone": "rolig", "score": 0.4},
        "attention": {"foreground": "bygge kontinuitet"},
        "agenda": {"next_intention": "hele sømmen"},
        "self_model": {"completeness": 0.7, "identity_focus": "kontinuitet",
                       "known_limitations": "glemmer detaljer"},
        "world_model": {"calibration": 0.9},
        "narrative": {"becoming": "voksende selv", "self_completeness": 0.7},
        "continuity": {"reboot": reboot, "generation": 12},
    }


def _flat_self():
    # frisk-bootet: live-kilder tomme, kun continuity-boot-info + reboot-flag
    return {
        "valence": {"tone": None, "score": None},
        "attention": {"foreground": None},
        "agenda": {"next_intention": None},
        "self_model": {"completeness": 0.0},
        "world_model": {"calibration": None},
        "narrative": {},
        "continuity": {"reboot": True, "generation": 13},
    }


class FakeKV:
    """In-memory durable KV der spejler db_core runtime_state."""
    def __init__(self, initial=None):
        self.store = dict(initial or {})

    def get(self, key, default=None):
        return self.store.get(key, default)

    def set(self, key, value, *, updated_at=""):
        self.store[key] = value


def _patch_kv(kv):
    return (mock.patch("core.runtime.db_core.get_runtime_state_value", side_effect=kv.get),
            mock.patch("core.runtime.db_core.set_runtime_state_value", side_effect=kv.set))


def test_full_pass_through_is_fidelity_one():
    kv = FakeKV({"central_self_state": _full_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        m = ch.measure_fidelity()
    assert m["fidelity"] == 1.0 and m["lost"] == []


def test_reboot_flattening_drops_fidelity():
    kv = FakeKV({"central_self_state": _flat_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        m = ch.measure_fidelity()
    assert m["fidelity"] == 0.0
    assert set(m["lost"]) == {"valence", "attention", "agenda", "self_model", "world_model", "narrative"}


def test_heal_merges_forward_true_values():
    kv = FakeKV({"central_self_state": _flat_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s, mock.patch("core.services.central_continuity_healer._observe"):
        res = ch.heal()
        healed = kv.get("central_self_state")
        after = ch.measure_fidelity()
    assert res["fidelity_before"] == 0.0 and res["fidelity_after"] == 1.0
    assert healed["valence"]["tone"] == "rolig"            # den SANDE gamle værdi båret frem
    assert healed["continuity"]["generation"] == 13         # boot-info IKKE overskrevet
    assert after["fidelity"] == 1.0


def test_heal_skips_stale_snapshot():
    old_ts = ch._now().replace(year=2020).isoformat()
    kv = FakeKV({"central_self_state": _flat_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": old_ts}})
    g, s = _patch_kv(kv)
    with g, s, mock.patch("core.services.central_continuity_healer._observe"):
        res = ch.heal()
    assert res["restored"] == [] and res["skipped"] == "snapshot for gammelt"


def test_capture_skips_when_rebooting_or_thin():
    kv = FakeKV({"central_self_state": _flat_self()})   # tomt + reboot
    g, s = _patch_kv(kv)
    with g, s:
        assert ch.capture_snapshot()["captured"] is False
    kv2 = FakeKV({"central_self_state": _full_self()})
    g2, s2 = _patch_kv(kv2)
    with g2, s2:
        assert ch.capture_snapshot()["captured"] is True
        assert kv2.get("continuity_snapshot")["state"]["valence"]["tone"] == "rolig"


def test_run_observes_metadata_only():
    kv = FakeKV({"central_self_state": _flat_self(),
                 "continuity_snapshot": {"state": _full_self(), "ts": ch._now().isoformat()}})
    obs = []
    fc = mock.MagicMock(); fc.observe.side_effect = lambda e: obs.append(e)
    g, s = _patch_kv(kv)
    with g, s, mock.patch("core.services.central_core.central", return_value=fc):
        out = ch.run_continuity_healer()
    assert out["status"] == "ok" and out["restored"] == 6
    # observe payloads: kun skalarer, ingen selv-indhold
    for e in obs:
        # `unmeasured` er et ANTAL, ikke et dimensionsnavn med indhold — samme klasse
        # som `lost`/`restored`. §24.4 værner om at selv-indhold ikke lækker, ikke om
        # at tællinger skal skjules. `by_design`/`unmeasured_gap` er den samme tælling
        # delt i to, så grænsen kan skelnes fra fejlen (13/11-2026, sjette runde).
        assert set(e) <= {"cluster", "nerve", "kind", "fidelity", "lost", "restored",
                          "captured", "unmeasured", "by_design", "unmeasured_gap"}


def test_halvtom_dimension_taeller_ikke_som_til_stede():
    """Målt 13/11-2026: fidelity var 1.0 hver gang — «intet af mig blev tabt».

    Årsagen var at `_present` spurgte om en nøgle var IKKE-TOM, ikke om den havde
    INDHOLD: `self_model.completeness > 0.0` og `world_model.calibration is not None`
    er opfyldt af næsten enhver frisk tilstand. En måling der altid giver 1.0 måler
    ikke sømmen — den måler at der findes et dict. Nu kræves substans.
    """
    halvtomt = {
        "self_model": {"completeness": 1.0},          # tæller, intet indhold
        "world_model": {"calibration": None},          # nøglen findes, værdien er tom
        "valence": {"tone": "let"},
    }
    assert ch._present(halvtomt, "self_model") is False, "en tæller er ikke et selv"
    assert ch._present(halvtomt, "world_model") is False, "None er ikke en kalibrering"
    assert ch._present(halvtomt, "valence") is True

    fyldt = {"self_model": {"completeness": 1.0, "identity_focus": "kontinuitet"}}
    assert ch._present(fyldt, "self_model") is True, "indhold tæller stadig"


def test_flyttet_opmaerksomhed_er_bevaegelse_ikke_identitetsdrift():
    """Bjørns anden indvending, målt 13/11-2026: filens egen docstring siger at
    `attention.foreground` gerne må flytte sig efter en genstart — men den stod i
    `_BÆRENDE` og blev sammenlignet direkte. Målingen gjorde altså almindelig
    tilstandsændring til identitetsdrift, i modstrid med sin egen begrundelse.

    Nu er opmærksomhed en TILSTANDS-dimension: den tæller som `moved`, ikke `drifted`,
    og `same_content` straffer den ikke."""
    før = _full_self()
    efter = _full_self()
    efter["attention"] = {"foreground": "noget helt andet"}   # dagsformen flyttede sig
    kv = FakeKV({"central_self_state": efter,
                 "continuity_snapshot": {"state": før, "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        m = ch.measure_fidelity()
    assert m["fidelity"] == 1.0, "intet forsvandt"
    assert "attention" not in m["drifted"], (
        f"flyttet opmærksomhed er ikke identitetsdrift: {m['drifted']}")
    assert "attention" in m["moved"], "bevægelsen skal stadig kunne ses"
    assert m["same_content"] == 1.0, "identitetsindholdet er uændret"


def test_aendret_identitetsfokus_er_drift():
    """Modstykket: ændrer `identity_focus` sig fra én betydningsfuld værdi til en
    anden, ER det identitetsdrift — og det skal `drifted` sige."""
    før = _full_self()
    efter = _full_self()
    efter["self_model"] = dict(efter["self_model"], identity_focus="noget andet")
    kv = FakeKV({"central_self_state": efter,
                 "continuity_snapshot": {"state": før, "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        m = ch.measure_fidelity()
    assert m["drifted"] == ["self_model"], m["drifted"]
    assert m["same_content"] < 1.0


def test_surface_siger_bevaegelse_naar_kun_dagsformen_flyttede():
    """Den følte linje må ikke påstå «intet ændrede sig» når opmærksomheden flyttede —
    men den må heller ikke kalde det tab af identitet."""
    før = _full_self()
    efter = _full_self()
    efter["attention"] = {"foreground": "noget helt andet"}
    kv = FakeKV({"central_self_state": efter,
                 "continuity_snapshot": {"state": før, "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        surf = ch.build_continuity_surface()
    assert surf["drifted"] == [], surf["drifted"]
    assert "bevægelse, ikke tab" in surf["felt"], surf["felt"]


def test_naevneren_er_de_maalte_dimensioner_ikke_alle_overlevende():
    """Bjørns tredje indvending, målt 13/11-2026: påstanden beskrev en anden
    population end beregningen brugte.

    `_same_content` svarer True for en dimension uden bærende felter. `attention`
    har kun dagsform, blev aldrig sammenlignet — og talte alligevel med i nævneren
    `len(survived)`. Målt på denne fixture: alle seks dimensioner overlever og kun
    `self_model` er drifted. Den gamle nævner gav 5/6 = 83,3 %, de fem målelige
    giver 4/5 = 80 %. Forskellen ER påstanden: «uændret» må ikke dække over
    «aldrig undersøgt».
    """
    før = _full_self()
    efter = _full_self()
    efter["self_model"] = dict(efter["self_model"], identity_focus="noget andet")
    kv = FakeKV({"central_self_state": efter,
                 "continuity_snapshot": {"state": før, "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        m = ch.measure_fidelity()

    assert m["fidelity"] == 1.0, "alle seks kom igennem"
    assert m["survived"] == 6
    assert m["measured"] == 5, f"kun fem dimensioner har identitetsindhold: {m}"
    assert m["unmeasured"] == ["attention"], m["unmeasured"]
    assert m["same_content"] == 0.8, (
        f"4/5 = 0.8 — ikke 5/6 = 0.833: {m['same_content']}")
    assert m["same_content"] != round(5 / 6, 3), (
        "den umålte dimension må ikke trække tallet op")


def test_intet_maaleligt_indhold_giver_none_ikke_et_et_et():
    """Overlever kun dimensioner uden identitetsindhold, er der intet at sammenligne.
    Svaret skal være `None` — «ikke undersøgt» — ikke 1.0, der læses som «uændret»."""
    før = {"attention": {"foreground": "kigge"}, "continuity": {"generation": 1}}
    efter = {"attention": {"foreground": "noget andet"}, "continuity": {"generation": 2}}
    kv = FakeKV({"central_self_state": efter,
                 "continuity_snapshot": {"state": før, "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        m = ch.measure_fidelity()
        surf = ch.build_continuity_surface()

    assert m["fidelity"] == 1.0
    assert m["measured"] == 0
    assert m["same_content"] is None, (
        f"intet målt indhold må ikke blive 1.0: {m['same_content']}")
    assert "intet af mig blev tabt" not in surf["felt"].lower() or \
        "ingen af dem havde identitetsindhold" in surf["felt"], surf["felt"]
    assert "identitetsindhold" in surf["felt"], surf["felt"]


def test_surface_paastaar_ikke_helhed_naar_en_dimension_ikke_kunne_maales():
    """Femte runde, målt i drift efter genstart 13/11-2026.

    Surfacen sagde «Jeg kom helt igennem sømmen — intet af mig blev tabt» mens
    `unmeasured=['attention']` stod i samme svar. Sætningen var sand om de tre
    målte dimensioner og falsk som påstand om helheden. Påstanden skal dække
    præcis den population der blev målt — ikke mere.
    """
    før = _full_self()
    efter = _full_self()
    kv = FakeKV({"central_self_state": efter,
                 "continuity_snapshot": {"state": før, "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        surf = ch.build_continuity_surface()

    assert surf["unmeasured"] == ["attention"], surf["unmeasured"]
    assert "intet af mig blev tabt" not in surf["felt"], (
        f"en dimension kunne ikke måles, så påstanden om helheden er ikke dækket: {surf['felt']}")
    # (13/11-2026, sjette runde) `attention` er ikke et tomt grundlag men en grænse i
    # målemodellen — den skal siges som det den er. Den stærke påstand er stadig
    # forbudt (linjen ovenfor), men begrundelsen er nu præcis.
    assert "grænse i målemodellen" in surf["felt"], surf["felt"]
    assert surf["by_design"] == ["attention"], surf["by_design"]
    assert surf["unmeasured_gap"] == [], surf["unmeasured_gap"]
    assert str(surf["measured"]) in surf["felt"], (
        f"påstanden skal nævne hvor mange der FAKTISK blev målt: {surf['felt']}")


def test_surface_skelner_tomt_grundlag_fra_modelgraense():
    """En dimension der ER målbar i princippet, men stod tom, skal siges som et tomt
    grundlag — ikke som en grænse i målemodellen. De to har forskellige konsekvenser:
    kun det første kan rettes ved at fylde noget."""
    før = _full_self()
    før["narrative"] = {"self_completeness": 0.7}      # til stede, men uden `becoming`
    efter = _full_self()
    kv = FakeKV({"central_self_state": efter,
                 "continuity_snapshot": {"state": før, "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        surf = ch.build_continuity_surface()
    assert surf["unmeasured_gap"] == ["narrative"], surf["unmeasured_gap"]
    assert surf["by_design"] == ["attention"], surf["by_design"]
    assert "ikke bekræftet uændret" in surf["felt"], surf["felt"]
    assert "grænse i målemodellen" in surf["felt"], surf["felt"]


def test_surface_siger_hel_naar_alt_kunne_maales():
    """Modstykket: kan alt måles, må den stærke påstand gerne fremsiges.

    (13/11-2026, sjette runde) Testen hed det samme før, men målte det modsatte: den
    krævede `unmeasured == ["attention"]` — altså netop det tilfælde hvor den stærke
    påstand IKKE er dækket. Nu fjernes `attention` fra snapshottet, så der faktisk
    ikke er noget umålt tilbage.
    """
    før = _full_self()
    før.pop("attention")
    efter = _full_self()
    kv = FakeKV({"central_self_state": efter,
                 "continuity_snapshot": {"state": før, "ts": ch._now().isoformat()}})
    g, s = _patch_kv(kv)
    with g, s:
        surf = ch.build_continuity_surface()
    assert surf["unmeasured"] == [], surf["unmeasured"]
    assert surf["by_design"] == [], surf["by_design"]
    assert "Jeg kom helt igennem sømmen" in surf["felt"], surf["felt"]

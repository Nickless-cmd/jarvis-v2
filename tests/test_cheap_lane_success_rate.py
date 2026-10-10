"""Kroniske fejlere udelukkes på FAKTISK historik — ikke på metadata.

Straffen i `adaptive_snapshot` er gradueret: maks ~24 point (10 pålidelighed +
8 kvalitet + 6 latency). Det er nok til at skubbe en dårlig provider ned — men
ikke til at udelukke den. Har den en god base-priority, vinder den lodtrækningen
så snart de bedre kandidater står i cooldown.

Målt 10/10-2026: `freeai::qwen7b` fejlede 98 af 101 kald i døgnet og blev valgt
~100 gange. DB-rækkens metadata sagde 18 kald (success_count=1, failure_count=17),
mens `cheap_provider_invocations` havde 103 i samme vindue. Samtidige skrivninger
overskriver metadata — historikken er den ene sandhed.

Dommeren her læser derfor historikken, over et vindue, og udelukker slottet hårdt
under en tærskel. Tidsbegrænset, så en provider der retter sig kommer tilbage.
"""

from __future__ import annotations


def _kald(provider: str, model: str, *, ok: int, n: int, profile: str = "default") -> None:
    """Skriv n invocations: de første `ok` gennemførte, resten fejlede."""
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation

    for i in range(n):
        record_cheap_provider_invocation(
            provider=provider,
            model=model,
            auth_profile=profile,
            status="completed" if i < ok else "failed",
            error_code="" if i < ok else "rate-limited",
        )


def test_fanger_en_doed_slot(isolated_runtime):
    """2 af 30 = 6,7 % — under gulvet, nok kald. Skal findes."""
    from core.services.cheap_lane_success_rate import find_chronic_failures

    _kald("freeai", "qwen7b", ok=2, n=30)
    fundet = find_chronic_failures(days=3, min_calls=20, floor=0.10)

    assert [(r["provider"], r["model"]) for r in fundet] == [("freeai", "qwen7b")]
    assert fundet[0]["success"] == 2
    assert fundet[0]["total"] == 30


def test_lader_en_sund_slot_vaere(isolated_runtime):
    """27 af 30 = 90 %. Ingen dom."""
    from core.services.cheap_lane_success_rate import find_chronic_failures

    _kald("nvidia-nim", "nemotron", ok=27, n=30)

    assert find_chronic_failures(days=3, min_calls=20, floor=0.10) == []


def test_doemmer_ikke_paa_for_faa_kald(isolated_runtime):
    """0 % men kun 5 kald — for lidt data til at dømme en ny provider."""
    from core.services.cheap_lane_success_rate import find_chronic_failures

    _kald("ny-provider", "m", ok=0, n=5)

    assert find_chronic_failures(days=3, min_calls=20, floor=0.10) == []


def test_taerskelen_er_haard_ved_gulvet(isolated_runtime):
    """Præcis på gulvet er ikke UNDER gulvet — 10,0 % overlever, 6,7 % dør."""
    from core.services.cheap_lane_success_rate import find_chronic_failures

    _kald("praecis", "m", ok=3, n=30)  # 10,0 %
    assert find_chronic_failures(days=3, min_calls=20, floor=0.10) == []

    _kald("under", "m", ok=2, n=30)  # 6,7 %
    fundet = find_chronic_failures(days=3, min_calls=20, floor=0.10)
    assert [r["provider"] for r in fundet] == ["under"]


def test_profilen_er_en_del_af_noeglen(isolated_runtime):
    """En død default-profil må ikke dømme account2 med samme model."""
    from core.services.cheap_lane_success_rate import find_chronic_failures

    _kald("reka", "glm5.3", ok=1, n=30, profile="default")   # 3,3 %
    _kald("reka", "glm5.3", ok=28, n=30, profile="account2")  # 93 %

    fundet = find_chronic_failures(days=3, min_calls=20, floor=0.10)

    assert [(r["provider"], r["auth_profile"]) for r in fundet] == [("reka", "default")]


def test_apply_quarantine_saetter_cooldown_i_db(isolated_runtime):
    """Karantænen skal lande i cheap_provider_runtime_state — den kilde
    selection-stien allerede læser gennem quota_snapshot."""
    from core.runtime.db import get_cheap_provider_runtime_state
    from core.services.cheap_lane_success_rate import apply_quarantine

    rows = [{
        "provider": "freeai", "model": "qwen7b", "auth_profile": "default",
        "success": 2, "total": 30, "rate": 0.0667,
    }]
    sat = apply_quarantine(rows, hours=24)

    assert sat == 1
    st = get_cheap_provider_runtime_state(provider="freeai", model="qwen7b") or {}
    assert st.get("cooldown_until"), "karantænen skal sætte en cooldown"


def test_apply_quarantine_roerer_ikke_en_slot_der_er_undtaget(isolated_runtime):
    """En provider Bjørn selv har slået fra manuelt skal ikke genåbnes af en fejl-dom."""
    from core.services.cheap_lane_success_rate import apply_quarantine

    assert apply_quarantine([], hours=24) == 0


def test_enforce_er_no_op_naar_flaget_er_slukket(isolated_runtime):
    """Default OFF → byte-identisk adfærd. Ingen query, ingen skrivning."""
    from core.services.cheap_lane_success_rate import enforce

    _kald("freeai", "qwen7b", ok=2, n=30)
    ud = enforce()

    assert ud["enabled"] is False
    assert ud["quarantined"] == 0


def test_enforce_karantaener_naar_flaget_er_taendt(isolated_runtime):
    from core.runtime.db import get_cheap_provider_runtime_state
    from core.runtime.db_core import set_runtime_state_value
    from core.services.cheap_lane_success_rate import enforce

    _kald("freeai", "qwen7b", ok=2, n=30)
    _kald("nvidia-nim", "nemotron", ok=28, n=30)
    set_runtime_state_value("cheap_lane_success_rate_exclusion_enabled", "on")

    ud = enforce()

    assert ud["enabled"] is True
    assert ud["quarantined"] == 1
    assert (get_cheap_provider_runtime_state(
        provider="nvidia-nim", model="nemotron") or {}).get("cooldown_until") in (None, "")


def test_enforce_er_self_safe_naar_db_er_nede(isolated_runtime, monkeypatch):
    """En fejl i dommeren må ALDRIG vælte routing-stien."""
    from core.services import cheap_lane_success_rate as sr

    monkeypatch.setattr(sr, "find_chronic_failures",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")))
    ud = sr.enforce()
    assert ud["quarantined"] == 0


# ── dommeren maa ikke forny sig selv (maalt i drift 10/10-2026) ──────────────
#
# `enforce()` kaldes fra `call_balanced` — ved HVERT balanceret kald, ikke ved
# run-end som docstringen foerst paastod. Maalt: 21 koersler paa 45 minutter, og
# der gaar ~4.360 kald gennem `call_balanced` i timen. Hver koersel skrev
# `cooldown_until = nu + 24t` igen, saa karantaenen blev fornyet i det uendelige:
# en provider der RETTEDE sig kunne aldrig komme tilbage af sig selv — hvilket
# var hele pointen med den tidsbegraensede karantaene.


def test_karantaenen_fornyes_ikke_naar_slottet_allerede_er_doemt(isolated_runtime):
    """Anden koersel paa et allerede doemt slot maa ikke skrive cooldown igen."""
    from core.runtime.db import get_cheap_provider_runtime_state
    from core.runtime.db_core import set_runtime_state_value
    from core.services.cheap_lane_success_rate import enforce

    _kald("freeai", "qwen7b", ok=2, n=30)
    set_runtime_state_value("cheap_lane_success_rate_exclusion_enabled", "on")

    foerste = enforce()
    assert foerste["quarantined"] == 1
    st1 = get_cheap_provider_runtime_state(provider="freeai", model="qwen7b") or {}
    cooldown1 = st1.get("cooldown_until")

    anden = enforce()
    st2 = get_cheap_provider_runtime_state(provider="freeai", model="qwen7b") or {}

    assert anden["quarantined"] == 0, "en allerede doemt slot skal ikke doemmes igen"
    assert st2.get("cooldown_until") == cooldown1, "cooldown maa ikke skubbes frem"


def test_udloebet_karantaene_doemmes_paa_ny(isolated_runtime):
    """Er cooldown UDLOEBET, skal dommen falde igen — ellers kan en doed
    provider snige sig tilbage uden en ny maaling."""
    from core.runtime.db import get_cheap_provider_runtime_state
    from core.runtime.db_core import set_runtime_state_value
    from core.services.cheap_lane_success_rate import enforce

    _kald("freeai", "qwen7b", ok=2, n=30)
    set_runtime_state_value("cheap_lane_success_rate_exclusion_enabled", "on")

    enforce()
    # Simulér at karantaenen er udloebet: saet cooldown til datiden.
    from core.runtime.db import upsert_cheap_provider_runtime_state
    upsert_cheap_provider_runtime_state(
        provider="freeai", model="qwen7b", status="quarantined",
        cooldown_until="2020-01-01T00:00:00+00:00",
        last_error_code="low-success-rate",
    )

    ud = enforce()
    st = get_cheap_provider_runtime_state(provider="freeai", model="qwen7b") or {}

    assert ud["quarantined"] == 1, "en udloebet karantaene skal fornyes"
    assert st.get("cooldown_until") != "2020-01-01T00:00:00+00:00"


def test_en_anden_grund_doemmes_igen(isolated_runtime):
    """Karantaene af en ANDEN aarsag (fx rate-limited) maa ikke blokere dommen."""
    from core.runtime.db import upsert_cheap_provider_runtime_state
    from core.runtime.db_core import set_runtime_state_value
    from core.services.cheap_lane_success_rate import enforce

    _kald("freeai", "qwen7b", ok=2, n=30)
    set_runtime_state_value("cheap_lane_success_rate_exclusion_enabled", "on")
    upsert_cheap_provider_runtime_state(
        provider="freeai", model="qwen7b", status="cooldown-active",
        cooldown_until="2099-01-01T00:00:00+00:00",
        last_error_code="rate-limited",
    )

    ud = enforce()

    assert ud["quarantined"] == 1, "en fremmed grund er ikke vaern mod en fejl-dom"

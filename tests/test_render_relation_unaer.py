"""`!` er unær — render_relation må ikke skrive den som infiks.

BAGGRUND (målt 28/10-2026). `RELATION_OPERATORS` mapper BÅDE `salience` og
`prediction_error` til `"!"`. `render_relation` skrev resultatet som
`f"{tx} {op} {ty}"` — altså `puls ! krop`. Men `!` er unær i lexikonet:
`PRIMITIVES["!"]` har eksemplerne `!grænse`, `!nysgerrighed`,
`!signal ⊂ nu`, og `central_notation.parse()` kender kun `!` som PRÆFIKS.

Konsekvensen var ikke kosmetisk. I `central_hypotheses` stod **75.877 rækker**
med infiks-formen (kun 10 unikke notationer: `puls ! kontinuitet`, `puls ! krop`,
`læring ! kontinuitet` …), og 97 % af Centralens notationer var derfor blinde
for den model-frie inferens. `parse()` kunne ikke læse dem, så dedup og
antecedent-korrelation — hele nordstjerne-beviset i §5 — fik intet at regne på.

Det var ikke parseren der var for snæver. Det var rendereren der skrev en form
sproget ikke har.

RETTELSEN. `!` skrives nu som præfiks på andet led: `x → !y` — «x fører til en
overraskelse i y», som er netop prediction_error. Det bevarer det binære
forhold OG er læsbart for `parse()`.

DETTE ER IKKE GJORT: de 75.877 eksisterende rækker er stadig i infiks-form.
Rettelsen virker fremad. En migrering (`puls ! krop` → `puls → !krop`) er en
ren teksttransformation, men den rører 75.877 rækker i en tabel med 135.124,
så den kræver Bjørns ord — den er ikke gjort her.
"""
from __future__ import annotations

import pytest

from core.services import central_lexicon as cl
from core.services import central_notation as cn


def _bundne_par() -> tuple[str, str]:
    """Find to kildenavne der faktisk er bundne i denne proces.

    `to_term` returnerer None for ubundne navne — og målt 28/10-2026 er
    `puls` i vokabularet men IKKE i `SEED_BINDINGS`, så den er ubundet.
    Testen må ikke antage en bestemt binding; den finder sine egne.
    """
    bundne = [n for n in cl.SEED_BINDINGS if cl.to_term(n)]
    if len(bundne) < 2:
        pytest.skip(
            f"kun {len(bundne)} bundne kilde-navne i lexikonet — "
            "kan ikke måle render_relation (den returnerer None uden bindinger)"
        )
    return bundne[0], bundne[1]


def test_prediction_error_skrives_som_praefiks() -> None:
    """`!` skal stå som præfiks på andet led, ikke som infiks."""
    a, b = _bundne_par()
    ud = cl.render_relation(a, b, relation="prediction_error")
    assert ud is not None, f"render_relation({a!r}, {b!r}) gav None"
    assert " ! " not in ud, f"infiks-form opstod: {ud!r} — `!` er unær"
    assert " → !" in ud, f"forventede `→ !` som præfiks-led, fik {ud!r}"


def test_resultatet_kan_parses() -> None:
    """MODPRØVE: det er hele pointen — notationen skal kunne læses bagefter.

    Uden denne kunne nogen «løse» opgaven ved at skrive `x !y` uden
    mellemrum og stadig bestå testen ovenfor.
    """
    a, b = _bundne_par()
    ud = cl.render_relation(a, b, relation="prediction_error")
    assert ud is not None
    p = cn.parse(ud)
    assert p is not None, f"parse() kunne IKKE læse {ud!r} — rettelsen virkede ikke"
    assert p["operator"] == "→"
    assert p["consequent"].startswith("!"), p
    assert p["antecedent"], "antecedent må ikke være tom i en binær relation"


def test_infiks_formen_er_faktisk_ulaeselig() -> None:
    """Bevis på hvorfor rettelsen var nødvendig — ikke en antagelse.

    Den gamle form skal fejle i parse(). Gør den ikke det, er hele
    begrundelsen forkert og rettelsen skal rulles tilbage.
    """
    assert cn.parse("puls ! krop") is None, (
        "infiks-formen KAN læses — så var diagnosen forkert"
    )
    assert cn.parse("puls → !krop") is not None


def test_causal_convergence_er_uaendret() -> None:
    """Regression: den binære standardform må ikke ændre sig."""
    a, b = _bundne_par()
    ud = cl.render_relation(a, b, relation="causal_convergence")
    assert ud is not None
    assert " ! " not in ud
    assert "→" in ud
    p = cn.parse(ud)
    assert p is not None and p["operator"] == "→"


def test_salience_er_dokumenteret_ikke_understoettet() -> None:
    """`salience` er ren unær («x er salient») og kan ikke udtrykkes binært.

    Ingen kalder den i dag (målt 28/10-2026). Testen fastholder at den
    IKKE giver en tavs forkert betydning: den giver prediction_error-formen,
    og det står skrevet i render_relation. Bliver salience reel, skal den
    have sin egen en-leds-vej — ikke denne.
    """
    a, b = _bundne_par()
    ud = cl.render_relation(a, b, relation="salience")
    assert ud is not None
    # Den deler tegn med prediction_error — det er netop det uløste problem.
    assert ud == cl.render_relation(a, b, relation="prediction_error"), (
        "salience og prediction_error deler `!` og er derfor ikke til at skelne "
        "i notationen — det er kendt og dokumenteret, ikke en ny fejl"
    )

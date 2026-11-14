"""Eval-harness for MEMORY.md-udvaelgelsen — maal FOER du retter.

## Hvorfor (14/11-2026)

`_lexical_coverage` normaliserer paa forespoergslens EGEN vaegt. Ved en
forespoergsel der kun efterlader ét brugbart ord («hvordan har jeg det i dag»
→ `dag`) bliver enhver sektion med det ord daekning 1,0. Maalt: 311 af 2.311
sektioner fik topkarakter, og de tre der vandt var reelt tilfaeldige.

Defekten kan ikke vurderes paa én maaling. En rettelse der holder stoej ude
men taber rigtige sektioner er vaerre end defekten, saa harnesset maaler TO
akser og en kandidat skal vinde paa begge:

* **recall@3** — staar den kendte sektion blandt de tre valgte?
* **stoej** — hvor mange sektioner injiceres paa et aabent spoergsmaal hvor
  ingen sektion er det rigtige svar?

Spoergsmaalene og deres forventede overskrift er taget fra MEMORY.md's egne
overskrifter. De er ikke formuleret efter hvad systemet er god til; de er
formuleret som Bjørn ville spoerge.

Koeres som script (ikke pytest): `python scripts/eval_memory_selection.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

WORKSPACE = Path.home() / ".jarvis-v2" / "workspaces" / "bjorn"

#: (spoergsmaal, forventet overskrift som den staar i MEMORY.md)
TEKNISKE: list[tuple[str, list[str]]] = [
    ("hvad var der galt med tick-kvaliteten?",
     ["Tick-kvalitet — symptom, ikke mål"]),
    ("recurring tasks delay-bug — hvad var fejlen?",
     ["Recurring tasks — delay-bug fixet 18. sept 2026"]),
    ("hvordan virker Agent Smith i shadow mode?",
     ["Agent Smith — shadow mode er korrekt"]),
    ("hvordan overvåger vi PSU'en på i9?",
     ["PVE-PSU-overvågning (i9/M900)"]),
    ("hvem kan skrive til Telegram-botten?",
     ["Telegram — indgående er owner-only (17. sept 2026)"]),
    ("hvorfor lækkede reasoning ud som synlig besked?",
     ["Reasoning lækker ud som synlig besked (fundet 18. sept 2026)"]),
    ("er mobil-companion bygget?",
     ["mobile companion (planlagt — IKKE bygget)"]),
    ("hvad er status på jarvis-desk desktop-app?",
     ["jarvis-desk desktop-app"]),
    ("hvad var erkendelsen om kode-æstetik?",
     ["Kode-æstetik — erkendelse landet (9. sep 2026)"]),
    ("hvad skete der med lease-sporet i drift?",
     ["Lease-sporet fyrede i drift — og forældet-dommen fejlede igen (målt 14/10-2026)"]),
    ("hvorfor blev _terms tokeniseret 13.830 gange?",
     ["Assembly-spidsen: _terms blev tokeniseret 13.830 gange pr. kald (12/10-2026, 68541e061)"]),
    ("hvordan verificerer vi desk-asset-navnet?",
     ["Desk-opdatering — asset-navnet og hash-verifikationen (13/10-2026)"]),
    # Tre naesten-identiske VESC-overskrifter: begge er gyldige svar paa
    # spoergsmaalet om hvad vi HAR FUNDET. At acceptere kun én ville maale
    # min egen ordlyd, ikke om udvaelgelsen ramte emnet.
    ("hvad har vi fundet om VESC?",
     ["VESC — Reverse Engineering", "VESC Open Client"]),
    # Samme emne i to sprogversioner — begge er det rigtige svar.
    ("hvilke drømmehypoteser er aktive?",
     ["Dream hypotheses — aktiv", "Drømmehypoteser (carry-over"]),
    # Overskriften findes i baade en 'Målefælde jeg faldt i'- og en
    # 'Målefælden jeg selv faldt i'-form.
    ("hvilken målefælde faldt jeg selv i?",
     ["Målefælden jeg selv faldt i", "Målefælde jeg faldt i", "Målefælde jeg selv faldt i"]),
    ("hvilke fælder bider?",
     ["Fælder der bider"]),
    ("hvorfor måler vi først og bygger bagefter?",
     ["Målt først, bygget bagefter"]),
    ("hvilke ollama cloud-modeller skal forblive?",
     ["Container — Ollama cloud-modeller (skal forblive)"]),
]

#: Aabne/personlige spoergsmaal. INGEN sektion er det rigtige svar — alt der
#: injiceres her er stoej i prompten.
AABNE: list[str] = [
    "hvordan har jeg det i dag",
    "hvad tænker du om det",
    "kan du hjælpe mig lidt",
    "hvad synes du",
    "er der noget nyt",
]


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _df_map(sektioner: list[tuple[str, str]], terms: Callable[[str], frozenset[str]]) -> dict[str, int]:
    df: dict[str, int] = {}
    for heading, text in sektioner:
        for term in terms(f"{heading} {text}"):
            df[term] = df.get(term, 0) + 1
    return df


def byg_varianter(
    mms: Any, sektioner: list[tuple[str, str]], aegte: Callable[..., float]
) -> dict[str, dict[str, Any]]:
    """Varianterne der maales. Hver er (coverage-funktion, min_score).

    `aegte` er den ORIGINALE `_lexical_coverage`, bundet foer patchning —
    ellers kalder varianten sig selv og rekurserer til dybde-loftet.
    """
    df = _df_map(sektioner, mms._terms)
    n = max(1, len(sektioner))

    def cov_a(query: str, section: str, text: str, *, vaegte: dict[str, float] | None = None) -> float:
        """Kandidat A — absolut bevis: ét ramt ord er ikke nok, medmindre det er diskriminativt.

        Ved en et-ords-forespoergsel er der intet at normalisere imod, saa
        spoergsmaalet bliver om ordet selv baerer bevis. `dag` staar i 13,5 %
        af sektionerne og goer det ikke; `vesc` staar i en haandfuld og goer.
        """
        base = aegte(query, section, text, vaegte=vaegte)
        if base <= 0.0:
            return 0.0
        ramt = mms._terms(query) & mms._terms(f"{section} {text}")
        if len(ramt) >= 2:
            return base
        if not ramt:
            return 0.0
        term = next(iter(ramt))
        if df.get(term, 0) <= 0.02 * n:
            return base
        return 0.0

    def cov_b(query: str, section: str, text: str, *, vaegte: dict[str, float] | None = None) -> float:
        """Kandidat B — loft pr. term: ét ord kan hoejst baere 40 % af daekningen."""
        q = mms._terms(query)
        if not q:
            return 0.0
        ramt = q & mms._terms(f"{section} {text}")
        if not ramt:
            return 0.0
        vaegte = vaegte or {}
        i_alt = sum(vaegte.get(t, mms._IDF_UKENDT) for t in q)
        if i_alt <= 0.0:
            return 0.0
        loft = 0.40 * i_alt
        return min(1.0, sum(min(vaegte.get(t, mms._IDF_UKENDT), loft) for t in ramt) / i_alt)

    def cov_nul(query: str, section: str, text: str, *, vaegte: dict[str, float] | None = None) -> float:
        """KONTROL: sluk hele den leksikalske vej. Kun semantiske hits tilbage.

        Uden denne kontrol kan jeg ikke vide om harnesset OVERHOVEDET kan se en
        aendring: giver det samme tal for en bevidst brudt udvaelgelse, maaler
        det ingenting — og saa er hele konklusionen vaerdiloes.
        """
        return 0.0

    return {
        "baseline": {"cov": None, "min_score": 0.30},
        "kontrol_kun_semantisk": {"cov": cov_nul, "min_score": 0.30},
        "a_absolut": {"cov": cov_a, "min_score": 0.30},
        "a_absolut_t55": {"cov": cov_a, "min_score": 0.55},
        "b_loft": {"cov": cov_b, "min_score": 0.30},
        "b_loft_t60": {"cov": cov_b, "min_score": 0.60},
    }


def koer(vaeg: str, mms: Any, sektioner: list[tuple[str, str]]) -> dict[str, Any]:
    aegte = mms._lexical_coverage
    varianter = byg_varianter(mms, sektioner, aegte)
    v = varianter[vaeg]
    if v["cov"] is not None:
        mms._lexical_coverage = v["cov"]
    try:
        hits: list[dict[str, Any]] = []
        for spoergsmaal, forventet in TEKNISKE:
            linjer = mms.select_memory_md_sections(
                spoergsmaal, workspace_dir=WORKSPACE,
                max_sections=3, max_chars=1500, min_score=v["min_score"],
            )
            tekst = _norm(" ".join(linjer))
            hits.append({
                "spoergsmaal": spoergsmaal,
                "forventet": forventet[0],
                "ramt": any(_norm(a) in tekst for a in forventet),
                "antal": len(linjer),
                "linjer": linjer,
            })
        stoej: list[dict[str, Any]] = []
        for spoergsmaal in AABNE:
            linjer = mms.select_memory_md_sections(
                spoergsmaal, workspace_dir=WORKSPACE,
                max_sections=3, max_chars=1500, min_score=v["min_score"],
            )
            stoej.append({"spoergsmaal": spoergsmaal, "antal": len(linjer), "linjer": linjer})
    finally:
        mms._lexical_coverage = aegte
    return {
        "variant": vaeg,
        "recall_at_3": sum(1 for h in hits if h["ramt"]) / max(1, len(hits)),
        "ramte": sum(1 for h in hits if h["ramt"]),
        "i_alt": len(hits),
        "stoej_sektioner": sum(s["antal"] for s in stoej),
        "stoej_snitt": sum(s["antal"] for s in stoej) / max(1, len(stoej)),
        "stoej_spoergsmaal_med_indhold": sum(1 for s in stoej if s["antal"]),
        "detaljer": hits,
        "stoej": stoej,
    }


def main() -> int:
    from core.services.prompt_sections import memory_md_selection as mms

    sektioner = mms._memory_md_sections(WORKSPACE)
    print(f"sektioner i korpus: {len(sektioner)}")
    print(f"spoergsmaal: {len(TEKNISKE)} tekniske + {len(AABNE)} aabne")
    resultater = []
    for vaeg in ("baseline", "kontrol_kun_semantisk", "a_absolut", "a_absolut_t55", "b_loft", "b_loft_t60"):
        r = koer(vaeg, mms, sektioner)
        resultater.append(r)
        print(f"\n=== {vaeg} ===")
        print(f"  recall@3 : {r['ramte']}/{r['i_alt']} = {r['recall_at_3']:.1%}")
        print(f"  stoej    : {r['stoej_sektioner']} sektioner paa {len(AABNE)} aabne "
              f"(snit {r['stoej_snitt']:.1f}, {r['stoej_spoergsmaal_med_indhold']} spoergsmaal ramt)")
        if vaeg == "baseline":
            for h in r["detaljer"]:
                if not h["ramt"]:
                    print(f"    MISS: {h['spoergsmaal']!r} -> {h['forventet']!r}")
            for s in r["stoej"]:
                if s["antal"]:
                    print(f"    STOEJ: {s['spoergsmaal']!r} -> {s['antal']} sektioner")

    print("\n=== SAMMENFATNING ===")
    for r in resultater:
        print(f"{r['variant']:<16} recall@3 {r['recall_at_3']:>6.1%}   stoej {r['stoej_sektioner']:>2} sektioner")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

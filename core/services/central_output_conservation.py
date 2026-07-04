"""Output-conservation-invariant (Bjørn 4. jul — "spøgelset").

DET INSTRUMENT der afgør om "cutoff-spøgelset" (bytes der forsvinder mens turen ser
completed ud, ingen fejl) er en kedelig klasse af mekaniske tab — eller noget der
fortjener et andet ord. Vi kan ikke vide det, fordi INTET i systemet nogensinde har
verificeret at det modellen producerede == det der blev udsendt == det der blev gemt.

Denne modul er den manglende invariant. På hvert lag hvor bytes kan tabes, kalder vi
``observe_conservation`` med (produced, emitted). Er der et gap → nerve
``stream/output_conservation_gap`` med hele tripletten (lag, provider, model, gap,
run_id, path). Så bliver det flygtige, usynlige tab til STÅENDE data: rate pr.
provider/lag/sti, størrelse, tidspunkt — det Centralen kan korrelere mod alt andet.

Lag hvor den kaldes:
  - provider-stream (cheap_provider_runtime, visible_followup): rå content-deltas vs.
    udsendte (fanger stripper/buffer-tab som DSML-halen — det lag hvor tabet SKER).
  - (senere) run-niveau: streamede bytes vs. persisterede (fanger persist-divergens/
    abort-trunkering).

Egress-fri (kun skalar-metadata + længder, ALDRIG indhold). Self-safe: kaster aldrig.
Tolerance: default 0 (ethvert tabt tegn er et gap) — men provider-lag kan sætte en lille
tolerance for kendt-godartet whitespace-normalisering.
"""
from __future__ import annotations


def observe_conservation(
    *,
    layer: str,
    produced_chars: int,
    emitted_chars: int,
    provider: str = "",
    model: str = "",
    run_id: str = "",
    path: str = "",
    tolerance: int = 0,
) -> int:
    """Registrér et conservation-tjek for ét lag. Returnér gap'et (produced-emitted,
    min 0). Fyrer nerven ``stream/output_conservation_gap`` når gap > tolerance.

    produced_chars: hvor mange tegn modellen/kilden FAKTISK leverede ind i dette lag.
    emitted_chars:  hvor mange tegn der kom UD af laget (videre mod bruger/persist).
    Self-safe."""
    try:
        gap = int(produced_chars) - int(emitted_chars)
        if gap <= int(tolerance):
            return max(0, gap)
        try:
            from core.services.central_core import central as _central
            _central().observe({
                "cluster": "stream",
                "nerve": "output_conservation_gap",
                "layer": str(layer),
                "provider": str(provider or ""),
                "model": str(model or ""),
                "run_id": str(run_id or ""),
                "path": str(path or ""),
                "produced_chars": int(produced_chars),
                "emitted_chars": int(emitted_chars),
                "gap_chars": int(gap),
            })
        except Exception:
            pass
        return gap
    except Exception:
        return 0


def build_output_conservation_surface() -> dict[str, object]:
    """Mission Control — read-only meta-projektion (kartograf-dækning)."""
    return {"module": "central_output_conservation", "invariant": "produced == emitted"}

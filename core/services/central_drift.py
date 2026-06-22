"""Flag-on-change (§7) — aktiv drift-detektion pr. nerve.

Centralen flagger AKTIVT når en nerves mønster RYKKER SIG — fejl-rate eller RED-rate
driver ud over nervens egen baseline ± tolerance. Ikke passiv log: proaktiv "noget
ændrede sig her". "Catch it live hver gang."

DETERMINISTISK + READ-ONLY: tællere/fordelinger + EWMA-baseline + tærskel. Muterer
ALDRIG kørende politik (det er §6-læring, udskudt). Den FLAGGER kun — flaget persisteres
som incident, så Bjørn/Claude kan fange driften live.

Baseline er pr.-proces in-memory (genopbygges efter genstart, kræver ét vindue at etablere);
flagene persisterer. Konservativ pr. §14: store skift flagges, små ignoreres.
"""
from __future__ import annotations

import threading
from typing import Any


class NerveDriftMonitor:
    """Pr.-nerve: akkumulér fejl/RED over et rullende vindue; flag hvis raten driver ud
    over baseline ± tol. Selv-sikker: returnerer None ved enhver tvivl."""

    def __init__(self, *, check_every: int = 30, tol: float = 0.3, alpha: float = 0.3) -> None:
        self._stats: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._check_every = max(5, int(check_every))
        self._tol = float(tol)
        self._alpha = float(alpha)

    def record(self, nerve: str, *, is_error: bool, is_red: bool) -> dict | None:
        """Opdatér nervens vindue. Returnér en drift-flag-dict hvis raten netop drev ud
        over baseline ± tol (ellers None). Etablerer baseline stille i første vindue."""
        try:
            with self._lock:
                s = self._stats.setdefault(
                    nerve, {"n": 0, "errors": 0, "reds": 0, "base_err": None, "base_red": None})
                s["n"] += 1
                if is_error:
                    s["errors"] += 1
                if is_red:
                    s["reds"] += 1
                if s["n"] < self._check_every:
                    return None

                err_rate = s["errors"] / s["n"]
                red_rate = s["reds"] / s["n"]
                flag: dict | None = None

                if s["base_err"] is None:
                    # første fulde vindue = etablér baseline, ingen flag endnu.
                    s["base_err"], s["base_red"] = err_rate, red_rate
                else:
                    from core.services.central_switches import drift_flag
                    ef = drift_flag(f"{nerve}.error_rate", err_rate,
                                    baseline=s["base_err"], tol=self._tol)
                    rf = drift_flag(f"{nerve}.red_rate", red_rate,
                                    baseline=s["base_red"], tol=self._tol)
                    flag = ef or rf
                    # EWMA — baselinen følger langsomt med, så kun SKIFT flagges.
                    s["base_err"] = self._alpha * err_rate + (1 - self._alpha) * s["base_err"]
                    s["base_red"] = self._alpha * red_rate + (1 - self._alpha) * s["base_red"]

                s["n"], s["errors"], s["reds"] = 0, 0, 0
                return flag
        except Exception:
            return None

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Read-only kig på baselines (til verifikation/debug). Selv-sikker."""
        try:
            with self._lock:
                return {k: dict(v) for k, v in self._stats.items()}
        except Exception:
            return {}

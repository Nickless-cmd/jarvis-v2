"""Værn for den offentlige status-rute — og for at den RIGE ikke bliver offentlig.

Baggrund (25/10-2026, Bjørn): forsiden på jarvis.srvlab.dk viste «offline»,
fordi vhosten proxyede ``/api/status`` til et dødt target. Da det blev rettet,
viste det sig at ``/status`` bærer ``model`` og ``daemons`` — og at dens egen
docstring påstod den var «public-safe, kun online + uptime». Kommentaren og
koden var uenige, og det var kommentaren der blev læst.

Valget blev en separat ``/status/public`` med en bevidst smal feltliste. Disse
tests værner to ting der begge kan smuldre stille:

1. **Feltlisten.** Tilføjer nogen ``model`` eller ``daemons`` til den
   offentlige rute, lækker det til hele internettet uden token.
2. **Adskillelsen.** Lemper nogen på ``/status`` i stedet for at bruge den
   smalle rute, er der ingen offentlig flade tilbage at beskytte — så
   ``/status`` skal fortsat kræve token.
"""
from __future__ import annotations

import inspect

import pytest


def _public_paths() -> tuple[str, ...]:
    from apps.api.jarvis_api.middleware import jarvisx_user_routing as m

    return m._PUBLIC_PATHS


def _er_public(sti: str) -> bool:
    from apps.api.jarvis_api.middleware import jarvisx_user_routing as m

    # Brug middlewarens EGEN matcher frem for at gentage dens logik her.
    # En test der selv implementerer reglen kan ikke se at reglen ændrer sig.
    for navn in ("_is_public_path", "_er_public_sti", "_public"):
        fn = getattr(m, navn, None)
        if callable(fn):
            try:
                return bool(fn(sti))
            except TypeError:
                pass
    for p in m._PUBLIC_PATHS:
        if sti == p or sti.startswith(p + "/"):
            return True
    return False


class TestDenOffentligeRute:
    def test_ruten_findes_og_returnerer_kun_online_og_uptime(self) -> None:
        """Den offentlige rute må ikke bære model, daemons eller versionstal."""
        from apps.api.jarvis_api.routes.status import status_public

        data = status_public()

        assert data["online"] is True
        assert isinstance(data["uptime_seconds"], int)
        assert isinstance(data["uptime_human"], str)

        # Feltlisten er en KONTRAKT, ikke et tilfælde. Disse må aldrig dukke op.
        for forbudt in ("model", "daemons", "environment", "version", "app_name"):
            assert forbudt not in data, (
                f"«{forbudt}» står i den OFFENTLIGE status. Ruten er token-fri, "
                f"så feltet er læsbart for alle på internettet. Flyt det til "
                f"/status (som kræver token) i stedet."
            )

    def test_den_rige_rute_baerer_det_offentlige_ikke_maa(self) -> None:
        """Bevis for at adskillelsen er reel: /status har felterne, /public ikke."""
        from apps.api.jarvis_api.routes.status import status, status_public

        rigtig = status()
        offentlig = status_public()

        assert "model" in rigtig and "daemons" in rigtig
        assert set(offentlig) < set(rigtig), (
            "den offentlige rute er ikke en ægte delmængde — så er adskillelsen "
            "kun kosmetisk"
        )


class TestAuthAdskillelsen:
    def test_offentlig_rute_slipper_gennem_uden_token(self) -> None:
        assert _er_public("/status/public"), (
            "/status/public står ikke i _PUBLIC_PATHS — så svarer den 401 og "
            "forsidens statusprik kan ikke læses udefra."
        )

    def test_den_rige_status_kraever_token(self) -> None:
        """Den vigtigste negative test.

        ``/status`` bærer modelnavn og daemontal. Stod den i _PUBLIC_PATHS,
        ville den lække uden at nogen behøvede at røre den offentlige rute —
        og ingen test af /status/public ville opdage det.
        """
        assert not _er_public("/status"), (
            "/status er blevet token-fri. Den bærer «model» og «daemons», så "
            "det gør intern drift-information læsbar for alle. Brug "
            "/status/public til forsiden i stedet."
        )

    def test_den_offentlige_rute_er_ikke_bare_et_praefiks_af_den_rige(self) -> None:
        """Præfiks-matchning må ikke gøre /status public via /status/public.

        Matcheren bruger ``startswith(p + "/")``. Retningen er sikker her
        (``/status/public`` er ikke et præfiks af ``/status``), men den er
        værd at måle: bytter nogen om på de to strenge, åbner det den rige.
        """
        assert not _er_public("/status/hemmelig"), (
            "en ukendt understi til /status slipper igennem — så er det ikke "
            "den konkrete rute der er fritaget, men hele dens stamme"
        )

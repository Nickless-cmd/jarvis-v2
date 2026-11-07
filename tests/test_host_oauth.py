"""Tokenopslaget maa ikke kassere et token der virker (7/11-2026).

## Hvorfor denne fil findes

Maalt 7/11-2026 i containeren: `find_host_oauth_token()` returnerede `None`,
og `claude_dispatch` doede med

    no host Claude Code OAuth token available — open Claude Code …

Men der VAR et token. 15 processer, ejet af samme uid, bar et
`CLAUDE_CODE_OAUTH_TOKEN` paa 108 tegn med praefiks `sk-ant-oat01`. Ingen af dem
havde `CLAUDECODE` eller `CLAUDE_CODE_ENTRYPOINT` — de var Xvfb-soeskende der
havde arvet miljoeet fra den session der startede dem.

Filteret kraevede hint-noeglen og kasserede derfor et token der beviseligt
virkede: `claude -p` svarede `OK` med praecis den vaerdi. Fejlen lignede en
manglende Claude Code-session, men var et for snaevert filter — og den slags
koster en hel arbejdsgang, fordi diagnosticen peger det forkerte sted hen.

Testen maaler FORMAT-VAERNET, ikke bare funktionen: fjerner man praefiks-reglen,
skal `test_token_paa_format_accepteres_uden_hint` fejle.
"""
from __future__ import annotations

from core.tools.claude_dispatch.host_oauth import (
    _OAUTH_TOKEN_PREFIXES,
    _looks_like_claude_host,
)


def test_hint_noegle_alene_er_nok() -> None:
    """En aegte Claude Code-host med miljoe-markoer skal altid accepteres."""
    assert _looks_like_claude_host({"CLAUDECODE": "1"}, "hvad-som-helst") is True
    assert _looks_like_claude_host({"CLAUDE_CODE_ENTRYPOINT": "cli"}, "x") is True


def test_token_paa_format_accepteres_uden_hint() -> None:
    """Det maalte tilfaelde: gyldigt token, ingen hint-noegle.

    Dette er den regel der blev tilfoejet 7/11-2026. Uden den doer dispatch
    paa en maskine hvor tokenet ligger i et arvet miljoe.
    """
    token = _OAUTH_TOKEN_PREFIXES[0] + "01-abc123"
    assert _looks_like_claude_host({}, token) is True


def test_vilkaarlig_vaerdi_uden_hint_afvises() -> None:
    """Vaernet skal stadig vaere et vaern: en tilfaeldig arvet streng er ikke et token."""
    assert _looks_like_claude_host({}, "en-tilfaeldig-vaerdi") is False
    assert _looks_like_claude_host({}, "") is False


def test_praefikset_er_claude_codes_eget() -> None:
    """Praefikset er ikke en gaettevaerdi — det er det format der blev maalt i drift."""
    assert _OAUTH_TOKEN_PREFIXES == ("sk-ant-oat",)

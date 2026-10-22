"""Vagt: et medlems workspace maa ikke ligge i klartekst med rigtigt indhold.

Baggrund (maalt 22/10-2026): krypteringen af member-workspaces er gatet af
`ENCRYPT_ON_WRITE` (`JARVISX_ENCRYPT_WORKSPACES`), som staar i de koerende
processers env — men IKKE i systemd-unit'en og ikke i repoets `.env`. En
genstart ad en anden vej, og graensen er vaek uden at nogen opdager det.

Tilstanden den dag, for de MENNESKELIGE medlemmer:

    bjorn     0 .enc   51 plain   (owner — by design)
    michelle 15 .enc    0 plain
    mikkel   15 .enc    0 plain
    lotte     0 .enc   15 plain   (alle 37-47 byte stubbe)
    rune      0 .enc   15 plain   (alle 37-47 byte stubbe)

Lotte og Rune laekker altsaa intet i dag: deres filer er tomme stubbe. Men i det
oejeblik en af dem skriver, skal indholdet lande som `.enc`. Denne test fanger
det oejehblik det ikke sker — den er en vagt paa TILSTANDEN, ikke paa flaget, saa
den ogsaa daekker en genstart der mister env'en.

Den maaler KUN registrerede mennesker fra `users`-tabellen. Agent-workspaces
(`toku-job`, `toku-agent`, pensionerede `.Bjørn.retired-*`) er ikke medlemmers
private rum og skal ikke krypteres — maalt 22/10: `toku-job` havde 7.634 byte
klartekst i TOOLS.md, og det er rigtigt for en agent.
"""
from __future__ import annotations

from pathlib import Path

#: En stub er en pladsholder paa nogle faa linjer. Alt over dette er indhold.
STUB_MAKS_BYTES = 200


def _medlems_workspaces() -> list[str]:
    """Workspace-navne for rigtige mennesker (role != owner), fra users-tabellen."""
    from core.runtime.db_core import connect

    with connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT workspace FROM users "
            "WHERE workspace IS NOT NULL AND workspace != '' "
            "AND (role IS NULL OR role != 'owner') AND deleted_at IS NULL"
        ).fetchall()
    return sorted({str(r[0]) for r in rows if r[0]})


def test_intet_medlems_workspace_har_klartekst_indhold():
    from core.runtime.config import WORKSPACES_DIR

    root = Path(WORKSPACES_DIR)
    if not root.is_dir():
        return  # intet miljoe at maale i (fx CI uden workspaces)

    problemer: list[str] = []
    for navn in _medlems_workspaces():
        ws = root / navn
        if not ws.is_dir():
            continue
        for fil in sorted(ws.glob("*.md")):
            stoerrelse = fil.stat().st_size
            if stoerrelse <= STUB_MAKS_BYTES:
                continue          # pladsholder — intet at laekke
            krypteret = fil.with_suffix(fil.suffix + ".enc")
            problemer.append(
                f"{navn}/{fil.name}: {stoerrelse} byte klartekst"
                + ("" if krypteret.exists() else " (ingen .enc ved siden af)")
            )

    assert not problemer, (
        "medlems-workspace har klartekst-indhold — krypteringen skriver ikke .enc.\n"
        "Tjek at JARVISX_ENCRYPT_WORKSPACES=1 staar i DEN KOERENDE proces OG i "
        "systemd-unit'en, saa den overlever en genstart:\n  "
        + "\n  ".join(problemer))


def test_kryptering_er_failsafe_for_ukendt_bruger():
    """`should_encrypt()` skal kryptere naar den ikke kan afgoere det."""
    from core.services.workspace_crypto import should_encrypt

    assert should_encrypt("en-helt-ukendt-workspace") is True

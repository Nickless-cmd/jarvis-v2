"""Git-handlinger for code-mode's workspace-vaelgere.

Desk skal kunne vise en branch-liste med soegefelt og oprette/udchecke en ny
branch, og vaelge mellem betroede mapper eller en ny lokal worktree. Alt det
krævede svar API'et ikke kunne give: der fandtes `/chat/git-status` (én branch,
ingen liste) og `/chat/workspace-trust` (én mappe ad gangen).

## De to veje er ikke den samme kommando

`kind="container"` koerer git i API-processen mod repoets egen rod.
`kind="workstation"` koerer over operator-broen paa Bjoerns maskine, hvor
`root` er en sti DEROVRE. Samme git-argumenter, to vidt forskellige
transportveje — derfor `_koer`, saa hver handling kun skrives én gang.

## Hvorfor der ikke bygges kommandostrenge med brugerinput

Container-vejen sender en argument-liste til subprocess (ingen skal). Bro-vejen
SKAL have en streng, og der citeres hvert felt med `shlex.quote`. Et branch-navn
er brugerinput; uden citering ville `foo; rm -rf ~` vaere en gyldig «branch».
"""
from __future__ import annotations

import shlex
import subprocess
from typing import Any

# Hver handling afsluttes med denne markoer, saa et sammensat bro-kald kan
# deles op igen. Git-output indeholder den ikke.
_SKILLER = "@@@JARVIS@@@"

_TIMEOUT = 20


def _koer_lokalt(root: str, args: list[list[str]]) -> tuple[bool, list[str]]:
    ud: list[str] = []
    for a in args:
        try:
            r = subprocess.run(
                ["git", "-C", root, *a],
                capture_output=True, text=True, timeout=_TIMEOUT,
            )
        except Exception as e:
            # Samme grund som i bro-vejen: en tavs False efterlader brugeren
            # med «kunne ikke» og ingen vej videre.
            return False, ud + [f"git kunne ikke koeres: {e}"]
        if r.returncode != 0 and not r.stdout.strip():
            return False, ud + [str(r.stderr or "").strip() or f"git afsluttede med {r.returncode}"]
        ud.append(r.stdout)
    return True, ud


def _koer_over_bro(root: str, args: list[list[str]], uid: str) -> tuple[bool, list[str]]:
    from apps.api.jarvis_api.routes.chat import _operator_exec  # sen import: kreds

    dele = [
        f"git -C {shlex.quote(root)} " + " ".join(shlex.quote(x) for x in a)
        for a in args
    ]
    kommando = f' ; echo "{_SKILLER}" ; '.join(dele)
    svar = _operator_exec("operator_bash", {"command": kommando, "_user_id": uid})
    if svar.get("status") != "ok":
        # Broens egen begrundelse SKAL med op. Uden den stod desk med «Kunne
        # ikke laese branches» uanset om broen var vaek, mappen ikke fandtes,
        # eller git ikke var installeret derovre — tre helt forskellige
        # problemer med én ubrugelig besked.
        grund = str(svar.get("error") or svar.get("status") or "broen svarede ikke")
        return False, [f"broen: {grund}"]
    stdout = str((svar.get("result") or {}).get("stdout") or "")
    return True, stdout.split(_SKILLER)


def _koer(kind: str, root: str, args: list[list[str]], uid: str) -> tuple[bool, list[str]]:
    """Koer git og faa ét output pr. argument-liste. False = kunne ikke."""
    if not root.strip():
        return False, ["ingen mappe valgt"]
    if kind == "workstation":
        return _koer_over_bro(root, args, uid)
    return _koer_lokalt(root, args)


def _rens(navne: list[str]) -> list[str]:
    """Git-linjer → rene navne. Fjerner markoerer, HEAD-pilen og dubletter."""
    ud: list[str] = []
    for linje in navne:
        n = linje.strip().lstrip("* ").strip()
        # `origin/HEAD -> origin/main` er en pegepind, ikke en branch.
        if not n or " -> " in n or n.endswith("/HEAD"):
            continue
        if n not in ud:
            ud.append(n)
    return ud


def list_branches(*, kind: str, root: str, uid: str = "") -> dict[str, Any]:
    """Alle branches plus den aktuelle. Tomt resultat = ikke et repo."""
    ok, ud = _koer(kind, root, [
        ["rev-parse", "--abbrev-ref", "HEAD"],
        ["for-each-ref", "--format=%(refname:short)", "refs/heads"],
        ["for-each-ref", "--format=%(refname:short)", "refs/remotes"],
    ], uid)
    if not ok or len(ud) < 2:
        # Grunden med op til klienten. «Kunne ikke laese branches» uden et
        # hvorfor er en blindgyde: broen vaek, mappen findes ikke og «ikke et
        # git-repo» ser ens ud, og kun den ene af dem kan brugeren selv rette.
        grund = next((x.strip() for x in reversed(ud) if x.strip()), "")
        return {"ok": False, "current": "", "local": [], "remote": [],
                "error": grund or "kunne ikke naa git i den mappe"}
    aktuel = (ud[0] or "").strip().splitlines()
    lokale = _rens((ud[1] or "").splitlines())
    fjerne = _rens((ud[2] or "").splitlines()) if len(ud) > 2 else []
    # En fjern-branch der allerede findes lokalt er ikke et selvstaendigt valg.
    kendte = {b.split("/", 1)[-1] for b in lokale}
    fjerne = [b for b in fjerne if b.split("/", 1)[-1] not in kendte]
    return {
        "ok": True,
        "current": aktuel[0].strip() if aktuel else "",
        "local": lokale,
        "remote": fjerne,
    }


def checkout_branch(
    *, kind: str, root: str, navn: str, opret: bool = False, uid: str = "",
) -> dict[str, Any]:
    """Skift til en branch, eller opret og skift til en ny.

    `opret=False` paa en fjern-branch giver git selv sporing (`checkout <navn>`
    finder `origin/<navn>`), saa der er ingen saerlig gren for det her.
    """
    rent = navn.strip()
    if not rent:
        return {"ok": False, "error": "tomt branch-navn"}
    # Git afviser selv ulovlige navne, men et navn der starter med bindestreg
    # ville blive laest som et FLAG foer git naar at se paa det.
    if rent.startswith("-"):
        return {"ok": False, "error": "branch-navn må ikke starte med bindestreg"}
    ok, ud = _koer(kind, root, [
        ["checkout", "-b", rent] if opret else ["checkout", rent],
        ["rev-parse", "--abbrev-ref", "HEAD"],
    ], uid)
    if not ok:
        return {"ok": False, "error": (ud[-1] if ud else "git svarede ikke")}
    aktuel = ""
    if len(ud) > 1 and ud[1].strip():
        aktuel = ud[1].strip().splitlines()[0].strip()
    # Sandheden er hvad HEAD siger bagefter — ikke at kommandoen returnerede 0.
    return {"ok": aktuel == rent, "current": aktuel}


def create_worktree(
    *, kind: str, root: str, navn: str, sti: str = "", uid: str = "",
) -> dict[str, Any]:
    """Opret en ny lokal worktree med sin egen branch.

    Standardplaceringen er `.worktrees/<navn>` under repoet — samme konvention
    som husets egen worktree-skill. Den mappe skal vaere ignoreret, ellers ender
    worktreens indhold i repoets status; det tjekkes, ikke antages.
    """
    rent = navn.strip()
    if not rent:
        return {"ok": False, "error": "tomt navn"}
    if rent.startswith("-"):
        return {"ok": False, "error": "navn må ikke starte med bindestreg"}
    maal = sti.strip() or f".worktrees/{rent}"
    ok, ud = _koer(kind, root, [
        ["worktree", "add", maal, "-b", rent],
        ["worktree", "list"],
    ], uid)
    if not ok:
        return {"ok": False, "error": (ud[-1] if ud else "git svarede ikke")}
    linjer = [l.strip() for l in (ud[-1] or "").splitlines() if l.strip()]
    # Bekraeft paa listen, ikke paa exit-koden: en worktree der ikke staar der
    # findes ikke, uanset hvad kommandoen sagde.
    fundet = any(rent in l for l in linjer)
    return {"ok": fundet, "path": maal, "worktrees": linjer}

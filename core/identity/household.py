"""Hvem BOR i huset — og hvem gør ikke.

Bjørn (owner): «ARKIVET ER FOR BJØRN + MICHELLE ... MIKKEL, RUNE OG LOTTE SKAL
IKKE HAVE ADGANG. De er familie og har hver deres egen samtale med Jarvis — men
arkivet er privat for dem der BOR i huset.»

Det er ikke en rangorden, og derfor er det ikke et privilegie-trin. Michelle får
IKKE mere magt end de andre medlemmer; hun får adgang til ét rum, fordi hun
deler det rum Jarvis sanser. Alt andet er uændret.

Netop dét er grunden til at `partner` er defineret som «member, plus husstand»
og ikke som «mellem member og owner». En rolle der ligger mellem to andre,
inviterer til at nogen en dag skriver `if role != "member"` og dermed uforvarende
giver — eller tager — noget. Her står det ét sted:

    ROLE_HOUSEHOLD  hvem der bor i huset
    is_member_like  hvem der har medlems-rettigheder (member OG partner)

Enhver ny kontrol skal bruge én af de to, aldrig en ny liste.
"""
from __future__ import annotations

# Roller med adgang til det der er privat for husstanden (Sansernes Arkiv).
ROLE_HOUSEHOLD = frozenset({"owner", "partner"})

# Roller der har medlems-rettigheder. `partner` ER en member — kvoter, tools og
# alt andet skal behandle de to ens. Uden dette ville Michelle stille og roligt
# MISTE ting, fordi de to eksisterende `role == "member"`-tjek pludselig ikke
# ramte hende længere.
ROLE_MEMBER_LIKE = frozenset({"member", "partner"})

# Alle gyldige roller ét sted, så et nyt trin ikke skal opdages i fem filer.
VALID_ROLES = frozenset({"owner", "partner", "member", "guest"})


def _norm(role: object) -> str:
    return str(role or "").strip().lower()


def is_household(role: object) -> bool:
    """Bor denne rolle i huset? (owner eller partner)"""
    return _norm(role) in ROLE_HOUSEHOLD


def is_member_like(role: object) -> bool:
    """Har denne rolle medlems-rettigheder? (member eller partner)"""
    return _norm(role) in ROLE_MEMBER_LIKE


def is_valid_role(role: object) -> bool:
    return _norm(role) in VALID_ROLES

#!/usr/bin/env python3
"""Admin-migration: knyt Google-email til eksisterende konti (§12).

Alle nuværende brugere har Gmail-adresser — deres login-email ER deres Gmail. Dette
script sætter google_email_hash så de kan logge ind med Google.

  python scripts/link_google_email.py --list
  python scripts/link_google_email.py --user <uid> --email bruger@gmail.com
  python scripts/link_google_email.py --all-from-login   # brug hver brugers login-email

Kør i conda ai-miljøet. GDPR: kun hash gemmes, aldrig rå email.
"""
from __future__ import annotations

import argparse

from core.identity import user_db
from core.runtime import db


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="vis alle brugere + om Google er linket")
    ap.add_argument("--user", default="", help="user_id at linke")
    ap.add_argument("--email", default="", help="Google-email til --user")
    ap.add_argument("--role", default="member", help="rolle for link (owner/member)")
    ap.add_argument("--all-from-login", action="store_true",
                    help="sæt google_email = login-email for ALLE ikke-linkede brugere")
    args = ap.parse_args()

    rows = db.list_user_rows() if hasattr(db, "list_user_rows") else []

    if args.list:
        for r in rows:
            uid = r.get("user_id")
            linked = bool(r.get("google_email_hash"))
            pub = user_db.get_user(uid) or {}
            print(f"{uid}  {pub.get('email', '?'):30}  role={pub.get('role', '?'):7}  google_linket={linked}")
        return 0

    if args.user and args.email:
        ok = user_db.set_google_email(args.user, args.email, role=args.role)
        print(f"{'OK' if ok else 'FEJL'}: {args.user} → {args.email} ({args.role})")
        return 0 if ok else 1

    if args.all_from_login:
        n = 0
        for r in rows:
            uid = r.get("user_id")
            if r.get("google_email_hash"):
                continue  # allerede linket
            pub = user_db.get_user(uid) or {}
            email = pub.get("email") or ""
            if "@" in email and user_db.set_google_email(uid, email):
                print(f"linket {uid} → {email}")
                n += 1
        print(f"Færdig — {n} konti linket fra login-email.")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

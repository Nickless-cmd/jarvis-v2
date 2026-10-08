"""JarvisX user-routing + bearer-token auth middleware.

The Electron desktop app injects identity on every request. v1 of this
middleware trusted X-JarvisX-User as plaintext identity — fine for
solo localhost use but a forge-anywhere hole the moment the API listens
on anything but 127.0.0.1.

v2 (this version) prefers a signed bearer token:

    Authorization: Bearer <jwt>      ← signed identity (trusted)
    X-JarvisX-User: <discord_id>     ← legacy plaintext (untrusted)
    X-JarvisX-User-Name: …           ← informational only
    X-JarvisX-Client:  …             ← informational only
    X-JarvisX-Project: …             ← workspace anchor (no identity claim)

Resolution order:
  1. If `Authorization: Bearer …` is present and verifies → use the
     token's claims as canonical identity. Header X-JarvisX-User is
     ignored (a forged value can't bypass a verified one).
  2. If no token AND auth_required() → reject with 401.
  3. If no token AND auth_required() is false → fall back to the legacy
     X-JarvisX-User header (dev mode / single-user localhost). Logged
     so the operator notices when their box is running unauthenticated.

Failure modes:
  • Token expired/forged AND auth required → 401, no fallback. The
    client must reissue.
  • Unknown user_id (token or header) → bind to "public" workspace.
    This avoids leaking Bjørn's workspace to anyone who happens to
    know his discord_id.
  • Lookup raises → log and proceed with default context. We never
    let a middleware error break the request — the worst case should
    be "as if no identity was supplied".
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# 401-grunde: hvornaar samme (grund, klient) sidst blev logget.
_AFVIS_SIDST: dict[tuple[str, str], float] = {}
_AFVIS_STILHED_S = 60.0


def _log_auth_afvisning(grund: str, request: "Request", raw_auth: str = "") -> None:
    """Sig HVORFOR en 401 skete — én gang i minuttet pr. klient og grund.

    Ved «token expired» siges ogsaa HVOR gammelt udloebet er, for det er det
    tal der afgoer om enheden kan forny sig selv eller skal have et nyt token
    baaret over i haanden. Uden det er svaret et gaet.
    """
    import time as _t
    try:
        klient = getattr(getattr(request, "client", None), "host", "") or "?"
        noegle = (grund[:80], klient)
        nu = _t.monotonic()
        sidst = _AFVIS_SIDST.get(noegle, 0.0)
        if nu - sidst < _AFVIS_STILHED_S:
            return
        _AFVIS_SIDST[noegle] = nu
        if len(_AFVIS_SIDST) > 256:
            _AFVIS_SIDST.clear()
        hale = ""
        if grund == "token expired" and raw_auth:
            from core.runtime.token_renewal import GRACE_DAYS, udloebs_alder_dage
            alder = udloebs_alder_dage(raw_auth)
            if alder is not None:
                kan = "kan fornys" if alder <= GRACE_DAYS else "FOR GAMMELT — kraever nyt token"
                hale = f" udloebet-for={alder}d ({kan})"
        logger.warning("auth-afvist: %s — klient=%s path=%s%s",
                       grund[:120], klient, request.url.path, hale)
    except Exception:
        pass

USER_HEADER = "x-jarvisx-user"
USER_NAME_HEADER = "x-jarvisx-user-name"
CLIENT_HEADER = "x-jarvisx-client"
PROJECT_HEADER = "x-jarvisx-project"
AUTH_HEADER = "authorization"

# Endpoints that must remain unauthenticated even when auth is required —
# otherwise the client can't bootstrap or recover from a stale token.
# Token issuance itself IS protected (owner-only), via _require_owner()
# inside the route handler.
_PUBLIC_PATHS = (
    "/health",
    "/api/auth/refresh",       # §22.6: refresh udløbet access-token (bærer egen refresh-token)
    # Fornyelse SKAL være public: hele pointen er at et udløbet token kan
    # veksles. Kræver den auth, kan netop den klient der har brug for den ikke
    # nå den. Ruten verificerer selv signaturen (core.runtime.token_renewal).
    "/api/auth/renew",
    "/api/auth/whoami-token",  # let clients self-check token validity
    "/api/auth/register",      # selvregistrering (spec 2026-06-15 §5) — public
    "/api/auth/verify-email",  # email-verifikations-link — public
    "/api/auth/login",         # login med email+password → bearer-token — public
    "/api/auth/google/start",  # Google app-login: start (ingen token endnu) — public
    "/api/auth/google/result", # Google app-login: poll token-retur (ingen token endnu) — public
    "/api/auth/pair/redeem",   # QR-pairing: mobil indløser kode → token (ingen token endnu) — public
    # BEMÆRK: /api/auth/google/link/start er IKKE public — den kræver den
    # indloggede brugers token for at vide hvilken konto Google skal knyttes til.
    "/docs",
    "/openapi.json",
    "/redoc",
    # Cross-process IPC from the runtime process (port 8011) to the
    # api process (port 80). The runtime can't realistically carry a
    # user token — it's a service, not a user. Each route under
    # /api/internal/ enforces loopback-only itself (see e.g.
    # routes/internal_discord.py), so exempting the prefix from token
    # auth doesn't open external access. We additionally tighten the
    # route-level check to reject requests with X-Forwarded-For
    # (which would mean Caddy or another proxy forwarded them).
    "/api/internal",
    # Anthropic-compat endpoint (Claude Desktop, claude-code) uses its
    # own x-api-key auth scheme via resolve_api_key() inside the route
    # handler. Bypass the Bearer-token middleware so the route can
    # apply its own auth.
    "/anthropic",
    # Blind-test UI (Phase 3) — Bjørn skal kunne tilgå det direkte i
    # browseren uden et bearer token. Ingen metadata-lækage via UI'et
    # da selve API-kaldene (/api/next etc) stadig kræver session_id,
    # ikke en bruger-identitet.
    "/interlanguage-blind",
    # ── PRIVATLIVSPOLITIK, OFFENTLIG MED VILJE (28/9-2026) ────────────────
    # Google Play kræver en URL til appens privatlivspolitik, og en
    # Play-reviewer har ikke et token til Bjørns server. En politik bag
    # login er derfor det samme som ingen politik.
    #
    # Politikken er offentlig uanset HTTP-metode. PWA-skallen nedenfor er
    # derimod kun åben for GET/HEAD fra eksterne klienter.
    #
    # Filen ligger i apps/jarvis-desk/public/privatlivspolitik.html og kopieres
    # til dist-web ved build — den serveres af samme UI-mount som `/`.
    # Indholdet er offentligt i sig selv: en beskrivelse af hvad appen
    # gør, uden brugernavne, uden nøgler, uden data.
    #
    # Bevidst en enkelt sti og ikke et præfiks — kun præcis denne fil åbnes.
    "/privatlivspolitik.html",
)


# ── UI-SKALLEN (15/9-2026; ekstern PWA 8/10-2026) ────────────────────────
# Bjoern: «jeg kan ikk åbene den i min browser». `/` svarede 401, saa den side
# der skulle logge ham ind laa selv bag login'et. Doeren var laast udefra.
#
# Den oprindelige undtagelse var kun lokal. Michelle bruger nu PWA'en over 5G,
# så login-siden og dens statiske filer skal også kunne hentes udefra.
#
# Det her aabner KUN skallen — HTML, JS, CSS. Hvert eneste /mc/* og /chat/*
# kraever stadig et token, saa login'et er ikke en formalitet: uden det viser
# siden en login-skaerm og intet andet.
_UI_SKAL = (
    "/", "/index.html", "/favicon.ico", "/favicon.svg", "/vite.svg",
    "/manifest.webmanifest", "/sw.js", "/icons/icon-192.png", "/icons/icon-512.png",
)
_UI_SKAL_PREFIX = ("/assets/",)


def _er_lokal_afsender(request: "Request") -> bool:
    """Kom kaldet fra loopback eller vores eget net?

    Hviler paa ``request.client.host``, og det er MAALT 15/9 foer det blev
    brugt: tre kald gennem Caddy til api.srvlab.dk, ét rent og to med
    forfalsket ``X-Forwarded-For`` (10.0.0.99 og 8.8.8.8). Alle tre blev
    logget som den aegte afsender 10.0.0.20 — Caddy og uvicorn tager det
    betroede hop, ikke klientens paastand.

    Fejlretning: kan adressen ikke laeses, er svaret NEJ. En doer man ikke kan
    se hvem der staar foran, skal blive lukket.
    """
    import ipaddress

    vaert = (getattr(getattr(request, "client", None), "host", "") or "").strip()
    if not vaert:
        return False
    try:
        ip = ipaddress.ip_address(vaert)
    except ValueError:
        return False
    return bool(ip.is_loopback or ip.is_private)


def _er_ui_skal(path: str) -> bool:
    return path in _UI_SKAL or any(path.startswith(p) for p in _UI_SKAL_PREFIX)


def _er_offentlig_ui_skal(request: Request) -> bool:
    """Lad en fjern PWA hente HTML, JS og CSS uden at åbne data eller maps."""
    if request.method not in ("GET", "HEAD"):
        return False
    path = request.url.path
    if path in _UI_SKAL:
        return True
    if not path.startswith("/assets/"):
        return False
    navn = path.removeprefix("/assets/")
    return bool(navn and "/" not in navn and navn.endswith((".js", ".css")))


def _is_public_path(path: str) -> bool:
    # OAuth connector-callback rammes af BROWSEREN uden bearer-token (16. jun 2026).
    # Kun /callback er public — /start kræver auth. State-parameteren er signeret +
    # binder bruger-id, så callback'en kan ikke forfalskes for en anden bruger.
    if path.startswith("/api/oauth/") and path.endswith("/callback"):
        return True
    for p in _PUBLIC_PATHS:
        if path == p or path.startswith(p + "/"):
            return True
    return False


def _er_signeret_filhentning(request: Request) -> bool:
    """Er dette en GET af én fil med en gyldig, levende signatur?

    Fritagelsen bor HER og ikke i ruten, fordi beslutningen om at slippe en
    request forbi auth skal ligge på det ene sted hvor auth afgøres. Lå den i
    ruten, ville der være to steder der kunne være uenige om hvad der er
    autentificeret — og den slags uenighed lækker altid i den forkerte
    retning (målt tre gange i indbakke-sporet samme døgn).

    Samme form som OAuth-callbacken ovenfor: beviset rejser med i adressen,
    signeret, så det ikke kan forfalskes.

    Fire led, og alle fire er nødvendige:

    * **GET.** En signatur er ret til at LÆSE én fil. Slap en POST igennem,
      var linket en skrivenøgle.
    * **Præcis én sti-del** efter `/files/`. `/files/` selv lister mappen —
      158 filer målt 4/10 — og en listning er ikke den fil der blev signeret.

      Dette led er REDUNDANT, og det står her fordi en mutation viste det:
      fjernes tjekket, bliver alle tests stadig grønne, fordi
      `file_links._rent_navn` afviser `a/b.pdf` og den tomme streng i forvejen.
      Det er altså dybde-forsvar hvor det indre lag allerede holder, ikke den
      betingelse der stopper noget. Det bliver, fordi en eksplicit afvisning
      på auth-grænsen er lettere at læse end en der følger af en anden fils
      navne-rensning — men ingen må tro at det er dét der beskytter.
    * `file_links.verificer` på **workspace** + filnavn + udløb + signatur.
      Workspacet kom til 4/10-2026 sammen med afgrænsningen: filer bor nu i
      `files/u/<workspace>/`, så `rapport.pdf` kan findes hos to brugere, og
      uden workspacet i signaturen ville den enes link passe på den andens
      fil. `ws` er derfor ikke en fri parameter — den er en del af det der
      signeres, og ruten læser den KUN når der intet token er.
    * **Fail-closed ved enhver undtagelse.** Kan vi ikke afgøre det, er det
      ikke autentificeret.
    """
    try:
        if request.method != "GET":
            return False
        sti = request.url.path
        if not sti.startswith("/files/"):
            return False
        rest = sti[len("/files/"):]
        if not rest or "/" in rest:
            return False
        from urllib.parse import unquote

        from core.services.file_links import verificer
        return verificer(unquote(rest),
                         request.query_params.get("udloeb"),
                         request.query_params.get("sig"),
                         workspace=request.query_params.get("ws") or "")
    except Exception as exc:  # noqa: BLE001
        # Fail-closed, og den SKAL ses: sker det hver gang, virker ingen
        # signerede links, og uden linjen stod det ingen steder.
        logger.warning("fil-signatur kunne ikke afgoeres — afvist: %s", exc)
        return False


async def jarvisx_user_routing_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    # CORS preflight (OPTIONS) skal aldrig kræve auth — preflight er
    # browser-til-server forhandling for at se HVILKE endpoints der er
    # tilgængelige. CORSMiddleware længere oppe i kæden svarer med
    # Access-Control-Allow-* headers. Hvis vi blokerer her med 401
    # ser browseren preflight som fejlet og afviser den faktiske request.
    if request.method == "OPTIONS":
        return await call_next(request)

    project_root = (request.headers.get(PROJECT_HEADER) or "").strip()
    raw_auth = request.headers.get(AUTH_HEADER) or ""
    legacy_user_id = (request.headers.get(USER_HEADER) or "").strip()

    # ── Step 1: try to verify a bearer token (canonical identity) ─
    token_claims: dict | None = None
    token_error: str | None = None
    if raw_auth.lower().startswith("bearer "):
        try:
            from core.runtime.jarvisx_auth import verify_token
            token_claims = verify_token(raw_auth)
        except Exception as exc:
            token_error = str(exc)
            token_claims = None

    # ── Step 2: enforce auth_required() globally ──────────────────
    # If we require auth and the request didn't bring a valid token,
    # block it before any context binding happens.
    _sti = request.url.path
    if (not token_claims and not _is_public_path(_sti)
            and not _er_signeret_filhentning(request)
            and not (_er_ui_skal(_sti) and (
                _er_lokal_afsender(request) or _er_offentlig_ui_skal(request)
            ))):
        try:
            from core.runtime.jarvisx_auth import auth_required
            require = auth_required()
        except Exception:
            require = False
        if require:
            grund = token_error or "missing or invalid bearer token"
            # Grunden stod KUN i svaret til klienten (8/9-2026). Serveren
            # loggede 401 uden at sige hvorfor, saa da Mikkels telefon gav 927
            # afvisninger paa seks timer, kunne intet i loggen skelne «udloebet»
            # fra «forkert signatur» fra «ingen token» — diagnosen krævede ti
            # maalinger i stedet for ét opslag.
            #
            # Rate-limitet pr. (grund, klient) i ét minut: en itererende klient
            # skal give ÉT signal, ikke tusind linjer. Aldrig selve token'en.
            _log_auth_afvisning(grund, request, raw_auth)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "authentication required",
                    "error": grund,
                    # Sig hvad klienten kan GØRE ved det. Et udloebet token er
                    # det eneste tilfaelde der har en vej tilbage uden ejeren:
                    # POST /api/auth/renew med det samme token. En forkert
                    # signatur har det ikke — der er intet at forny.
                    "can_renew": grund == "token expired",
                },
            )

    # ── Step 3: resolve effective identity ────────────────────────
    if token_claims:
        user_id = str(token_claims.get("sub") or "").strip()
    else:
        user_id = legacy_user_id

    # Stash resolvet identitet i scope-state så API-forbindelses-nerven (ydre middleware) kan se
    # HVEM der forbandt uden at gen-verificere tokenet. Metadata-only, self-safe. (6. jul)
    try:
        request.state.jarvis_user_id = user_id
    except Exception:
        pass

    if not user_id and not project_root:
        # No identity at all + no project anchor → default context, fast path.
        return await call_next(request)

    # Resolve the workspace. We import lazily so this module is cheap to
    # import at app boot even if identity isn't fully wired yet.
    try:
        from core.identity.users import find_user_by_discord_id
        from core.identity.workspace_context import set_context, reset_context
        from core.identity.project_context import (
            set_project_root,
            reset_project_root,
        )
    except Exception as exc:
        logger.warning("jarvisx middleware: identity import failed: %s", exc)
        return await call_next(request)

    if user_id:
        try:
            user = find_user_by_discord_id(user_id)
        except Exception as exc:
            logger.warning("jarvisx middleware: user lookup failed for %s: %s", user_id, exc)
            user = None
    else:
        # Project-only request (no user header) — keep workspace default,
        # but still bind the project anchor below.
        user = None

    if user_id and user is None:
        # Unknown discord_id — same fallback as discord_gateway / user_context.
        # We bind to "public" workspace so memory writes can't accidentally
        # land in an owner's workspace via a forged header.
        workspace_name = "public"
        display = ""
        from urllib.parse import unquote
        raw_name = request.headers.get(USER_NAME_HEADER) or ""
        if raw_name:
            try:
                display = unquote(raw_name)[:120]
            except Exception:
                display = ""
        bound_user_id = user_id
    elif user is not None:
        workspace_name = user.workspace
        display = user.name
        bound_user_id = user.discord_id
    else:
        # No user header at all (project-only request) — keep defaults.
        workspace_name = ""
        display = ""
        bound_user_id = ""

    ws_token = None
    if workspace_name:
        try:
            # Channel: derive from X-JarvisX-Client header. Webchat
            # sends nothing; jarvisx-electron sends e.g.
            # 'jarvisx-electron/0.1.5-poc'. We normalize to the package
            # name (everything before the first '/') so downstream code
            # can match on stable values.
            _xc_raw = (request.headers.get("x-jarvisx-client") or "").strip()
            _channel = _xc_raw.split("/", 1)[0].strip().lower() if _xc_raw else "webchat"
            ws_token = set_context(
                workspace_name=workspace_name,
                user_id=bound_user_id,
                user_display_name=display,
                role=str((token_claims or {}).get("role") or "").strip().lower(),
                channel=_channel,
                enhed=str((token_claims or {}).get("enhed") or ""),
                app_id=str((token_claims or {}).get("app_id") or ""),
            )
        except Exception as exc:
            logger.warning("jarvisx middleware: set_context failed: %s", exc)
            return await call_next(request)

    proj_token = None
    if project_root:
        try:
            proj_token = set_project_root(project_root)
        except Exception as exc:
            logger.warning("jarvisx middleware: set_project_root failed: %s", exc)

    try:
        return await call_next(request)
    finally:
        if ws_token is not None:
            try:
                reset_context(ws_token)
            except Exception:
                pass
        if proj_token is not None:
            try:
                reset_project_root(proj_token)
            except Exception:
                pass

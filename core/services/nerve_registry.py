"""Selv-registrerende nerve-arkitektur — Fase B + Fase C (spec 2026-07-13).

Centralen skal ikke kun *observere* sine nerver — den skal *administrere* dem: vide
præcist hvad der findes, hvordan det skal tolkes, og kunne loade nye komponenter
GOVERNED (identitets-verificeret, approval-gatet, sandboxet) uden en rød deploy-kæde.

Dette modul bærer to ting:

  * **Fase B — komponent-registry + manifest-kontrakt.** Hver nerve/gate/daemon
    *deklarerer sig selv* mod en **ubrydelig kontrakt** (``NerveManifest``). Centralen
    validerer manifestet og registrerer det DURABELT (KV via db_core.runtime_state).
    En overtrædelse af kontrakten = HELE modulet afvist med en præcis fejl-liste —
    aldrig en delvis load. Tre kontrakt-VARIANTER, én pr. komponent-slags (spec
    §"TRE kontrakt-typer"): gate-cluster · daemon-cluster · nerve. Plus rolle-baseret
    strenghed pr. identitets-tier (owner/claude løsere; jarvis strammere; ukendt afvist).

  * **Fase C — GOVERNED auto-plugin.** Den HØJEST-privilegerede dør: kode der loades ind
    i kontrol-planen. Governance ER designet, ikke et appendiks. Et plugin aktiveres
    ALDRIG uden (a) gyldig HMAC-identitets-signatur mod en hemmelighed i runtime.json
    (aldrig i git — Jarvis' repo er PUBLIC), (b) eksplicit owner-approval (alt starter
    PENDING), (c) capability-sandbox (deklareret + håndhævet). En ukendt/uverificeret
    identitet → AFVIST, aldrig loadet. Et plugin der kaster → auto-suspenderet, aldrig
    smittende.

Grund-invariant #1 (bærer alt): **Centralen har ansvaret. ALTID.** Et modul der handler
udenom ``central().decide``/``observe`` består ikke kontrakten og loades ikke.

Selv-sikker OVERALT: en registry-/manifest-/loader-fejl må ALDRIG kunne vælte heartbeat,
import eller runtime. Alle offentlige funktioner er defensive; en DB-/offline-fejl bliver
til en tom liste / afvisning, aldrig et raise der bobler op i hot-path.
"""
from __future__ import annotations

import hashlib
import hmac
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

# ── Durable KV-nøgler (byg PÅ substratet: db_core.runtime_state, ingen ny ledger) ──
_MANIFEST_KEY = "nerve_manifests"          # {name: manifest_dict}
_APPROVAL_KEY = "nerve_plugin_approvals"   # {name: approval_record_dict}

_LOCK = threading.RLock()


# ════════════════════════════════════════════════════════════════════════════
#  Kontrakt-vokabular
# ════════════════════════════════════════════════════════════════════════════
class ContractVariant(str, Enum):
    """TRE kontrakt-typer — én pr. komponent-slags (spec §"TRE kontrakt-typer").

    Kontrakten er ikke én-størrelse: gate-cluster, daemon-cluster og nerve får HVER
    sin variant, tilpasset dens natur, så hver fejl kan attribueres til sit cluster."""
    GATE_CLUSTER = "gate_cluster"      # Verdict-form (decision/reason/detected/pattern)
    DAEMON_CLUSTER = "daemon_cluster"  # tick-form, event-gate pr. familie, member-funktioner
    NERVE = "nerve"                    # observe/signal-form, tidsserie, klasse


class IdentityTier(str, Enum):
    """Rolle-baseret strenghed (spec §"Rolle-baseret strenghed" + Fase C §1)."""
    OWNER = "owner"      # Bjørn — betroet, kan aktivere hvad vi vil
    CLAUDE = "claude"    # betroet — vi ER approveren
    JARVIS = "jarvis"    # strengere: observe_only frit i shadow, ellers approval
    UNKNOWN = "unknown"  # afvist, aldrig loadet


class Capability(str, Enum):
    """HVAD et modul MÅ — håndhæves (spec invariant #6 + Fase C §3)."""
    OBSERVE_ONLY = "observe_only"
    CAN_EMIT = "can_emit"
    CAN_BLOCK = "can_block"
    CAN_MUTATE = "can_mutate"


class Mode(str, Enum):
    SHADOW = "shadow"
    ON = "on"
    OFF = "off"


class PluginStatus(str, Enum):
    """Governed plugin-livscyklus (Fase C). Default: PENDING — intet auto-on."""
    REJECTED = "rejected"    # ugyldig identitet / kontrakt-brud → aldrig loadet
    PENDING = "pending"      # afventer eksplicit owner/claude-approval
    APPROVED = "approved"    # godkendt, men ikke aktiveret endnu
    ACTIVE = "active"        # kører (kun efter approval)
    SUSPENDED = "suspended"  # kastede / kill-switch → auto-suspenderet, ikke smittende


_VALID_CAPS = {c.value for c in Capability}
_HAND_CAPS = {Capability.CAN_EMIT.value, Capability.CAN_BLOCK.value,
              Capability.CAN_MUTATE.value}  # "hænder" — ikke observe-only


# ════════════════════════════════════════════════════════════════════════════
#  NerveManifest — den ubrydelige kontrakt, i data-form
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class NerveManifest:
    """Et modul der DEKLARERER sig selv mod kontrakten.

    Obligatoriske felter (mangler ét → afvist med præcis fejl): name, cluster, kind,
    contract_variant, kill_switch_key. Plus governance-felter: klass (cognitive/security),
    identity_tier + identity_signature (Fase C), capabilities (håndhæves), mode, module_path,
    entrypoint, interface. trace/log/learning er OBLIGATORISK-TÆNDT (invarianter #3-5)."""

    # ── Kerne-identitet (task-obligatorisk) ──
    name: str
    cluster: str
    kind: str                                    # fri beskrivelse af komponent-arten
    contract_variant: str                        # ContractVariant-værdi
    kill_switch_key: str                         # OBLIGATORISK — hvert modul er flag-bart
    description: str = ""                         # owner-vendt beskrivelse

    # ── Governance / rolle ──
    klass: str = "cognitive"                     # cognitive|security → fail-open/closed
    identity_tier: str = IdentityTier.UNKNOWN.value
    identity_signature: str = ""                 # HMAC, verificeres mod runtime.json (Fase C §2)
    capabilities: list[str] = field(default_factory=lambda: [Capability.OBSERVE_ONLY.value])
    mode: str = Mode.SHADOW.value                # start-tilstand

    # ── Hvor koden bor + interface ──
    module_path: str = ""
    entrypoint: str = ""
    interface: dict[str, Any] = field(default_factory=dict)  # {input_ctx: [...], output: ...}

    # ── Ubrydelige invarianter (TÆNDT fra start) ──
    trace: bool = True                           # invariant #3 — trace pr. fyring
    log: bool = True                             # invariant #4 — struktureret logger
    learning: bool = True                        # invariant #5 — Centralen aggregerer straks
    central_authority: bool = True               # invariant #1 — flyder gennem Centralen

    # ── Bogføring ──
    registered_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "NerveManifest":
        """Rekonstruér fra durabel form. Self-safe — ukendte felter ignoreres."""
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


# ── Variant-specifikke krav: interface-felter der SKAL være til stede pr. variant ──
# (spec §"TRE kontrakt-typer": hver variant bærer sin natur, så fejl kan attribueres)
_VARIANT_INTERFACE_REQUIRED: dict[str, tuple[str, ...]] = {
    ContractVariant.GATE_CLUSTER.value: ("output",),   # skal producere en Verdict
    ContractVariant.DAEMON_CLUSTER.value: ("tick",),    # tick-form
    ContractVariant.NERVE.value: ("output",),           # observe/signal-form
}


# ════════════════════════════════════════════════════════════════════════════
#  Kontrakt-validering — alt-eller-intet, præcise fejl
# ════════════════════════════════════════════════════════════════════════════
def validate_manifest(manifest: NerveManifest) -> list[str]:
    """Validér et manifest mod den ubrydelige kontrakt. Returnerer en LISTE af præcise
    fejl-strenge (tom liste = kontrakt-compliant). Kaster ALDRIG — en validerings-fejl
    må ikke kunne vælte load-stien; en intern fejl bliver selv en afvisnings-grund.

    Alt-eller-intet: kaldere loader kun hvis listen er tom (ingen delvis load)."""
    errors: list[str] = []
    try:
        m = manifest
        # 1) Obligatoriske kerne-felter
        for fname in ("name", "cluster", "kind", "contract_variant", "kill_switch_key"):
            if not str(getattr(m, fname, "") or "").strip():
                errors.append(f"mangler {fname}")

        # 2) Kontrakt-variant gyldig
        variant = str(m.contract_variant or "").strip()
        if variant and variant not in {v.value for v in ContractVariant}:
            errors.append(f"ukendt contract_variant '{variant}'")

        # 3) Klasse gyldig (styrer fail-open/closed)
        if str(m.klass or "").strip() not in ("cognitive", "security"):
            errors.append(f"ugyldig klass '{m.klass}' (skal være cognitive|security)")

        # 4) Mode gyldig
        if str(m.mode or "").strip() not in {mm.value for mm in Mode}:
            errors.append(f"ugyldig mode '{m.mode}'")

        # 5) Capabilities gyldige + ikke-tomme
        caps = list(m.capabilities or [])
        if not caps:
            errors.append("mangler capabilities (mindst én kræves)")
        bad = [c for c in caps if c not in _VALID_CAPS]
        if bad:
            errors.append(f"ukendte capabilities {bad} (gyldige: {sorted(_VALID_CAPS)})")

        # 6) Capability-KOHÆRENS (invariant #6): observe_only kan ikke sameksistere med hænder
        if Capability.OBSERVE_ONLY.value in caps and (set(caps) & _HAND_CAPS):
            errors.append("observe_only kan ikke kombineres med can_emit/can_block/can_mutate")

        # 7) Ubrydelige invarianter TÆNDT (spec #3-5 + #1)
        if not m.trace:
            errors.append("trace er obligatorisk (invariant #3)")
        if not m.log:
            errors.append("log er obligatorisk (invariant #4)")
        if not m.learning:
            errors.append("learning skal være TÆNDT fra start (invariant #5)")
        if not m.central_authority:
            errors.append("handler udenom central().decide/observe (invariant #1)")

        # 8) Variant-specifikt interface
        req = _VARIANT_INTERFACE_REQUIRED.get(variant, ())
        iface = m.interface or {}
        for k in req:
            if k not in iface:
                errors.append(f"variant '{variant}' kræver interface.{k}")

        # 9) Identitets-tier gyldig; ukendt = afvist (Fase C §1)
        tier = str(m.identity_tier or "").strip()
        if tier not in {t.value for t in IdentityTier} or tier == IdentityTier.UNKNOWN.value:
            errors.append(f"ukendt/uverificeret identitets-tier '{tier}' → afvist")

        # 10) ROLLE-BASERET STRENGHED (spec §"Rolle-baseret strenghed"):
        #     Jarvis-moduler med en HÅND (can_emit/block/mutate) må ikke starte 'on' direkte —
        #     de kræver shadow-først + eksplicit approval (håndhæves i loaderen). Her fanger vi
        #     den forbudte kombination ved døren: jarvis + hånd + mode==on = kontrakt-brud.
        if tier == IdentityTier.JARVIS.value:
            has_hand = bool(set(caps) & _HAND_CAPS)
            if has_hand and str(m.mode) == Mode.ON.value:
                errors.append(
                    "jarvis-identitet med can_emit/can_block/can_mutate kræver approval "
                    "(må ikke starte mode 'on' — shadow-først + owner/claude-godkendelse)"
                )
    except Exception as exc:  # noqa: BLE001 — validering må aldrig kaste videre
        errors.append(f"intern validerings-fejl: {exc!r}")
    return errors


def is_compliant(manifest: NerveManifest) -> bool:
    """True hvis manifestet består HELE kontrakten (ingen fejl)."""
    return not validate_manifest(manifest)


# ════════════════════════════════════════════════════════════════════════════
#  Durable komponent-registry (Fase B)
# ════════════════════════════════════════════════════════════════════════════
def _load_kv(key: str) -> dict[str, Any]:
    """Læs en durabel KV-dict. Self-safe → {} ved enhver fejl/offline."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        val = get_runtime_state_value(key, {}) or {}
        return dict(val) if isinstance(val, dict) else {}
    except Exception:
        return {}


def _save_kv(key: str, value: dict[str, Any]) -> bool:
    """Skriv en durabel KV-dict. Self-safe → False ved fejl (aldrig raise)."""
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
        return True
    except Exception:
        return False


def register(manifest: NerveManifest, *, now: float | None = None) -> dict[str, Any]:
    """Registrér en komponent i det durable registry — men KUN hvis den består HELE
    kontrakten. Returnerer {ok, name, errors}. Self-safe: kaster aldrig.

    Bemærk: registrering ≠ aktivering. Et registreret modul administreres af Centralen
    (kill-switch, mønster-læring, selv-audit). Governed AKTIVERING af et plugin går
    gennem ``GovernedPluginLoader`` (Fase C) — registrering alene tænder intet."""
    try:
        errors = validate_manifest(manifest)
        if errors:
            return {"ok": False, "name": manifest.name, "errors": errors}
        manifest.registered_at = float(now if now is not None else time.time())
        with _LOCK:
            store = _load_kv(_MANIFEST_KEY)
            store[str(manifest.name)] = manifest.to_dict()
            saved = _save_kv(_MANIFEST_KEY, store)
        if not saved:
            return {"ok": False, "name": manifest.name,
                    "errors": ["durabel skrivning fejlede (self-safe)"]}
        return {"ok": True, "name": manifest.name, "errors": []}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "name": getattr(manifest, "name", "?"),
                "errors": [f"intern registrerings-fejl: {exc!r}"]}


def unregister(name: str) -> bool:
    """Fjern en komponent fra registry. Self-safe."""
    try:
        with _LOCK:
            store = _load_kv(_MANIFEST_KEY)
            if str(name) in store:
                store.pop(str(name), None)
                return _save_kv(_MANIFEST_KEY, store)
        return False
    except Exception:
        return False


def get_manifest(name: str) -> NerveManifest | None:
    """Hent ét registreret manifest. Self-safe → None."""
    try:
        raw = _load_kv(_MANIFEST_KEY).get(str(name))
        return NerveManifest.from_dict(raw) if isinstance(raw, dict) else None
    except Exception:
        return None


def is_registered(name: str) -> bool:
    try:
        return str(name) in _load_kv(_MANIFEST_KEY)
    except Exception:
        return False


def all_manifests() -> list[NerveManifest]:
    """Alle registrerede manifester. Self-safe → []."""
    try:
        out: list[NerveManifest] = []
        for raw in _load_kv(_MANIFEST_KEY).values():
            if isinstance(raw, dict):
                out.append(NerveManifest.from_dict(raw))
        return out
    except Exception:
        return []


def registered_names() -> set[str]:
    """Navne på alt der er registreret (til connectivity-audittens compliant-markering)."""
    try:
        return set(_load_kv(_MANIFEST_KEY).keys())
    except Exception:
        return set()


def compliant_names() -> set[str]:
    """Navne på registrerede komponenter der STADIG består kontrakten (selv-audit-basis)."""
    try:
        out: set[str] = set()
        for raw in _load_kv(_MANIFEST_KEY).values():
            if isinstance(raw, dict):
                m = NerveManifest.from_dict(raw)
                if is_compliant(m):
                    out.add(str(m.name))
        return out
    except Exception:
        return set()


# ════════════════════════════════════════════════════════════════════════════
#  to_manifest() adapter (Boy-Scout: wrap eksisterende nerver uden rewrite)
# ════════════════════════════════════════════════════════════════════════════
def to_manifest(
    descriptor: Any,
    *,
    name: str = "",
    cluster: str = "",
    kind: str = "",
    contract_variant: str = ContractVariant.NERVE.value,
    klass: str = "cognitive",
    identity_tier: str = IdentityTier.OWNER.value,
    capabilities: list[str] | None = None,
    mode: str = Mode.SHADOW.value,
    description: str = "",
    module_path: str = "",
    entrypoint: str = "",
    interface: dict[str, Any] | None = None,
    kill_switch_key: str = "",
    identity_signature: str = "",
) -> NerveManifest:
    """Adapter: bring en EKSISTERENDE nerve/gate/daemon under kontrakten uden at rewrite
    den (bagud-kompatibel bro — samme Boy-Scout-mønster som store-fil-splittet).

    ``descriptor`` kan være en dict, et objekt med attributter, eller None. Felter der ikke
    fremgår af descriptoren udfyldes fra kwargs/defaults. Self-safe: ukendte former giver et
    manifest med tomme felter (som så fejler valideringen med præcise fejl — aldrig et crash).

    Migration (spec §MIGRATION): man omskriver ikke 122 nerver på én gang — man giver en
    nerve dette manifest når den alligevel røres (Boy-Scout), og den er derefter under
    samme kontrakt som alt nyt."""
    def _pick(key: str, fallback: str) -> str:
        try:
            if isinstance(descriptor, dict):
                v = descriptor.get(key)
            else:
                v = getattr(descriptor, key, None)
            return str(v) if v not in (None, "") else fallback
        except Exception:
            return fallback

    resolved_name = name or _pick("name", "") or _pick("nerve", "")
    resolved_cluster = cluster or _pick("cluster", "")
    resolved_kind = kind or _pick("kind", "") or contract_variant
    # kill_switch_key: brug den eksplicitte, ellers udled en standard fra cluster/name
    ks = kill_switch_key or _pick("kill_switch_key", "")
    if not ks and resolved_cluster and resolved_name:
        ks = f"flag:central.switch.{resolved_cluster}.{resolved_name}"

    caps = capabilities if capabilities is not None else [Capability.OBSERVE_ONLY.value]
    iface = interface if interface is not None else {"input_ctx": [], "output": "Signal"}

    return NerveManifest(
        name=resolved_name,
        cluster=resolved_cluster,
        kind=resolved_kind,
        contract_variant=contract_variant,
        kill_switch_key=ks,
        description=description or _pick("description", ""),
        klass=klass,
        identity_tier=identity_tier,
        identity_signature=identity_signature,
        capabilities=list(caps),
        mode=mode,
        module_path=module_path or _pick("module_path", ""),
        entrypoint=entrypoint or _pick("entrypoint", ""),
        interface=dict(iface),
    )


# ════════════════════════════════════════════════════════════════════════════
#  Fase C — identitets-signatur (HMAC mod runtime.json-hemmelighed, aldrig i git)
# ════════════════════════════════════════════════════════════════════════════
def _identity_secret(tier: str) -> bytes | None:
    """Læs den per-identitet signing-hemmelighed fra runtime.json (aldrig committet).

    Nøgle-navn: ``nerve_identity_secret_<tier>`` (fx nerve_identity_secret_owner). Hemmeligheden
    bor KUN på maskinen (spec Fase C §2: repoet kan være fuldt public uden forfalsknings-risiko).
    Self-safe: mangler nøglen / fejler læsning → None (→ verifikation fejler-lukket → afvist)."""
    try:
        from core.runtime.secrets import read_runtime_key
        raw = read_runtime_key(f"nerve_identity_secret_{str(tier).strip().lower()}")
        s = str(raw or "").strip()
        return s.encode("utf-8") if s else None
    except Exception:
        return None


def _canonical_identity_payload(manifest: NerveManifest) -> bytes:
    """Kanonisk, stabil streng der SIGNERES — binder identiteten til modulets kerne-form.
    Ændrer man name/cluster/module_path/entrypoint/tier, invalideres signaturen."""
    parts = [
        str(manifest.name), str(manifest.cluster), str(manifest.kind),
        str(manifest.contract_variant), str(manifest.module_path),
        str(manifest.entrypoint), str(manifest.identity_tier),
    ]
    return "\x1f".join(parts).encode("utf-8")


def sign_manifest(manifest: NerveManifest, *, tier: str | None = None) -> str:
    """Producér en identitets-signatur for et manifest (lokal tooling — kræver hemmeligheden
    på maskinen). Returnerer "" hvis hemmeligheden mangler (kan ikke signere uden nøgle)."""
    t = str(tier or manifest.identity_tier or "").strip().lower()
    secret = _identity_secret(t)
    if not secret:
        return ""
    try:
        return hmac.new(secret, _canonical_identity_payload(manifest),
                        hashlib.sha256).hexdigest()
    except Exception:
        return ""


def verify_identity(manifest: NerveManifest) -> bool:
    """Verificér manifestets identitets-signatur mod den lokale runtime.json-hemmelighed.

    FAIL-LUKKET (SECURITY-klasse): mangler hemmelighed, mangler signatur, ukendt tier, eller
    et mismatch → False. En fremmed der læser det public repo har IKKE hemmeligheden og kan
    derfor ikke forfalske en gyldig signatur. Bruger ``hmac.compare_digest`` (konstant-tid)."""
    try:
        tier = str(manifest.identity_tier or "").strip().lower()
        if tier not in {t.value for t in IdentityTier} or tier == IdentityTier.UNKNOWN.value:
            return False
        sig = str(manifest.identity_signature or "").strip()
        if not sig:
            return False
        secret = _identity_secret(tier)
        if not secret:
            return False
        expected = hmac.new(secret, _canonical_identity_payload(manifest),
                            hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════════════════
#  Fase C — GOVERNED plugin-loader (approval-gatet, sandboxet, aldrig auto-on)
# ════════════════════════════════════════════════════════════════════════════
_TRUSTED_TIERS = {IdentityTier.OWNER.value, IdentityTier.CLAUDE.value}


class GovernedPluginLoader:
    """Den HØJEST-privilegerede dør. Et plugin aktiveres ALDRIG uden:
      (a) gyldig HMAC-identitets-signatur (``verify_identity``),
      (b) kontrakt-compliant manifest (``validate_manifest``),
      (c) eksplicit approval (``approve``) — INTET starter aktivt,
      (d) capability-sandbox (deklareret + håndhævet ved aktivering),
      (e) isolation: en kastende aktivering → SUSPENDED, aldrig smittende.

    Approval-køen er durabel (KV). Default for ALT: PENDING (jarvis) eller REJECTED
    (ugyldig identitet). Ingen sti aktiverer uden et eksplicit ``approve``-kald."""

    def __init__(self, *, approval_key: str = _APPROVAL_KEY) -> None:
        self._key = approval_key

    # ── kø-persistens ──
    def _load(self) -> dict[str, Any]:
        return _load_kv(self._key)

    def _save(self, data: dict[str, Any]) -> bool:
        return _save_kv(self._key, data)

    def _record(self, name: str) -> dict[str, Any] | None:
        rec = self._load().get(str(name))
        return dict(rec) if isinstance(rec, dict) else None

    def _write_record(self, name: str, rec: dict[str, Any]) -> bool:
        with _LOCK:
            data = self._load()
            data[str(name)] = rec
            return self._save(data)

    # ── submit: identitets-verifikation + kontrakt → PENDING/REJECTED (aldrig ACTIVE) ──
    def submit(self, manifest: NerveManifest, *, now: float | None = None) -> dict[str, Any]:
        """Indlever et plugin til governed load. Verificerer identitet + kontrakt og lander
        det i køen som PENDING (gyldigt) eller REJECTED (ugyldigt). Aktiverer ALDRIG her.

        Returnerer {name, status, errors}. Self-safe."""
        try:
            ts = float(now if now is not None else time.time())
            name = str(manifest.name or "").strip()
            errors = validate_manifest(manifest)
            identity_ok = verify_identity(manifest)
            if not identity_ok:
                errors = errors + ["identitets-signatur ugyldig eller uverificerbar → afvist"]

            if errors:
                rec = {
                    "name": name, "status": PluginStatus.REJECTED.value,
                    "identity_tier": manifest.identity_tier, "errors": errors,
                    "manifest": manifest.to_dict(), "submitted_at": ts,
                    "approver": "", "approved_at": 0.0,
                }
                self._write_record(name, rec)
                self._audit("plugin_rejected", name, manifest.identity_tier, errors=errors)
                return {"name": name, "status": PluginStatus.REJECTED.value, "errors": errors}

            # Gyldig identitet + kontrakt → PENDING. INTET auto-on, heller ikke for owner/claude:
            # aktivering kræver ALTID et eksplicit approve-kald (owner sign-off). For owner/claude
            # er den godkendelse friktionsfri (de ER approveren); for jarvis kræver den owner/claude.
            rec = {
                "name": name, "status": PluginStatus.PENDING.value,
                "identity_tier": manifest.identity_tier, "errors": [],
                "manifest": manifest.to_dict(), "submitted_at": ts,
                "approver": "", "approved_at": 0.0,
            }
            self._write_record(name, rec)
            self._audit("plugin_pending", name, manifest.identity_tier)
            return {"name": name, "status": PluginStatus.PENDING.value, "errors": []}
        except Exception as exc:  # noqa: BLE001
            return {"name": getattr(manifest, "name", "?"),
                    "status": PluginStatus.REJECTED.value,
                    "errors": [f"intern submit-fejl: {exc!r}"]}

    # ── approve: den eneste vej til aktiverbar tilstand ──
    def approve(self, name: str, *, approver_tier: str, now: float | None = None) -> dict[str, Any]:
        """Eksplicit owner/claude sign-off. KUN owner/claude kan godkende (approver_tier).

        Håndhæver rolle-strenghed: en jarvis-plugin med en HÅND kræver en betroet approver —
        og selv en owner/claude-plugin kan ikke aktiveres uden dette kald (spec: intet auto-on).
        Returnerer {name, status, errors}. Self-safe."""
        try:
            approver = str(approver_tier or "").strip().lower()
            if approver not in _TRUSTED_TIERS:
                return {"name": name, "status": None,
                        "errors": [f"approver '{approver}' er ikke owner/claude — kan ikke godkende"]}
            rec = self._record(name)
            if rec is None:
                return {"name": name, "status": None, "errors": ["ukendt plugin (ikke indleveret)"]}
            if rec.get("status") == PluginStatus.REJECTED.value:
                return {"name": name, "status": PluginStatus.REJECTED.value,
                        "errors": ["afvist plugin kan ikke godkendes (genindlever et rettet manifest)"]}
            rec["status"] = PluginStatus.APPROVED.value
            rec["approver"] = approver
            rec["approved_at"] = float(now if now is not None else time.time())
            self._write_record(name, rec)
            self._audit("plugin_approved", name, rec.get("identity_tier"), approver=approver)
            return {"name": name, "status": PluginStatus.APPROVED.value, "errors": []}
        except Exception as exc:  # noqa: BLE001
            return {"name": name, "status": None, "errors": [f"intern approve-fejl: {exc!r}"]}

    def reject(self, name: str, *, reason: str = "") -> dict[str, Any]:
        """Eksplicit afvisning (owner-veto). Self-safe."""
        try:
            rec = self._record(name)
            if rec is None:
                return {"name": name, "status": None, "errors": ["ukendt plugin"]}
            rec["status"] = PluginStatus.REJECTED.value
            rec["errors"] = list(rec.get("errors") or []) + ([reason] if reason else [])
            self._write_record(name, rec)
            self._audit("plugin_rejected", name, rec.get("identity_tier"), errors=[reason])
            return {"name": name, "status": PluginStatus.REJECTED.value, "errors": []}
        except Exception as exc:  # noqa: BLE001
            return {"name": name, "status": None, "errors": [f"intern reject-fejl: {exc!r}"]}

    # ── activate: kun efter APPROVED; sandbox + isolation ──
    def activate(
        self, name: str, *, loader_fn: Callable[[NerveManifest], Any] | None = None,
        now: float | None = None,
    ) -> dict[str, Any]:
        """Aktivér et GODKENDT plugin. Umuligt uden forudgående ``approve`` (spec-invariant:
        intet auto-on uden owner sign-off). Ved aktivering:
          * re-verificeres identitet + kontrakt (forsvar mod en manipuleret kø-post),
          * registreres manifestet i komponent-registry (Fase B),
          * køres et valgfrit ``loader_fn(manifest)`` ISOLERET (try/except) — kaster det,
            auto-suspenderes plugin'et (SUSPENDED), aldrig smittende (spec Fase C §4).

        Returnerer {name, status, errors}. Self-safe."""
        try:
            rec = self._record(name)
            if rec is None:
                return {"name": name, "status": None, "errors": ["ukendt plugin"]}
            if rec.get("status") != PluginStatus.APPROVED.value:
                return {"name": name, "status": rec.get("status"),
                        "errors": [f"kan ikke aktivere: status er '{rec.get('status')}', "
                                   f"ikke '{PluginStatus.APPROVED.value}' (kræver approval)"]}
            manifest = NerveManifest.from_dict(rec.get("manifest") or {})

            # Re-verificér ved døren (forsvar-i-dybden mod en pillet kø-post)
            reverify = validate_manifest(manifest)
            if not verify_identity(manifest):
                reverify = reverify + ["identitets-signatur ugyldig ved aktivering → afvist"]
            if reverify:
                rec["status"] = PluginStatus.REJECTED.value
                rec["errors"] = reverify
                self._write_record(name, rec)
                self._audit("plugin_rejected", name, manifest.identity_tier, errors=reverify)
                return {"name": name, "status": PluginStatus.REJECTED.value, "errors": reverify}

            # Registrér i Fase-B-registry (Centralen administrerer det herfra)
            register(manifest, now=now)

            # Isoleret load (dead-man): en kastende loader smitter ikke Centralen
            if loader_fn is not None:
                try:
                    loader_fn(manifest)
                except Exception as exc:  # noqa: BLE001
                    rec["status"] = PluginStatus.SUSPENDED.value
                    rec["errors"] = [f"loader kastede → auto-suspenderet: {exc!r}"]
                    self._write_record(name, rec)
                    self._audit("plugin_suspended", name, manifest.identity_tier,
                                errors=rec["errors"])
                    return {"name": name, "status": PluginStatus.SUSPENDED.value,
                            "errors": rec["errors"]}

            rec["status"] = PluginStatus.ACTIVE.value
            rec["activated_at"] = float(now if now is not None else time.time())
            self._write_record(name, rec)
            self._audit("plugin_activated", name, manifest.identity_tier)
            return {"name": name, "status": PluginStatus.ACTIVE.value, "errors": []}
        except Exception as exc:  # noqa: BLE001
            return {"name": name, "status": None, "errors": [f"intern activate-fejl: {exc!r}"]}

    # ── introspection ──
    def status(self, name: str) -> str | None:
        rec = self._record(name)
        return None if rec is None else str(rec.get("status") or "")

    def pending(self) -> list[dict[str, Any]]:
        try:
            return [r for r in self._load().values()
                    if isinstance(r, dict) and r.get("status") == PluginStatus.PENDING.value]
        except Exception:
            return []

    def is_active(self, name: str) -> bool:
        return self.status(name) == PluginStatus.ACTIVE.value

    # ── audit (spec Fase C §6): hver load/approval logges til Centralen ──
    def _audit(self, event: str, name: str, tier: Any, *, approver: str = "",
               errors: list[str] | None = None) -> None:
        """Bedste-indsats audit til Centralen. Self-safe — audit må aldrig vælte loaderen."""
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": "central_meta", "nerve": "governed_plugin",
                "kind": event, "plugin": str(name),
                "identity_tier": str(tier or ""), "approver": approver,
                "errors": list(errors or []), "flagged": event in (
                    "plugin_rejected", "plugin_suspended"),
            })
        except Exception:
            pass


# Modul-singleton (bekvem default; tests kan instantiere deres egen mod en isoleret KV-nøgle)
_LOADER = GovernedPluginLoader()


def loader() -> GovernedPluginLoader:
    return _LOADER


# ════════════════════════════════════════════════════════════════════════════
#  Migration-proof (Boy-Scout): et par EKSISTERENDE nerver bragt under kontrakten
# ════════════════════════════════════════════════════════════════════════════
#  Vi migrerer ikke 122 nerver på én gang (spec §MIGRATION). Vi beviser at adapteren
#  bærer de tre komponent-slags ved at beskrive nogle nerver der ALLEREDE fyrer live —
#  én pr. kontrakt-variant — via to_manifest(). Owner-tier (vi er forfatteren).
_SEED_DESCRIPTORS: tuple[dict[str, Any], ...] = (
    # NERVE-variant: gate_pattern_repeat (central_meta) — Fase-A vane-nudge, observe-only.
    {
        "descriptor": {"cluster": "central_meta", "nerve": "gate_pattern_repeat"},
        "contract_variant": ContractVariant.NERVE.value,
        "kind": "pattern_habit_nudge",
        "klass": "cognitive",
        "capabilities": [Capability.OBSERVE_ONLY.value],
        "module_path": "core.services.gate_pattern_learning",
        "entrypoint": "record_gate_pattern",
        "description": "Nudger Centralen når et gate-mønster bliver en vane (Fase A).",
        "interface": {"input_ctx": ["pattern", "detected_text"], "output": "Signal"},
    },
    # NERVE-variant: oauth_state (auth) — anti-CSRF observe-only.
    {
        "descriptor": {"cluster": "auth", "nerve": "oauth_state"},
        "contract_variant": ContractVariant.NERVE.value,
        "kind": "auth_state_validation",
        "klass": "security",
        "capabilities": [Capability.OBSERVE_ONLY.value],
        "module_path": "core.services.oauth_flow",
        "entrypoint": "verify_state",
        "description": "Observerer anti-CSRF OAuth-state-validering (valid/invalid).",
        "interface": {"input_ctx": ["state"], "output": "Signal"},
    },
    # GATE_CLUSTER-variant: fact_gate — Verdict-producerende gate der KAN blokere/warn.
    {
        "descriptor": {"cluster": "gate", "nerve": "fact_gate"},
        "contract_variant": ContractVariant.GATE_CLUSTER.value,
        "kind": "self_stats_fact_gate",
        "klass": "cognitive",
        "capabilities": [Capability.CAN_EMIT.value, Capability.CAN_BLOCK.value],
        "mode": Mode.ON.value,
        "module_path": "core.services.gate_kernel",
        "entrypoint": "evaluate",
        "description": "Fanger tal-claims uden tool-verifikation (TruthGate 2978).",
        "interface": {"input_ctx": ["text"], "output": "Verdict"},
    },
)


def seed_known_nerves(*, now: float | None = None) -> list[dict[str, Any]]:
    """Registrér de par EKSISTERENDE nerver ovenfor mod kontrakten — proof-of-adapter.

    Idempotent (register overskriver samme navn). Self-safe → returnerer resultat-liste,
    kaster aldrig. Kaldes ikke ved import (holder tests/opstart rene) — kaldes eksplicit
    fra migrations-tooling eller tests."""
    results: list[dict[str, Any]] = []
    for spec in _SEED_DESCRIPTORS:
        try:
            kwargs = {k: v for k, v in spec.items() if k != "descriptor"}
            m = to_manifest(spec["descriptor"], identity_tier=IdentityTier.OWNER.value, **kwargs)
            results.append(register(m, now=now))
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "errors": [f"seed-fejl: {exc!r}"]})
    return results

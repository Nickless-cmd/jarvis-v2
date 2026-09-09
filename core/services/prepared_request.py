"""`PreparedRequest` — det der skal til for at bygge NØJAGTIG samme anmodning igen.

Spec: Fase 2 — «prepared requests can be reconstructed with route, prompt,
ordered tool schemas, derived-history watermark, profile hash, and compaction
generation», og §514's krav om at hver komponent gemmes «inline or by immutable
reference».

## Hvorfor et genforsøg skal være byte-identisk

Et genforsøg der sender noget ANDET end det der fejlede, prøver ikke det samme
igen — det prøver noget nyt og kalder det et genforsøg. Så kan man ikke vide om
fejlen gik væk, eller om man bare stillede et andet spørgsmål.

Værre: ændrede prompten sig stille mellem forsøg 1 og 2, ville modellen se to
forskellige samtaler, og den historik der til sidst gemmes, ville høre til en
anmodning der aldrig blev sendt.

## Kravet der ikke kan snydes: et hash uden indhold er ikke nok

Spec'en er utvetydig: «a hash without retrievable content is insufficient.»

Et hash beviser at to ting ER ens. Det kan ikke bygge nogen af dem. Gemmer man
kun `sha256(prompt)`, kan man bagefter afgøre om en prompt man STADIG har, er
den rigtige — men man kan ikke genskabe den hvis den er væk. Og det er netop
når den er væk, man har brug for den.

Derfor: `reconstruct()` afviser at bygge en anmodning hvor en komponent kun
findes som hash. Ikke som en advarsel — som en fejl, fordi alternativet er en
anmodning der ser komplet ud og mangler noget.

## Rækkefølgen af værktøjsskemaer er en del af anmodningen

Værktøjer i en anden rækkefølge er en anden anmodning: modellerne er følsomme
over for det, og cachen brydes. Derfor gemmes de som en LISTE, ikke et sæt, og
digesten dækker rækkefølgen.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


class IncompleteRequest(RuntimeError):
    """En komponent findes kun som hash. Anmodningen kan ikke genskabes."""


def digest(v: Any) -> str:
    """Stabil digest. Nøgler sorteres, så to ens objekter altid giver samme svar."""
    s = json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()


@dataclass(frozen=True)
class Component:
    """En del af anmodningen: enten indholdet, eller en hentbar reference.

    `ref` er ikke et hash — det er en NØGLE man kan slå op. Forskellen er hele
    pointen: et hash beviser identitet, en reference giver indholdet tilbage.
    """

    value: Any = None
    ref: str = ""
    #: Sat når indholdet er væk og KUN digesten er tilbage. Så kan
    #: `reconstruct()` sige præcis hvad der mangler, i stedet for at bygge
    #: noget ufuldstændigt.
    only_digest: str = ""

    def resolve(self, hent=None) -> Any:
        if self.only_digest:
            raise IncompleteRequest(
                f"komponenten findes kun som digest ({self.only_digest}) — "
                "et hash beviser identitet, men kan ikke bygge indholdet"
            )
        if self.ref:
            if hent is None:
                raise IncompleteRequest(
                    f"komponenten ligger bag referencen {self.ref!r}, og der er "
                    "ingen opslagsfunktion til at hente den"
                )
            v = hent(self.ref)
            if v is None:
                raise IncompleteRequest(f"referencen {self.ref!r} kunne ikke hentes")
            return v
        return self.value


@dataclass(frozen=True)
class PreparedRequest:
    """Alt der skal til for at bygge anmodningen igen — ikke for at genkende den."""

    request_series_id: str
    provider_id: str
    model: str
    params: dict[str, Any] = field(default_factory=dict)

    #: Den EFFEKTIVE prompt. Inline eller bag en hentbar reference.
    prompt: Component = field(default_factory=Component)
    #: Værktøjsskemaerne i RÆKKEFØLGE. En anden rækkefølge er en anden anmodning.
    tool_schemas: Component = field(default_factory=Component)

    #: Hvor langt i den udledte historik anmodningen så. Uden den kan man ikke
    #: vide om et genforsøg ser mere end originalen gjorde.
    derived_history_watermark: int = 0
    #: Hvilken kompakterings-generation prompten stammer fra. Skifter den, er
    #: det ikke længere samme anmodningsserie.
    compaction_generation: int = 0
    profile_hash: str = ""

    def body_digest(self, hent=None) -> str:
        """Digest over det der faktisk sendes — rækkefølge inkluderet."""
        return digest({
            "provider_id": self.provider_id, "model": self.model,
            "params": self.params,
            "prompt": self.prompt.resolve(hent),
            "tool_schemas": self.tool_schemas.resolve(hent),
            "derived_history_watermark": self.derived_history_watermark,
            "compaction_generation": self.compaction_generation,
            "profile_hash": self.profile_hash,
        })

    def reconstruct(self, hent=None) -> dict[str, Any]:
        """Byg anmodningen igen. Kaster hvis en komponent kun findes som hash.

        Det er en FEJL og ikke en advarsel, fordi alternativet er en anmodning
        der ser komplet ud og mangler noget.
        """
        krop = {
            "provider_id": self.provider_id,
            "model": self.model,
            "params": dict(self.params),
            "prompt": self.prompt.resolve(hent),
            "tools": list(self.tool_schemas.resolve(hent) or []),
        }
        krop["body_digest"] = self.body_digest(hent)
        return krop

    def same_series_as(self, other: "PreparedRequest") -> bool:
        """Er det stadig SAMME anmodningsserie?

        En rute-ændring bryder den ikke — spec'en tillader `route_override` og
        kræver kun at skiftet er logget. En kompaktering eller et flyttet
        historik-vandmærke gør: dér ser modellen noget andet, og så er det ikke
        et genforsøg længere.
        """
        return (self.request_series_id == other.request_series_id
                and self.compaction_generation == other.compaction_generation
                and self.derived_history_watermark == other.derived_history_watermark
                and self.profile_hash == other.profile_hash)


def forget_content(p: PreparedRequest) -> PreparedRequest:
    """Efterlign at indholdet er væk og kun digesten er tilbage.

    Findes for at kunne PRØVE at genskabelsen fejler højt. Det er den eneste
    måde at vide at kravet «et hash uden indhold er ikke nok» faktisk holder,
    frem for at være en sætning i en kommentar.
    """
    from dataclasses import replace
    return replace(
        p,
        prompt=Component(only_digest=digest(p.prompt.value)),
        tool_schemas=Component(only_digest=digest(p.tool_schemas.value)),
    )

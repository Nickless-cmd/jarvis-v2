"""Registret over udbydere og modeller — laesning OG skrivning. Owner-only.

Indtil 16/9-2026 kunne registret kun laeses (og kun de foerste 8 udbydere og 12
modeller, `provider_router_summary()` klipper). Der fandtes ingen vej til at
slaa en udbyder eller model FRA uden at redigere filen i haanden. De tre nye
flader i desk skal kunne styre det, og en knap uden en skrivevej er en knap der
lyver.

Hver skrivning tager backup foerst og udsender `runtime.provider_registry_changed`.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/mc/provider-registry", tags=["mc-provider-registry"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


class _ModelBody(BaseModel):
    provider: str
    model: str
    aktiv: bool = True
    grund: str = ""


class _ProviderBody(BaseModel):
    provider: str
    aktiv: bool = True
    grund: str = ""


class _GendanBody(BaseModel):
    sti: str = ""


@router.get("")
async def registret() -> dict:
    """HELE registret: alle udbydere, alle modeller, pr. lane."""
    _require_owner()
    from core.services.provider_registry_admin import fuld_registrering
    return await asyncio.to_thread(fuld_registrering)


@router.post("/model")
async def saet_model(body: _ModelBody) -> dict:
    """Slaa én model til eller fra."""
    _require_owner()
    from core.services.provider_registry_admin import saet_model_aktiv
    return await asyncio.to_thread(
        saet_model_aktiv, provider=body.provider, model=body.model,
        aktiv=body.aktiv, grund=body.grund)


@router.post("/provider")
async def saet_provider(body: _ProviderBody) -> dict:
    """Slaa en hel udbyder til eller fra."""
    _require_owner()
    from core.services.provider_registry_admin import saet_udbyder_aktiv
    return await asyncio.to_thread(
        saet_udbyder_aktiv, provider=body.provider, aktiv=body.aktiv, grund=body.grund)


@router.delete("/model")
async def fjern_model_route(provider: str, model: str) -> dict:
    """Fjern én model fra registret. Legitimationen roeres ikke."""
    _require_owner()
    from core.services.provider_registry_admin import fjern_model
    return await asyncio.to_thread(fjern_model, provider=provider, model=model)


@router.delete("/provider")
async def fjern_provider_route(provider: str) -> dict:
    """Fjern en udbyder og dens modeller. Legitimationen roeres ikke."""
    _require_owner()
    from core.services.provider_registry_admin import fjern_udbyder
    return await asyncio.to_thread(fjern_udbyder, provider=provider)


@router.get("/backups")
async def liste_backups() -> dict:
    """Hvilke tilbagerulninger kan vaelges."""
    _require_owner()
    from core.services.provider_registry_admin import backups
    return {"backups": await asyncio.to_thread(backups)}


@router.post("/restore")
async def gendan(body: _GendanBody) -> dict:
    """Rul registret tilbage. Tom sti = nyeste backup."""
    _require_owner()
    from core.services.provider_registry_admin import gendan_backup
    return await asyncio.to_thread(gendan_backup, sti=body.sti)

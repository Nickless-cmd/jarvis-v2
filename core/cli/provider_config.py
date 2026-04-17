from __future__ import annotations

import argparse
import json

from core.services.non_visible_lane_execution import (
    cheap_lane_execution_truth,
    local_lane_execution_truth,
)
from core.services.cheap_provider_runtime import (
    CheapProviderError,
    list_provider_models,
    provider_runtime_defaults,
    smoke_cheap_lane,
    supported_cheap_providers,
    test_provider_target,
)
from core.auth.profiles import save_provider_credentials
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.db import init_db
from core.runtime.provider_router import (
    configure_provider_router_entry,
    provider_router_summary,
    select_main_agent_target,
)


def cmd_configure_provider(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider=args.provider,
        model=args.model,
        auth_mode=args.auth_mode,
        auth_profile=args.auth_profile,
        base_url=args.base_url,
        api_key=args.api_key,
        lane=args.lane,
        set_visible=args.set_visible,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_coding_lane(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider="openai",
        model=args.model,
        auth_mode="api-key",
        auth_profile=args.auth_profile,
        base_url=args.base_url,
        api_key=args.api_key,
        lane="coding",
        set_visible=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "coding_lane": {
                    "provider": "openai",
                    "lane": "coding",
                    "auth_mode": "api-key",
                    "auth_profile": args.auth_profile,
                },
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_copilot_coding_lane(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider="github-copilot",
        model=args.model,
        auth_mode="oauth",
        auth_profile=args.auth_profile,
        base_url="",
        api_key="",
        lane="coding",
        set_visible=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "coding_lane": {
                    "provider": "github-copilot",
                    "lane": "coding",
                    "auth_mode": "oauth",
                    "auth_profile": args.auth_profile,
                },
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_openai_oauth_coding_lane(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider="openai-codex",
        model=args.model,
        auth_mode="oauth",
        auth_profile=args.auth_profile,
        base_url=args.base_url,
        api_key="",
        lane="coding",
        set_visible=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "coding_lane": {
                    "provider": "openai-codex",
                    "lane": "coding",
                    "auth_mode": "oauth",
                    "auth_profile": args.auth_profile,
                    "base_url": args.base_url,
                    "subscription_auth": True,
                },
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_codex_cli_coding_lane(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider="codex-cli",
        model=args.model,
        auth_mode="none",
        auth_profile="",
        base_url="",
        api_key="",
        lane="coding",
        set_visible=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "coding_lane": {
                    "provider": "codex-cli",
                    "lane": "coding",
                    "auth_mode": "none",
                    "model": args.model,
                    "subscription_backend": True,
                },
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_local_lane(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider="ollama",
        model=args.model,
        auth_mode="none",
        auth_profile="",
        base_url=args.base_url,
        api_key="",
        lane="local",
        set_visible=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "local_lane": {
                    "provider": "ollama",
                    "lane": "local",
                    "auth_mode": "none",
                    "base_url": args.base_url,
                    "model": args.model,
                },
                "local_lane_execution": local_lane_execution_truth(),
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_select_main_agent(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = select_main_agent_target(
        provider=args.provider,
        model=args.model,
        auth_profile=args.auth_profile,
    )


def cmd_configure_cheap_provider(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    defaults = provider_runtime_defaults(args.provider)
    base_url = str(args.base_url or defaults.get("base_url") or "")
    auth_profile = str(args.auth_profile or args.provider)
    result = configure_provider_router_entry(
        provider=args.provider,
        model=args.model,
        auth_mode="api-key",
        auth_profile=auth_profile,
        base_url=base_url,
        api_key="",
        lane="cheap",
        set_visible=False,
    )
    credentials: dict[str, str] = {}
    if str(args.api_key or "").strip():
        credentials["api_key"] = str(args.api_key).strip()
    if str(args.account_id or "").strip():
        credentials["account_id"] = str(args.account_id).strip()
    if credentials:
        save_provider_credentials(
            profile=auth_profile,
            provider=args.provider,
            credentials=credentials,
        )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "provider_defaults": defaults,
                "cheap_lane": cheap_lane_execution_truth(),
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_cheap_lane_status(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    print(json.dumps(cheap_lane_execution_truth(), indent=2, ensure_ascii=False))


def cmd_list_provider_models(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    print(
        json.dumps(
            list_provider_models(
                provider=args.provider,
                auth_profile=args.auth_profile,
                base_url=args.base_url,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_test_provider(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    try:
        probe = test_provider_target(
            provider=args.provider,
            model=args.model,
            auth_profile=args.auth_profile,
            base_url=args.base_url,
            message=args.message,
        )
        payload = {"ok": True, "probe": probe}
    except CheapProviderError as exc:
        payload = {
            "ok": False,
            "probe": {
                "provider": args.provider,
                "model": args.model,
                "auth_profile": args.auth_profile,
                "status": exc.code,
                "message": exc.message,
                "status_code": exc.status_code,
                "retry_after_seconds": exc.retry_after_seconds,
            },
        }
    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_cheap_lane_smoke(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    print(
        json.dumps(
            smoke_cheap_lane(message=args.message),
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_list_cheap_providers(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    print(
        json.dumps(
            {"providers": supported_cheap_providers()},
            indent=2,
            ensure_ascii=False,
        )
    )
    print(
        json.dumps(
            {
                "ok": True,
                "selected": result,
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )

from __future__ import annotations

import argparse
import json

from apps.api.jarvis_api.services.non_visible_lane_execution import (
    local_lane_execution_truth,
)
from core.runtime.bootstrap import ensure_runtime_dirs
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

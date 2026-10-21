"""Tests for classify_command — auto/approval/destructive/blocked routing.

2026-05-22 (Claude): added after live-debug showed Jarvis hung on every
factual question that triggered a tool-call. Hallucination-guard told
him to verify via tool → he picked bash + dig → classify_command
returned "approval" → approval-card was emitted → no auto-confirmation
in the chat session → 240s timeout. dig/host/nslookup/etc are pure
read-only and now auto-approved.
"""
from __future__ import annotations

import pytest

from core.tools.simple_tools import classify_command


class TestNetworkReadOnlyAutoApproved:
    """DNS / route diagnostic tools are query-only — must be auto."""

    @pytest.mark.parametrize("command", [
        "dig srvlab.dk",
        "dig +short jarvis.srvlab.dk any",
        "host srvlab.dk",
        "nslookup jarvis.srvlab.dk",
        "traceroute 8.8.8.8",
        "tracepath 1.1.1.1",
        "mtr -r google.com",
        "mtr --report google.com",
        "getent hosts srvlab.dk",
        "arp -a",
        "arp -n",
    ])
    def test_query_tool_is_auto(self, command):
        assert classify_command(command) == "auto"


class TestBoundedPingAutoApproved:
    """ping with -c N is bounded; bare ping loops forever."""

    @pytest.mark.parametrize("command", [
        "ping -c 4 srvlab.dk",
        "ping -c 1 8.8.8.8",
        "ping -W 2 -c 3 1.1.1.1",
        "ping6 -c 2 ::1",
    ])
    def test_bounded_ping_is_auto(self, command):
        assert classify_command(command) == "auto"

    @pytest.mark.parametrize("command", [
        "ping srvlab.dk",        # unbounded — could loop forever
        "ping6 ::1",
        "ping -v srvlab.dk",     # has flags but no -c
    ])
    def test_unbounded_ping_needs_approval(self, command):
        assert classify_command(command) == "approval"


class TestExistingClassificationStillWorks:
    """Smoke check that adding network tools didn't break existing routes."""

    def test_destructive_still_blocked(self):
        assert classify_command("rm /tmp/file") == "destructive"
        assert classify_command("git reset --hard HEAD") == "destructive"

    def test_read_only_still_auto(self):
        assert classify_command("ls /tmp") == "auto"
        assert classify_command("whoami") == "auto"
        assert classify_command("cat /etc/hostname") == "auto"


class TestGithubCliReadOnly:
    """`gh` er en ren læsning for view/list-subkommandoerne — og kun dem.

    Målt 21/10-2026 (Bjørn: «wakeups skal forsætte med sessions permissions»):
    en vækning skulle verificere en release med `gh release view` og fik
    `approval_needed` tilbage — selv om kommandoen kun læser. Vækningen måtte
    falde tilbage til `web_fetch` mod en HTML-side, som er en svagere måling
    (draft-releases er usynlige der, så fravær kan ikke skelnes fra «ikke
    klar»). `gh` stod ingen steder i klassifikatoren; git havde sin egen liste.
    """

    @pytest.mark.parametrize("command", [
        "gh release view jarvis-desktop-v0.6.252 --json assets",
        "gh release view",
        "gh release list --limit 5",
        "gh pr view 42",
        "gh pr list",
        "gh pr diff 42",
        "gh pr checks 42",
        "gh issue view 7",
        "gh issue list",
        "gh run view 12345",
        "gh run list --limit 3",
        "gh repo view Nickless-cmd/jarvis-v2",
        "gh workflow list",
        "gh auth status",
    ])
    def test_gh_read_only_is_auto(self, command):
        assert classify_command(command) == "auto"

    @pytest.mark.parametrize("command", [
        "gh release create v1.0 --notes x",
        "gh release delete v1.0",
        "gh release upload v1.0 fil.zip",
        "gh release download v1.0",       # skriver til disk
        "gh api -X POST /repos/x/releases",
        "gh pr merge 42",
        "gh pr create --title x",
        "gh repo clone x/y",              # skriver til disk
        "gh auth login",
    ])
    def test_gh_mutations_need_approval(self, command):
        assert classify_command(command) == "approval"

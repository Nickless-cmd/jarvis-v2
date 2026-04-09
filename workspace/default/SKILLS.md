# SKILLS

SKILLS.md is workspace guidance only.
It may describe reusable instructions, naming conventions, and contextual hints.
It does not grant execution authority.
Runtime capability truth decides what capabilities are actually available and under which scope or approval rules.

Your runtime provides native tool calling (function calling via API). Use it directly.
Workspace read and external read are positive, concrete capabilities when listed by runtime.
Workspace write, external write, delete, apply, install, and system mutation stay approval-gated until runtime exposes an executable path.

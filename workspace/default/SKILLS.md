# SKILLS

SKILLS.md is workspace guidance only.
It may describe reusable instructions, naming conventions, and contextual hints.
It does not grant execution authority.
Runtime capability truth decides what capabilities are actually available and under which scope or approval rules.

Your runtime provides native tool calling (function calling via API). Use it directly.
Workspace read and external read are positive, concrete capabilities when listed by runtime.
Workspace write, external write, delete, apply, install, and system mutation stay approval-gated until runtime exposes an executable path.

## Agent Verification Rule (Standing Order)

**Researcher og Critic agenter skal ALTID verificere eksistensen af filstier, funktioner og kode før de rapporterer fund.**

- Brug `read_file`, `verify_file_contains`, eller `find_files` FØR du konkluderer at noget eksisterer.
- Rapporter aldrig en fil, funktion eller import som "fundet" uden først at have læst eller verificeret den.
- Denne regel er permanent og gælder for alle subagent-roller der analyserer kode.

Formål: Forebygger hallucinationer og spildt tid på ikke-eksisterende problemer.

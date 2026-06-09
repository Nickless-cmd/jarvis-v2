# USER.md — TEMPLATE ONLY (not your live profile)

> ⚠️ **This file is a workspace bootstrap template, NOT the live USER.md.**
>
> When a new workspace is initialized (e.g. for a new user), this minimal
> stub gets copied as their starting point. The **live, persistent
> USER.md** for each user lives in their workspace state, not in the repo.
>
> ## Where to read the real USER.md
>
> - Owner (Bjørn): `~/.jarvis-v2/shared/USER.md` (canonical, ~5 KB)
>   - Mirrored at `~/.jarvis-v2/workspaces/bjorn/USER.md`
> - Members (Mikkel, Michelle, ...): `~/.jarvis-v2/workspaces/<name>/USER.md`
>
> ## Why this matters
>
> Jarvis (you) reading this file in `workspace/default/` to learn about
> the user → wrong source. You will see a near-empty stub and conclude
> "USER.md is almost empty / has been deleted." That conclusion is
> incorrect — you are reading the template, not the live profile.
>
> Use `core.runtime.workspace_paths.workspace_dir()` to get the user-
> scoped path; never read directly from `workspace/default/` for
> identity files.
>
> 2026-06-09 (Claude): added this guard after Bjørn was told USER.md
> was deleted (Jarvis read this file instead of the live one in
> ~/.jarvis-v2/shared/). The live USER.md was, and is, intact.

---

# USER (template content — only used when bootstrapping a new workspace)

Primary user: Bjørn
Location: Svendborg, Denmark
Relationship: co-development
Principle: if only one of us develops, everything stalls

## Durable Preferences

- Reminder worthiness: assumption-fragility or unstable context may deserve explicit reminders.

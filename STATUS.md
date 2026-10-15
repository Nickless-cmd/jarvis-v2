# Feature status

The repository-wide status source remains
[`docs/design-history/CURRENT_STATUS.md`](docs/design-history/CURRENT_STATUS.md).
This file records the status of the 2026-10-15 Jarvis Desk Adaptive Chat Flow
delivery requested for this implementation.

## Adaptive Chat Flow — complete locally

- Chat Mode offers Living, Calm, and Adaptive without consulting the Code Mode
  row-view preference.
- Code Mode retains the existing row presentation and pacing.
- Active and historical Chat messages share content-preserving fallback rules.
- First-run comparison is live, single-run, per authenticated user, and is
  acknowledged only after render.
- Preference API, persistence, deterministic aggregates, suggestions, and the
  Jarvis preference tool are implemented without storing conversation text.
- Rich output, expandable work detail, Mission Control observability,
  accessibility, and existing scroll ownership remain available.
- Verification: 2,623 frontend tests passed (1 skipped); lint exited 0 with
  0 errors and 55 existing warnings; renderer build exited 0; 68 focused
  backend tests passed; Python compilation
  succeeded, and all five critical mutation checks failed and recovered as
  expected.

Release state: committed locally only. No automatic deployment, tag, push,
package publication, or service restart.

# central — Central CLI (Leverance 1)

Let terminal-klient til Den Intelligente Central. Live-feed + kommandoer, remote-først.

## Install
```bash
conda activate ai
pip install -e apps/central_cli
```
Registrerer `central` som kommando.

## Brug
```bash
central                         # Live TUI (3-panel: feed | output | command bar)
central --script status         # One-shot status-panel (afslutter)
central --script status --json  # Rå JSON (== gamle 'jc status')
central --script series         # Per-nerve tidsserie
central --script diag           # Diagnostik
central --remote http://10.0.0.39:8080 --script status   # anden base
```

## Auth (remote-først)
Genbruger `jc`'s setup: token læses fra `~/.config/jarvis-owner-token`, base `https://api.srvlab.dk`
(Cloudflare-tunnel → container). Override via `CENTRAL_CLI_TOKEN` / `CENTRAL_CLI_API_URL` / `--remote`.

## Kommandoer (L1)
Read: `status realtime series diag providers mind overview costs runs approvals nerve <n>` +
alt central_terminal-vokabular via `/central/command` (`incidents trace scan instrument daemons
model learning drift breakers autonomy clusters`).
Write (øjeblikkelig effekt): `toggle <nerve> on|off`, `resolve`, `approve|deny tool|autonomy|initiative <id>`.

## Status
Leverance 1 = brugbar live read + de eksisterende writes. Leverance 2 (backend: healer/governance-
skrivning) + Leverance 3 (fuld realtime + J.A.R.V.I.S-polish + desk-nedgradering) = egne planer.

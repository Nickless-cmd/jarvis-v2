#!/usr/bin/env bash
# Pre-commit hook: block Jarvis-issued API keys (jvs-<user>-<hex>) from
# being committed. detect-secrets' entropy detector missed the original
# leak in commit a1f1f9ee (2026-05-06) because the hex chunk's entropy
# in context was below threshold. A literal regex match is unambiguous.
#
# Receives staged file paths as positional args.
set -u
found=0
for f in "$@"; do
    [ -f "$f" ] || continue
    if grep -EnH "jvs-[a-z0-9]+-[0-9a-f]{20,}" "$f"; then
        echo "ERROR: Jarvis-issued API key found in $f." >&2
        echo "       Move it to ~/.jarvis-v2/state/anthropic_api_keys.json (gitignored)." >&2
        found=1
    fi
done
exit $found

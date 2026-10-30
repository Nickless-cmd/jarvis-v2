# Investigation 2: source reveal

This mapping was applied after opaque `results.json` had been written.
Generator intent is provenance, not ground truth about every observed pattern.

| Source | Generator | Selected perspective | Discovery MI | Confirmation MI | Search exceedances | Confirmation exceedances |
|---|---|---|---:|---:|---:|---:|
| S-05E2 | `noisy_context_xor` | `joint(v0,context)` | 0.476542 | 0.467335 | 0/250 | 0/250 |
| S-11B3 | `independent_prng` | `xor(v0,v2,v3)` | 0.003250 | 0.000100 | 221/250 | 139/250 |
| S-197C | `partition_specific_relation` | `joint(v2,context)` | 0.584464 | 0.000991 | 0/250 | 104/250 |
| S-B4E5 | `noisy_triple_xor` | `xor(v0,v1,v2)` | 0.411795 | 0.379161 | 0/250 | 0/250 |
| S-D592 | `deterministic_digest` | `xor(v0,v2,v3)` | 0.010503 | 0.000018 | 4/250 | 205/250 |

Descriptions and intended contrasts are preserved in `source_key.json`.
Interpretation and limitations belong in the living research notebook.

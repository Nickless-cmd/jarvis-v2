# Investigation 2: opaque measured summary

Source meanings were not available to the analyzer. Scores are plug-in
mutual information; calibration measures are descriptive, not universal thresholds.

| Source | Selected discovery perspective | Discovery MI | Search-null q95 | Confirmation MI | Confirmation-null q95 |
|---|---|---:|---:|---:|---:|
| S-05E2 | `joint(v0,context)` | 0.476542 | 0.009380 | 0.467335 | 0.003268 |
| S-11B3 | `xor(v0,v2,v3)` | 0.003250 | 0.009162 | 0.000100 | 0.001211 |
| S-197C | `joint(v2,context)` | 0.584464 | 0.008910 | 0.000991 | 0.002819 |
| S-B4E5 | `xor(v0,v1,v2)` | 0.411795 | 0.008985 | 0.379161 | 0.001548 |
| S-D592 | `xor(v0,v2,v3)` | 0.010503 | 0.008970 | 0.000018 | 0.001266 |

The search-null comparison accounts for selecting the largest score from the
declared catalog. Confirmation evaluates that selected perspective without reselection.

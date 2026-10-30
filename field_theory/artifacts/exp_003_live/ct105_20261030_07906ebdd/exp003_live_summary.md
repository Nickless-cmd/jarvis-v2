# Live Investigation 3: measured summary

**Evidence status:** retrospective exploration of the already inspected live snapshot.

Primary rolling windows: 47 overlapping views.
Joint MI range: 0.000000 to 0.251291 bits.

| Train → evaluate block | Base loss | Model loss | Model+weekday loss | Weekday gain vs model | Exact joint coverage |
|---|---:|---:|---:|---:|---:|
| 1 → 2 | 0.089514 | 0.087050 | 0.092042 | -0.004993 | 0.064 |
| 2 → 3 | 0.671581 | 0.686971 | 0.694069 | -0.007098 | 0.488 |
| 3 → 4 | 0.500130 | 0.501507 | 0.563630 | -0.062123 | 0.939 |
| 4 → 5 | 0.587244 | 0.575075 | 0.595179 | -0.020104 | 0.763 |

The full report must interpret composition, entropy, conditional-null,
sensitivity, discontinuity, transport, and context coverage together.
No row in this summary is independent confirmation.

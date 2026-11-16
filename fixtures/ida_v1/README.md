# Ida fixture pack v1

Versioned research replay pack for the Asset Decision Desk (Hurricane Ida remnants 2021-09-01).

## Contents

| File | Role |
| --- | --- |
| `access_signals.json` | Labeled **synthetic** DOT / 511 / MTA joins (≥40). NOT official closures. |
| `decision_desk_shortlist.json` | Default light desk bundle (shortlist + top decision-class). |
| `engine_disagreement.json` | HAND vs SFINCS nested wet/dry chips — **non-peer**, never blended. |

## Honesty

- Research only · NOT NWS · NOT decision-grade
- Synthetic access joins are marked `synthetic: true`
- HAND screening cm ≠ SFINCS metres ≠ FloodNet street peaks
- Henri is **not** in this pack (Event picker stays hidden until parity)

## Checksums

```bash
cd fixtures/ida_v1 && sha256sum -c SHA256SUMS
```

UI should show fixture id `ida_v1` / `ida_access_signals_v2`.

# MS-SatShield Implementation Plan

## Phase 0: Defaults and scope
- Key mode: src+dst in parallel.
- FO/FI estimator: bitmap (m=256) as primary.
- Synthetic first: sweep B/r/M to collapse rate-only separability, then validate FO/FI recovery.
- Set baseline epoch length and top-k parameters aligned with SatShield.

## Phase 1: Top-k detector (SatShield baseline)
- Implement Top-k + auxiliary table update logic (Algorithm 1 parity).
- Add epoch snapshot and heavy-key export.
- Add unit tests using synthetic Zipf flows.

## Phase 2: Multi-signature features
- Implement fan-out/fan-in estimators for candidates only.
- Add persistence tracking across epochs.
- Add score normalization and queue mapping.

## Phase 3: Attack models (A/B/C)
- A: many bots + low per-bot rate (rate separability collapse).
- B: decoy fan-out expansion (rate collapse + fan-out separation).
- C: pulse/on-off attacks (persistence benefit).

## Phase 4: Simulation harness
- Connect to Icarus traces or synthetic generators.
- Add topology routing hooks for target-link selection.
- Produce epoch-level metrics and time-series outputs.

## Phase 5: Experiment matrix
- Reproduce SatShield baseline, then run A/B/C degradations.
- Compare rate-only vs rate+fan-out vs rate+fan-out+persist.
- Sweep K, epoch, and FO estimator parameters.

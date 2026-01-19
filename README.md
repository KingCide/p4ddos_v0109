# p4ddos_v0109

Framework for implementing MS-SatShield (multi-signature SatShield) in the LEO LFA setting.

## Layout

- `src/ms_satshield`: detector, fan-out estimators, scoring, queue mapping
- `src/sim`: topology/traffic stubs and experiment runner
- `experiments`: CLI entry points
- `configs`: experiment configs (to be added)
- `progress`: project progress notes and plans

## Notes

- Design is aligned with documents in `p4ddos_v0109/关键资料`.
- P4 data-plane logic is modeled in Python for simulation; P4 integration can be added later.
- Synthetic sweep entry: `p4ddos_v0109/experiments/sweep_rate_collapse.py`

"""Sweep B/r/M to show rate-only separability collapse and FO/FI recovery."""

from __future__ import annotations

import argparse
import csv
from typing import Dict, Iterable, List, Tuple

from ms_satshield.config import EpochConfig, FanoutConfig, QueueConfig, ScoreConfig, TopKConfig
from ms_satshield.epoch import MultiEpochResult, MultiKeyEpochManager
from ms_satshield.metrics import precision_recall_f1
from sim.runner import ExperimentConfig, ExperimentRunner
from sim.synthetic import SyntheticAttack, SyntheticAttackConfig, SyntheticBenign, SyntheticBenignConfig


def _parse_list(values: str, caster) -> List:
    return [caster(item.strip()) for item in values.split(",") if item.strip()]


def _epoch_metrics(
    results: List[MultiEpochResult],
    truth_src: Iterable[int],
    truth_dst: Iterable[int],
    num_queues: int,
    warmup_epochs: int,
) -> Dict[str, Tuple[float, float, float]]:
    src_truth = set(truth_src)
    dst_truth = set(truth_dst)
    rate_only_src = []
    rate_only_dst = []
    multi_src = []
    multi_dst = []

    for idx, epoch in enumerate(results):
        if idx < warmup_epochs:
            continue
        src = epoch.results.get("src")
        dst = epoch.results.get("dst")
        if src:
            src_keys = [rec.key for rec in src.heavy_keys]
            rate_only_src.append(precision_recall_f1(src_keys, src_truth))
            multi_keys = [k for k, q in src.queue_map.items() if q == num_queues - 1]
            multi_src.append(precision_recall_f1(multi_keys, src_truth))
        if dst:
            dst_keys = [rec.key for rec in dst.heavy_keys]
            rate_only_dst.append(precision_recall_f1(dst_keys, dst_truth))
            multi_keys = [k for k, q in dst.queue_map.items() if q == num_queues - 1]
            multi_dst.append(precision_recall_f1(multi_keys, dst_truth))

    def _avg(values: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        if not values:
            return 0.0, 0.0, 0.0
        p = sum(v[0] for v in values) / len(values)
        r = sum(v[1] for v in values) / len(values)
        f = sum(v[2] for v in values) / len(values)
        return p, r, f

    return {
        "rate_only_src": _avg(rate_only_src),
        "multi_src": _avg(multi_src),
        "rate_only_dst": _avg(rate_only_dst),
        "multi_dst": _avg(multi_dst),
    }


def run_sweep(args: argparse.Namespace) -> List[Dict[str, object]]:
    bots = _parse_list(args.bots, int)
    rates = _parse_list(args.rates, float)
    decoys = _parse_list(args.decoys, int)

    topk_cfg = TopKConfig(epoch_ms=args.epoch_ms, key_mode="src+dst")
    fanout_cfg = FanoutConfig(mode="bitmap", bitmap_bits=args.bitmap_bits)
    score_cfg = ScoreConfig(alpha=args.alpha, beta=args.beta, gamma=args.gamma, persist_k=args.persist_k)
    queue_cfg = QueueConfig(num_queues=args.queues)
    epoch_cfg = EpochConfig(epoch_ms=args.epoch_ms, persist_k=args.persist_k)

    benign_cfg = SyntheticBenignConfig(
        flows=args.benign_flows,
        rate_kbps_mu=args.benign_mu,
        rate_kbps_sigma=args.benign_sigma,
        duration_ms=args.duration_ms,
        epoch_ms=args.epoch_ms,
    )

    rows: List[Dict[str, object]] = []
    for b in bots:
        for r in rates:
            for m in decoys:
                detector = MultiKeyEpochManager(
                    topk_cfg,
                    fanout_cfg,
                    score_cfg,
                    queue_cfg,
                    epoch_cfg,
                    key_mode="src+dst",
                )
                runner = ExperimentRunner(detector, ExperimentConfig(epoch_ms=args.epoch_ms))
                attack_cfg = SyntheticAttackConfig(
                    bots=b,
                    rate_mbps=r,
                    decoys=m,
                    attack_start_ms=0,
                    attack_end_ms=args.duration_ms,
                    epoch_ms=args.epoch_ms,
                    decoy_sample=args.decoy_sample,
                )
                attack = SyntheticAttack(attack_cfg)
                benign = SyntheticBenign(benign_cfg)
                results = runner.run([benign, attack])
                metrics = _epoch_metrics(
                    results,
                    attack.attack_srcs,
                    attack.attack_dsts,
                    queue_cfg.num_queues,
                    args.warmup_epochs,
                )
                rows.append(
                    {
                        "bots": b,
                        "rate_mbps": r,
                        "decoys": m,
                        "rate_only_src_f1": metrics["rate_only_src"][2],
                        "multi_src_f1": metrics["multi_src"][2],
                        "rate_only_dst_f1": metrics["rate_only_dst"][2],
                        "multi_dst_f1": metrics["multi_dst"][2],
                    }
                )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bots", default="100,500,2000,10000")
    parser.add_argument("--rates", default="100,20,5,1")
    parser.add_argument("--decoys", default="1,10,100,1000")
    parser.add_argument("--epoch-ms", type=int, default=1000)
    parser.add_argument("--duration-ms", type=int, default=5000)
    parser.add_argument("--benign-flows", type=int, default=5000)
    parser.add_argument("--benign-mu", type=float, default=4.5)
    parser.add_argument("--benign-sigma", type=float, default=1.0)
    parser.add_argument("--bitmap-bits", type=int, default=256)
    parser.add_argument("--alpha", type=float, default=0.6)
    parser.add_argument("--beta", type=float, default=0.3)
    parser.add_argument("--gamma", type=float, default=0.1)
    parser.add_argument("--persist-k", type=int, default=3)
    parser.add_argument("--queues", type=int, default=4)
    parser.add_argument("--decoy-sample", type=int, default=None)
    parser.add_argument("--warmup-epochs", type=int, default=1)
    parser.add_argument("--output", default="p4ddos_v0109/progress/sweep_results.csv")
    return parser.parse_args()


def write_csv(path: str, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    rows = run_sweep(args)
    write_csv(args.output, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

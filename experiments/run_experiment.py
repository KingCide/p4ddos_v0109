"""CLI entry for running MS-SatShield experiments (skeleton)."""

from __future__ import annotations

import argparse

from ms_satshield.config import EpochConfig, FanoutConfig, QueueConfig, ScoreConfig, TopKConfig
from ms_satshield.epoch import EpochManager
from sim.runner import ExperimentConfig, ExperimentRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epoch-ms", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    topk_cfg = TopKConfig(epoch_ms=args.epoch_ms)
    fanout_cfg = FanoutConfig()
    score_cfg = ScoreConfig()
    queue_cfg = QueueConfig()
    epoch_cfg = EpochConfig(epoch_ms=args.epoch_ms)

    detector = EpochManager(topk_cfg, fanout_cfg, score_cfg, queue_cfg, epoch_cfg)
    runner = ExperimentRunner(detector, ExperimentConfig(epoch_ms=args.epoch_ms))

    # TODO: Wire traffic sources and topology routing.
    runner.run([])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

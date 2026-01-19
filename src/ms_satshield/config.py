"""Configuration dataclasses for MS-SatShield components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopKConfig:
    k: int = 10_000
    stages: int = 8
    buckets_per_stage: int = 2048
    epoch_ms: int = 1000
    heavy_threshold_bytes: int = 0
    key_mode: str = "src+dst"


@dataclass(frozen=True)
class FanoutConfig:
    mode: str = "bitmap"  # bitmap | hll-lite
    bitmap_bits: int = 256
    hll_p: int = 6
    hll_reg_bits: int = 6
    candidate_k: int = 10_000


@dataclass(frozen=True)
class ScoreConfig:
    alpha: float = 0.6
    beta: float = 0.3
    gamma: float = 0.1
    persist_k: int = 3
    norm_mode: str = "p99"  # p99 | max | zscore


@dataclass(frozen=True)
class QueueConfig:
    num_queues: int = 4
    mapping: str = "sigmoid"  # sigmoid | quantile


@dataclass(frozen=True)
class EpochConfig:
    epoch_ms: int = 1000
    persist_k: int = 3

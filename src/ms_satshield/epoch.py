"""Epoch-based controller logic for MS-SatShield."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set

from .config import EpochConfig, FanoutConfig, QueueConfig, ScoreConfig, TopKConfig
from .detector import FlowDetector, FlowRecord
from .fanout import BitmapEstimator, FanoutEstimator, HLLLiteEstimator
from .scheduler import QueueMapper
from .scoring import ScoreModel


@dataclass
class CandidateFeatures:
    rate: float
    fanout: float
    persist: float


@dataclass
class EpochResult:
    heavy_keys: List[FlowRecord]
    scores: Dict[int, float]
    queue_map: Dict[int, int]


class EpochManager:
    def __init__(
        self,
        topk_cfg: TopKConfig,
        fanout_cfg: FanoutConfig,
        score_cfg: ScoreConfig,
        queue_cfg: QueueConfig,
        epoch_cfg: EpochConfig,
    ) -> None:
        self._detector = FlowDetector(topk_cfg)
        self._score_model = ScoreModel(score_cfg)
        self._queue_mapper = QueueMapper(queue_cfg)
        self._epoch_cfg = epoch_cfg
        self._fanout: FanoutEstimator
        if fanout_cfg.mode == "hll-lite":
            self._fanout = HLLLiteEstimator(fanout_cfg)
        else:
            self._fanout = BitmapEstimator(fanout_cfg)
        self._candidates: Set[int] = set()
        self._persist: Dict[int, int] = {}
        self._bytes: Dict[int, int] = {}

    def on_packet(self, key: int, other: int, size: int) -> None:
        self._detector.on_packet(key, size)
        if key in self._candidates:
            self._fanout.update(key, other)
            self._bytes[key] = self._bytes.get(key, 0) + size

    def end_epoch(self) -> EpochResult:
        heavy = self._detector.end_epoch()
        heavy_keys = {rec.key for rec in heavy}
        features = self._build_features(heavy)
        stats = self._score_model.compute_stats(
            (f.rate for f in features.values()),
            (f.fanout for f in features.values()),
            (f.persist for f in features.values()),
        )
        scores = {
            key: self._score_model.score(f.rate, f.fanout, f.persist, stats)
            for key, f in features.items()
        }
        self._queue_mapper.update(scores.values())
        queue_map = {key: self._queue_mapper.map_score(score) for key, score in scores.items()}
        self._rotate_epoch(heavy_keys)
        return EpochResult(heavy_keys=heavy, scores=scores, queue_map=queue_map)

    def _build_features(self, heavy: Iterable[FlowRecord]) -> Dict[int, CandidateFeatures]:
        features: Dict[int, CandidateFeatures] = {}
        for rec in heavy:
            persist = float(self._persist.get(rec.key, 0))
            rate = float(self._bytes.get(rec.key, 0)) / max(1.0, self._epoch_cfg.epoch_ms / 1000.0)
            fanout = float(self._fanout.estimate(rec.key))
            features[rec.key] = CandidateFeatures(rate=rate, fanout=fanout, persist=persist)
        return features

    def _rotate_epoch(self, heavy_keys: Set[int]) -> None:
        for key in heavy_keys:
            self._persist[key] = min(self._epoch_cfg.persist_k, self._persist.get(key, 0) + 1)
        for key in list(self._persist.keys()):
            if key not in heavy_keys:
                self._persist[key] = max(0, self._persist[key] - 1)
                if self._persist[key] == 0:
                    self._persist.pop(key, None)
        self._candidates = set(heavy_keys)
        self._bytes.clear()
        self._fanout.reset()
        self._detector.reset()


@dataclass
class MultiEpochResult:
    results: Dict[str, EpochResult]


class MultiKeyEpochManager:
    """Runs MS-SatShield for src/dst keys in parallel."""

    def __init__(
        self,
        topk_cfg: TopKConfig,
        fanout_cfg: FanoutConfig,
        score_cfg: ScoreConfig,
        queue_cfg: QueueConfig,
        epoch_cfg: EpochConfig,
        key_mode: str = "src+dst",
    ) -> None:
        self.key_mode = key_mode
        self._managers: Dict[str, EpochManager] = {}
        if key_mode in ("src", "src+dst"):
            self._managers["src"] = EpochManager(
                topk_cfg, fanout_cfg, score_cfg, queue_cfg, epoch_cfg
            )
        if key_mode in ("dst", "src+dst"):
            self._managers["dst"] = EpochManager(
                topk_cfg, fanout_cfg, score_cfg, queue_cfg, epoch_cfg
            )
        if not self._managers:
            raise ValueError(f"Unsupported key_mode: {key_mode}")

    def on_packet(self, src: int, dst: int, size: int) -> None:
        manager = self._managers.get("src")
        if manager is not None:
            manager.on_packet(src, dst, size)
        manager = self._managers.get("dst")
        if manager is not None:
            manager.on_packet(dst, src, size)

    def end_epoch(self) -> MultiEpochResult:
        return MultiEpochResult(
            results={key: mgr.end_epoch() for key, mgr in self._managers.items()}
        )

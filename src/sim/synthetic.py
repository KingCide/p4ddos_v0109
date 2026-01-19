"""Synthetic traffic generators for separability sweeps."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, Iterator, List, Optional

from .flow import FlowKey, Packet
from .traffic import AttackParams, TrafficSource


@dataclass(frozen=True)
class SyntheticBenignConfig:
    flows: int
    rate_kbps_mu: float
    rate_kbps_sigma: float
    duration_ms: int
    epoch_ms: int
    seed: int = 1


class SyntheticBenign(TrafficSource):
    def __init__(self, config: SyntheticBenignConfig) -> None:
        self.config = config
        rng = random.Random(config.seed)
        self._flows: List[FlowKey] = []
        self._rates_kbps: List[float] = []
        src_base = 100_000
        dst_base = 200_000
        for idx in range(config.flows):
            src = src_base + idx
            dst = dst_base + idx
            rate = rng.lognormvariate(config.rate_kbps_mu, config.rate_kbps_sigma)
            self._flows.append(FlowKey(src=src, dst=dst))
            self._rates_kbps.append(rate)

    def packets(self) -> Iterator[Packet]:
        epoch_ms = self.config.epoch_ms
        epoch_count = max(1, int(self.config.duration_ms / epoch_ms))
        for epoch in range(epoch_count):
            base_ts = epoch * epoch_ms
            for idx, (flow, rate_kbps) in enumerate(zip(self._flows, self._rates_kbps)):
                size = int(rate_kbps * 1000 / 8 * (epoch_ms / 1000))
                if size <= 0:
                    size = 1
                ts_ms = base_ts + (idx / max(1, len(self._flows))) * (epoch_ms - 1)
                yield Packet(ts_ms=ts_ms, src=flow.src, dst=flow.dst, size=size, flow=flow)


@dataclass(frozen=True)
class SyntheticAttackConfig:
    bots: int
    rate_mbps: float
    decoys: int
    attack_start_ms: int
    attack_end_ms: int
    epoch_ms: int
    seed: int = 7
    decoy_sample: Optional[int] = None


class SyntheticAttack(TrafficSource):
    def __init__(self, config: SyntheticAttackConfig) -> None:
        self.config = config
        rng = random.Random(config.seed)
        self.attack_srcs = [10_000_000 + i for i in range(config.bots)]
        self.attack_dsts = [20_000_000 + i for i in range(config.decoys)]
        sample = config.decoy_sample or config.decoys
        self._decoy_sample = max(1, min(sample, config.decoys))
        self._bot_decoys: Dict[int, List[int]] = {}
        for bot in self.attack_srcs:
            if self._decoy_sample == config.decoys:
                decoys = list(self.attack_dsts)
            else:
                decoys = rng.sample(self.attack_dsts, self._decoy_sample)
            self._bot_decoys[bot] = decoys

    def packets(self) -> Iterator[Packet]:
        epoch_ms = self.config.epoch_ms
        bytes_per_bot = self.config.rate_mbps * 1_000_000 / 8 * (epoch_ms / 1000)
        bytes_per_flow = bytes_per_bot / self._decoy_sample
        for ts_ms in range(self.config.attack_start_ms, self.config.attack_end_ms, epoch_ms):
            for bot_idx, bot in enumerate(self.attack_srcs):
                decoys = self._bot_decoys[bot]
                for decoy_idx, decoy in enumerate(decoys):
                    size = int(bytes_per_flow)
                    if size <= 0:
                        size = 1
                    flow = FlowKey(src=bot, dst=decoy)
                    offset = (bot_idx + decoy_idx / max(1, len(decoys))) / max(1, self.config.bots)
                    yield Packet(
                        ts_ms=ts_ms + offset * (epoch_ms - 1),
                        src=bot,
                        dst=decoy,
                        size=size,
                        flow=flow,
                    )

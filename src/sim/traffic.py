"""Traffic generation stubs for benign and attack flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Protocol

from .flow import Packet


class TrafficSource(Protocol):
    def packets(self) -> Iterator[Packet]:
        ...


@dataclass(frozen=True)
class AttackParams:
    bots: int
    rate_mbps: float
    decoys: int
    attack_start_ms: float
    attack_end_ms: float


class LFABase(TrafficSource):
    def __init__(self, params: AttackParams) -> None:
        self.params = params

    def packets(self) -> Iterator[Packet]:
        raise NotImplementedError


class BenignReplay(TrafficSource):
    def __init__(self, trace_path: str) -> None:
        self.trace_path = trace_path

    def packets(self) -> Iterator[Packet]:
        raise NotImplementedError

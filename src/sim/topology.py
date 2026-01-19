"""Topology and routing interfaces for LEO simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Protocol


@dataclass(frozen=True)
class Link:
    src: int
    dst: int
    capacity_gbps: float


@dataclass(frozen=True)
class Path:
    nodes: List[int]
    links: List[Link]


class RoutingModel(Protocol):
    def paths(self, src: int, dst: int, ts_ms: float) -> List[Path]:
        ...


class TopologyProvider(Protocol):
    def snapshot(self, ts_ms: float) -> Iterable[Link]:
        ...

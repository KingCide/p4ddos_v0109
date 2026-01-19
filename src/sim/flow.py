"""Flow and packet structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlowKey:
    src: int
    dst: int


@dataclass(frozen=True)
class Packet:
    ts_ms: float
    src: int
    dst: int
    size: int
    flow: FlowKey

"""LFA attack variants aligned with degradation settings A/B/C."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List

from .flow import FlowKey, Packet
from .traffic import AttackParams, LFABase


@dataclass(frozen=True)
class PulseParams:
    period_ms: float
    on_ms: float


class LFADegenerationA(LFABase):
    """Many bots, lower per-bot rate."""

    def packets(self) -> Iterator[Packet]:
        raise NotImplementedError


class LFADegenerationB(LFABase):
    """Decoy fan-out expansion."""

    def packets(self) -> Iterator[Packet]:
        raise NotImplementedError


class LFADegenerationC(LFABase):
    """Pulse/on-off attacks for persistence evaluation."""

    def __init__(self, params: AttackParams, pulse: PulseParams) -> None:
        super().__init__(params)
        self.pulse = pulse

    def packets(self) -> Iterator[Packet]:
        raise NotImplementedError

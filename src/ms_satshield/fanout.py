"""Fan-out / fan-in estimators for candidate keys."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List

from .config import FanoutConfig


class FanoutEstimator:
    def update(self, key: int, other: int) -> None:
        raise NotImplementedError

    def estimate(self, key: int) -> float:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError


class BitmapEstimator(FanoutEstimator):
    def __init__(self, config: FanoutConfig) -> None:
        self._bits = config.bitmap_bits
        self._maps: Dict[int, int] = {}

    def update(self, key: int, other: int) -> None:
        idx = self._hash(other) % self._bits
        bitset = self._maps.get(key, 0)
        bitset |= 1 << idx
        self._maps[key] = bitset

    def estimate(self, key: int) -> float:
        bitset = self._maps.get(key, 0)
        zeros = self._bits - bitset.bit_count()
        if zeros == 0:
            return float(self._bits)
        return -self._bits * math.log(zeros / self._bits)

    def reset(self) -> None:
        self._maps.clear()

    @staticmethod
    def _hash(value: int) -> int:
        return hash(value) & 0xFFFFFFFF


class HLLLiteEstimator(FanoutEstimator):
    def __init__(self, config: FanoutConfig) -> None:
        self._p = config.hll_p
        self._m = 1 << self._p
        self._reg_bits = config.hll_reg_bits
        self._maps: Dict[int, List[int]] = {}
        self._alpha = self._alpha_m(self._m)

    def update(self, key: int, other: int) -> None:
        y = self._hash(other)
        j = y & (self._m - 1)
        w = y >> self._p
        rank = self._rho(w, 32 - self._p)
        regs = self._maps.get(key)
        if regs is None:
            regs = [0] * self._m
            self._maps[key] = regs
        if rank > regs[j]:
            regs[j] = rank

    def estimate(self, key: int) -> float:
        regs = self._maps.get(key)
        if regs is None:
            return 0.0
        inv_sum = sum(2.0 ** (-r) for r in regs)
        if inv_sum == 0:
            return 0.0
        return self._alpha * (self._m ** 2) / inv_sum

    def reset(self) -> None:
        self._maps.clear()

    @staticmethod
    def _hash(value: int) -> int:
        return hash(value) & 0xFFFFFFFF

    @staticmethod
    def _rho(value: int, bits: int) -> int:
        if value == 0:
            return bits + 1
        return bits - value.bit_length() + 1

    @staticmethod
    def _alpha_m(m: int) -> float:
        if m == 16:
            return 0.673
        if m == 32:
            return 0.697
        if m == 64:
            return 0.709
        return 0.7213 / (1 + 1.079 / m)

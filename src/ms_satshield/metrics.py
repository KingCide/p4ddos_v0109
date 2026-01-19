"""Metrics for detection and mitigation."""

from __future__ import annotations

from typing import Iterable, Tuple


def precision_recall_f1(pred: Iterable[int], truth: Iterable[int]) -> Tuple[float, float, float]:
    pred_set = set(pred)
    truth_set = set(truth)
    tp = len(pred_set & truth_set)
    fp = len(pred_set - truth_set)
    fn = len(truth_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def average_relative_error(estimates: Iterable[float], truths: Iterable[float]) -> float:
    est_list = list(estimates)
    truth_list = list(truths)
    if not est_list or len(est_list) != len(truth_list):
        return 0.0
    errors = []
    for est, true in zip(est_list, truth_list):
        if true == 0:
            continue
        errors.append(abs(est - true) / true)
    if not errors:
        return 0.0
    return sum(errors) / len(errors)


def reaction_time(attack_start_ms: float, mitigation_start_ms: float) -> float:
    return max(0.0, mitigation_start_ms - attack_start_ms)


def throughput_drop(before: float, during: float) -> float:
    if before <= 0:
        return 0.0
    return max(0.0, (before - during) / before)

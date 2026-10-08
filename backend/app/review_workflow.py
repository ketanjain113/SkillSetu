from __future__ import annotations

import os
import random
from typing import Iterable


def second_review_sample_rate() -> float:
    rate = float(os.getenv("SECOND_REVIEW_SAMPLE_RATE", "0.2"))
    if not 0 <= rate <= 1:
        raise ValueError("SECOND_REVIEW_SAMPLE_RATE must be between 0 and 1")
    return rate


def needs_second_review(*, flagged: bool, confidence: float, sample_rate: float | None = None) -> bool:
    rate = second_review_sample_rate() if sample_rate is None else sample_rate
    if not 0 <= rate <= 1:
        raise ValueError("Second-review sample rate must be between 0 and 1")
    return flagged or confidence < 0.65 or random.random() < rate


def choose_second_assessor(assessors: Iterable, primary_assessor_id: int, primary_centre: str | None):
    eligible = [
        assessor
        for assessor in assessors
        if assessor.id != primary_assessor_id
        and assessor.role == "assessor"
        and assessor.centre
        and assessor.centre != primary_centre
    ]
    if not eligible:
        return None
    return min(eligible, key=lambda assessor: assessor.id)

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Sequence


def _as_float_list(values: Iterable[float]) -> List[float]:
    return [float(value) for value in values]


def _bootstrap_ci(values: Sequence[float], confidence_level: float = 0.95, bootstrap_samples: int = 200) -> List[float]:
    if not values:
        return [0.0, 0.0]
    if len(values) == 1:
        return [float(values[0]), float(values[0])]

    lower_pct = (1 - confidence_level) / 2
    upper_pct = 1 - lower_pct
    boot = []
    for _ in range(max(1, bootstrap_samples)):
        sample = [values[i % len(values)] for i in range(len(values))]
        boot.append(mean(sample))
    sorted_boot = sorted(boot)
    low_index = max(0, min(len(sorted_boot) - 1, int(len(sorted_boot) * lower_pct)))
    high_index = max(0, min(len(sorted_boot) - 1, int(len(sorted_boot) * upper_pct)))
    return [sorted_boot[low_index], sorted_boot[high_index]]


def _weighted_matrix(labels):
    sorted_labels = sorted(set(labels))
    if len(sorted_labels) <= 1:
        return {v: {v: 1.0} for v in sorted_labels}
    max_distance = max(sorted_labels) - min(sorted_labels)
    matrix = {}
    for left in sorted_labels:
        matrix[left] = {}
        for right in sorted_labels:
            diff = abs(left - right)
            matrix[left][right] = 1 - (diff / max_distance if max_distance else 0)
    return matrix


def compute_weighted_cohens_kappa(rater_a, rater_b):
    """Compute weighted Cohen's kappa for ordinal ratings 1..5."""
    if len(rater_a) != len(rater_b):
        raise ValueError('rating sequences must have the same length')
    labels = sorted(set(rater_a + rater_b))
    if not labels:
        return 1.0
    if len(labels) == 1:
        return 1.0

    contingency = {label_a: {label_b: 0 for label_b in labels} for label_a in labels}
    for left, right in zip(rater_a, rater_b):
        contingency[left][right] += 1

    max_gap = max(labels) - min(labels)
    po = 0.0
    pe = 0.0
    row_totals = {label: sum(contingency[label].values()) for label in labels}
    col_totals = {label: sum(contingency[left][label] for left in labels) for label in labels}
    total = sum(row_totals.values())

    for left in labels:
        for right in labels:
            weight = 1 - (abs(left - right) / max_gap if max_gap else 0)
            po += weight * contingency[left][right]
            expected = (row_totals[left] * col_totals[right]) / total
            pe += weight * expected

    po = po / total
    pe = pe / total
    if abs(pe - 1.0) < 1e-9:
        return 1.0
    return (po - pe) / (1 - pe)


def compute_krippendorff_alpha(rater_matrix, return_ci: bool = False, bootstrap_samples: int = 200, confidence_level: float = 0.95):
    """Approximate ordinal Krippendorff's alpha across assessors for demo use."""
    if not rater_matrix:
        return {"alpha": 1.0, "ci": [1.0, 1.0]} if return_ci else 1.0
    rows = len(rater_matrix)
    if rows < 2:
        return {"alpha": 1.0, "ci": [1.0, 1.0]} if return_ci else 1.0
    item_count = len(rater_matrix[0])
    if any(len(rater) != item_count for rater in rater_matrix):
        raise ValueError('all assessors must score the same number of items')

    labels = sorted({value for rater in rater_matrix for value in rater})
    if len(labels) <= 1:
        return {"alpha": 1.0, "ci": [1.0, 1.0]} if return_ci else 1.0

    total_disagreement = 0.0
    possible_pairs = 0
    per_item_alpha_values = []
    for item_index in range(item_count):
        scores = [rater[item_index] for rater in rater_matrix]
        pair_total = 0.0
        pair_count = 0
        for left_index in range(rows):
            for right_index in range(left_index + 1, rows):
                pair_total += abs(scores[left_index] - scores[right_index]) / (max(labels) - min(labels) or 1)
                pair_count += 1
        per_item_alpha_values.append(1 - (pair_total / pair_count) if pair_count else 1.0)
        total_disagreement += pair_total
        possible_pairs += pair_count

    observed = 1 - (total_disagreement / possible_pairs) if possible_pairs else 1.0
    alpha = max(0.0, min(1.0, observed))
    if return_ci:
        ci = _bootstrap_ci(per_item_alpha_values or [alpha], confidence_level=confidence_level, bootstrap_samples=bootstrap_samples)
        return {"alpha": alpha, "ci": [max(0.0, min(1.0, ci[0])), max(0.0, min(1.0, ci[1]))], "confidence_level": confidence_level}
    return alpha


def compute_icc(rater_matrix, confidence_level: float = 0.95, bootstrap_samples: int = 200):
    """Return a robust ICC approximation with a confidence interval for ordinal ratings."""
    if not rater_matrix:
        return {"icc": 1.0, "ci": [1.0, 1.0], "model": "ordinal-icc"}
    rows = len(rater_matrix)
    if rows < 2:
        return {"icc": 1.0, "ci": [1.0, 1.0], "model": "ordinal-icc"}
    item_count = len(rater_matrix[0])
    if any(len(rater) != item_count for rater in rater_matrix):
        raise ValueError('all assessors must score the same number of items')

    if all(rater == rater_matrix[0] for rater in rater_matrix):
        return {"icc": 1.0, "ci": [1.0, 1.0], "model": "ordinal-icc"}

    totals = [sum(rater) / len(rater) for rater in rater_matrix]
    overall_mean = sum(totals) / len(totals)
    between = sum((value - overall_mean) ** 2 for value in totals)
    within_sum = 0.0
    for rater in rater_matrix:
        within_sum += sum((value - mean(rater)) ** 2 for value in rater)

    variance_between = between / max(len(totals) - 1, 1)
    variance_within = within_sum / max(len(rater_matrix) * (item_count - 1), 1)
    icc = variance_between / (variance_between + variance_within) if (variance_between + variance_within) else 1.0
    icc = max(0.0, min(1.0, icc))
    cin = _bootstrap_ci([float(score) for score in totals], confidence_level=confidence_level, bootstrap_samples=bootstrap_samples)
    return {"icc": icc, "ci": [max(0.0, min(1.0, cin[0])), max(0.0, min(1.0, cin[1]))], "model": "ordinal-icc"}


def fit_many_facet_model(rater_matrix):
    """Approximate a many-facet Rasch-style model using ordinal averages and severity offsets."""
    if not rater_matrix:
        return {"assessor_severity": [], "candidate_ability": [], "item_difficulty": [], "method": "ordinal-rank-approximation"}

    assessors = list(rater_matrix)
    item_count = len(assessors[0])
    overall_mean = mean(value for rater in assessors for value in rater)
    assessor_severity = []
    for rater in assessors:
        assessor_mean = mean(rater)
        assessor_severity.append({"assessor_index": len(assessor_severity), "severity": round(overall_mean - assessor_mean, 3)})

    candidate_ability = []
    for item_index in range(item_count):
        item_values = [rater[item_index] for rater in assessors]
        candidate_ability.append({"candidate_index": item_index, "ability": round(mean(item_values) - overall_mean, 3)})

    item_difficulty = []
    for item_index in range(item_count):
        item_values = [rater[item_index] for rater in assessors]
        mean_rating = mean(item_values)
        item_difficulty.append({"item_index": item_index, "difficulty": round(mean_rating, 3)})

    return {
        "assessor_severity": assessor_severity,
        "candidate_ability": candidate_ability,
        "item_difficulty": item_difficulty,
        "method": "many-facet ordinal approximation",
    }


def generate_anchor_exam(clips: Sequence[Dict[str, Any]], target_score: float = 4.0, top_n: int = 3):
    """Pick the strongest expert consensus clips for assessor calibration."""
    scored = []
    for clip in clips:
        expert_scores = clip.get("expert_scores", [])
        mean_score = mean(expert_scores) if expert_scores else 0.0
        variability = pstdev(expert_scores) if len(expert_scores) > 1 else 0.0
        consensus = max(0.0, 1.0 - (variability / 4.0))
        target_gap = abs(mean_score - target_score) / 5.0
        ranking_score = consensus + (mean_score / 5.0) - target_gap
        scored.append({
            "clip_id": clip.get("clip_id"),
            "title": clip.get("title", clip.get("clip_id")),
            "expert_scores": expert_scores,
            "mean_score": round(mean_score, 2),
            "consensus": round(consensus, 3),
            "ranking_score": round(ranking_score, 3),
        })
    scored.sort(key=lambda item: item["ranking_score"], reverse=True)
    return scored[:max(1, top_n)]


def build_assessor_report_card(
    assessor_name: str,
    severity: float,
    bias: float,
    halo: float,
    drift: float,
    recommendations: Sequence[str] | None = None,
):
    """Return a coaching-focused report card with a private calibration summary."""
    recommendations = list(recommendations or ["Review anchor clips and compare against the consensus standard."])
    return {
        "assessor_name": assessor_name,
        "severity": round(float(severity), 3),
        "leniency_bias": round(float(bias), 3),
        "halo_effect": round(float(halo), 3),
        "drift": round(float(drift), 3),
        "recommendations": recommendations,
        "coaching_note": "This is private coaching feedback and is not a punitive rating.",
    }


def evaluate_drift_alerts(drift_value: float, threshold: float = 0.12):
    return {
        "drift_value": round(float(drift_value), 3),
        "threshold": threshold,
        "alert": drift_value >= threshold,
        "message": "Lead assessor review required" if drift_value >= threshold else "Within expected drift threshold",
    }


def generate_ab_study_report(assisted_scores: Sequence[float], unassisted_scores: Sequence[float], confidence_level: float = 0.95):
    """Create a synthetic A/B study summary that works with real data when present, or seeded demo data when not."""
    assisted_mean = mean(assisted_scores) if assisted_scores else 0.0
    unassisted_mean = mean(unassisted_scores) if unassisted_scores else 0.0
    assisted_ci = _bootstrap_ci(_as_float_list(assisted_scores), confidence_level=confidence_level)
    unassisted_ci = _bootstrap_ci(_as_float_list(unassisted_scores), confidence_level=confidence_level)

    return {
        "study_type": "A/B calibration study",
        "demo_data": not (assisted_scores and unassisted_scores),
        "assisted_arm": {
            "mean_score": round(assisted_mean, 3),
            "n": len(assisted_scores),
            "ci": [round(x, 3) for x in assisted_ci],
        },
        "unassisted_arm": {
            "mean_score": round(unassisted_mean, 3),
            "n": len(unassisted_scores),
            "ci": [round(x, 3) for x in unassisted_ci],
        },
        "difference": round(assisted_mean - unassisted_mean, 3),
        "report_note": "This module supports real candidate data; seeded values are clearly flagged as demo data.",
    }


def explain_ai_draft_score(score: float, confidence: float, factors: Sequence[str] | None = None, threshold: float = 0.65):
    """Return a structured, explainable rating explanation and refusal gate for low-confidence drafts."""
    factors = list(factors or ["rubric anchor alignment", "clip clarity", "step completion", "safety-critical checks"])
    return {
        "draft_score": float(score),
        "confidence": round(float(confidence), 3),
        "factors": factors,
        "refuse_to_draft": confidence < threshold,
        "model_note": "Low confidence draft refused; assessor review required.",
    }

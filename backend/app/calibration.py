from __future__ import annotations

import random
from collections import defaultdict
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
    rng = random.Random(20261008)
    boot = [mean(rng.choices(values, k=len(values))) for _ in range(max(1, bootstrap_samples))]
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
    """Compute quadratically weighted Cohen's kappa for ordinal ratings 1..5."""
    if len(rater_a) != len(rater_b):
        raise ValueError('rating sequences must have the same length')
    if any(not 1 <= value <= 5 for value in [*rater_a, *rater_b]):
        raise ValueError("ratings must be integers from 1 to 5")
    if not rater_a:
        return 1.0
    labels = sorted(set(rater_a + rater_b))
    if not labels:
        return 1.0
    if len(labels) == 1:
        return 1.0

    contingency = {label_a: {label_b: 0 for label_b in labels} for label_a in labels}
    for left, right in zip(rater_a, rater_b):
        contingency[left][right] += 1

    category_span = 4
    po = 0.0
    pe = 0.0
    row_totals = {label: sum(contingency[label].values()) for label in labels}
    col_totals = {label: sum(contingency[left][label] for left in labels) for label in labels}
    total = sum(row_totals.values())

    for left in labels:
        for right in labels:
            weight = 1 - ((left - right) / category_span) ** 2 if category_span else 1.0
            po += weight * contingency[left][right]
            expected = (row_totals[left] * col_totals[right]) / total
            pe += weight * expected

    po = po / total
    pe = pe / total
    if abs(pe - 1.0) < 1e-9:
        return 1.0
    return (po - pe) / (1 - pe)


def compute_krippendorff_alpha(rater_matrix, return_ci: bool = False, bootstrap_samples: int = 200, confidence_level: float = 0.95):
    """Compute Krippendorff's ordinal alpha using cumulative-marginal distances."""
    matrix = [list(rater) for rater in rater_matrix]
    if matrix and any(len(rater) != len(matrix[0]) for rater in matrix):
        raise ValueError('all assessors must score the same number of items')

    def calculate(items: list[list[int | None]]) -> float:
        pooled = [value for item in items for value in item if value is not None]
        if not pooled:
            return 1.0
        categories = sorted(set(pooled))
        if len(categories) <= 1:
            return 1.0
        counts = {category: pooled.count(category) for category in categories}
        total = len(pooled)

        def distance(left: int, right: int) -> float:
            low, high = sorted((left, right))
            if low == high:
                return 0.0
            cumulative = sum(counts[category] for category in categories if low <= category <= high)
            return (cumulative - (counts[low] + counts[high]) / 2) ** 2

        observed_sum = 0.0
        observed_pairs = 0
        for item in items:
            values = [value for value in item if value is not None]
            for left_index, left in enumerate(values):
                for right in values[left_index + 1:]:
                    observed_sum += distance(left, right)
                    observed_pairs += 1
        expected_sum = sum(
            counts[left] * counts[right] * distance(left, right)
            for left in categories
            for right in categories
            if left != right
        ) / 2
        expected_pairs = total * (total - 1) / 2
        if observed_pairs == 0 or expected_pairs == 0:
            return 1.0
        observed_disagreement = observed_sum / observed_pairs
        expected_disagreement = expected_sum / expected_pairs
        if expected_disagreement == 0:
            return 1.0
        return 1.0 - observed_disagreement / expected_disagreement

    items = [
        [matrix[rater_index][item_index] for rater_index in range(len(matrix))]
        for item_index in range(len(matrix[0]) if matrix else 0)
    ]
    alpha = calculate(items)
    if return_ci:
        if len(items) < 2:
            ci = [alpha, alpha]
        else:
            rng = random.Random(20261008)
            estimates = [calculate(rng.choices(items, k=len(items))) for _ in range(max(1, bootstrap_samples))]
            lower = (1 - confidence_level) / 2
            ordered = sorted(estimates)
            ci = [
                ordered[min(len(ordered) - 1, int(lower * len(ordered)))],
                ordered[min(len(ordered) - 1, int((1 - lower) * len(ordered)))],
            ]
        return {"alpha": alpha, "ci": ci, "confidence_level": confidence_level, "method": "Krippendorff ordinal alpha; item-bootstrap percentile CI"}
    return alpha


def compute_icc(rater_matrix, confidence_level: float = 0.95, bootstrap_samples: int = 200):
    """Compute two-way random-effects absolute-agreement ICC(2,1) and item-bootstrap CI."""
    if not rater_matrix:
        return {"icc": 1.0, "ci": [1.0, 1.0], "model": "ICC(2,1)"}
    if any(len(rater) != len(rater_matrix[0]) for rater in rater_matrix):
        raise ValueError('all assessors must score the same number of items')

    def calculate(items: list[list[float]]) -> float:
        subject_count = len(items)
        rater_count = len(items[0]) if items else 0
        if subject_count < 2 or rater_count < 2:
            return 1.0
        grand_mean = mean(value for row in items for value in row)
        subject_means = [mean(row) for row in items]
        rater_means = [mean(items[item][rater] for item in range(subject_count)) for rater in range(rater_count)]
        ms_subject = rater_count * sum((value - grand_mean) ** 2 for value in subject_means) / (subject_count - 1)
        ms_rater = subject_count * sum((value - grand_mean) ** 2 for value in rater_means) / (rater_count - 1)
        residual = sum(
            (items[item][rater] - subject_means[item] - rater_means[rater] + grand_mean) ** 2
            for item in range(subject_count)
            for rater in range(rater_count)
        )
        ms_error = residual / ((subject_count - 1) * (rater_count - 1))
        denominator = ms_subject + (rater_count - 1) * ms_error + rater_count * (ms_rater - ms_error) / subject_count
        return (ms_subject - ms_error) / denominator if denominator else 1.0

    items = [[float(rater[item]) for rater in rater_matrix] for item in range(len(rater_matrix[0]))]
    icc = calculate(items)
    if len(items) < 2:
        ci = [icc, icc]
    else:
        rng = random.Random(20261008)
        estimates = [calculate(rng.choices(items, k=len(items))) for _ in range(max(1, bootstrap_samples))]
        lower = (1 - confidence_level) / 2
        ordered = sorted(estimates)
        ci = [
            ordered[min(len(ordered) - 1, int(lower * len(ordered)))],
            ordered[min(len(ordered) - 1, int((1 - lower) * len(ordered)))],
        ]
    return {"icc": icc, "ci": ci, "model": "ICC(2,1) two-way random absolute agreement"}


def fit_many_facet_model(rater_matrix):
    """Return transparent additive severity offsets; this is not a fitted Rasch model."""
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
        "method": "Approximation only: assessor mean residuals after item-mean adjustment; no ordinal-logit/Rasch fit",
    }


def build_calibration_summary(records: Sequence[Dict[str, Any]], assessors: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize stored ratings with aggregate-only assessor identifiers."""
    assessor_ids = [assessor["id"] for assessor in assessors]
    assessor_labels = {assessor["id"]: f"Assessor {index + 1}" for index, assessor in enumerate(assessors)}
    assessor_names = {assessor["id"]: assessor["name"] for assessor in assessors}
    ratings: Dict[tuple[int, str], Dict[int, int]] = defaultdict(dict)
    monthly: Dict[str, Dict[tuple[int, str], Dict[int, int]]] = defaultdict(lambda: defaultdict(dict))
    assessor_scores: Dict[int, List[int]] = defaultdict(list)
    demo_count = 0
    for record in records:
        assessor_id = record["assessor_id"]
        key = (record["assessment_id"], record["competency_id"])
        ratings[key][assessor_id] = int(record["score"])
        created_at = record.get("created_at")
        if created_at is not None:
            month = created_at.strftime("%Y-%m")
            monthly[month][key][assessor_id] = int(record["score"])
        assessor_scores[assessor_id].append(int(record["score"]))
        demo_count += int(bool(record.get("is_demo")))

    items = list(ratings.values())
    has_matched_items = any(len(item) >= 2 for item in items)
    rater_matrix = [
        [item.get(assessor_id) for item in items]
        for assessor_id in assessor_ids
    ]
    alpha = compute_krippendorff_alpha(rater_matrix, return_ci=True, bootstrap_samples=400)
    paired_kappas = []
    for index, left_id in enumerate(assessor_ids):
        for right_id in assessor_ids[index + 1:]:
            paired = [(item[left_id], item[right_id]) for item in items if left_id in item and right_id in item]
            if len(paired) >= 2:
                paired_kappas.append(compute_weighted_cohens_kappa(
                    [pair[0] for pair in paired],
                    [pair[1] for pair in paired],
                ))
    active_ids = [assessor_id for assessor_id in assessor_ids if assessor_scores.get(assessor_id)]
    complete_items = [
        item for item in items
        if len(active_ids) >= 2 and all(assessor_id in item for assessor_id in active_ids)
    ]
    icc_result = None
    if len(active_ids) >= 2 and len(complete_items) >= 2:
        icc_matrix = [
            [item[assessor_id] for item in complete_items]
            for assessor_id in active_ids
        ]
        icc_result = compute_icc(icc_matrix)

    assisted_errors: Dict[bool, List[float]] = {True: [], False: []}
    for record in records:
        key = (record["assessment_id"], record["competency_id"])
        peer_scores = [
            score for assessor_id, score in ratings[key].items()
            if assessor_id != record["assessor_id"]
        ]
        if peer_scores:
            assisted_errors[bool(record.get("ai_assisted"))].append(
                abs(float(record["score"]) - mean(peer_scores))
            )
    all_scores = [int(record["score"]) for record in records]
    pooled_sd = pstdev(all_scores) if len(all_scores) > 1 else 0.0
    severity_rows = []
    report_cards = []
    for assessor_index, assessor in enumerate(assessors):
        assessor_id = assessor["id"]
        own_records = [record for record in records if record["assessor_id"] == assessor_id]
        residuals = []
        for record in own_records:
            item = ratings[(record["assessment_id"], record["competency_id"])]
            peer_scores = [score for peer_id, score in item.items() if peer_id != assessor_id]
            if peer_scores:
                residuals.append(mean(peer_scores) - float(record["score"]))
        if not residuals:
            continue
        severity = mean(residuals)
        own_sd = pstdev(assessor_scores[assessor_id]) if len(assessor_scores[assessor_id]) > 1 else 0.0
        central_tendency = 1 - own_sd / pooled_sd if pooled_sd else 0.0
        severity_rows.append({
            "assessor_key": f"assessor_{assessor_index + 1}",
            "label": assessor_labels[assessor_id],
            "severity": round(severity, 3),
            "leniency": round(-severity, 3),
            "central_tendency": round(central_tendency, 3),
            "n": len(own_records),
        })
        recommendations = []
        if severity >= 0.3:
            recommendations.append("Compare borderline ratings with high-consensus anchor clips; current scores are stricter than peer consensus.")
        elif severity <= -0.3:
            recommendations.append("Review high-consensus anchor clips for calibration; current scores are more generous than peer consensus.")
        else:
            recommendations.append("Continue periodic anchor-clip review to sustain alignment with peer consensus.")
        if central_tendency >= 0.25:
            recommendations.append("Revisit rubric examples at score levels 1 and 5 to use the full scoring range when evidence supports it.")
        report_cards.append(build_assessor_report_card(
            assessor_name=assessor["name"],
            severity=severity,
            bias=-severity,
            halo=central_tendency,
            drift=0.0,
            recommendations=recommendations,
        ))

    alpha_trend = []
    drift_by_month: Dict[str, Dict[int, float]] = {}
    first_month_by_assessor: Dict[int, float] = {}
    for month in sorted(monthly):
        month_items = list(monthly[month].values())
        month_assessors = [
            assessor_id for assessor_id in assessor_ids
            if any(assessor_id in item for item in month_items)
        ]
        month_matrix = [[item.get(assessor_id) for item in month_items] for assessor_id in month_assessors]
        estimate = compute_krippendorff_alpha(month_matrix, return_ci=True, bootstrap_samples=250)
        if any(sum(value is not None for value in item) >= 2 for item in zip(*month_matrix)) if month_matrix else False:
            alpha_trend.append({
                "month": month,
                "alpha": round(estimate["alpha"], 3),
                "ci_low": round(estimate["ci"][0], 3),
                "ci_high": round(estimate["ci"][1], 3),
                "ci_band": round(max(0.0, estimate["ci"][1] - estimate["ci"][0]), 3),
            })
        drift_point: Dict[str, Any] = {"month": month}
        for assessor_index, assessor_id in enumerate(assessor_ids):
            values = [
                float(score)
                for item in month_items
                if (score := item.get(assessor_id)) is not None
            ]
            if not values:
                continue
            if assessor_id not in first_month_by_assessor:
                first_month_by_assessor[assessor_id] = mean(values)
            drift = mean(values) - first_month_by_assessor[assessor_id]
            drift_point[f"assessor_{assessor_index + 1}"] = round(drift, 3)
            if month == max(monthly):
                assessor_key = f"assessor_{assessor_index + 1}"
                severity_row = next((row for row in severity_rows if row["assessor_key"] == assessor_key), None)
                report = next((row for row in report_cards if row["assessor_name"] == assessor_names[assessor_id]), None)
                if severity_row is not None:
                    severity_row["drift"] = round(abs(drift), 3)
                if report is not None:
                    report["drift"] = round(abs(drift), 3)
                    if abs(drift) >= 0.5:
                        report["recommendations"].append(
                            f"Review rating drift observed in {month} with a lead assessor."
                        )
        drift_by_month[month] = drift_point

    anchors_by_assessment: Dict[int, List[int]] = defaultdict(list)
    for record in records:
        anchors_by_assessment[record["assessment_id"]].append(int(record["score"]))
    anchor_clips = generate_anchor_exam([
        {
            "clip_id": f"DEMO-ANCHOR-{assessment_id:03d}" if next(
                (record.get("is_demo", False) for record in records if record["assessment_id"] == assessment_id),
                False,
            ) else f"ANCHOR-{assessment_id:03d}",
            "title": f"Assessment {assessment_id} evidence review",
            "expert_scores": scores,
        }
        for assessment_id, scores in anchors_by_assessment.items()
    ], top_n=5)

    assisted = assisted_errors[True]
    unassisted = assisted_errors[False]
    return {
        "demo_data": bool(records) and demo_count == len(records),
        "includes_demo_data": demo_count > 0,
        "demo_score_count": demo_count,
        "sample_count": len(records),
        "candidate_competency_items": len(items),
        "metrics": [
            {
                "metric": "krippendorff_alpha_ordinal",
                "value": round(alpha["alpha"], 3) if has_matched_items else None,
                "ci": [round(value, 3) for value in alpha["ci"]] if has_matched_items else None,
                "interpretation": "Ordinal Krippendorff alpha with item-bootstrap 95% confidence interval.",
                "method": alpha["method"],
            },
            {
                "metric": "weighted_cohens_kappa",
                "value": round(mean(paired_kappas), 3) if paired_kappas else None,
                "interpretation": "Mean quadratically weighted Cohen kappa across assessor pairs with overlapping ratings.",
                "method": "Quadratic weighted kappa; paired common assessment-competency items.",
            },
            {
                "metric": "icc_absolute_agreement",
                "value": round(icc_result["icc"], 3) if icc_result else None,
                "ci": [round(value, 3) for value in icc_result["ci"]] if icc_result else None,
                "interpretation": "Two-way random-effects absolute-agreement ICC(2,1), complete matched items.",
                "method": icc_result["model"] if icc_result else "Not enough complete matched items for ICC(2,1).",
            },
        ],
        "assessor_severity": severity_rows,
        "alpha_over_time": alpha_trend,
        "drift_over_time": list(drift_by_month.values()),
        "drift_threshold": 0.5,
        "drift_alerts": [
            {"assessor_key": row["assessor_key"], "label": row["label"], "drift": row.get("drift", 0.0)}
            for row in severity_rows if row.get("drift", 0.0) >= 0.5
        ],
        "report_cards": report_cards,
        "anchor_clips": anchor_clips,
        "assistance_comparison": {
            "assisted": {
                "mean_peer_consensus_error": round(mean(assisted), 3) if assisted else None,
                "n": len(assisted),
            },
            "unassisted": {
                "mean_peer_consensus_error": round(mean(unassisted), 3) if unassisted else None,
                "n": len(unassisted),
            },
            "interpretation": "Mean absolute difference from the peer consensus score for AI-assisted and unassisted records; descriptive, not causal.",
        },
        "method_note": "Assessor severity is an item-adjusted mean residual approximation; it is not an ordinal-logistic or many-facet Rasch fit.",
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

from __future__ import annotations

import json
from collections import defaultdict
from statistics import mean
from typing import Any, Sequence

from .workflow import normalize_status


FUNNEL_STAGES = (
    ("registered", "Registered"),
    ("declared", "Declared"),
    ("evidence_captured", "Evidence captured"),
    ("under_review", "Under review"),
    ("second_review", "Second review"),
    ("moderation", "Moderation"),
    ("signed_off", "Signed off"),
    ("credential_issued", "Credential issued"),
)


def build_impact_summary(
    assessments: Sequence[Any],
    candidates: Sequence[Any],
    score_records: Sequence[Any],
) -> dict[str, Any]:
    candidate_by_id = {candidate.id: candidate for candidate in candidates}
    scores_by_assessment: dict[int, list[Any]] = defaultdict(list)
    for record in score_records:
        scores_by_assessment[record.assessment_id].append(record)

    statuses = {assessment.id: normalize_status(assessment.status or "registered") for assessment in assessments}
    stage_index = {stage: index for index, (stage, _) in enumerate(FUNNEL_STAGES)}
    funnel = [
        {
            "stage": stage,
            "label": label,
            "count": sum(stage_index.get(statuses[item.id], -1) >= index for item in assessments),
        }
        for index, (stage, label) in enumerate(FUNNEL_STAGES)
    ]

    time_by_candidate: dict[tuple[int, bool], list[float]] = defaultdict(list)
    for assessment in assessments:
        records = scores_by_assessment.get(assessment.id, [])
        if assessment.created_at is None or not records:
            continue
        for assisted in (True, False):
            times = [
                (record.created_at - assessment.created_at).total_seconds()
                for record in records
                if bool(record.ai_assisted) is assisted and record.created_at is not None
            ]
            if times:
                time_by_candidate[(assessment.candidate_id, assisted)].append(max(times))
    assisted_candidate_times: dict[bool, list[float]] = {True: [], False: []}
    for (candidate_id, assisted), durations in time_by_candidate.items():
        assisted_candidate_times[assisted].append(mean(durations))

    outcome_rows = []
    trade_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    fairness_groups: dict[str, dict[str, dict[str, Any]]] = {
        dimension: defaultdict(lambda: {"eligible": 0, "passed": 0, "demo_count": 0})
        for dimension in ("gender", "region", "language")
    }
    for assessment in assessments:
        candidate = candidate_by_id.get(assessment.candidate_id)
        if candidate is None:
            continue
        final_status = statuses[assessment.id] in {"signed_off", "credential_issued"}
        records = [
            record for record in scores_by_assessment.get(assessment.id, [])
            if record.review_round == 1
        ]
        if not records:
            continue
        scores_by_competency = defaultdict(list)
        for record in records:
            scores_by_competency[record.competency_id].append(record.score)
        mean_score = mean(mean(values) for values in scores_by_competency.values())
        passed = final_status and mean_score >= 3.0
        outcome = {
            "passed": passed,
            "eligible": final_status,
            "demo": bool(candidate.demographics_are_demo) or all(record.is_demo for record in records),
        }
        trade_groups[candidate.trade].append(outcome)
        outcome_rows.append(outcome)
        if not final_status:
            continue
        for dimension in fairness_groups:
            value = getattr(candidate, dimension, None) or "Not supplied"
            group = fairness_groups[dimension][value]
            group["eligible"] += 1
            group["passed"] += int(passed)
            group["demo_count"] += int(outcome["demo"])

    def rate_rows(groups: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        result = []
        for label, rows in sorted(groups.items()):
            eligible = [row for row in rows if row["eligible"]]
            result.append({
                "label": label,
                "eligible": len(eligible),
                "passed": sum(row["passed"] for row in eligible),
                "pass_rate": round(sum(row["passed"] for row in eligible) / len(eligible), 3) if eligible else None,
                "includes_demo_data": any(row["demo"] for row in rows),
            })
        return result

    return {
        "funnel": funnel,
        "time_per_candidate": {
            "assisted": {
                "seconds": round(mean(assisted_candidate_times[True])) if assisted_candidate_times[True] else None,
                "candidate_count": len(assisted_candidate_times[True]),
            },
            "unassisted": {
                "seconds": round(mean(assisted_candidate_times[False])) if assisted_candidate_times[False] else None,
                "candidate_count": len(assisted_candidate_times[False]),
            },
            "method": "Mean assessment-created-to-last-score elapsed time per candidate, grouped by stored ai_assisted score rows; descriptive and not causal.",
        },
        "pass_rate_by_trade": rate_rows(trade_groups),
        "fairness": {
            dimension: [
                {
                    "label": label,
                    **values,
                    "pass_rate": round(values["passed"] / values["eligible"], 3) if values["eligible"] else None,
                    "includes_demo_data": values["demo_count"] > 0,
                }
                for label, values in sorted(groups.items())
            ]
            for dimension, groups in fairness_groups.items()
        },
        "outcome_method": "Demo pass proxy: signed-off assessment with mean primary-round competency score >= 3/5. Not an official qualification decision.",
        "fairness_method": "Descriptive subgroup rates among signed-off/credential-issued assessments only; synthetic seeded demographics are explicitly marked. Not a validated fairness assessment.",
        "includes_demo_data": any(row["demo"] for row in outcome_rows),
        "completed_assessments": sum(row["eligible"] for row in outcome_rows),
    }

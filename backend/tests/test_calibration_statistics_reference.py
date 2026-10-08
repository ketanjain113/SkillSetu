from app.calibration import (
    build_calibration_summary,
    compute_icc,
    compute_krippendorff_alpha,
    compute_weighted_cohens_kappa,
)
from app import main
from types import SimpleNamespace
import copy


def test_ordinal_alpha_matches_hand_calculated_reference():
    # Three matched items: two exact matches and one adjacent disagreement.
    ratings = [[1, 2, 3], [1, 2, 2]]
    assert abs(compute_krippendorff_alpha(ratings) - (7 / 9)) < 1e-12


def test_quadratic_weighted_kappa_matches_hand_calculated_reference():
    first = [1, 2, 3, 4, 5]
    second = [1, 2, 2, 4, 5]
    assert abs(compute_weighted_cohens_kappa(first, second) - (20 / 21)) < 1e-12


def test_icc_matches_two_way_random_single_measure_reference():
    ratings = [[1, 2, 3, 4], [2, 4, 5, 4]]
    assert abs(compute_icc(ratings)["icc"] - (28 / 55)) < 1e-12


def test_summary_marks_approximation_and_provides_stable_alpha_interval():
    from datetime import datetime

    rows = [
        {
            "assessment_id": item,
            "competency_id": "c1",
            "assessor_id": assessor,
            "score": score,
            "ai_assisted": False,
            "is_demo": False,
            "created_at": datetime(2025, 1, item),
        }
        for item, scores in enumerate(([1, 1], [2, 2], [3, 2]), start=1)
        for assessor, score in enumerate(scores, start=1)
    ]
    summary = build_calibration_summary(rows, [{"id": 1, "name": "Assessor 1"}, {"id": 2, "name": "Assessor 2"}])
    alpha_metric = next(metric for metric in summary["metrics"] if metric["metric"] == "krippendorff_alpha_ordinal")
    assert "approximation" in summary["method_note"]
    assert alpha_metric["ci"][0] <= alpha_metric["value"] <= alpha_metric["ci"][1]
    assert len(summary["alpha_over_time"]) == 1


def test_assessor_calibration_response_hides_other_private_report_cards(monkeypatch):
    from datetime import datetime

    records = [
        {
            "assessment_id": item,
            "competency_id": "c1",
            "assessor_id": assessor,
            "score": score,
            "ai_assisted": False,
            "is_demo": True,
            "created_at": datetime(2025, 1, item),
        }
        for item, scores in enumerate(([2, 4], [3, 5], [4, 5]), start=1)
        for assessor, score in enumerate(scores, start=1)
    ]
    assessors = [{"id": 1, "name": "Assessor One"}, {"id": 2, "name": "Assessor Two"}]
    summary = build_calibration_summary(records, assessors)
    monkeypatch.setattr(main, "load_calibration_data", lambda _: (copy.deepcopy(summary), []))

    assessor_response = main.calibration(None, SimpleNamespace(role="assessor", full_name="Assessor One"))
    admin_response = main.calibration(None, SimpleNamespace(role="admin", full_name="Administrator"))

    assert [card["assessor_name"] for card in assessor_response["report_cards"]] == ["Assessor One"]
    assert len(admin_response["report_cards"]) == 2
    assert assessor_response["viewer"]["report_is_private"] is True

from app.calibration import (
    build_assessor_report_card,
    compute_icc,
    fit_many_facet_model,
    generate_anchor_exam,
)


def test_icc_is_one_for_identical_ratings():
    ratings = [
        [3, 4, 5, 3],
        [3, 4, 5, 3],
        [3, 4, 5, 3],
    ]
    result = compute_icc(ratings)
    assert result["icc"] == 1.0
    assert result["ci"][0] <= 1.0


def test_many_facet_model_returns_severity_and_ability():
    assessors = [
        [3, 4, 5],
        [2, 3, 4],
        [1, 2, 3],
    ]
    model = fit_many_facet_model(assessors)
    assert "assessor_severity" in model
    assert "candidate_ability" in model
    assert "item_difficulty" in model
    assert len(model["assessor_severity"]) == 3


def test_anchor_exam_selects_top_consensus_clip():
    clips = [
        {"clip_id": "A", "expert_scores": [4, 5, 5]},
        {"clip_id": "B", "expert_scores": [2, 3, 2]},
        {"clip_id": "C", "expert_scores": [4, 4, 5]},
    ]
    exam = generate_anchor_exam(clips)
    assert exam[0]["clip_id"] == "A"


def test_assessor_report_card_has_coaching_fields():
    report = build_assessor_report_card(
        assessor_name="Assessor A",
        severity=0.12,
        bias=0.08,
        halo=0.05,
        drift=0.14,
        recommendations=["Review anchor clips"],
    )
    assert report["assessor_name"] == "Assessor A"
    assert "severity" in report
    assert "drift" in report
    assert "recommendations" in report

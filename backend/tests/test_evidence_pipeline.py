from app.ai_services import evaluate_evidence_sufficiency


def test_evidence_sufficiency_missing_steps_and_blur_are_flagged():
    result = evaluate_evidence_sufficiency(
        required_steps=['check risk', 'wear ppe', 'test continuity'],
        captured_steps=['check risk'],
        brightness=40,
        blur=0.9,
        is_blurry=True,
    )
    assert result['sufficient'] is False
    assert len(result['flags']) >= 2
    assert 're-record' in ' '.join(result['flags']).lower()

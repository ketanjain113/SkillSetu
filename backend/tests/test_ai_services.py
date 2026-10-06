from app.ai_services import (
    EvidenceAIService,
    create_ai_service,
    evaluate_evidence_sufficiency,
    normalize_ai_settings,
)


def test_default_ai_mode_uses_mock_service():
    service = create_ai_service()
    assert isinstance(service, EvidenceAIService)
    assert service.mode == 'mock'


def test_mock_service_generates_step_tags_and_quality_signal():
    service = create_ai_service(mode='mock')
    result = service.analyze_steps([
        'check risk',
        'wear ppe',
        'test continuity',
    ])
    assert len(result['steps']) >= 3
    assert result['steps'][0]['label'] in {'AI suggested', 'manual-review'}


def test_evidence_sufficiency_flags_low_quality_and_missing_steps():
    result = evaluate_evidence_sufficiency(
        required_steps=['check risk', 'wear ppe', 'test continuity'],
        captured_steps=['check risk'],
        brightness=35,
        blur=0.9,
        is_blurry=True,
    )
    assert result['sufficient'] is False
    assert 'insufficient evidence' in ' '.join(result['flags']).lower()
    assert 're-record' in ' '.join(result['flags']).lower() or 'missing' in ' '.join(result['flags']).lower()


def test_normalize_ai_settings_reads_env_flag():
    config = normalize_ai_settings({'AI_MODE': 'real'})
    assert config['mode'] == 'real'

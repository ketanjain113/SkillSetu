from app.trade_packs import DEFAULT_TRADE_PACKS, evaluate_pack_outcome, rank_qualification_packs, validate_trade_pack


def test_default_pack_set_has_required_trades_and_schema():
    required_ids = {
        'domestic-electrician',
        'plumber-general',
        'mason',
        'tailor-sewing-machine-operator',
        'domestic-data-entry-operator',
    }
    ids = {pack['pack_id'] for pack in DEFAULT_TRADE_PACKS}
    assert required_ids.issubset(ids)

    for pack in DEFAULT_TRADE_PACKS:
        validated = validate_trade_pack(pack)
        assert validated['valid'] is True, validated['errors']
        assert isinstance(pack['nos'], list) and len(pack['nos']) >= 5
        assert isinstance(pack['checklist'], list) and len(pack['checklist']) >= 6
        assert pack['pass_threshold'] >= 0.6


def test_safety_cap_blocks_competence_when_required_step_fails():
    result = evaluate_pack_outcome(
        average_score=4.8,
        safety_critical_passed=False,
        safety_critical_steps=['Lockout/tagout verified'],
    )
    assert result['overall_status'] == 'Not yet competent'
    assert result['safety_cap_applied'] is True


def test_declaration_match_uses_query_relevance_over_pack_length():
    matches = rank_qualification_packs(
        "I checked the switchboard, tested continuity, and completed a household lighting installation.",
        DEFAULT_TRADE_PACKS,
    )

    assert matches[0]["pack_id"] == "domestic-electrician"

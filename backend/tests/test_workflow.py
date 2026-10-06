import pytest

from app.workflow import VALID_TRANSITIONS, can_transition, normalize_status


def test_workflow_accepts_known_statuses_and_transitions():
    assert normalize_status('Declared') == 'declared'
    assert can_transition('declared', 'evidence_captured') is True
    assert can_transition('evidence_captured', 'under_review') is True
    assert can_transition('declared', 'signed_off') is False


def test_workflow_rejects_invalid_transition():
    with pytest.raises(ValueError):
        can_transition('declared', 'signed_off', strict=True)


def test_transition_map_contains_all_required_states():
    required = {'registered', 'declared', 'evidence_captured', 'under_review', 'second_review', 'moderation', 'signed_off', 'credential_issued', 'appeal'}
    assert required.issubset(set(VALID_TRANSITIONS.keys()))

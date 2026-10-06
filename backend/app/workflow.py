from __future__ import annotations

from typing import Dict, List

VALID_TRANSITIONS: Dict[str, List[str]] = {
    'registered': ['declared'],
    'declared': ['evidence_captured', 'under_review'],
    'evidence_captured': ['under_review', 'second_review'],
    'under_review': ['second_review', 'moderation', 'signed_off'],
    'second_review': ['moderation', 'signed_off'],
    'moderation': ['signed_off', 'appeal'],
    'signed_off': ['credential_issued', 'appeal'],
    'credential_issued': ['appeal'],
    'appeal': ['registered', 'declared', 'under_review'],
}

KNOWN_STATUS_VALUES = set(VALID_TRANSITIONS.keys())


def normalize_status(value: str) -> str:
    normalized = str(value or '').strip().lower().replace(' ', '_').replace('-', '_')
    aliases = {
        'draft': 'registered',
        'ready_for_review': 'under_review',
        'review': 'under_review',
        'second_review_flagged': 'second_review',
        'moderator_review': 'moderation',
        'approved': 'signed_off',
        'certified': 'credential_issued',
    }
    return aliases.get(normalized, normalized)


def can_transition(current: str, next_state: str, strict: bool = False) -> bool:
    current_norm = normalize_status(current)
    next_norm = normalize_status(next_state)
    if current_norm not in VALID_TRANSITIONS:
        if strict:
            raise ValueError(f'Unknown current status: {current}')
        return False
    if next_norm not in VALID_TRANSITIONS and strict:
        raise ValueError(f'Unknown next status: {next_state}')
    if next_norm == current_norm:
        return True
    allowed = VALID_TRANSITIONS.get(current_norm, [])
    if next_norm in allowed:
        return True
    if strict:
        raise ValueError(f'Invalid transition from {current_norm} to {next_norm}')
    return False


def status_tracker() -> List[str]:
    return ['registered', 'declared', 'evidence_captured', 'under_review', 'second_review', 'moderation', 'signed_off', 'credential_issued', 'appeal']

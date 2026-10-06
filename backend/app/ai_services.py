from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


class BaseAIService:
    def __init__(self, mode: str = 'mock') -> None:
        self.mode = mode

    def analyze_steps(self, steps: List[str], **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError

    def score_quality(self, brightness: Optional[float] = None, blur: Optional[float] = None, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError


class MockAIService(BaseAIService):
    def analyze_steps(self, steps: List[str], **kwargs: Any) -> Dict[str, Any]:
        tagged_steps = []
        for index, step in enumerate(steps):
            tagged_steps.append({
                'step': step,
                'label': 'AI suggested' if index % 2 == 0 else 'manual-review',
                'confidence': 0.8 if index % 2 == 0 else 0.55,
                'start': index * 1.5,
                'end': index * 1.5 + 1.2,
            })
        return {'steps': tagged_steps, 'source': 'mock', 'note': 'AI suggested output is demo-only and requires assessor review.'}

    def score_quality(self, brightness: Optional[float] = None, blur: Optional[float] = None, **kwargs: Any) -> Dict[str, Any]:
        brightness_value = brightness if brightness is not None else 120.0
        blur_value = blur if blur is not None else 0.25
        return {
            'brightness': brightness_value,
            'blur': blur_value,
            'quality_flag': 'Good light' if brightness_value > 60 and brightness_value < 180 and blur_value < 0.5 else 'Needs retake',
            'source': 'mock',
        }


class EvidenceAIService(MockAIService):
    def __init__(self, mode: str = 'mock') -> None:
        super().__init__(mode=mode)

    def analyze_steps(self, steps: List[str], **kwargs: Any) -> Dict[str, Any]:
        if self.mode == 'real':
            return {
                'steps': [
                    {
                        'step': step,
                        'label': 'AI tagged',
                        'confidence': 0.88,
                        'start': idx * 2.0,
                        'end': idx * 2.0 + 1.8,
                        'evidence_frame': f'thumb-{idx}.jpg',
                    }
                    for idx, step in enumerate(steps)
                ],
                'source': 'real',
                'note': 'Real mode is a pluggable interface placeholder for MediaPipe-style detection.',
            }
        return super().analyze_steps(steps, **kwargs)

    def score_quality(self, brightness: Optional[float] = None, blur: Optional[float] = None, **kwargs: Any) -> Dict[str, Any]:
        if self.mode == 'real':
            return {
                'brightness': brightness if brightness is not None else 110.0,
                'blur': blur if blur is not None else 0.32,
                'quality_flag': 'sufficient' if (brightness or 110.0) > 60 and (blur or 0.32) < 0.6 else 'insufficient evidence',
                'source': 'real',
            }
        return super().score_quality(brightness, blur, **kwargs)


def normalize_ai_settings(env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    env = env or os.environ
    mode = str(env.get('AI_MODE', 'mock')).strip().lower()
    return {'mode': mode if mode in {'mock', 'real'} else 'mock'}


def create_ai_service(mode: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> BaseAIService:
    settings = normalize_ai_settings(env)
    resolved_mode = (mode or settings['mode'])
    return EvidenceAIService(mode=resolved_mode)


def evaluate_evidence_sufficiency(
    required_steps: List[str],
    captured_steps: List[str],
    brightness: Optional[float] = None,
    blur: Optional[float] = None,
    is_blurry: bool = False,
) -> Dict[str, Any]:
    missing = [step for step in required_steps if step.lower() not in [item.lower() for item in captured_steps]]
    low_light = brightness is not None and brightness < 50
    high_blur = (blur is not None and blur > 0.7) or is_blurry
    flags: List[str] = []
    if missing:
        flags.append(f"Missing required steps: {', '.join(missing[:3])}")
    if low_light:
        flags.append('Low light detected; re-record in brighter conditions.')
    if high_blur:
        flags.append('Insufficient evidence: clip is blurry or low-quality; re-record the unclear steps.')
    if not missing and not low_light and not high_blur:
        flags.append('Evidence sufficient for assessor review.')
    return {
        'sufficient': not missing and not low_light and not high_blur,
        'missing_steps': missing,
        'flags': flags,
    }

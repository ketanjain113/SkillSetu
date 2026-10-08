import requests

BASE_URL = 'http://127.0.0.1:8000'


def test_worker_assessor_certificate_flow():
    worker = requests.post(
        f'{BASE_URL}/api/auth/login',
        json={'username': 'worker1', 'password': 'worker123'},
        timeout=10,
    )
    assert worker.status_code == 200
    worker_token = worker.json()['access_token']

    declaration = requests.post(
        f'{BASE_URL}/api/declare',
        json={'text': 'I checked the switchboard, tested continuity, and completed a household lighting installation.'},
        headers={'Authorization': f'Bearer {worker_token}'},
        timeout=10,
    )
    assert declaration.status_code == 200
    matches = declaration.json()['matches']
    assert len(matches) >= 1

    assessment = requests.post(
        f'{BASE_URL}/api/assessments',
        json={
            'text': 'I checked the switchboard, tested continuity, and completed a household lighting installation.',
            'matches': matches,
        },
        headers={'Authorization': f'Bearer {worker_token}'},
        timeout=10,
    )
    assert assessment.status_code == 200
    assessment_id = assessment.json()['id']

    assessor = requests.post(
        f'{BASE_URL}/api/auth/login',
        json={'username': 'assessor1', 'password': 'assessor123'},
        timeout=10,
    )
    assert assessor.status_code == 200
    assessor_token = assessor.json()['access_token']
    competencies = requests.get(f'{BASE_URL}/api/competencies', timeout=10).json()['competencies']
    second_review_assigned = False
    for competency in competencies:
        response = requests.post(
            f'{BASE_URL}/api/score',
            json={
                'assessment_id': assessment_id,
                'competency_id': competency['id'],
                'score': 4,
                'explanation': 'Evidence was assessed against the competency rubric.',
            },
            headers={'Authorization': f'Bearer {assessor_token}'},
            timeout=10,
        )
        assert response.status_code == 200, response.text
        second_review_assigned = second_review_assigned or response.json()['second_review_assigned']

    if second_review_assigned:
        second_assessor = requests.post(
            f'{BASE_URL}/api/auth/login',
            json={'username': 'assessor2', 'password': 'assessor123'},
            timeout=10,
        )
        assert second_assessor.status_code == 200
        second_token = second_assessor.json()['access_token']
        for competency in competencies:
            response = requests.post(
                f'{BASE_URL}/api/score',
                json={
                    'assessment_id': assessment_id,
                    'competency_id': competency['id'],
                    'score': 4,
                    'explanation': 'Independent second review against the competency rubric.',
                },
                headers={'Authorization': f'Bearer {second_token}'},
                timeout=10,
            )
            assert response.status_code == 200, response.text

    cert = requests.get(
        f'{BASE_URL}/api/certificate/{assessment_id}',
        headers={'Authorization': f'Bearer {assessor_token}'},
        timeout=10,
    )
    assert cert.status_code == 200
    payload = cert.json()
    assert payload['trade'] == 'Domestic Electrician'
    assert payload['assessor_signoff'] is True

from app.calibration import compute_krippendorff_alpha, compute_weighted_cohens_kappa
from app.match import hash_chain


def test_weighted_kappa_perfect_agreement():
    a = [1, 2, 3, 4, 5]
    b = [1, 2, 3, 4, 5]
    assert compute_weighted_cohens_kappa(a, b) == 1.0


def test_krippendorff_alpha_perfect_agreement():
    assessors = [
        [1, 2, 3, 4],
        [1, 2, 3, 4],
        [1, 2, 3, 4],
    ]
    alpha = compute_krippendorff_alpha(assessors)
    assert abs(alpha - 1.0) < 1e-9


def test_hash_chain_is_stable_and_reproducible():
    values = ["a", "b", "c"]
    chained = hash_chain(values)
    assert len(chained) == 64
    assert chained == hash_chain(values)

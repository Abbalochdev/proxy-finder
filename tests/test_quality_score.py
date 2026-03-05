from proxy_finder.core.validator import ProxyValidator


def test_quality_score_prioritizes_faster_valid_elite_proxy():
    validator = ProxyValidator()
    fast_elite = validator.calculate_quality_score('valid', 0.5, 'elite')
    low_quality_proxy = validator.calculate_quality_score('unvalidated', 8.0, 'transparent')
    assert fast_elite > low_quality_proxy


def test_quality_score_treats_invalid_speed_sentinel_and_missing_speed_equally():
    validator = ProxyValidator()
    very_slow = validator.calculate_quality_score('valid', 999.99, 'anonymous')
    missing_speed = validator.calculate_quality_score('valid', None, 'anonymous')
    assert very_slow == missing_speed
    assert 0 <= very_slow <= 100


def test_quality_score_rewards_anonymity_for_same_speed_and_status():
    validator = ProxyValidator()
    elite = validator.calculate_quality_score('valid', 2.0, 'elite')
    transparent = validator.calculate_quality_score('valid', 2.0, 'transparent')
    assert elite > transparent

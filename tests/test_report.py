from decimal import Decimal

from billups.report import cramers_v, smallest_circular_interval


def test_cramers_v_independent_and_associated_examples():
    """Cramer's V distinguishes independent and associated tables."""
    independent = [
        {"city_id": city, "category": category, "attempt_count": 10}
        for city in [1, 2]
        for category in ["A", "B"]
    ]
    associated = [
        {"city_id": 1, "category": "A", "attempt_count": 20},
        {"city_id": 1, "category": "B", "attempt_count": 0},
        {"city_id": 2, "category": "A", "attempt_count": 0},
        {"city_id": 2, "category": "B", "attempt_count": 20},
    ]
    assert cramers_v(independent) == 0
    assert cramers_v(associated) == 1


def test_circular_interval_can_cross_midnight():
    """The opening interval supports demand spanning midnight."""
    result = smallest_circular_interval({23: Decimal(50), 0: Decimal(40), 12: Decimal(10)})
    assert result["start_hour"] == 23
    assert result["end_hour"] == 1
    assert result["hours"] == 2
    assert result["share"] == 0.9

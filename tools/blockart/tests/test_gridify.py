from tools.blockart.gridify import coverage_to_char


def test_coverage_to_char_thresholds():
    assert coverage_to_char(0.95) == "█"
    assert coverage_to_char(0.85) == "█"
    assert coverage_to_char(0.70) == "▓"
    assert coverage_to_char(0.60) == "▓"
    assert coverage_to_char(0.40) == "▒"
    assert coverage_to_char(0.35) == "▒"
    assert coverage_to_char(0.20) == "░"
    assert coverage_to_char(0.12) == "░"
    assert coverage_to_char(0.05) is None
    assert coverage_to_char(0.0) is None

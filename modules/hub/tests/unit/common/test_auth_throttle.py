from app.common.auth_throttle import caller_address, masked_address


def test_the_caller_is_the_address_the_platform_appended():
    # Everything before the last entry is whatever the client sent; trusting it would let a caller dodge its lockout.
    assert caller_address("1.2.3.4, 203.0.113.7", "10.0.0.1") == "203.0.113.7"
    assert caller_address(None, "10.0.0.1") == "10.0.0.1"
    assert caller_address(" , ", None) == "unknown"


def test_a_notice_carries_only_part_of_an_address():
    assert masked_address("203.0.113.7") == "203.0.113.x"
    assert masked_address("2001:db8:85a3:8d3:1319:8a2e:370:7348") == "2001:db8:85a3:…"
    assert masked_address("unknown") == "unknown"

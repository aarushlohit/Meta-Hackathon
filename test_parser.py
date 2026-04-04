from parser import parse_message_to_action


def test_valid_messages_parse_correctly():
    p1 = parse_message_to_action("investigate alert_1")
    p2 = parse_message_to_action("block 192.168.1.1")
    p3 = parse_message_to_action("resolve alert_2")

    assert p1.is_valid is True
    assert p1.verb == "investigate"
    assert p1.target == "alert_1"

    assert p2.is_valid is True
    assert p2.verb == "block"
    assert p2.target == "192.168.1.1"

    assert p3.is_valid is True
    assert p3.verb == "resolve"
    assert p3.target == "alert_2"


def test_invalid_messages_safe_fallback():
    parsed = parse_message_to_action("do something dangerous")
    assert parsed.is_valid is False
    assert parsed.verb == "invalid"


def test_empty_input_no_crash():
    parsed_1 = parse_message_to_action("")
    parsed_2 = parse_message_to_action("   ")

    assert parsed_1.is_valid is False
    assert parsed_2.is_valid is False


def test_random_text_safe_fallback():
    samples = [
        "@@@",
        "hello world",
        "DROP TABLE users",
        "\\x00\\x01",
        "12345",
    ]
    for sample in samples:
        parsed = parse_message_to_action(sample)
        assert parsed.is_valid is False
        assert parsed.verb == "invalid"


def test_non_string_input_safe_fallback():
    parsed_none = parse_message_to_action(None)
    parsed_int = parse_message_to_action(123)

    assert parsed_none.is_valid is False
    assert parsed_int.is_valid is False

from textj.accuracy import character_error_rate, levenshtein_distance, normalize_metric_text


def test_levenshtein_distance() -> None:
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("한글", "한굴") == 1


def test_character_error_rate() -> None:
    assert character_error_rate("abcd", "abxd") == 0.25
    assert character_error_rate("", "") == 0.0
    assert character_error_rate("", "x") == 1.0


def test_metric_normalization_handles_newlines_and_trailing_space() -> None:
    assert normalize_metric_text(" hello  \r\nworld \r\n") == "hello\nworld"

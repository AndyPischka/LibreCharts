"""Tests of consistent rounding (M16)."""

from __future__ import annotations

import pytest

from librecharts.core.model import Format
from librecharts.core.rounding import consistent, consistent_shares


def test_integral_values_sum_to_the_integral_total() -> None:
    labels = consistent([1.0, 1.0, 1.0], 3.0, Format())
    assert labels == ("1", "1", "1")


def test_thirds_round_to_a_sum_of_one_hundred() -> None:
    labels = consistent([100.0, 100.0, 100.0], 300.0, Format())
    assert labels == ("100", "100", "100")
    shares = consistent_shares([100.0, 100.0, 100.0], 300.0, Format())
    assert shares == ("33.4%", "33.3%", "33.3%")  # a tie carries the remainder to the first


def test_shares_sum_to_exactly_one_hundred_percent() -> None:
    shares = consistent_shares([1.0, 1.0, 1.0], 3.0, Format())
    assert sum(float(s.rstrip("%")) for s in shares if s is not None) == pytest.approx(100.0)


def test_shares_with_fixed_decimals_sum_to_one_hundred() -> None:
    fmt = Format(decimals=0)
    shares = consistent_shares([1.0, 1.0, 1.0], 3.0, fmt)
    assert shares == ("34%", "33%", "33%")


def test_shares_with_a_german_separator_keep_their_comma() -> None:
    shares = consistent_shares([1.0, 1.0, 1.0], 3.0, Format(separator=",", language="de"))
    assert shares == ("33,4%", "33,3%", "33,3%")


def test_a_value_without_a_share_keeps_its_empty_place() -> None:
    shares = consistent_shares([None, -5.0, 95.0], 95.0, Format(decimals=0))
    assert shares == (None, None, "100%")


def test_segments_round_to_the_total_at_two_decimals() -> None:
    labels = consistent([0.125, 0.125, 0.125], 0.375, Format())
    assert sum(float(label) for label in labels if label is not None) == 0.38  # the rounded total
    assert labels == ("0.13", "0.13", "0.12")  # ties carry the remainder forward


def test_fixed_decimals_apply_to_segments_and_total() -> None:
    fmt = Format(decimals=1)
    labels = consistent([1.25, 1.25], 2.5, fmt)
    assert labels == ("1.3", "1.2")  # 1.3 + 1.2 instead of 1.3 + 1.3 = 2.6


def test_a_magnitude_scales_the_labels() -> None:
    labels = consistent([1_500_000.0, 1_500_000.0], 3_000_000.0, Format(magnitude=6))
    assert labels == ("1.5 M", "1.5 M")
    german = consistent(
        [1_500_000.0, 1_500_000.0], 3_000_000.0, Format(magnitude=6, separator=",", language="de")
    )
    assert german == ("1,5 Mio.", "1,5 Mio.")


def test_negative_segments_sum_to_the_negative_total() -> None:
    labels = consistent([-1.25, -1.25], -2.5, Format(decimals=0))
    assert sum(float(label) for label in labels if label is not None) == -2.0  # the rounded total
    assert labels == ("-1", "-1")  # -1.25 floors to -2; one unit goes to each


def test_mixed_signs_round_to_the_net_total() -> None:
    labels = consistent([3.3, -1.3], 2.0, Format(decimals=0))
    assert sum(float(label) for label in labels if label is not None) == 2.0


def test_a_single_segment_needs_no_adjustment() -> None:
    assert consistent([2.4], 2.4, Format(decimals=0)) == ("2",)


def test_none_values_keep_their_places() -> None:
    labels = consistent([1.0, None, 1.0, None], 2.0, Format())
    assert labels == ("1", None, "1", None)

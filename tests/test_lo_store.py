"""lo/store.py against a minimal fake of LibreOffice's document properties."""

from dataclasses import replace

import pytest

from librecharts.core.datasheet import sample_state
from librecharts.core.state_io import StateError
from librecharts.lo import store


class FakeProps:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.attributes: dict[str, int] = {}

    def getPropertySetInfo(self) -> "FakeProps":
        return self

    def hasPropertyByName(self, name: str) -> bool:
        return name in self.values

    def addProperty(self, name: str, attributes: int, value: str) -> None:
        assert name not in self.values, "LibreOffice raises PropertyExistException here"
        self.values[name], self.attributes[name] = value, attributes

    def setPropertyValue(self, name: str, value: str) -> None:
        self.values[name] = value

    def getPropertyValue(self, name: str) -> str:
        return self.values[name]


class FakeDoc:
    def __init__(self) -> None:
        self.props = FakeProps()

    def getDocumentProperties(self) -> "FakeDoc":
        return self

    def getUserDefinedProperties(self) -> FakeProps:
        return self.props


class FakeShape:
    def __init__(self, name: str) -> None:
        self.Name = name


class FakePage:
    def __init__(self, *names: str) -> None:
        self.shapes = [FakeShape(n) for n in names]

    def getCount(self) -> int:
        return len(self.shapes)

    def getByIndex(self, i: int) -> FakeShape:
        return self.shapes[i]


def test_state_round_trips_through_document_properties() -> None:
    doc = FakeDoc()
    store.write_state(doc, "abc", sample_state())
    assert store.read_state(doc, "abc") == sample_state()
    assert doc.props.attributes["librecharts:abc"] == 128  # removable, for later clean-up


def test_writing_again_overwrites() -> None:
    doc = FakeDoc()
    store.write_state(doc, "abc", sample_state())
    clustered = replace(sample_state(), grouping="clustered")
    store.write_state(doc, "abc", clustered)
    assert store.read_state(doc, "abc") == clustered


def test_missing_state_reads_as_none() -> None:
    assert store.read_state(FakeDoc(), "nope") is None


def test_corrupt_state_raises() -> None:
    doc = FakeDoc()
    doc.props.values["librecharts:abc"] = "{broken"
    with pytest.raises(StateError):
        store.read_state(doc, "abc")


def test_find_charts_returns_only_anchored_groups() -> None:
    page = FakePage("Rectangle 1", "librecharts:a1", "librecharts:", "librecharts:b2")
    found = store.find_charts(page)
    assert [chart_id for _, chart_id in found] == ["a1", "b2"]


def test_new_ids_are_unique_and_short() -> None:
    ids = {store.new_chart_id() for _ in range(1000)}
    assert len(ids) == 1000
    assert all(len(i) == 12 for i in ids)

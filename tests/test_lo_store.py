"""lo/store.py against a minimal fake of LibreOffice's document properties."""

from dataclasses import replace
from types import SimpleNamespace

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

    def removeProperty(self, name: str) -> None:
        del self.values[name], self.attributes[name]

    def getPropertyValue(self, name: str) -> str:
        return self.values[name]

    def getProperties(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(Name=n) for n in self.values]


class FakeDoc:
    def __init__(self, *pages: "FakePage") -> None:
        self.props = FakeProps()
        self.pages = list(pages)

    def getDrawPages(self) -> "FakeDoc":
        return self

    def getCount(self) -> int:
        return len(self.pages)

    def getByIndex(self, i: int) -> "FakePage":
        return self.pages[i]

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
    assert all(i[-1] in "abcdef" for i in ids)  # LibreOffice strips trailing digits on copy


ORIGIN = "6d412c74fd91"
MANGLED = "6d412c74fd 1"


def _doc_with_chart(*extra_names: str) -> tuple[FakeDoc, FakeShape, list[FakeShape]]:
    original = FakeShape(f"librecharts:{ORIGIN}")
    extras = [FakeShape(n) for n in extra_names]
    page = FakePage()
    page.shapes = [original, *extras]
    doc = FakeDoc(page)
    store.write_state(doc, ORIGIN, sample_state())
    return doc, original, extras


def test_claim_of_an_unshared_chart_changes_nothing() -> None:
    doc, original, _ = _doc_with_chart()
    assert store.claim(doc, original) == ORIGIN
    assert original.Name == f"librecharts:{ORIGIN}"
    assert len(doc.props.values) == 1


def test_a_renamed_copy_is_forked_with_its_own_state() -> None:
    doc, _, (copy,) = _doc_with_chart(f"librecharts:{MANGLED}")
    new_id = store.claim(doc, copy)
    assert new_id is not None
    assert new_id != ORIGIN
    assert copy.Name == f"librecharts:{new_id}"
    assert store.read_state(doc, new_id) == sample_state()
    assert store.read_state(doc, ORIGIN) == sample_state()


def test_forked_copies_are_independent() -> None:
    doc, original, (copy,) = _doc_with_chart(f"librecharts:{MANGLED}")
    new_id = store.claim(doc, copy)
    assert new_id is not None
    store.write_state(doc, new_id, replace(sample_state(), grouping="clustered"))
    assert store.read_state(doc, ORIGIN) == sample_state()
    assert store.claim(doc, original) == ORIGIN  # the original no longer clashes


def test_copy_of_a_letter_ending_id_keeps_the_whole_id() -> None:
    doc = FakeDoc(FakePage("librecharts:fa7ccda9dfcc", "librecharts:fa7ccda9dfcc 1"))
    store.write_state(doc, "fa7ccda9dfcc", sample_state())
    copy = doc.pages[0].shapes[1]
    new_id = store.claim(doc, copy)
    assert new_id not in (None, "fa7ccda9dfcc")
    assert store.read_state(doc, new_id or "") == sample_state()


def test_groups_sharing_an_exact_name_fork_the_one_being_claimed() -> None:
    doc, _, (twin,) = _doc_with_chart(f"librecharts:{ORIGIN}")
    new_id = store.claim(doc, twin)
    assert new_id not in (None, ORIGIN)


def test_chart_without_stored_state_is_orphaned() -> None:
    doc = FakeDoc(FakePage("librecharts:abcdef012345"))
    assert store.claim(doc, doc.pages[0].shapes[0]) is None


def test_ambiguous_or_short_prefixes_are_not_guessed() -> None:
    doc, _, (copy, short) = _doc_with_chart("librecharts:6d412c74fd 1", "librecharts:6d41 1")
    store.write_state(doc, "6d412c74fd22", sample_state())  # a second chart with the same prefix
    assert store.claim(doc, copy) is None
    assert store.claim(doc, short) is None


def test_non_chart_shape_cannot_be_claimed() -> None:
    doc, _, _ = _doc_with_chart()
    assert store.claim(doc, FakeShape("Rectangle 1")) is None


def test_document_wide_properties_are_no_chart_states() -> None:
    doc = FakeDoc(FakePage("librecharts:scheme", "librecharts:agenda"))
    store.write_property(doc, store.SCHEME_PROPERTY, "{}")
    store.write_property(doc, store.AGENDA_PROPERTY, "{}")
    assert [store.claim(doc, shape) for shape in doc.pages[0].shapes] == [None, None]


def test_remove_property_removes_it_once() -> None:
    doc = FakeDoc()
    store.write_property(doc, store.AGENDA_PROPERTY, "{}")
    store.remove_property(doc, store.AGENDA_PROPERTY)
    store.remove_property(doc, store.AGENDA_PROPERTY)
    assert store.read_property(doc, store.AGENDA_PROPERTY) is None


def test_all_charts_spans_every_slide() -> None:
    doc = FakeDoc(FakePage("librecharts:a1", "x"), FakePage("librecharts:b2"))
    assert [i for _, i in store.all_charts(doc)] == ["a1", "b2"]

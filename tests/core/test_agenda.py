from collections.abc import Callable, Iterator

import pytest

from librecharts.core import agenda, style
from librecharts.core.agenda import MAIN, Agenda, AgendaError, Chapter, Line, Slide


def ids(*names: str) -> Callable[[], str]:
    """An id factory handing out ``names`` padded to valid chapter ids."""
    supply: Iterator[str] = iter(name.ljust(12, "0") for name in names)
    return lambda: next(supply)


def chapters(*pairs: tuple[str, str]) -> Agenda:
    return Agenda(tuple(Chapter(chapter_id.ljust(12, "0"), title) for chapter_id, title in pairs))


ABC = chapters(("a", "Intro"), ("b", "Market"), ("c", "Plan"))
A, B, C = (chapter.id for chapter in ABC.chapters)


def test_new_ids_are_valid_and_unique() -> None:
    made = {agenda.new_id() for _ in range(100)}
    assert len(made) == 100
    assert all(agenda.role(agenda.shape_name(chapter_id)) == chapter_id for chapter_id in made)


def test_shape_names_round_trip() -> None:
    assert agenda.shape_name(MAIN) == "librecharts-agenda"
    assert agenda.role("librecharts-agenda") == MAIN
    assert agenda.role(agenda.shape_name(A)) == A


@pytest.mark.parametrize(
    "name",
    [
        "",
        "librecharts-agenda 1",  # the list of a slide the user duplicated
        "librecharts-agenda:a00000000000 1",
        "librecharts-agenda:xyz",
        "librecharts:abc",
        "Title 1",
    ],
)
def test_other_names_are_no_agenda_lists(name: str) -> None:
    assert agenda.role(name) is None


def test_titles_are_the_non_empty_paragraphs_without_numbers() -> None:
    text = "1\tIntro\r\n2.\tMarket\r\n\n  3) Plan  \n4. Outlook\n2025 figures\n\t\n"
    assert agenda.parse_titles(text) == ("Intro", "Market", "Plan", "Outlook", "2025 figures")


def test_kept_titles_keep_their_chapter_also_when_moved() -> None:
    assert agenda.reconcile(ABC, ["Plan", "Intro", "Market"]) == Agenda(
        (ABC.chapters[2], ABC.chapters[0], ABC.chapters[1])
    )


def test_a_changed_title_renames_its_chapter() -> None:
    result = agenda.reconcile(ABC, ["Intro", "Markets", "Plan"], ids("x"))
    assert result.ids() == (A, B, C)
    assert result.chapters[1].title == "Markets"


def test_added_and_deleted_titles() -> None:
    added = agenda.reconcile(ABC, ["Intro", "New", "Market", "Plan"], ids("x"))
    assert added.ids() == (A, "x".ljust(12, "0"), B, C)
    deleted = agenda.reconcile(ABC, ["Intro", "Plan"], ids("x"))
    assert deleted.ids() == (A, C)


def test_insert_agenda_after_the_current_slide_with_placeholders() -> None:
    outcome = agenda.insert_agenda(None, (), 2, ["One", "Two"], ids("p", "q"))
    assert [c.title for c in outcome.agenda.chapters] == ["One", "Two"]
    assert outcome.slides == (Slide(3, MAIN),)


def test_insert_agenda_again_lists_the_stored_chapters_and_moves_later_dividers() -> None:
    outcome = agenda.insert_agenda(ABC, (Slide(1, A), Slide(4, B)), 2, ["One"], ids("p"))
    assert outcome.agenda == ABC
    assert outcome.slides == (Slide(1, A), Slide(3, MAIN), Slide(5, B))


def test_a_second_agenda_is_refused() -> None:
    with pytest.raises(AgendaError, match="already"):
        agenda.insert_agenda(ABC, (Slide(1, MAIN),), 3, ["One"])


def test_update_removes_the_dividers_of_deleted_chapters_only() -> None:
    unknown = "f".ljust(12, "0")
    slides = (Slide(1, MAIN), Slide(2, A), Slide(4, B), Slide(6, unknown), Slide(7, C))
    outcome = agenda.update(ABC, ["Intro", "Plan"], slides)
    assert outcome.slides == (Slide(1, MAIN), Slide(2, A), Slide(5, unknown), Slide(6, C))
    assert outcome.agenda.ids() == (A, C)


def test_an_empty_agenda_is_refused() -> None:
    with pytest.raises(AgendaError, match="at least one"):
        agenda.update(ABC, [], (Slide(1, MAIN),))


def test_the_first_divider_starts_the_first_chapter() -> None:
    outcome, chapter = agenda.start_chapter(
        ABC, ["Intro", "Market", "Plan"], (Slide(1, MAIN),), 3, "New"
    )
    assert chapter == A
    assert outcome.agenda == ABC
    assert outcome.slides == (Slide(1, MAIN), Slide(3, A))


def test_a_divider_starts_the_chapter_after_the_previous_divider() -> None:
    slides = (Slide(1, MAIN), Slide(2, A))
    outcome, chapter = agenda.start_chapter(ABC, ["Intro", "Market", "Plan"], slides, 5, "New")
    assert chapter == B
    assert outcome.slides == (Slide(1, MAIN), Slide(2, A), Slide(5, B))


def test_a_divider_between_two_placed_chapters_inserts_a_new_one() -> None:
    slides = (Slide(1, MAIN), Slide(2, A), Slide(6, B))
    outcome, chapter = agenda.start_chapter(
        ABC, ["Intro", "Market", "Plan"], slides, 4, "New", ids("n")
    )
    assert chapter == "n".ljust(12, "0")
    assert [c.title for c in outcome.agenda.chapters] == ["Intro", "New", "Market", "Plan"]
    assert outcome.slides == (Slide(1, MAIN), Slide(2, A), Slide(4, chapter), Slide(7, B))


def test_a_divider_after_the_last_chapter_adds_one_at_the_end() -> None:
    slides = (Slide(1, MAIN), Slide(2, A), Slide(4, B), Slide(6, C))
    outcome, chapter = agenda.start_chapter(
        ABC, ["Intro", "Market", "Plan"], slides, 8, "New", ids("n")
    )
    assert outcome.agenda.chapters[-1] == Chapter(chapter, "New")
    assert outcome.slides[-1] == Slide(8, chapter)


def test_starting_a_chapter_applies_the_edited_list_first() -> None:
    slides = (Slide(1, MAIN), Slide(2, A), Slide(4, B))
    outcome, chapter = agenda.start_chapter(ABC, ["Intro", "Plan"], slides, 6, "New")
    # Market and its divider are gone; the slide that was at 6 is now at 5
    assert chapter == C
    assert outcome.slides == (Slide(1, MAIN), Slide(2, A), Slide(5, C))


def test_a_chapter_cannot_start_on_the_first_slide() -> None:
    with pytest.raises(AgendaError, match="first slide"):
        agenda.start_chapter(ABC, ["Intro"], (Slide(3, MAIN),), 0, "New")
    with pytest.raises(AgendaError, match="first slide"):  # after its divider was removed
        agenda.start_chapter(ABC, ["Intro"], (Slide(0, B), Slide(3, MAIN)), 1, "New")


def test_changes_keep_present_roles_and_order_removals_and_inserts() -> None:
    current = (Slide(1, MAIN), Slide(3, A), Slide(5, B), Slide(8, C))
    target = (Slide(1, MAIN), Slide(2, "x"), Slide(4, A), Slide(7, C), Slide(9, "y"))
    remove, insert = agenda.changes(current, target)
    assert remove == (5,)
    assert insert == (Slide(2, "x"), Slide(9, "y"))
    assert agenda.changes(target, current) == ((9, 2), (Slide(5, B),))


def test_main_list_is_numbered_in_the_text_colour() -> None:
    assert agenda.lines(ABC, style.DEFAULT) == (
        Line("1\tIntro", style.TEXT_COLOR),
        Line("2\tMarket", style.TEXT_COLOR),
        Line("3\tPlan", style.TEXT_COLOR),
    )


def test_a_divider_highlights_its_chapter() -> None:
    lines = agenda.lines(ABC, style.DEFAULT, B)
    assert lines[1] == Line("2\tMarket", agenda.accent(style.DEFAULT), bold=True)
    muted = style.mix(style.TEXT_COLOR, style.WHITE, agenda.MUTED_SHARE)
    assert lines[0] == Line("1\tIntro", muted)
    assert lines[2] == Line("3\tPlan", muted)


def test_the_accent_is_the_most_readable_palette_colour() -> None:
    assert agenda.accent(style.DEFAULT) == 0x5E8AC7
    assert agenda.accent(style.HIGH_CONTRAST) == 0x1F4E79
    pale = style.Scheme("Pale", (0xEEEEEE, 0xDDDDDD), text=0x123456)
    assert agenda.accent(pale) == 0x123456


def test_json_round_trip() -> None:
    assert agenda.from_json(agenda.to_json(ABC)) == ABC
    assert agenda.from_json(agenda.to_json(Agenda())) == Agenda()
    umlauts = chapters(("a", "Überblick"))
    assert agenda.from_json(agenda.to_json(umlauts)) == umlauts


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("{", "invalid JSON"),
        ("[]", "JSON object"),
        ('{"chapters": []}', "version"),
        ('{"v": true, "chapters": []}', "version"),
        ('{"v": 2, "chapters": []}', "newer"),
        ('{"v": 1}', "list"),
        ('{"v": 1, "chapters": [1]}', "JSON object"),
        ('{"v": 1, "chapters": [{"id": "x", "title": "A"}]}', "chapter id"),
        ('{"v": 1, "chapters": [{"id": "a00000000000", "title": 3}]}', "title"),
        (
            '{"v": 1, "chapters": [{"id": "a00000000000", "title": "A"},'
            ' {"id": "a00000000000", "title": "B"}]}',
            "unique",
        ),
    ],
)
def test_malformed_agendas_are_rejected(text: str, message: str) -> None:
    with pytest.raises(AgendaError, match=message):
        agenda.from_json(text)

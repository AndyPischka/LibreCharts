"""The command line's arguments (M18): parsing and localized help, without LibreOffice."""

from __future__ import annotations

import pytest

from librecharts.core import cli


def test_build_takes_a_template_a_data_file_and_an_output() -> None:
    args = cli.parser().parse_args(
        ["build", "--template", "t.odp", "--data", "d.json", "--out", "deck.odp"]
    )
    assert (args.command, args.template, args.data, args.out) == (
        "build",
        "t.odp",
        "d.json",
        "deck.odp",
    )


def test_update_takes_a_deck_and_saves_over_it_by_default() -> None:
    args = cli.parser().parse_args(["update", "deck.odp"])
    assert (args.command, args.deck, args.out) == ("update", "deck.odp", "")


def test_update_can_write_another_file() -> None:
    args = cli.parser().parse_args(["update", "deck.odp", "--out", "new.odp"])
    assert args.out == "new.odp"


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit):
        cli.parser().parse_args([])


def test_build_needs_its_three_arguments() -> None:
    with pytest.raises(SystemExit):
        cli.parser().parse_args(["build", "--template", "t.odp"])


def test_the_pipe_is_internal() -> None:
    args = cli.parser().parse_args(["--pipe", "p1", "update", "deck.odp"])
    assert args.pipe == "p1"


def test_the_locale_works_before_and_after_the_command() -> None:
    before = cli.parser().parse_args(["--locale", "de", "update", "deck.odp"])
    after = cli.parser().parse_args(["update", "deck.odp", "--locale", "de"])
    attached = cli.parser().parse_args(["update", "deck.odp", "--locale=de"])
    assert (before.locale, after.locale, attached.locale) == ("de", "de", "de")


def test_without_a_locale_the_default_stands_after_a_command() -> None:
    args = cli.parser("fr").parse_args(["update", "deck.odp"])
    assert args.locale == ""


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--locale", "de", "update", "deck.odp"], "de"),
        (["update", "deck.odp", "--locale", "de-DE"], "de-DE"),
        (["update", "deck.odp", "--locale=de-AT"], "de-AT"),
        (["update", "deck.odp"], ""),
        (["--locale"], ""),
    ],
)
def test_the_help_language_is_found_before_parsing(argv: list[str], expected: str) -> None:
    assert cli.argument_locale(argv) == expected


def test_the_help_speaks_the_chosen_language() -> None:
    assert "Deck-Beschreibung" in cli.parser("de").format_help()
    assert "deck specification" in cli.parser("en").format_help()
    assert "deck specification" in cli.parser().format_help()  # English fallback


def test_help_exits_without_a_libreoffice() -> None:
    with pytest.raises(SystemExit) as exit_code:
        cli.parser().parse_args(["--help"])
    assert exit_code.value.code == 0

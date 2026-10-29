# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Number-format and value-line dialogs (ADR 0014).

Both are opened asynchronously (an ``AsyncCallback``) so the command that asked for them returns
first. They are built in code, no resource file to ship. Validation lives in ``core/format.py`` and
``core/value_line.py``. Headless LibreOffice returns from ``execute()`` at once, so the dialogs are
tested by hand; their logic is tested in ``tests/core``.
"""

from __future__ import annotations

import datetime
import traceback
from dataclasses import replace
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XCallback, XItemListener

from librecharts.core.format import number_format
from librecharts.core.gantt import serial
from librecharts.core.layout.common import format_value
from librecharts.core.messages import text
from librecharts.core.model import Annotation, ChartState
from librecharts.core.value_line import check, check_date, date_input
from librecharts.lo import chart, store, ui

_PUSH_BUTTON_CANCEL = 2  # com.sun.star.awt.PushButtonType.CANCEL
_RED = 0xCC0000
_MAGNITUDES = (0, 3, 6, 9)
_MAGNITUDE_KEYS = (
    "format_magnitude_none",
    "format_magnitude_thousands",
    "format_magnitude_millions",
    "format_magnitude_billions",
)

# Pending requests by presentation and dialog: a Python object passed to AsyncCallback must stay
# alive.
_requests: dict[str, Any] = {}


def request_number(ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
    """Ask for the number format of the chart in ``group``, then store the answer."""
    key = f"{frame.getController().getModel().RuntimeUID}:number"
    if key not in _requests:
        _requests[key] = _NumberRequest(key, ctx, frame, group, state)


def request_value_line(
    ctx: Any, frame: Any, group: Any, state: ChartState, index: int | None
) -> None:
    """Ask for a value line (new if ``index`` is ``None``, else change that annotation)."""
    key = f"{frame.getController().getModel().RuntimeUID}:value_line"
    if key not in _requests:
        _requests[key] = _ValueLineRequest(key, ctx, frame, group, state, index)


class _Request(unohelper.Base, XCallback):
    """Runs the dialog after the command returned, then stores the answer."""

    def __init__(self, key: str, ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
        self.key, self.ctx, self.frame, self.group, self.state = key, ctx, frame, group, state
        callback = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        callback.addCallback(self, None)  # None: void any, see lo/resize.py

    def notify(self, data: Any) -> None:
        try:
            self.answer()
        except Exception:
            # Never let an exception escape into LibreOffice's callback processing.
            traceback.print_exc()
        finally:
            _requests.pop(self.key, None)

    def answer(self) -> None:
        raise NotImplementedError

    def current(self) -> ChartState | None:
        """The stored state at dialog time: the user may have edited the chart since the command."""
        doc = self.frame.getController().getModel()
        chart_id = store.chart_id_of(self.group)
        return (store.read_state(doc, chart_id) if chart_id else None) or self.state


class _NumberRequest(_Request):
    def answer(self) -> None:
        state = self.current()
        if state is None:
            return
        locale = ui.ui_locale(self.ctx)
        choice = ask_number(self.ctx, self.frame, state, locale)
        if choice is not None:
            chart.redraw(
                self.frame.getController().getModel(),
                self.group,
                replace(state, format=choice),
            )


class _ValueLineRequest(_Request):
    def __init__(
        self,
        key: str,
        ctx: Any,
        frame: Any,
        group: Any,
        state: ChartState,
        index: int | None,
    ) -> None:
        super().__init__(key, ctx, frame, group, state)
        self.index = index

    def answer(self) -> None:
        state = self.current()
        if state is None:
            return
        locale = ui.ui_locale(self.ctx)
        current = state.annotations[self.index] if self.index is not None else None
        choice = ask_value_line(self.ctx, self.frame, state, current, locale)
        if isinstance(choice, _Cancelled):
            return
        doc = self.frame.getController().getModel()
        if self.index is None:
            chart.add_annotation(doc, self.group, Annotation("value_line", 0, 0, value=choice))
        else:
            notes = (
                *state.annotations[: self.index],
                replace(state.annotations[self.index], value=choice),
                *state.annotations[self.index + 1 :],
            )
            chart.redraw(doc, self.group, replace(state, annotations=notes))


def ask_number(ctx: Any, frame: Any, state: ChartState, locale: str) -> Any | None:
    """Show the number-format dialog (modal); the new ``Format`` or ``None`` if cancelled."""
    fmt = state.format
    dialog = _build_number(ctx, frame, locale, fmt)
    outcome: list[Any] = []
    dialog.getControl("ok").addActionListener(
        _OkListener(dialog, locale, outcome, lambda: _number_outcome(dialog, state))
    )
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else None


def _number_outcome(dialog: Any, state: ChartState) -> Any | str:
    position = dialog.getControl("magnitude").getSelectedItemPos()
    magnitude = str(_MAGNITUDES[max(position, 0)])
    separator = "," if dialog.getControl("sep_comma").getState() else "."
    return number_format(
        state.format,
        dialog.getControl("decimals").getText(),
        magnitude,
        dialog.getControl("unit").getText(),
        separator,
    )


def ask_value_line(
    ctx: Any,
    frame: Any,
    state: ChartState,
    current: Annotation | None,
    locale: str,
) -> float | _Cancelled | None:
    """Show the value-line dialog; ``None`` for the average, a number, or ``CANCELLED``.

    A Gantt chart asks for a date instead (a date line), today's date filled in for a new one.
    """
    if state.kind == "gantt":
        return _ask_date_line(ctx, frame, state, current, locale)
    manual = current is not None and current.value is not None
    shown = (
        ""
        if current is None or current.value is None
        else format_value(current.value, state.format)
    )
    dialog = _build_value_line(ctx, frame, locale, manual=manual, value=shown)
    outcome: list[Any] = []
    dialog.getControl("ok").addActionListener(
        _OkListener(dialog, locale, outcome, lambda: _value_line_outcome(dialog))
    )
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else CANCELLED


def _ask_date_line(
    ctx: Any, frame: Any, state: ChartState, current: Annotation | None, locale: str
) -> float | _Cancelled:
    language = state.format.language
    value = (
        current.value
        if current is not None and current.value is not None
        else float(serial(datetime.date.today()))
    )
    builder = _Builder(ctx, frame, text("date_line_title", locale), 190, 92, locale)
    builder.label("date_line_date", 10, 10, 170, 10)
    builder.edit("value", 10, 22, 90, 12, date_input(value, language))
    dialog = builder.finish("date_line", top=48)
    outcome: list[Any] = []
    dialog.getControl("ok").addActionListener(
        _OkListener(
            dialog,
            locale,
            outcome,
            lambda: check_date(dialog.getControl("value").getText(), language),
        )
    )
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else CANCELLED


class _Cancelled:
    """Returned by :func:`ask_value_line` when the user closed the dialog without an answer."""


CANCELLED = _Cancelled()


def _value_line_outcome(dialog: Any) -> float | str | None:
    if dialog.getControl("average").getState():
        return None
    return check(dialog.getControl("value").getText())


class _OkListener(unohelper.Base, XActionListener):
    """Validates with ``outcome``; keeps the dialog open and shows the error message."""

    def __init__(self, dialog: Any, locale: str, results: list[Any], outcome: Any) -> None:
        self.dialog, self.locale, self.results, self.outcome = (
            dialog,
            locale,
            results,
            outcome,
        )

    def actionPerformed(self, event: Any) -> None:
        try:
            result = self.outcome()
            if isinstance(result, str) and result in _MESSAGES:
                self.dialog.getModel().getByName("error").Label = text(result, self.locale)
                return
            self.results.append(result)
            self.dialog.endExecute()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


_MESSAGES = frozenset(
    {
        "format_decimals_invalid",
        "format_unit_too_long",
        "format_magnitude_invalid",
        "format_separator_invalid",
        "value_line_not_a_number",
        "date_line_invalid",
    }
)


class _RadioListener(unohelper.Base, XItemListener):
    """Enables the value field only while "value" is chosen."""

    def __init__(self, dialog: Any) -> None:
        self.dialog = dialog

    def itemStateChanged(self, event: Any) -> None:
        try:
            self.dialog.getModel().getByName("value").Enabled = bool(
                self.dialog.getControl("value_choice").getState()
            )
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _build_number(ctx: Any, frame: Any, locale: str, fmt: Any) -> Any:
    builder = _Builder(ctx, frame, text("format_title", locale), 220, 168, locale)
    builder.edit("decimals", 14, 18, 60, 12, "" if fmt.decimals is None else str(fmt.decimals))
    builder.label("format_decimals", 14, 8, 190, 10)
    builder.listbox(
        "magnitude",
        14,
        52,
        190,
        14,
        [text(key, locale) for key in _MAGNITUDE_KEYS],
        _MAGNITUDES.index(fmt.magnitude),
    )
    builder.label("format_magnitude", 14, 42, 190, 10)
    builder.edit("unit", 14, 88, 120, 12, fmt.unit)
    builder.label("format_unit", 14, 78, 190, 10)
    builder.radio("sep_dot", 14, 108, 80, 10, "format_separator_dot", fmt.separator == ".")
    builder.radio("sep_comma", 104, 108, 80, 10, "format_separator_comma", fmt.separator == ",")
    builder.label("format_separator", 14, 98, 190, 10)
    return builder.finish("number")


def _build_value_line(ctx: Any, frame: Any, locale: str, *, manual: bool, value: str) -> Any:
    builder = _Builder(ctx, frame, text("value_line_title", locale), 190, 112, locale)
    builder.radio("average", 10, 10, 170, 10, "value_line_average", not manual)
    builder.radio("value_choice", 10, 25, 170, 10, "value_line_value", manual)
    builder.edit("value", 100, 40, 70, 12, value)
    dialog = builder.finish("value_line", top=70)
    dialog.getModel().getByName("value").Enabled = manual
    dialog.getControl("average").addItemListener(_RadioListener(dialog))
    dialog.getControl("value_choice").addItemListener(_RadioListener(dialog))
    return dialog


class _Builder:
    """Adds controls to a ``UnoControlDialogModel`` with "Map AppFont" sizes."""

    def __init__(
        self, ctx: Any, frame: Any, title: str, width: int, height: int, locale: str
    ) -> None:
        self.ctx, self.frame, self.locale = ctx, frame, locale
        self.smgr = ctx.ServiceManager
        self.model = self.smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel", ctx
        )
        self.model.Title, self.model.Width, self.model.Height = title, width, height

    def _add(
        self, kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any
    ) -> None:
        control = self.model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        self.model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    def label(self, key: str, x: int, y: int, width: int, height: int) -> None:
        self._add("FixedText", key, x, y, width, height, Label=text(key, self.locale))

    def edit(self, name: str, x: int, y: int, width: int, height: int, value: str) -> None:
        self._add("Edit", name, x, y, width, height, Text=value)

    def listbox(
        self,
        name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        entries: list[str],
        selected: int,
    ) -> None:
        self._add(
            "ListBox",
            name,
            x,
            y,
            width,
            height,
            StringItemList=tuple(entries),
            Dropdown=True,
            SelectedItemPos=selected,
        )

    def radio(
        self,
        name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        key: str,
        state: bool,
    ) -> None:
        self._add(
            "RadioButton", name, x, y, width, height, Label=text(key, self.locale), State=int(state)
        )

    def finish(self, prefix: str, top: int = 118) -> Any:
        """Add the error text and the buttons; ``top`` is the error text's y position."""
        self._add(
            "FixedText",
            "error",
            10,
            top,
            self.model.Width - 30,
            18,
            Label="",
            TextColor=_RED,
            MultiLine=True,
        )
        button_y = top + 20
        self._add(
            "Button",
            "ok",
            80,
            button_y,
            50,
            14,
            Label=text("button_ok", self.locale),
            DefaultButton=True,
        )
        self._add(
            "Button",
            "cancel",
            134,
            button_y,
            50,
            14,
            Label=text("button_cancel", self.locale),
            PushButtonType=_PUSH_BUTTON_CANCEL,
        )
        dialog = self.smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", self.ctx)
        dialog.setModel(self.model)
        toolkit = self.smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        dialog.createPeer(toolkit, self.frame.getContainerWindow())
        return dialog

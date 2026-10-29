# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The link dialog: a spreadsheet file, a sheet and a range or range name (ADR 0020).

Opened asynchronously (an ``AsyncCallback``) like the axis break dialog and built in code.
Choosing a file reads its sheets, their used areas and its named ranges; changing the sheet
proposes its used area. OK reads the range and keeps the dialog open with the reason if that
fails, so a link is only made from data that could be read. Rules live in ``core/links.py``.
"""

from __future__ import annotations

import contextlib
import traceback
from typing import Any

import uno
import unohelper
from com.sun.star.awt import XActionListener, XCallback, XItemListener

from librecharts.core import links as core_links
from librecharts.core.messages import text
from librecharts.core.model import ChartState
from librecharts.lo import chart, datasheet, links, store, ui

_PUSH_BUTTON_CANCEL = 2  # com.sun.star.awt.PushButtonType.CANCEL
_RED = 0xCC0000
_PATTERNS = "*.ods;*.fods;*.xlsx;*.xlsm;*.xls;*.csv"

# Pending requests by presentation: a Python object passed to AsyncCallback must stay alive.
_requests: dict[str, _Request] = {}


def request(ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
    """Ask for the source of the chart in ``group``, then link it: one undo step.

    The dialog starts from the chart's current link, if it has one. Cancel changes nothing.
    """
    key = str(frame.getController().getModel().RuntimeUID)
    if key in _requests:  # a dialog is already open
        return
    _requests[key] = _Request(key, ctx, frame, group, state)


class _Request(unohelper.Base, XCallback):
    def __init__(self, key: str, ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
        self.key, self.ctx, self.frame, self.group, self.state = key, ctx, frame, group, state
        callback = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        callback.addCallback(self, None)  # None: void any, see lo/resize.py

    def notify(self, data: Any) -> None:
        try:
            doc = self.frame.getController().getModel()
            # The user may have edited the chart since the command: start from the stored state.
            chart_id = store.chart_id_of(self.group)
            state = (store.read_state(doc, chart_id) if chart_id else None) or self.state
            linked = ask(self.ctx, self.frame, doc, state)
            if linked is not None and chart_id is not None:
                chart.redraw(doc, self.group, linked)
                datasheet.refresh(doc, chart_id)
        except Exception:
            # Never let an exception escape into LibreOffice's callback processing.
            traceback.print_exc()
        finally:
            _requests.pop(self.key, None)


def ask(ctx: Any, frame: Any, doc: Any, state: ChartState) -> ChartState | None:
    """Show the dialog (modal); the linked state with its data, or ``None`` if cancelled."""
    locale = ui.ui_locale(ctx)
    dialog = _build(ctx, frame, locale)
    form = _Form(ctx, dialog, doc, state, locale)
    dialog.getControl("browse").addActionListener(_Browse(form))
    dialog.getControl("sheet").addItemListener(_SheetChanged(form))
    dialog.getControl("ok").addActionListener(_Ok(form))
    if state.link is not None:
        try:
            url = links.locate(ctx, doc, state.link)
        except links.LinkError:
            url = state.link.url
        form.choose(url, state.link.sheet, state.link.range)
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return form.result


class _Form:
    """The dialog's state between its listeners."""

    def __init__(self, ctx: Any, dialog: Any, doc: Any, state: ChartState, locale: str) -> None:
        self.ctx, self.dialog, self.doc, self.state, self.locale = ctx, dialog, doc, state, locale
        self.url = ""
        self.workbook: links.Workbook | None = None
        self.proposed = ""  # the used area filled in last: replaced when the sheet changes
        self.result: ChartState | None = None

    def choose(self, url: str, sheet: str = "", reference: str = "") -> None:
        """Take the file at ``url``: list its sheets and range names."""
        self.error("")
        self.url, self.workbook = url, None
        self.dialog.getControl("file").setText(_system_path(url))
        sheets = self.dialog.getControl("sheet")
        sheets.removeItems(0, sheets.getItemCount())
        names = self.dialog.getControl("range")
        names.removeItems(0, names.getItemCount())
        try:
            workbook = links.inspect(self.ctx, url)
        except links.LinkError as exc:
            self.error(text(exc.key, self.locale, file=core_links.file_name(url)))
            return
        self.workbook = workbook
        sheets.addItems(workbook.sheets, 0)
        if workbook.names:
            names.addItems(workbook.names, 0)
        position = workbook.sheets.index(sheet) if sheet in workbook.sheets else 0
        if workbook.sheets:
            sheets.selectItemPos(position, True)
        self.proposed = ""
        names.setText(reference)
        self.sheet_changed()

    def sheet_changed(self) -> None:
        """Propose the used area of the chosen sheet, unless the user typed a range."""
        position = self.dialog.getControl("sheet").getSelectedItemPos()
        if self.workbook is None or not 0 <= position < len(self.workbook.used):
            return
        field = self.dialog.getControl("range")
        if field.getText().strip() in ("", self.proposed):
            self.proposed = self.workbook.used[position]
            field.setText(self.proposed)

    def accept(self) -> None:
        """Link to what the fields say, or say what is wrong and stay open."""
        if not self.url:
            self.error(text("link_no_file", self.locale))
            return
        sheet = str(self.dialog.getControl("sheet").getSelectedItem() or "")
        reference = str(self.dialog.getControl("range").getText())
        checked = core_links.target(sheet, reference)
        if isinstance(checked, str):
            self.error(text(checked, self.locale, range=reference.strip()))
            return
        try:
            self.result = links.link(self.ctx, self.doc, self.state, self.url, *checked)
        except links.LinkError as exc:
            self.error(exc.message(self.locale))
            return
        self.dialog.endExecute()

    def browse(self) -> None:
        picker = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.ui.dialogs.FilePicker", self.ctx
        )
        picker.setTitle(text("link_title", self.locale))
        label = text("link_filter", self.locale)
        picker.appendFilter(label, _PATTERNS)
        picker.setCurrentFilter(label)
        if self.url:
            with contextlib.suppress(Exception):
                picker.setDisplayDirectory(self.url.rsplit("/", 1)[0])
        if picker.execute() != 1:  # com.sun.star.ui.dialogs.ExecutableDialogResults.OK
            return
        files = picker.getFiles()
        if files:
            self.choose(str(files[0]))

    def error(self, message: str) -> None:
        self.dialog.getModel().getByName("error").Label = message


class _Browse(unohelper.Base, XActionListener):
    def __init__(self, form: _Form) -> None:
        self.form = form

    def actionPerformed(self, event: Any) -> None:
        try:
            self.form.browse()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


class _Ok(unohelper.Base, XActionListener):
    def __init__(self, form: _Form) -> None:
        self.form = form

    def actionPerformed(self, event: Any) -> None:
        try:
            self.form.accept()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


class _SheetChanged(unohelper.Base, XItemListener):
    def __init__(self, form: _Form) -> None:
        self.form = form

    def itemStateChanged(self, event: Any) -> None:
        try:
            self.form.sheet_changed()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _system_path(url: str) -> str:
    try:
        return str(uno.fileUrlToSystemPath(url))
    except Exception:  # not a file URL
        return url


def _build(ctx: Any, frame: Any, locale: str) -> Any:
    """The dialog control, not yet shown. Sizes are in "Map AppFont" units."""
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("link_title", locale), 230, 160

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    add("FixedText", "file_label", 10, 8, 210, 10, Label=text("link_file", locale), TabIndex=0)
    add("Edit", "file", 10, 20, 158, 12, ReadOnly=True, TabIndex=1)
    add(
        "Button",
        "browse",
        172,
        19,
        48,
        14,
        Label=text("link_browse", locale),
        TabIndex=2,
    )
    add("FixedText", "sheet_label", 10, 40, 100, 10, Label=text("link_sheet", locale), TabIndex=3)
    add("ListBox", "sheet", 10, 52, 100, 12, Dropdown=True, TabIndex=4)
    add("FixedText", "range_label", 120, 40, 100, 10, Label=text("link_range", locale), TabIndex=5)
    add("ComboBox", "range", 120, 52, 100, 12, Dropdown=True, TabIndex=6)
    add(
        "FixedText",
        "hint",
        10,
        72,
        210,
        20,
        Label=text("link_hint", locale),
        MultiLine=True,
        TabIndex=7,
    )
    add("FixedText", "error", 10, 96, 210, 36, Label="", TextColor=_RED, MultiLine=True, TabIndex=8)
    add(
        "Button",
        "ok",
        114,
        140,
        50,
        14,
        Label=text("button_ok", locale),
        DefaultButton=True,
        TabIndex=9,
    )
    add(
        "Button",
        "cancel",
        170,
        140,
        50,
        14,
        Label=text("button_cancel", locale),
        PushButtonType=_PUSH_BUTTON_CANCEL,
        TabIndex=10,
    )

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.createPeer(toolkit, frame.getContainerWindow())
    return dialog

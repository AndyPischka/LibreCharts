# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The LibreCharts panel in the Impress sidebar (contents: core/panel.py).

Registered by ``Sidebar.xcu`` (deck and panel) and ``Factories.xcu`` (the factory, which
``extension/entry.py`` implements with ``create``). The panel is a plain window container with
buttons and labels. It follows the selection and the document, redrawing only when its content
changed. Nothing here may raise into LibreOffice's listener handling.
"""

from __future__ import annotations

import contextlib
import traceback
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XAdjustmentListener, XCallback, XWindowListener
from com.sun.star.ui import LayoutSize, XSidebarPanel, XToolPanel, XUIElement
from com.sun.star.util import XModifyListener
from com.sun.star.view import XSelectionChangeListener

from librecharts.core.messages import text
from librecharts.core.panel import Button, Panel, content
from librecharts.core.state_io import StateError
from librecharts.lo import agenda, arrange, commands, scheme, store, ui
from librecharts.lo import elements as lo_elements

_TOOLPANEL = 7  # com.sun.star.ui.UIElementType.TOOLPANEL
_POSSIZE = 15  # com.sun.star.awt.PosSize.POSSIZE
_EXTENSION_ID = "org.librecharts.extension"

MARGIN, GAP, BUTTON_HEIGHT, LABEL_HEIGHT, HEADING_HEIGHT = 8, 4, 26, 18, 20
ICON_SIZE, FLOW_MIN_WIDTH = 30, 100
REMOVE_WIDTH = 24
REMOVE_LABEL = chr(0xD7)  # multiplication sign
DEFAULT_WIDTH = 240
MIN_HEIGHT, SCROLLBAR_WIDTH, LINE_STEP = 150, 16, 30

Rect = tuple[int, int, int, int]


def create(ctx: Any, resource_url: str, args: Any) -> Any:
    """The panel for ``private:resource/toolpanel/org.librecharts/Panel``; ``args`` as passed by
    LibreOffice's sidebar (``Frame``, ``ParentWindow``, ``Sidebar``)."""
    values = {a.Name: a.Value for a in args}
    return _Panel(ctx, resource_url, values["Frame"], values["ParentWindow"], values.get("Sidebar"))


class _Panel(unohelper.Base, XUIElement, XToolPanel, XSidebarPanel):
    def __init__(self, ctx: Any, url: str, frame: Any, parent: Any, sidebar: Any) -> None:
        # the attributes of XUIElement
        self.Frame, self.ResourceURL, self.Type = frame, url, _TOOLPANEL
        self.ctx, self.sidebar = ctx, sidebar
        self.locale = ui.ui_locale(ctx)
        self.shown: Panel | None = None
        self.width, self.height = DEFAULT_WIDTH, 200  # of the container; of the content
        self.view_height = self.height  # what the sidebar gives the container
        self.offset = 0  # how far the content is scrolled up
        self.controls: list[tuple[Any, Rect]] = []  # scrolled with the content
        self.fixed: list[Any] = []  # the scrollbar
        self.images = _extension_url(ctx)
        self.disposers: list[Any] = []

        smgr = ctx.ServiceManager
        self.model = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlContainerModel", ctx
        )
        self.container = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlContainer", ctx)
        self.container.setModel(self.model)
        toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        self.container.createPeer(toolkit, parent)
        self.container.setPosSize(0, 0, self.width, self.view_height, _POSSIZE)
        self.container.setVisible(True)

        resized = _Resized(self)
        self.container.addWindowListener(resized)
        self.disposers.append(lambda: self.container.removeWindowListener(resized))
        controller = frame.getController()
        selection = _Changed(self)
        controller.addSelectionChangeListener(selection)
        self.disposers.append(lambda: controller.removeSelectionChangeListener(selection))
        document = controller.getModel()
        document.addModifyListener(selection)
        self.disposers.append(lambda: document.removeModifyListener(selection))
        self.disposers.append(selection.stop)
        self.refresh()

    # XUIElement
    def getRealInterface(self) -> Any:
        return self.container

    # XToolPanel
    def getWindow(self) -> Any:
        return self.container

    def createAccessible(self, parent: Any) -> Any:
        return None

    # XSidebarPanel
    def getHeightRequest(self) -> Any:
        # Take what fits; the panel scrolls itself when the sidebar gives it less than the content.
        return LayoutSize(MIN_HEIGHT, -1, self.height)

    def dispose(self) -> None:
        for disposer in self.disposers:
            with contextlib.suppress(Exception):  # the frame may be gone already
                disposer()
        self.disposers.clear()

    # content

    def refresh(self) -> None:
        """Redraw if the selection or the chart changed since the last time."""
        panel = self._current()
        if panel != self.shown:
            self.shown = panel
            self.draw()

    def _current(self) -> Panel:
        controller = self.Frame.getController()
        doc = controller.getModel()
        group = commands.selected_chart(controller)
        state = None
        if group is not None:
            chart_id = store.resolve(doc, group)
            try:
                state = store.read_state(doc, chart_id) if chart_id else None
            except StateError:
                state = None
        return content(
            state,
            group is not None,
            self.locale,
            scheme.load(doc).name,
            bool(lo_elements.selected_elements(controller)),
            len(arrange.selected_shapes(controller)),
            agenda.stored(doc),
            agenda.role_of_page(controller.getCurrentPage()) is not None,
        )

    def draw(self) -> None:
        panel = self.shown
        if panel is None:
            return
        self._clear()
        content_height = self._fill(panel, self.width)
        if content_height > self.view_height:  # narrower, to make room for the scrollbar
            self._clear()
            content_height = self._fill(panel, self.width - SCROLLBAR_WIDTH)
        self.offset = max(min(self.offset, content_height - self.view_height), 0)
        self.scroll_to(self.offset)
        if content_height > self.view_height:
            self._add_scrollbar(content_height)
        if content_height != self.height:
            self.height = content_height
            if self.sidebar is not None:
                self.sidebar.requestLayout()

    def _clear(self) -> None:
        for control in [*self.fixed, *(control for control, _ in self.controls)]:
            self.container.removeControl(control)
            control.dispose()
        self.controls.clear()
        self.fixed.clear()

    def _fill(self, panel: Panel, width: int) -> int:
        """Create the controls for ``width``; the height of the content."""
        layout = _Layout(self, width)
        layout.heading("panel_insert")
        layout.icons(panel.insert)
        layout.heading("panel_chart")
        layout.label(panel.status, lines=2)
        for button in panel.edit:
            layout.button(button)
        if panel.link_status:
            layout.label(panel.link_status, lines=3)
        layout.flow(panel.link)
        for button in panel.options:
            layout.button(button)
        if panel.format:
            layout.heading("panel_format")
            for button in panel.format:
                layout.button(button)
        layout.heading("panel_elements")
        layout.icons(panel.elements)
        layout.heading("panel_arrange")
        layout.icons(panel.arrange)
        layout.heading("panel_agenda")
        layout.flow(panel.agenda)
        layout.heading("panel_annotations")
        layout.icons(panel.add)
        layout.heading("panel_list")
        if not panel.rows:
            layout.label(text("panel_no_annotations", self.locale))
        for row in panel.rows:
            layout.row(row.title, row.remove)
        layout.button(panel.remove_all)
        layout.heading("panel_document")
        layout.button(panel.update_all)
        layout.label(f"{text('panel_scheme', self.locale)}: {panel.scheme}")
        layout.flow(panel.schemes)
        layout.flow(panel.scheme_files)
        return layout.y + MARGIN

    def _add_scrollbar(self, content_height: int) -> None:
        bar = self._create("ScrollBar", Orientation=1, ScrollValueMax=content_height)
        model = bar.getModel()
        model.VisibleSize = self.view_height
        model.LineIncrement = LINE_STEP
        model.BlockIncrement = max(self.view_height - LINE_STEP, LINE_STEP)
        model.ScrollValue = self.offset
        self.container.addControl("scrollbar", bar)
        bar.setPosSize(self.width - SCROLLBAR_WIDTH, 0, SCROLLBAR_WIDTH, self.view_height, _POSSIZE)
        bar.addAdjustmentListener(_Scrolled(self))
        self.fixed.append(bar)

    def scroll_to(self, offset: int) -> None:
        self.offset = offset
        for control, (x, y, width, height) in self.controls:
            control.setPosSize(x, y - offset, width, height, _POSSIZE)

    def _create(self, kind: str, **props: Any) -> Any:
        smgr = self.ctx.ServiceManager
        model = smgr.createInstanceWithContext(f"com.sun.star.awt.UnoControl{kind}Model", self.ctx)
        for prop, value in props.items():
            setattr(model, prop, value)
        control = smgr.createInstanceWithContext(f"com.sun.star.awt.UnoControl{kind}", self.ctx)
        control.setModel(model)
        return control

    def add_control(self, kind: str, rect: Rect, **props: Any) -> Any:
        control = self._create(kind, **props)
        self.container.addControl(f"c{len(self.controls)}", control)
        x, y, width, height = rect
        control.setPosSize(x, y - self.offset, width, height, _POSSIZE)
        self.controls.append((control, rect))
        return control

    def dispatch(self, command: str) -> None:
        helper = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.DispatchHelper", self.ctx
        )
        helper.executeDispatch(self.Frame, command, "", 0, ())
        self.refresh()

    def image(self, icon: str) -> str:
        return f"{self.images}/images/{icon}_16.png" if icon and self.images else ""


class _Layout:
    """Stacks controls top to bottom over the panel's width."""

    def __init__(self, panel: _Panel, width: int) -> None:
        self.panel, self.width, self.y = panel, width, MARGIN

    def _rect(self, height: int, right: int = MARGIN) -> Rect:
        rect = (MARGIN, self.y, max(self.width - MARGIN - right, 20), height)
        self.y += height + GAP
        return rect

    def heading(self, key: str) -> None:
        self.y += GAP
        self.panel.add_control(
            "FixedText",
            self._rect(HEADING_HEIGHT),
            Label=text(key, self.panel.locale),
            FontWeight=150.0,
        )

    def label(self, label: str, lines: int = 1) -> None:
        self.panel.add_control(
            "FixedText", self._rect(LABEL_HEIGHT * lines), Label=label, MultiLine=lines > 1
        )

    def button(self, button: Button) -> None:
        control = self.panel.add_control(
            "Button",
            self._rect(BUTTON_HEIGHT),
            Label=button.title,
            Enabled=button.enabled,
            ImageURL=self.panel.image(button.icon),
            ImageAlign=0,  # left
        )
        control.addActionListener(_Click(self.panel, button.command))

    def icons(self, buttons: tuple[Button, ...]) -> None:
        """Icon-only buttons side by side, wrapping into rows; the title is the tooltip."""
        width = max(self.width - 2 * MARGIN, ICON_SIZE)
        columns = max((width + GAP) // (ICON_SIZE + GAP), 1)
        for start in range(0, len(buttons), columns):
            top = self.y
            for column, button in enumerate(buttons[start : start + columns]):
                image = self.panel.image(button.icon)
                control = self.panel.add_control(
                    "Button",
                    (MARGIN + column * (ICON_SIZE + GAP), top, ICON_SIZE, ICON_SIZE),
                    Label="" if image else button.title,
                    Enabled=button.enabled,
                    ImageURL=image,
                    ImageAlign=1,  # centre
                    HelpText=button.title,
                )
                control.addActionListener(_Click(self.panel, button.command))
            self.y = top + ICON_SIZE + GAP

    def flow(self, buttons: tuple[Button, ...], min_width: int = FLOW_MIN_WIDTH) -> None:
        """Text buttons side by side, as many per row as fit at ``min_width``."""
        width = max(self.width - 2 * MARGIN, min_width)
        columns = max((width + GAP) // (min_width + GAP), 1)
        cell = (width - (columns - 1) * GAP) // columns
        for start in range(0, len(buttons), columns):
            top = self.y
            for column, button in enumerate(buttons[start : start + columns]):
                control = self.panel.add_control(
                    "Button",
                    (MARGIN + column * (cell + GAP), top, cell, BUTTON_HEIGHT),
                    Label=button.title,
                    Enabled=button.enabled,
                    HelpText=button.title,
                )
                control.addActionListener(_Click(self.panel, button.command))
            self.y = top + BUTTON_HEIGHT + GAP

    def row(self, title: str, remove: str) -> None:
        """An annotation: its title, and a button that removes it."""
        top = self.y
        self.panel.add_control(
            "FixedText",
            self._rect(BUTTON_HEIGHT, right=MARGIN + REMOVE_WIDTH + GAP),
            Label=title,
            VerticalAlign=1,  # middle
        )
        control = self.panel.add_control(
            "Button",
            (self.width - MARGIN - REMOVE_WIDTH, top, REMOVE_WIDTH, BUTTON_HEIGHT),
            Label=REMOVE_LABEL,
        )
        control.addActionListener(_Click(self.panel, "org.librecharts:" + remove))


class _Click(unohelper.Base, XActionListener):
    def __init__(self, panel: _Panel, command: str) -> None:
        self.panel, self.command = panel, command

    def actionPerformed(self, event: Any) -> None:
        try:
            self.panel.dispatch(self.command)
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


class _Changed(unohelper.Base, XSelectionChangeListener, XModifyListener, XCallback):
    """Selection or document changed: show what the panel should show now.

    Modify events are coalesced into one asynchronous refresh on the main thread: redrawing a
    chart sets every property of every new shape, thousands of modify events, and refreshing on
    each made a date edit in a Gantt data sheet take half a minute.
    """

    def __init__(self, panel: _Panel) -> None:
        self.panel = panel
        self._pending = False
        self._stopped = False
        ctx = panel.ctx
        self._async = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )

    def stop(self) -> None:
        """No more refreshes, not even an already scheduled one: the panel is gone."""
        self._stopped = True

    def selectionChanged(self, event: Any) -> None:
        self._refresh()

    def modified(self, event: Any) -> None:
        if self._pending:
            return
        try:
            self._async.addCallback(self, None)  # None: the void "any", see lo/resize.py
            self._pending = True
        except Exception:
            traceback.print_exc()

    # XCallback
    def notify(self, data: Any) -> None:
        self._pending = False
        self._refresh()

    def _refresh(self) -> None:
        if self._stopped:
            return
        try:
            self.panel.refresh()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


class _Scrolled(unohelper.Base, XAdjustmentListener):
    def __init__(self, panel: _Panel) -> None:
        self.panel = panel

    def adjustmentValueChanged(self, event: Any) -> None:
        try:
            self.panel.scroll_to(int(event.Value))
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


class _Resized(unohelper.Base, XWindowListener):
    def __init__(self, panel: _Panel) -> None:
        self.panel = panel

    def windowResized(self, event: Any) -> None:
        try:
            if (event.Width, event.Height) != (self.panel.width, self.panel.view_height):
                self.panel.width, self.panel.view_height = event.Width, event.Height
                self.panel.draw()
        except Exception:
            traceback.print_exc()

    def windowMoved(self, event: Any) -> None:
        pass

    def windowShown(self, event: Any) -> None:
        pass

    def windowHidden(self, event: Any) -> None:
        pass

    def disposing(self, event: Any) -> None:
        pass


def _extension_url(ctx: Any) -> str:
    """The extension's folder as a URL, or empty if it cannot be found."""
    try:
        provider = ctx.getValueByName(
            "/singletons/com.sun.star.deployment.PackageInformationProvider"
        )
        return str(provider.getPackageLocation(_EXTENSION_ID)).rstrip("/")
    except Exception:
        return ""

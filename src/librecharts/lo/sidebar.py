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
from com.sun.star.awt import XActionListener, XWindowListener
from com.sun.star.ui import LayoutSize, XSidebarPanel, XToolPanel, XUIElement
from com.sun.star.util import XModifyListener
from com.sun.star.view import XSelectionChangeListener

from librecharts.core.messages import text
from librecharts.core.panel import Button, Panel, content
from librecharts.core.state_io import StateError
from librecharts.lo import commands, scheme, store, ui

_TOOLPANEL = 7  # com.sun.star.ui.UIElementType.TOOLPANEL
_POSSIZE = 15  # com.sun.star.awt.PosSize.POSSIZE
_EXTENSION_ID = "org.librecharts.extension"

MARGIN, GAP, BUTTON_HEIGHT, LABEL_HEIGHT, HEADING_HEIGHT = 8, 4, 26, 18, 20
ICON_SIZE, FLOW_MIN_WIDTH = 30, 100
REMOVE_WIDTH = 24
REMOVE_LABEL = chr(0xD7)  # multiplication sign
DEFAULT_WIDTH = 240

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
        self.width, self.height = DEFAULT_WIDTH, 200
        self.controls: list[Any] = []
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
        self.container.setPosSize(0, 0, self.width, self.height, _POSSIZE)
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
        return LayoutSize(self.height, self.height, self.height)

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
        return content(state, group is not None, self.locale, scheme.load(doc).name)

    def draw(self) -> None:
        panel = self.shown
        if panel is None:
            return
        for control in self.controls:
            self.container.removeControl(control)
            control.dispose()
        self.controls.clear()
        layout = _Layout(self)
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
        self.height = layout.y + MARGIN
        self.container.setPosSize(0, 0, self.width, self.height, _POSSIZE)
        if self.sidebar is not None:
            self.sidebar.requestLayout()

    def add_control(self, kind: str, rect: Rect, **props: Any) -> Any:
        smgr = self.ctx.ServiceManager
        model = smgr.createInstanceWithContext(f"com.sun.star.awt.UnoControl{kind}Model", self.ctx)
        for prop, value in props.items():
            setattr(model, prop, value)
        control = smgr.createInstanceWithContext(f"com.sun.star.awt.UnoControl{kind}", self.ctx)
        control.setModel(model)
        self.container.addControl(f"c{len(self.controls)}", control)
        control.setPosSize(*rect, _POSSIZE)
        self.controls.append(control)
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

    def __init__(self, panel: _Panel) -> None:
        self.panel, self.y = panel, MARGIN

    def _rect(self, height: int, right: int = MARGIN) -> Rect:
        rect = (MARGIN, self.y, max(self.panel.width - MARGIN - right, 20), height)
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
        width = max(self.panel.width - 2 * MARGIN, ICON_SIZE)
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
        width = max(self.panel.width - 2 * MARGIN, min_width)
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
            (self.panel.width - MARGIN - REMOVE_WIDTH, top, REMOVE_WIDTH, BUTTON_HEIGHT),
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


class _Changed(unohelper.Base, XSelectionChangeListener, XModifyListener):
    """Selection or document changed: show what the panel should show now."""

    def __init__(self, panel: _Panel) -> None:
        self.panel = panel

    def selectionChanged(self, event: Any) -> None:
        self._refresh()

    def modified(self, event: Any) -> None:
        self._refresh()

    def _refresh(self) -> None:
        try:
            self.panel.refresh()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


class _Resized(unohelper.Base, XWindowListener):
    def __init__(self, panel: _Panel) -> None:
        self.panel = panel

    def windowResized(self, event: Any) -> None:
        try:
            if event.Width != self.panel.width:  # not the resize draw() itself causes
                self.panel.width = event.Width
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

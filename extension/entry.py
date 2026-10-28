# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""LibreOffice entry point: a protocol handler behind the "LibreCharts" menu.

Runs inside LibreOffice's bundled Python. Keep it thin: logic belongs in librecharts.core.
"""

import os
import sys

# Make the bundled librecharts package importable from inside the .oxt.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unohelper
from com.sun.star.awt import Point, Size
from com.sun.star.frame import XDispatch, XDispatchProvider
from com.sun.star.lang import XInitialization, XServiceInfo

IMPLEMENTATION_NAME = "org.librecharts.ProtocolHandler"
SERVICE_NAME = "com.sun.star.frame.ProtocolHandler"
PROTOCOL = "org.librecharts:"


class ProtocolHandler(unohelper.Base, XInitialization, XDispatchProvider, XDispatch, XServiceInfo):
    def __init__(self, ctx):
        self.ctx = ctx
        self.frame = None

    # XInitialization
    def initialize(self, args):
        if args:
            self.frame = args[0]

    # XDispatchProvider
    def queryDispatch(self, url, target_frame_name, search_flags):
        return self if url.Protocol == PROTOCOL else None

    def queryDispatches(self, requests):
        return [self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags) for r in requests]

    # XDispatch
    def dispatch(self, url, arguments):
        if url.Path == "InsertChart":
            self._insert_placeholder()

    def addStatusListener(self, control, url):
        pass

    def removeStatusListener(self, control, url):
        pass

    # XServiceInfo
    def getImplementationName(self):
        return IMPLEMENTATION_NAME

    def supportsService(self, name):
        return name == SERVICE_NAME

    def getSupportedServiceNames(self):
        return (SERVICE_NAME,)

    def _insert_placeholder(self):
        if self.frame is None:
            return
        controller = self.frame.getController()
        model = controller.getModel()
        shape = model.createInstance("com.sun.star.drawing.RectangleShape")
        shape.Size = Size(8000, 5000)
        shape.Position = Point(2000, 2000)
        controller.getCurrentPage().add(shape)
        shape.String = "LibreCharts placeholder"  # text can only be set once the shape is on a page


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(ProtocolHandler, IMPLEMENTATION_NAME, (SERVICE_NAME,))

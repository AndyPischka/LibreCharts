# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""LibreOffice entry point: a protocol handler behind the "LibreCharts" menu.

Runs inside LibreOffice's bundled Python. Keep it thin: logic belongs in librecharts.core.
"""

import os
import sys
import traceback

# Make the bundled librecharts package importable from inside the .oxt.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unohelper
from com.sun.star.frame import XDispatch, XDispatchProvider
from com.sun.star.lang import XInitialization, XServiceInfo
from com.sun.star.task import XJob

from librecharts.lo import commands, resize

IMPLEMENTATION_NAME = "org.librecharts.ProtocolHandler"
SERVICE_NAME = "com.sun.star.frame.ProtocolHandler"
PROTOCOL = "org.librecharts:"
JOB_IMPLEMENTATION_NAME = "org.librecharts.DocumentJob"
JOB_SERVICE_NAME = "com.sun.star.task.Job"
PRESENTATION_SERVICE = "com.sun.star.presentation.PresentationDocument"


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
        if self.frame is None:
            return
        try:
            if url.Path == "InsertColumnChart":
                commands.insert_column_chart(self.frame)
            elif url.Path == "InsertBarChart":
                commands.insert_bar_chart(self.frame)
            elif url.Path == "InsertWaterfallChart":
                commands.insert_waterfall_chart(self.frame)
            elif url.Path == "EditData":
                commands.edit_data(self.ctx, self.frame)
        except Exception:
            # An exception escaping a Python dispatch can take LibreOffice down with it.
            traceback.print_exc()

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


class DocumentJob(unohelper.Base, XJob, XServiceInfo):
    """Runs for every opened document (Jobs.xcu): watches presentations for resized charts.

    LibreOffice runs document-event jobs for visible documents only; hidden ones are not watched.
    """

    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, args):
        try:
            environment = next((a.Value for a in args if a.Name == "Environment"), ())
            model = next((a.Value for a in environment if a.Name == "Model"), None)
            if model is not None and model.supportsService(PRESENTATION_SERVICE):
                resize.watch(model)
        except Exception:
            traceback.print_exc()
        return None

    def getImplementationName(self):
        return JOB_IMPLEMENTATION_NAME

    def supportsService(self, name):
        return name == JOB_SERVICE_NAME

    def getSupportedServiceNames(self):
        return (JOB_SERVICE_NAME,)


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(ProtocolHandler, IMPLEMENTATION_NAME, (SERVICE_NAME,))
g_ImplementationHelper.addImplementation(DocumentJob, JOB_IMPLEMENTATION_NAME, (JOB_SERVICE_NAME,))

import win32serviceutil
import win32service
import win32event
import servicemanager

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from manager.openportmanager import OpenportManagerService


class OpenportManagerWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OpenportManagerService"
    _svc_display_name_ = "Openport Service"
    _svc_description_ = "This service restarts the openport shares when the computer starts up."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.stopped = False

        self.openport_manager_service = OpenportManagerService()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.openport_manager_service.stop()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.openport_manager_service.start()


if __name__ == '__main__':
    #managerservice = OpenportManagerService()
    #managerservice.start()


    win32serviceutil.HandleCommandLine(OpenportManagerWindowsService)
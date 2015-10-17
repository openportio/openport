import os
import sys
import win32serviceutil
import win32service
import win32event
import win32evtlogutil
import servicemanager
import winerror

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.osinteraction import getInstance


class OpenportManagerWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OpenportService"
    _svc_display_name_ = "Openport Service"
    _svc_description_ = "This service restarts the openport shares when the computer starts up."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.stopped = False

        self.os_interaction = getInstance()
        openport_exec = self.os_interaction.get_openport_exec()
        openport_exec.extend(['--restart-shares'])
        self.os_interaction.start_process(openport_exec)
        self.stopped = True

    def SvcStop(self):
#        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32evtlogutil.ReportEvent(self._svc_name_, servicemanager.PYS_SERVICE_STOPPING, 0,
                                    servicemanager.EVENTLOG_INFORMATION_TYPE, (self._svc_name_, ''))
        win32event.SetEvent(self.hWaitStop)

        # No service to stop

        win32evtlogutil.ReportEvent(self._svc_name_, servicemanager.PYS_SERVICE_STOPPED, 0,
                                    servicemanager.EVENTLOG_INFORMATION_TYPE, (self._svc_name_, ''))

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        #self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        #self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        #
        win32evtlogutil.ReportEvent(self._svc_name_, servicemanager.PYS_SERVICE_STARTED, 0,
                                    servicemanager.EVENTLOG_INFORMATION_TYPE, (self._svc_name_, ''))

        # No service to start

        win32evtlogutil.ReportEvent(self._svc_name_, servicemanager.PYS_SERVICE_STOPPED, 0,
                                    servicemanager.EVENTLOG_INFORMATION_TYPE, (self._svc_name_, ''))

if __name__ == '__main__':
    #managerservice = OpenportManagerService()
    #managerservice.start()

    if len(sys.argv) == 1:
        try:
            evtsrc_dll = os.path.abspath(servicemanager.__file__)
            servicemanager.PrepareToHostSingle(OpenportManagerWindowsService)
            servicemanager.Initialize(OpenportManagerWindowsService._svc_name_, evtsrc_dll)
            servicemanager.StartServiceCtrlDispatcher()
        except win32service.error as details:
            if details[0] == winerror.ERROR_FAILED_SERVICE_CONTROLLER_CONNECT:
                win32serviceutil.usage()
    else:
        win32serviceutil.HandleCommandLine(OpenportManagerWindowsService)

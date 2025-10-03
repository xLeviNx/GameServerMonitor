import asyncio
import os
import sys
import threading

import servicemanager
import win32service

if sys.platform == 'win32' and (3, 8, 0) <= sys.version_info < (3, 9, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
venv = os.getenv('VIRTUAL_ENV', os.path.join(path, 'venv'))

lib_path = os.path.join(venv, 'Lib', 'site-packages')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)
else:
    # Fallback: try lowercase 'lib' for edge cases
    lib_path_lower = os.path.join(venv, 'lib', 'site-packages')
    if os.path.exists(lib_path_lower):
        sys.path.insert(0, lib_path_lower)

import win32serviceutil

os.chdir(path)

from discordgsm.main import client


class WindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = os.getenv('SERVICE_NAME', 'DgsmSvc')
    _svc_display_name_ = os.getenv('SERVICE_DISPLAY_NAME', 'DiscordGSM Service')
    _svc_description_ = os.getenv('SERVICE_DESCRIPTION', 'A discord bot that monitors your game server and tracks the live data of your game servers.')

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = threading.Event()
        self.is_running = False

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop_event.set()
        
        if self.is_running:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(client.close(), loop)
                else:
                    asyncio.run(client.close())
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error closing client: {str(e)}")
                pass

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        self.is_running = True
        try:
            client.run(os.environ['APP_TOKEN'])
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {str(e)}")
            raise
        finally:
            self.is_running = False


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(WindowsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(WindowsService)

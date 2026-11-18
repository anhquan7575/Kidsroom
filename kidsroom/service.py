"""Windows SCM entry point. This module must remain importable without Qt."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import sys

import pywintypes
import servicemanager
import win32con
import win32event
import win32process
import win32profile
import win32security
import win32service
import win32serviceutil
import win32ts
import winreg


SERVICE_NAME = "Kidsroom"
REGISTRY_PATH = rf"SYSTEM\CurrentControlSet\Services\{SERVICE_NAME}\Parameters"


def agent_executable() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).with_name("Kidsroom.exe")
    return Path(sys.executable).with_name("pythonw.exe")


def read_configuration() -> tuple[str, str]:
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGISTRY_PATH) as key:
        sid = winreg.QueryValueEx(key, "ChildSid")[0]
        python = winreg.QueryValueEx(key, "AgentPython")[0]
    if not Path(python).is_file():
        raise FileNotFoundError(f"Agent interpreter not found: {python}")
    return sid, python


def configure_account(username: str):
    if not username.strip():
        raise ValueError("Specify a child Windows account, e.g. COMPUTER\\child.")
    sid, _, account_type = win32security.LookupAccountName(None, username)
    if account_type != win32security.SidTypeUser:
        raise ValueError("The configured principal must be a Windows user account.")
    pythonw = agent_executable()
    if not pythonw.is_file():
        raise FileNotFoundError(pythonw)
    # This HKLM configuration is writable only by administrators, never by the GUI.
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, REGISTRY_PATH, 0,
                           winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "ChildSid", 0, winreg.REG_SZ,
                         win32security.ConvertSidToStringSid(sid))
        winreg.SetValueEx(key, "AgentPython", 0, winreg.REG_SZ, str(pythonw))
    print(f"Configured child account: {username}")


def launch_agent(session_id: int, expected_sid: str, python: str):
    token = win32ts.WTSQueryUserToken(session_id)
    try:
        sid, _ = win32security.GetTokenInformation(token, win32security.TokenUser)
        if win32security.ConvertSidToStringSid(sid) != expected_sid:
            return None
        startup = win32process.STARTUPINFO()
        startup.lpDesktop = "winsta0\\default"
        environment = win32profile.CreateEnvironmentBlock(token, False)
        arguments = [python]
        if Path(python).name.casefold() != "kidsroom.exe":
            arguments.extend(["-I", "-m", "kidsroom"])
        command = subprocess.list2cmdline(arguments)
        process, thread, pid, _ = win32process.CreateProcessAsUser(
            token, python, command, None, None, False,
            win32con.CREATE_UNICODE_ENVIRONMENT,
            environment, str(Path(python).parent), startup,
        )
        thread.Close()
        servicemanager.LogInfoMsg(f"Kidsroom: started GUI pid={pid}, session={session_id}")
        return process
    finally:
        token.Close()


class KidsroomService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = "Kidsroom Learning Companion"
    _svc_description_ = "Starts the learning screen in the configured child account; no UI in session 0."
    _exe_name_ = sys.executable
    _exe_args_ = "host" if getattr(sys, "frozen", False) else "-I -m kidsroom.service host"

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        processes = {}
        previous_error = None
        try:
            child_sid, python = read_configuration()
            servicemanager.LogInfoMsg("Kidsroom service started.")
            while win32event.WaitForSingleObject(self.stop_event, 2000) == win32event.WAIT_TIMEOUT:
                for session_id, process in list(processes.items()):
                    if win32event.WaitForSingleObject(process, 0) != win32event.WAIT_TIMEOUT:
                        process.Close()
                        del processes[session_id]
                try:
                    session = win32ts.WTSGetActiveConsoleSessionId()
                    if session != 0xFFFFFFFF and session not in processes:
                        process = launch_agent(session, child_sid, python)
                        if process is not None:
                            processes[session] = process
                    previous_error = None
                except pywintypes.error as error:
                    message = str(error)
                    if message != previous_error:
                        servicemanager.LogErrorMsg(f"Kidsroom session launch: {message}")
                    previous_error = message
        except Exception:
            servicemanager.LogErrorMsg("Kidsroom service failed:\n" + logging.Formatter().formatException(
                sys.exc_info()
            ))
            raise
        finally:
            for process in processes.values():
                process.Close()
            servicemanager.LogInfoMsg("Kidsroom service stopped; GUI processes were not terminated.")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "host":
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(KidsroomService)
        servicemanager.StartServiceCtrlDispatcher()
    elif len(sys.argv) >= 2 and sys.argv[1] == "configure":
        if len(sys.argv) != 3:
            raise SystemExit('Usage: python -m kidsroom.service configure "COMPUTER\\child"')
        configure_account(sys.argv[2])
    else:
        raise SystemExit(win32serviceutil.HandleCommandLine(
            KidsroomService, serviceClassString="kidsroom.service.KidsroomService"
        ))


if __name__ == "__main__":
    main()

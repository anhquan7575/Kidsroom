from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import win32event
import win32security

from kidsroom import service


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch.object(service.win32ts, "WTSQueryUserToken"),
            patch.object(service.win32security, "GetTokenInformation"),
            patch.object(service.win32profile, "CreateEnvironmentBlock"),
            patch.object(service.win32process, "CreateProcessAsUser"),
            patch.object(service.servicemanager, "LogInfoMsg"),
        ]
        self.token, self.info, self.env, self.create, self.log = [p.start() for p in self.patches]
        self.sid = win32security.ConvertStringSidToSid("S-1-5-21-1-2-3-1001")
        self.info.return_value = (self.sid, 0)

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def test_never_launches_for_different_windows_account(self):
        self.assertIsNone(service.launch_agent(1, "S-1-5-21-1-2-3-1002", "pythonw.exe"))
        self.create.assert_not_called()
        self.token.return_value.Close.assert_called_once()

    def test_launches_in_interactive_desktop_using_child_token(self):
        process, thread = MagicMock(), MagicMock()
        self.create.return_value = process, thread, 123, 456
        python = r"C:\Program Files\Kidsroom\runtime\Scripts\pythonw.exe"
        result = service.launch_agent(1, "S-1-5-21-1-2-3-1001", python)
        self.assertIs(result, process)
        args = self.create.call_args.args
        self.assertEqual(args[0], self.token.return_value)
        self.assertEqual(args[1], python)
        self.assertIn("-I -m kidsroom", args[2])
        self.assertEqual(args[-1].lpDesktop, "winsta0\\default")
        thread.Close.assert_called_once()
        self.token.return_value.Close.assert_called_once()

    def test_token_closed_when_process_creation_fails(self):
        self.create.side_effect = OSError("test launch error")
        with self.assertRaises(OSError):
            service.launch_agent(1, "S-1-5-21-1-2-3-1001", "pythonw.exe")
        self.token.return_value.Close.assert_called_once()

    def test_bundled_agent_launches_exe_without_python_module_arguments(self):
        executable = r"C:\Program Files\Kidsroom\Kidsroom.exe"
        self.create.return_value = MagicMock(), MagicMock(), 123, 456
        service.launch_agent(1, "S-1-5-21-1-2-3-1001", executable)
        args = self.create.call_args.args
        self.assertEqual(args[2], f'"{executable}"')
        self.assertEqual(args[-2], str(Path(executable).parent))

    def test_frozen_configuration_records_gui_not_service_executable(self):
        self.info.return_value = (self.sid, 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gui = root / "Kidsroom.exe"
            gui.touch()
            with patch.object(service.sys, "frozen", True, create=True), \
                    patch.object(service.sys, "executable", str(root / "KidsroomService.exe")), \
                    patch.object(service.win32security, "LookupAccountName",
                                 return_value=(self.sid, "COMPUTER", win32security.SidTypeUser)), \
                    patch.object(service.winreg, "CreateKeyEx"), \
                    patch.object(service.winreg, "SetValueEx") as write, \
                    patch("builtins.print"):
                service.configure_account("COMPUTER\\child")
            self.assertEqual(write.call_args_list[-1].args[-1], str(gui))

    def test_service_relaunches_exited_gui_on_next_poll(self):
        instance = object.__new__(service.KidsroomService)
        instance.stop_event = object()
        first, second = MagicMock(), MagicMock()
        polls = 0

        def wait(handle, timeout):
            nonlocal polls
            if handle is instance.stop_event:
                polls += 1
                return win32event.WAIT_TIMEOUT if polls <= 2 else win32event.WAIT_OBJECT_0
            self.assertIs(handle, first)
            return win32event.WAIT_OBJECT_0

        with patch.object(service, "read_configuration", return_value=("child-sid", "pythonw.exe")), \
                patch.object(service.win32ts, "WTSGetActiveConsoleSessionId", return_value=1), \
                patch.object(service, "launch_agent", side_effect=[first, second]) as launch, \
                patch.object(service.win32event, "WaitForSingleObject", side_effect=wait):
            instance.SvcDoRun()
        self.assertEqual(launch.call_count, 2)
        first.Close.assert_called_once()
        second.Close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

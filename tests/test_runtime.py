import unittest
from unittest.mock import MagicMock, call, patch

from kidsroom import runtime


class FrozenRuntimeTests(unittest.TestCase):
    def test_bundled_dll_directory_is_restored_even_when_external_launch_fails(self):
        kernel = MagicMock()
        original = r"C:\Program Files\Kidsroom\_internal"

        def get_directory(size, buffer):
            if not size:
                return len(original) + 1
            buffer.value = original
            return len(original)

        kernel.GetDllDirectoryW.side_effect = get_directory
        kernel.SetDllDirectoryW.return_value = 1
        with patch.object(runtime.sys, "frozen", True, create=True), \
                patch.object(runtime.sys, "_MEIPASS", original, create=True), \
                patch.object(runtime.ctypes, "WinDLL", return_value=kernel):
            with self.assertRaisesRegex(OSError, "launch failed"):
                with runtime.external_dll_search():
                    raise OSError("launch failed")
        self.assertEqual(kernel.SetDllDirectoryW.call_args_list, [call(None), call(original)])

    def test_external_app_does_not_inherit_bundled_qt_paths(self):
        kernel = MagicMock()
        kernel.GetDllDirectoryW.return_value = 0
        kernel.SetDllDirectoryW.return_value = 1
        bundle = r"C:\Program Files\Kidsroom\_internal"
        environment = {
            "PATH": bundle + os.pathsep + r"C:\Windows\System32",
            "QT_PLUGIN_PATH": bundle + r"\PySide6\plugins",
            "QML2_IMPORT_PATH": bundle + r"\PySide6\qml",
            "QT_QPA_PLATFORM_PLUGIN_PATH": r"C:\OtherApp\plugins",
        }
        with patch.object(runtime.sys, "frozen", True, create=True), \
                patch.object(runtime.sys, "_MEIPASS", bundle, create=True), \
                patch.object(runtime.ctypes, "WinDLL", return_value=kernel), \
                patch.dict(os.environ, environment, clear=True):
            with runtime.external_dll_search() as cleaned:
                self.assertEqual(cleaned["PATH"], r"C:\Windows\System32")
                self.assertNotIn("QT_PLUGIN_PATH", cleaned)
                self.assertNotIn("QML2_IMPORT_PATH", cleaned)
                self.assertEqual(cleaned["QT_QPA_PLATFORM_PLUGIN_PATH"], r"C:\OtherApp\plugins")
            self.assertEqual(os.environ["QT_PLUGIN_PATH"], environment["QT_PLUGIN_PATH"])

    def test_failure_to_reset_dll_search_is_explicit(self):
        kernel = MagicMock()
        kernel.GetDllDirectoryW.return_value = 0
        kernel.SetDllDirectoryW.return_value = 0
        with patch.object(runtime.sys, "frozen", True, create=True), \
                patch.object(runtime.ctypes, "WinDLL", return_value=kernel):
            with self.assertRaises(OSError):
                with runtime.external_dll_search():
                    self.fail("External launch must not run after reset failure.")


if __name__ == "__main__":
    unittest.main()
import os

from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import sys


@contextmanager
def external_dll_search():
    if not getattr(sys, "frozen", False) or sys.platform != "win32":
        yield
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetDllDirectoryW.argtypes = [ctypes.c_ulong, ctypes.c_wchar_p]
    kernel.GetDllDirectoryW.restype = ctypes.c_ulong
    kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
    kernel.SetDllDirectoryW.restype = ctypes.c_int
    size = kernel.GetDllDirectoryW(0, None)
    directory = ctypes.create_unicode_buffer(size + 1)
    if size and not kernel.GetDllDirectoryW(len(directory), directory):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.SetDllDirectoryW(None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        environment = os.environ.copy()
        bundle = Path(sys._MEIPASS).resolve()
        for name in ("PATH", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
                     "QML_IMPORT_PATH", "QML2_IMPORT_PATH", "QT_QPA_FONTDIR"):
            if name not in environment:
                continue
            paths = environment[name].split(os.pathsep)
            kept = [path for path in paths if not path or not Path(path).resolve().is_relative_to(bundle)]
            if kept:
                environment[name] = os.pathsep.join(kept)
            else:
                del environment[name]
        yield environment
    finally:
        if not kernel.SetDllDirectoryW(directory.value or None):
            raise ctypes.WinError(ctypes.get_last_error())
